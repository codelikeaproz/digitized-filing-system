import os
import re
import sqlite3
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.utils import timezone

from documents.models import Document
from documents.services import build_folder_path_map
from orgunits.models import OrgUnit


INVALID_ARCHIVE_SEGMENT_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def backup_timestamp():
    return timezone.localtime().strftime("%Y%m%d_%H%M%S")


def database_backup_filename():
    return f"DFS_DATABASE_{backup_timestamp()}.sql"


def media_backup_filename():
    return f"DFS_MEDIA_{backup_timestamp()}.zip"


def _backup_temp_dir():
    temp_dir = Path(getattr(settings, "BACKUP_TEMP_DIR", settings.BASE_DIR / "tmp" / "backups"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _run_command(command, *, output_path):
    env = os.environ.copy()
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "Backup command failed.")

    output_path.write_bytes(result.stdout)


def _safe_archive_segment(value, fallback):
    segment = INVALID_ARCHIVE_SEGMENT_CHARS.sub("_", (value or "").strip()).rstrip(". ")
    return segment if segment not in {"", ".", ".."} else fallback


def _org_unit_path_map():
    rows = {
        row["id"]: row
        for row in OrgUnit.objects.values("id", "name", "parent_id")
    }

    paths = {}
    for org_unit_id in rows:
        parts = []
        current_id = org_unit_id
        visited = set()
        while current_id and current_id in rows and current_id not in visited:
            visited.add(current_id)
            row = rows[current_id]
            parts.append(_safe_archive_segment(row["name"], "Unnamed Office"))
            current_id = row["parent_id"]
        paths[org_unit_id] = list(reversed(parts))
    return paths


def _unique_archive_name(archive_name, document_id, used_names):
    normalized = archive_name.casefold()
    if normalized not in used_names:
        used_names.add(normalized)
        return archive_name

    path = PurePosixPath(archive_name)
    candidate = path.with_name(f"{path.stem}__{document_id}{path.suffix}").as_posix()
    used_names.add(candidate.casefold())
    return candidate


def create_database_backup():
    filename = database_backup_filename()
    output_path = _backup_temp_dir() / filename
    db_settings = settings.DATABASES["default"]

    if settings.DB_ENGINE == "mysql":
        command = [
            "mysqldump",
            f"--host={db_settings.get('HOST', 'localhost')}",
            f"--port={str(db_settings.get('PORT', '3306'))}",
            f"--user={db_settings.get('USER', '')}",
        ]
        password = db_settings.get("PASSWORD")
        if password:
            command.append(f"--password={password}")
        command.extend(
            [
                "--single-transaction",
                "--routines",
                "--triggers",
                "--skip-ssl",
                db_settings.get("NAME", ""),
            ]
        )
        _run_command(command, output_path=output_path)
    else:
        sqlite_path = Path(db_settings["NAME"])
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found at {sqlite_path}")

        with sqlite3.connect(sqlite_path) as connection, output_path.open("w", encoding="utf-8") as dump_file:
            for line in connection.iterdump():
                dump_file.write(f"{line}\n")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Database backup file was not created.")

    return output_path, filename


def create_media_backup():
    filename = media_backup_filename()
    output_path = _backup_temp_dir() / filename
    media_root = Path(settings.MEDIA_ROOT)
    media_root.mkdir(parents=True, exist_ok=True)

    documents = list(
        Document.objects.exclude(file="").values("id", "file", "folder_id", "folder__org_unit_id")
    )
    folder_paths = build_folder_path_map(row["folder_id"] for row in documents)
    org_unit_paths = _org_unit_path_map()
    documents_by_file = {str(row["file"]).replace("\\", "/"): row for row in documents}
    used_names = set()

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(media_root):
            for file_name in files:
                absolute_path = Path(root) / file_name
                relative_path = absolute_path.relative_to(media_root)
                stored_name = relative_path.as_posix()
                document = documents_by_file.get(stored_name)

                if document:
                    org_parts = org_unit_paths.get(document["folder__org_unit_id"], ["Unassigned Office"])
                    folder_parts = [
                        _safe_archive_segment(part, "Unnamed Folder")
                        for part in folder_paths.get(document["folder_id"], "").split(" > ")
                        if part
                    ]
                    archive_name = PurePosixPath(
                        "documents", *org_parts, *folder_parts, relative_path.name
                    ).as_posix()
                    archive_name = _unique_archive_name(archive_name, document["id"], used_names)
                elif relative_path.parts and relative_path.parts[0] == "documents":
                    archive_name = PurePosixPath("_unlinked", *relative_path.parts).as_posix()
                else:
                    archive_name = stored_name

                archive.write(absolute_path, arcname=archive_name)

    return output_path, filename


def remove_backup_file(path):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass

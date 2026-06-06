import os
import sqlite3
import subprocess
import zipfile
from pathlib import Path

from django.conf import settings
from django.utils import timezone


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

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(media_root):
            for file_name in files:
                absolute_path = Path(root) / file_name
                relative_path = absolute_path.relative_to(media_root)
                archive.write(absolute_path, arcname=str(relative_path).replace("\\", "/"))

    return output_path, filename


def remove_backup_file(path):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass

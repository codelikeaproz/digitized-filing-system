import hashlib
import json
import logging
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


DEFAULT_CONFIG = {
    "base_url": "http://127.0.0.1:8000",
    "api_token": "change-me-local-scanner-token",
    "station_id": "SCANNER-PC-01",
    "station_name": "Scanner PC 01",
    "incoming_dir": r"C:\DFS_Scanner\Incoming",
    "uploaded_dir": r"C:\DFS_Scanner\Uploaded",
    "failed_dir": r"C:\DFS_Scanner\Failed",
    "unmatched_dir": r"C:\DFS_Scanner\Unmatched",
    "poll_seconds": 3,
    "stable_seconds": 2,
    "max_upload_retries": 3,
}


def load_config():
    config_path = Path(__file__).with_name("scanner_bridge.config.json")
    if not config_path.exists():
        return DEFAULT_CONFIG
    with config_path.open("r", encoding="utf-8") as config_file:
        return {**DEFAULT_CONFIG, **json.load(config_file)}


class ScannerBridge:
    def __init__(self, config):
        self.config = config
        self.incoming_dir = Path(config["incoming_dir"])
        self.uploaded_dir = Path(config["uploaded_dir"])
        self.failed_dir = Path(config["failed_dir"])
        self.unmatched_dir = Path(config["unmatched_dir"])
        for directory in [self.incoming_dir, self.uploaded_dir, self.failed_dir, self.unmatched_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def run(self):
        logging.info("Scanner bridge started for %s", self.config["station_id"])
        print(f"Scanner Bridge running for {self.config['station_id']}")
        print(f"Watching folder: {self.incoming_dir}")
        print("Keep this window open. Press Ctrl+C to stop.")
        while True:
            self.send_heartbeat("CONNECTED")
            self.process_existing_files()
            time.sleep(self.config["poll_seconds"])

    def headers(self, extra=None):
        headers = {
            "X-Scanner-Token": self.config["api_token"],
            "X-Scanner-Station": self.config["station_id"],
        }
        if extra:
            headers.update(extra)
        return headers

    def request_json(self, method, endpoint, payload=None, query=None):
        url = f"{self.config['base_url']}{endpoint}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        data = None
        headers = self.headers()
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    def send_heartbeat(self, status, error_message=""):
        try:
            self.request_json(
                "POST",
                "/api/scanner/stations/heartbeat",
                {
                    "station_id": self.config["station_id"],
                    "name": self.config["station_name"],
                    "status": status,
                    "watched_folder": str(self.incoming_dir),
                    "error_message": error_message,
                },
            )
            print(f"Heartbeat OK: {self.config['station_id']} -> {self.config['base_url']}")
        except Exception as exc:
            logging.warning("Heartbeat failed: %s", exc)
            print(f"Heartbeat failed: {exc}")

    def process_existing_files(self):
        for path in sorted(self.incoming_dir.glob("*.pdf"), key=lambda item: item.stat().st_mtime):
            self.process_pdf(path)

    def process_pdf(self, path):
        if not self.wait_until_file_stable(path):
            return
        job = self.get_pending_job()
        if not job:
            logging.warning("No pending scan job. Moving to unmatched: %s", path)
            print(f"No pending scan job. Moving {path.name} to Unmatched.")
            self.move_file(path, self.unmatched_dir)
            return
        try:
            self.upload_file(job["id"], path)
            self.move_file(path, self.uploaded_dir)
            logging.info("Uploaded %s for scan job %s", path.name, job["id"])
            print(f"Uploaded {path.name} for scan job #{job['id']}")
        except Exception as exc:
            logging.exception("Upload failed for %s", path)
            print(f"Upload failed for {path.name}: {exc}")
            self.report_job_failure(job["id"], str(exc))
            self.move_file(path, self.failed_dir)

    def get_pending_job(self):
        try:
            return self.request_json(
                "GET",
                "/api/scan-jobs/pending",
                query={"station_id": self.config["station_id"]},
            ) or None
        except Exception as exc:
            logging.warning("Pending job check failed: %s", exc)
            return None

    def upload_file(self, job_id, path):
        file_hash = self.sha256(path)
        for attempt in range(1, self.config["max_upload_retries"] + 1):
            try:
                self.multipart_upload(
                    f"/api/scan-jobs/{job_id}/upload",
                    fields={
                        "station_id": self.config["station_id"],
                        "original_filename": path.name,
                        "sha256": file_hash,
                    },
                    file_field="file",
                    file_path=path,
                )
                return
            except Exception:
                if attempt == self.config["max_upload_retries"]:
                    raise
                time.sleep(2 * attempt)

    def multipart_upload(self, endpoint, fields, file_field, file_path):
        boundary = f"----DFSBridge{uuid.uuid4().hex}"
        body = bytearray()
        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'
                "Content-Type: application/pdf\r\n\r\n"
            ).encode("utf-8")
        )
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        request = urllib.request.Request(
            f"{self.config['base_url']}{endpoint}",
            data=bytes(body),
            headers=self.headers({"Content-Type": f"multipart/form-data; boundary={boundary}"}),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(exc.read().decode("utf-8", errors="replace")) from exc

    def report_job_failure(self, job_id, message):
        try:
            self.request_json("PATCH", f"/api/scan-jobs/{job_id}/fail", {"error_message": message[:1000]})
        except Exception:
            logging.exception("Failed to report scan job failure")

    def wait_until_file_stable(self, path):
        last_size = -1
        stable_since = None
        while True:
            if not path.exists():
                return False
            current_size = path.stat().st_size
            if current_size == last_size and current_size > 0:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since >= self.config["stable_seconds"]:
                    return True
            else:
                last_size = current_size
                stable_since = None
            time.sleep(0.5)

    def move_file(self, source, target_dir):
        target = target_dir / source.name
        if target.exists():
            target = target_dir / f"{source.stem}_{int(time.time())}{source.suffix}"
        shutil.move(str(source), str(target))

    def sha256(self, path):
        digest = hashlib.sha256()
        with path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


if __name__ == "__main__":
    logging.basicConfig(
        filename=str(Path(__file__).with_name("scanner_bridge.log")),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    ScannerBridge(load_config()).run()

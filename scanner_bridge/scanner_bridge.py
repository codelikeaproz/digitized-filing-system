import hashlib
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


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


def load_config() -> dict:
    config_path = Path(__file__).with_name("scanner_bridge.config.json")
    if not config_path.exists():
        return DEFAULT_CONFIG

    with config_path.open("r", encoding="utf-8") as config_file:
        file_config = json.load(config_file)
    return {**DEFAULT_CONFIG, **file_config}


class ScannerBridge:
    def __init__(self, config: dict):
        self.config = config
        self.incoming_dir = Path(config["incoming_dir"])
        self.uploaded_dir = Path(config["uploaded_dir"])
        self.failed_dir = Path(config["failed_dir"])
        self.unmatched_dir = Path(config["unmatched_dir"])

        for directory in [self.incoming_dir, self.uploaded_dir, self.failed_dir, self.unmatched_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Scanner-Token": config["api_token"],
                "X-Scanner-Station": config["station_id"],
            }
        )

    def run(self):
        logging.info("Scanner bridge started for %s", self.config["station_id"])

        observer = Observer()
        observer.schedule(ScanFileHandler(self), str(self.incoming_dir), recursive=False)
        observer.start()

        try:
            while True:
                self.send_heartbeat("CONNECTED")
                self.process_existing_files()
                time.sleep(self.config["poll_seconds"])
        except KeyboardInterrupt:
            logging.info("Scanner bridge stopped by user")
        finally:
            observer.stop()
            observer.join()

    def send_heartbeat(self, status: str, error_message: str = ""):
        try:
            self.session.post(
                f"{self.config['base_url']}/api/scanner/stations/heartbeat",
                json={
                    "station_id": self.config["station_id"],
                    "name": self.config["station_name"],
                    "status": status,
                    "watched_folder": str(self.incoming_dir),
                    "error_message": error_message,
                },
                timeout=5,
            )
        except requests.RequestException as exc:
            logging.warning("Heartbeat failed: %s", exc)

    def process_existing_files(self):
        pdfs = sorted(self.incoming_dir.glob("*.pdf"), key=lambda path: path.stat().st_mtime)
        for path in pdfs:
            self.process_pdf(path)

    def process_pdf(self, path: Path):
        if not path.exists() or path.suffix.lower() != ".pdf":
            return

        if not self.wait_until_file_stable(path):
            logging.warning("File did not become stable: %s", path)
            return

        job = self.get_pending_job()
        if not job:
            logging.warning("No pending scan job. Moving file to unmatched: %s", path)
            self.move_file(path, self.unmatched_dir)
            return

        try:
            self.upload_file(job["id"], path)
            self.move_file(path, self.uploaded_dir)
            logging.info("Uploaded %s for scan job %s", path.name, job["id"])
        except Exception as exc:
            logging.exception("Upload failed for %s", path)
            self.report_job_failure(job["id"], str(exc))
            self.move_file(path, self.failed_dir)
            self.send_heartbeat("ERROR", str(exc)[:500])

    def get_pending_job(self) -> Optional[dict]:
        try:
            response = self.session.get(
                f"{self.config['base_url']}/api/scan-jobs/pending",
                params={"station_id": self.config["station_id"]},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data or None
        except requests.RequestException as exc:
            logging.warning("Could not fetch pending scan job: %s", exc)
            return None

    def upload_file(self, job_id: str, path: Path):
        file_hash = self.sha256(path)

        for attempt in range(1, self.config["max_upload_retries"] + 1):
            try:
                with path.open("rb") as file_obj:
                    response = self.session.post(
                        f"{self.config['base_url']}/api/scan-jobs/{job_id}/upload",
                        files={"file": (path.name, file_obj, "application/pdf")},
                        data={
                            "station_id": self.config["station_id"],
                            "original_filename": path.name,
                            "sha256": file_hash,
                        },
                        timeout=60,
                    )

                if response.status_code in (200, 201):
                    return

                raise RuntimeError(f"Upload rejected: {response.status_code} {response.text}")
            except requests.RequestException as exc:
                logging.warning("Upload attempt %s failed: %s", attempt, exc)
                if attempt == self.config["max_upload_retries"]:
                    raise
                time.sleep(2 * attempt)

    def report_job_failure(self, job_id: str, message: str):
        try:
            self.session.patch(
                f"{self.config['base_url']}/api/scan-jobs/{job_id}/fail",
                json={"error_message": message[:1000]},
                timeout=10,
            )
        except requests.RequestException:
            logging.exception("Failed to report scan job failure")

    def wait_until_file_stable(self, path: Path) -> bool:
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

    def move_file(self, source: Path, target_dir: Path):
        target = target_dir / source.name
        if target.exists():
            target = target_dir / f"{source.stem}_{int(time.time())}{source.suffix}"
        shutil.move(str(source), str(target))

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


class ScanFileHandler(FileSystemEventHandler):
    def __init__(self, bridge: ScannerBridge):
        self.bridge = bridge

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() == ".pdf":
            self.bridge.process_pdf(path)

    def on_moved(self, event):
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if path.suffix.lower() == ".pdf":
            self.bridge.process_pdf(path)


if __name__ == "__main__":
    logging.basicConfig(
        filename=str(Path(__file__).with_name("scanner_bridge.log")),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    ScannerBridge(load_config()).run()

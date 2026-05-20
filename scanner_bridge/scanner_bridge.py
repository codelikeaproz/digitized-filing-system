import configparser
import hashlib
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import queue
import shutil
import sys
import threading
import time

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


TEMP_SUFFIXES = {".tmp", ".part", ".crdownload"}
DEFAULT_STATION_ID = "SCANNER-PC-01"


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def load_config(config_path):
    parser = configparser.ConfigParser()
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    parser.read(config_path, encoding="utf-8")
    return parser


def setup_logging(log_folder):
    log_folder.mkdir(parents=True, exist_ok=True)
    log_path = log_folder / "scanner_bridge.log"

    logger = logging.getLogger("DigiFileScannerBridge")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def as_path(config, section, key):
    return Path(config.get(section, key)).expanduser()


def unique_destination(folder, filename):
    target = folder / filename
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    candidate = folder / f"{stem}_{timestamp}{suffix}"
    counter = 1
    while candidate.exists():
        candidate = folder / f"{stem}_{timestamp}_{counter}{suffix}"
        counter += 1
    return candidate


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ScanFolderHandler(FileSystemEventHandler):
    def __init__(self, bridge):
        self.bridge = bridge

    def on_created(self, event):
        self.bridge.enqueue(event.src_path)

    def on_modified(self, event):
        self.bridge.enqueue(event.src_path)

    def on_moved(self, event):
        self.bridge.enqueue(event.dest_path)


class ScannerBridge:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.watch_folder = as_path(config, "scanner", "watch_folder")
        self.processed_folder = as_path(config, "scanner", "processed_folder")
        self.failed_folder = as_path(config, "scanner", "failed_folder")
        self.station_id = config.get("scanner", "station_id", fallback=DEFAULT_STATION_ID).strip() or DEFAULT_STATION_ID
        self.station_name = config.get("scanner", "station_name", fallback=self.station_id).strip() or self.station_id

        self.health_url = config.get("server", "health_url").strip()
        self.pending_job_url = config.get("server", "pending_job_url", fallback="").strip()
        self.upload_url_template = config.get(
            "server",
            "upload_job_url_template",
            fallback=config.get("server", "api_url", fallback=""),
        ).strip()
        self.heartbeat_url = config.get("server", "heartbeat_url", fallback="").strip()
        self.timeout_seconds = config.getint("server", "timeout_seconds", fallback=30)

        self.token = config.get("auth", "token", fallback="").strip()
        self.auth_mode = config.get("auth", "mode", fallback="scanner_token").strip().lower()
        self.queue = queue.Queue()
        self.queued_paths = set()
        self.queued_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.last_heartbeat = 0

    def headers(self):
        headers = {
            "X-Scanner-Station": self.station_id,
        }
        if self.token and self.auth_mode in {"scanner_token", "both"}:
            headers["X-Scanner-Token"] = self.token
        if self.token and self.auth_mode in {"bearer", "both"}:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def ensure_folders(self):
        for folder in [self.watch_folder, self.processed_folder, self.failed_folder]:
            folder.mkdir(parents=True, exist_ok=True)

    def wait_for_backend(self):
        self.logger.info("Checking DFS backend: %s", self.health_url)
        while not self.stop_event.is_set():
            try:
                response = requests.get(
                    self.health_url,
                    headers=self.headers(),
                    params={"station_id": self.station_id},
                    timeout=10,
                )
                if response.status_code < 500:
                    self.logger.info("Connected to DFS backend.")
                    return
                self.logger.warning("Waiting for DFS backend... HTTP %s", response.status_code)
            except requests.RequestException as exc:
                self.logger.warning("Waiting for DFS backend... %s", exc)
            time.sleep(5)

    def send_heartbeat(self, force=False):
        if not self.heartbeat_url:
            return
        now = time.time()
        if not force and now - self.last_heartbeat < 10:
            return
        try:
            response = requests.post(
                self.heartbeat_url,
                headers=self.headers(),
                data={
                    "station_id": self.station_id,
                    "name": self.station_name,
                    "status": "CONNECTED",
                    "watched_folder": str(self.watch_folder),
                },
                timeout=10,
            )
            if response.ok:
                self.last_heartbeat = now
            else:
                self.logger.warning("Scanner heartbeat failed: HTTP %s %s", response.status_code, response.text[:300])
        except requests.RequestException as exc:
            self.logger.warning("Scanner heartbeat failed: %s", exc)

    def is_candidate_pdf(self, path):
        if path.is_dir():
            return False
        if path.name.startswith("~") or path.name.startswith("."):
            return False
        if path.suffix.lower() in TEMP_SUFFIXES:
            return False
        return path.suffix.lower() == ".pdf"

    def enqueue(self, raw_path):
        path = Path(raw_path)
        if not self.is_candidate_pdf(path):
            return

        resolved = str(path.resolve())
        with self.queued_lock:
            if resolved in self.queued_paths:
                return
            self.queued_paths.add(resolved)
        self.logger.info("PDF detected: %s", path.name)
        self.queue.put(path)

    def wait_until_stable(self, path):
        stable_checks = 0
        previous_size = -1
        while stable_checks < 2 and not self.stop_event.is_set():
            if not path.exists():
                raise FileNotFoundError(f"File disappeared before upload: {path}")

            size = path.stat().st_size
            if size <= 0:
                stable_checks = 0
            elif size == previous_size:
                try:
                    with path.open("rb"):
                        pass
                    stable_checks += 1
                except OSError:
                    stable_checks = 0
            else:
                stable_checks = 0

            previous_size = size
            time.sleep(2)

        if self.stop_event.is_set():
            raise RuntimeError("Bridge stopped before file became stable.")
        return previous_size

    def get_pending_job(self):
        if not self.pending_job_url:
            return None
        response = requests.get(
            self.pending_job_url,
            headers=self.headers(),
            params={"station_id": self.station_id},
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json() if response.content else {}
        return data if data.get("id") else None

    def wait_for_pending_job(self):
        deadline = time.time() + 60
        while time.time() < deadline and not self.stop_event.is_set():
            job = self.get_pending_job()
            if job:
                return job
            self.logger.info("No pending scan job yet for station %s. Waiting...", self.station_id)
            time.sleep(2)
        return None

    def upload_to_job(self, path, job):
        upload_url = self.upload_url_template.format(job_id=job["id"])
        sha256 = file_sha256(path)
        with path.open("rb") as file_obj:
            files = {
                "file": (path.name, file_obj, "application/pdf"),
            }
            data = {
                "source": "Scanned",
                "station_id": self.station_id,
                "original_filename": path.name,
                "sha256": sha256,
            }
            response = requests.post(
                upload_url,
                headers=self.headers(),
                data=data,
                files=files,
                timeout=self.timeout_seconds,
            )
        if not response.ok:
            raise requests.HTTPError(
                f"Upload failed: HTTP {response.status_code} {response.text[:1000]}",
                response=response,
            )
        return response

    def move_file(self, path, destination_folder):
        destination_folder.mkdir(parents=True, exist_ok=True)
        destination = unique_destination(destination_folder, path.name)
        shutil.move(str(path), str(destination))
        return destination

    def process_file(self, path):
        try:
            self.logger.info("Waiting until file is fully written: %s", path.name)
            size = self.wait_until_stable(path)
            self.logger.info("File is stable: %s (%s bytes)", path.name, size)

            job = self.wait_for_pending_job()
            if not job:
                raise RuntimeError("No pending DFS scan job found. Create a scan job in DFS before scanning.")

            self.logger.info("Uploading %s to scan job #%s (%s)", path.name, job.get("id"), job.get("code", "no-code"))
            self.upload_to_job(path, job)
            destination = self.move_file(path, self.processed_folder)
            self.logger.info("Uploaded and moved to processed: %s", destination.name)
        except Exception as exc:
            self.logger.exception("Upload failed for %s: %s", path.name, exc)
            try:
                if path.exists():
                    destination = self.move_file(path, self.failed_folder)
                    self.logger.info("Moved failed scan to failed folder: %s", destination.name)
            except Exception as move_exc:
                self.logger.exception("Failed to move scan to failed folder: %s", move_exc)
        finally:
            with self.queued_lock:
                self.queued_paths.discard(str(path.resolve()))

    def worker_loop(self):
        while not self.stop_event.is_set():
            self.send_heartbeat()
            try:
                path = self.queue.get(timeout=1)
            except queue.Empty:
                continue
            try:
                self.process_file(path)
            finally:
                self.queue.task_done()

    def enqueue_existing_files(self):
        for path in sorted(self.watch_folder.glob("*.pdf")):
            self.enqueue(path)

    def run(self):
        self.ensure_folders()
        self.logger.info("DigiFile Scanner Bridge starting.")
        self.logger.info("Station: %s", self.station_id)
        self.logger.info("Watching folder: %s", self.watch_folder)
        self.logger.info("Processed folder: %s", self.processed_folder)
        self.logger.info("Failed folder: %s", self.failed_folder)

        self.wait_for_backend()
        self.send_heartbeat(force=True)

        worker = threading.Thread(target=self.worker_loop, daemon=True)
        worker.start()

        observer = Observer()
        observer.schedule(ScanFolderHandler(self), str(self.watch_folder), recursive=False)
        observer.start()
        self.enqueue_existing_files()

        self.logger.info("Scanner Bridge is running. Press Ctrl+C to stop.")
        try:
            while True:
                self.send_heartbeat()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Stop requested.")
        finally:
            self.stop_event.set()
            observer.stop()
            observer.join(timeout=10)
            self.logger.info("Scanner Bridge stopped.")


def main():
    base_dir = app_dir()
    config_path = base_dir / "config.ini"
    config = load_config(config_path)
    log_folder = as_path(config, "logging", "log_folder") if config.has_section("logging") else base_dir / "logs"
    logger = setup_logging(log_folder)
    logger.info("Config loaded: %s", config_path)
    bridge = ScannerBridge(config, logger)
    bridge.run()


if __name__ == "__main__":
    main()

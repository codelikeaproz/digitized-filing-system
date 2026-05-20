DigiFile Scanner Bridge
=======================

Purpose
-------
This bridge watches a local Epson Scan 2 output folder and uploads scanned PDF files to the existing DigiFile/DFS backend.

It does not control the scanner directly. Epson Scan 2 handles scanning. The bridge only watches for finished PDF files and sends them to DFS.


Stakeholder Folder Structure
----------------------------
Use this structure on the stakeholder computer:

C:\DigiFile\
  scanner-bridge\
    DigiFileScannerBridge.exe
    config.ini
    start_scanner_bridge.bat
    README.txt
    logs\

  scans\
    incoming\
    processed\
    failed\

Epson Scan 2 must save scanned PDFs to:

C:\DigiFile\scans\incoming


Important DFS Flow
------------------
1. In DFS, the user clicks Scan with Epson and enters document metadata.
2. DFS creates a pending scan job for this scanner station.
3. Epson Scan 2 saves the scanned PDF to C:\DigiFile\scans\incoming.
4. The bridge detects the PDF, waits until writing is complete, uploads it to the pending scan job, then moves the PDF.

This keeps DFS validation intact, including folder, category, document code, role access, and audit logs.


Configuration
-------------
Edit:

C:\DigiFile\scanner-bridge\config.ini

Example:

[scanner]
station_id=SCANNER-PC-01
station_name=DigiFile Scanner
watch_folder=C:\DigiFile\scans\incoming
processed_folder=C:\DigiFile\scans\processed
failed_folder=C:\DigiFile\scans\failed

[server]
health_url=http://localhost:8000/api/scan-jobs/pending
api_url=http://localhost:8000/api/scan-jobs/{job_id}/upload
pending_job_url=http://localhost:8000/api/scan-jobs/pending
upload_job_url_template=http://localhost:8000/api/scan-jobs/{job_id}/upload
heartbeat_url=http://localhost:8000/api/scanner/stations/heartbeat
timeout_seconds=30

[auth]
mode=scanner_token
token=PASTE_SCANNER_BRIDGE_TOKEN_HERE

[logging]
log_folder=C:\DigiFile\scanner-bridge\logs

The token must match SCANNER_BRIDGE_TOKEN in the DFS backend .env file.

For the current DFS scanner endpoints, keep mode=scanner_token. Use mode=bearer only if a future upload endpoint expects Authorization: Bearer tokens.


Manual Stakeholder Setup
------------------------
1. Copy the DigiFile folder to C:\DigiFile.
2. Confirm these folders exist:
   C:\DigiFile\scans\incoming
   C:\DigiFile\scans\processed
   C:\DigiFile\scans\failed
   C:\DigiFile\scanner-bridge\logs
3. Configure Epson Scan 2 to save PDF files to:
   C:\DigiFile\scans\incoming
4. Edit config.ini if the backend URL, scanner station ID, or token changes.
5. Run:
   C:\DigiFile\scanner-bridge\start_scanner_bridge.bat
6. Open DFS, choose Scan with Epson, enter metadata, and create the scan job.
7. Scan a PDF using Epson Scan 2.
8. Confirm the document appears in DFS.
9. Confirm the PDF moves to:
   C:\DigiFile\scans\processed
10. If it fails, check:
   C:\DigiFile\scans\failed
   C:\DigiFile\scanner-bridge\logs\scanner_bridge.log


Manual Test Checklist
---------------------
[ ] DFS backend is running.
[ ] The bridge starts and logs "Connected to DFS backend."
[ ] DFS upload dialog shows the scanner bridge as connected.
[ ] Epson Scan 2 saves PDFs to C:\DigiFile\scans\incoming.
[ ] A scan job is created in DFS before scanning.
[ ] The PDF moves from incoming to processed.
[ ] The document appears in the selected DFS folder.
[ ] Audit logs show the scan upload.


Build EXE on Development Machine
--------------------------------
Python is required only on the development/build machine, not on the stakeholder PC after the EXE is built.

From this scanner_bridge folder:

pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --name DigiFileScannerBridge scanner_bridge.py

After build, copy:

dist\DigiFileScannerBridge.exe

to:

C:\DigiFile\scanner-bridge\

Also copy:

config.example.ini as config.ini
start_scanner_bridge.bat
README.txt

Do not commit or share the real config.ini after adding the real scanner token. Keep only config.example.ini in Git.


Task Scheduler Note
-------------------
Do not configure Task Scheduler first. Manual testing must work first.

After stable manual testing, Task Scheduler can run:

Task Name:
DigiFile Scanner Bridge

Trigger:
At log on

Action:
C:\DigiFile\scanner-bridge\start_scanner_bridge.bat

Start in:
C:\DigiFile\scanner-bridge

The batch file includes pause during stakeholder testing so errors remain visible. Remove pause only after the setup is stable.


Troubleshooting
---------------
Backend not running:
- Start the DFS backend first.
- The bridge will keep logging "Waiting for DFS backend..." until it can connect.

Wrong API URL:
- Check config.ini server URLs.
- If the backend is on another computer, replace localhost with that computer's IP address.

Wrong token:
- The config.ini token must match SCANNER_BRIDGE_TOKEN in the DFS backend .env.
- A wrong token usually causes HTTP 403 or "Invalid scanner bridge token."

Epson Scan 2 saving to wrong folder:
- Set Epson Scan 2 output folder to C:\DigiFile\scans\incoming.
- The bridge ignores PDFs saved outside the configured incoming folder.

Non-PDF file ignored:
- The bridge only processes .pdf files.
- Temporary files like .tmp, .part, and .crdownload are ignored.

File stuck in failed folder:
- Open scanner_bridge.log and read the upload error.
- Common causes are duplicate document code, duplicate file name in folder, no pending scan job, wrong token, or backend validation failure.
- Create a new DFS scan job, fix metadata if needed, then move the PDF back to incoming.

Windows permission issue:
- Make sure the Windows user can read and write:
  C:\DigiFile\scanner-bridge
  C:\DigiFile\scans
- Try running start_scanner_bridge.bat as Administrator for testing only.

Firewall or network issue:
- If the backend is on another computer, allow the backend port, usually 8000, through Windows Firewall.
- Confirm the stakeholder PC can open:
  http://BACKEND-IP:8000

No pending scan job:
- In DFS, click Scan with Epson and create the scan job before scanning.
- The bridge uploads scanned files to the active pending job for the configured station_id.

Bridge not showing connected in DFS:
- Confirm heartbeat_url in config.ini.
- Confirm station_id matches VITE_SCANNER_STATION_ID in the frontend environment.
- Confirm the token matches the backend scanner bridge token.

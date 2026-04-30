@echo off
cd /d "%~dp0"
echo Starting DFS Scanner Bridge...
echo Keep this window open while scanning.
echo.
"C:\Users\ciscl\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "%~dp0scanner_bridge_stdlib.py"
echo.
echo Scanner bridge stopped. Press any key to close.
pause > nul

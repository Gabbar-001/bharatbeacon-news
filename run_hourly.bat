@echo off
cd /d "D:\youtube news"
"C:\Users\mr_un\AppData\Local\Microsoft\WindowsApps\python.exe" "D:\youtube news\run_hourly.py" >> "D:\youtube news\output\logs\task_scheduler.log" 2>&1

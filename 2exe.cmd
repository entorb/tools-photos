@echo off
pyinstaller --onefile --console Photo-SyncShrink.py
move dist\*.exe .\

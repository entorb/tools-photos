@echo off
pyinstaller --onefile --console Photo-SyncShrink.py
move dist\*.exe .\

pp -M Image::EXIF -o Photo-Rename_From_EXIF.exe Photo-Rename_From_EXIF.pl

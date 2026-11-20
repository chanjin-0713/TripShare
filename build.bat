@echo off
REM TripShare.exe 빌드 (Python 3.12 + PyInstaller 필요, 빌드하는 PC에서만)
REM 사용법: TripShare 폴더에서 build.bat 실행 -> dist\TripShare.exe 생성
python -m pip install pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name TripShare main.py || exit /b 1
echo.
echo 빌드 완료: dist\TripShare.exe

@echo off
chcp 65001 >nul
title CẬP NHẬT TỰ ĐỘNG MEXICO ÔNG GIÀ STUDIO TỪ GITHUB (KHÔNG MẤT KỊCH BẢN & BẢN QUYỀN)
color 0A

echo ============================================================================
echo   CÔNG CỤ CẬP NHẬT TỰ ĐỘNG — MEXICO ÔNG GIÀ STUDIO (OTA GITHUB V1.0.9+)
echo   - Tự động tải bản mới nhất trực tiếp từ GitHub chính thức (Key Ông Già Mexico)
echo   - Giữ nguyên 100%% Kịch bản đã tạo (projects/, config/saved_ideas.json)
echo   - Giữ nguyên 100%% Key bản quyền (config/license.json) ^& Chrome (config/browser_profiles)
echo ============================================================================
echo.

set "SRC_DIR=%~dp0"
if "%SRC_DIR:~-1%"=="\" set "SRC_DIR=%SRC_DIR:~0,-1%"

:: 1. Tự động nhận diện thư mục cài đặt chính
set "TARGET_DIR=%SRC_DIR%"
if exist "%SRC_DIR%\bin" (
    set "TARGET_DIR=%SRC_DIR%"
) else if exist "%SRC_DIR%\..\bin" (
    for %%I in ("%SRC_DIR%\..") do set "TARGET_DIR=%%~fI"
) else if exist "%SRC_DIR%\..\Mexico_Ong_Gia_Studio\bin" (
    for %%I in ("%SRC_DIR%\..\Mexico_Ong_Gia_Studio") do set "TARGET_DIR=%%~fI"
)

set "PYTHON_EXE="
if exist "%TARGET_DIR%\config\python_path.txt" (
    for /f "usebackq delims=" %%P in ("%TARGET_DIR%\config\python_path.txt") do if not defined PYTHON_EXE if exist "%%~P" set "PYTHON_EXE=%%~P"
)
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYTHON_EXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYTHON_EXE if exist "C:\Program Files\Python311\python.exe" set "PYTHON_EXE=C:\Program Files\Python311\python.exe"

set "APP_STOPPED=0"
set "UPDATE_OK=0"

:: 2. Nếu chạy từ gói giải nén thì chép vào thư mục cài đặt trước
if /I "%SRC_DIR%"=="%TARGET_DIR%" goto :download_update
if not exist "%SRC_DIR%\backend" goto :download_update
call :stop_app
echo [2/4] Đang chép file từ gói giải nén vào thư mục chính: "%TARGET_DIR%"
xcopy "%SRC_DIR%\backend\*" "%TARGET_DIR%\backend\" /E /I /Y /Q >nul
xcopy "%SRC_DIR%\frontend\*" "%TARGET_DIR%\frontend\" /E /I /Y /Q >nul
xcopy "%SRC_DIR%\adas_skills\*" "%TARGET_DIR%\adas_skills\" /E /I /Y /Q >nul
for %%F in (main.py requirements.txt version.json Chay_App.bat Cai_Dat_May_Moi.bat) do (
    if exist "%SRC_DIR%\%%F" copy /Y "%SRC_DIR%\%%F" "%TARGET_DIR%\%%F" >nul
)

:: 3. Tải gói mới, xác minh chữ ký rồi mới dừng ứng dụng và cài đặt
:download_update
echo [3/4] Đang tải và xác minh gói cập nhật từ GitHub...
set "GH_TMP=%TARGET_DIR%\_gh_ota_tmp"
if exist "%GH_TMP%" rmdir /S /Q "%GH_TMP%" >nul 2>&1
mkdir "%GH_TMP%" >nul 2>&1

if not defined PYTHON_EXE (
    echo       [LỖI] Không tìm thấy Python để xác minh gói cập nhật.
    goto :finish_update
)
if not exist "%TARGET_DIR%\backend\ota_security.py" (
    echo       [LỖI] Thiếu bộ xác minh chữ ký backend\ota_security.py.
    goto :finish_update
)
curl.exe -L --fail -s --show-error --connect-timeout 20 -o "%GH_TMP%\update.zip" "https://codeload.github.com/phamngocthu661-lang/mexico-ong-gia-studio/zip/refs/heads/main"
if errorlevel 1 (
    echo       [LỖI] Không tải được gói cập nhật. Vui lòng kiểm tra mạng.
    goto :finish_update
)
tar -xf "%GH_TMP%\update.zip" -C "%GH_TMP%" >nul 2>&1
if errorlevel 1 (
    echo       [LỖI] Gói cập nhật bị lỗi giải nén.
    goto :finish_update
)
del /f /q "%GH_TMP%\update.zip" >nul 2>&1
set "PKG_DIR="
for /d %%D in ("%GH_TMP%\mexico-ong-gia-studio-*") do set "PKG_DIR=%%~fD"
if not defined PKG_DIR (
    echo       [LỖI] Gói cập nhật không đúng cấu trúc.
    goto :finish_update
)
"%PYTHON_EXE%" -B -I "%TARGET_DIR%\backend\ota_security.py" verify --package "%PKG_DIR%" --root "%TARGET_DIR%"
if errorlevel 1 (
    echo       [LỖI] Gói không qua được xác minh. Không cài đặt.
    goto :finish_update
)
call :stop_app
echo       -^> Đang cài bản mới và sao lưu bản hiện tại...
"%PYTHON_EXE%" -B -I "%TARGET_DIR%\backend\ota_security.py" install --package "%PKG_DIR%" --root "%TARGET_DIR%"
if errorlevel 1 (
    echo       [LỖI] Cài đặt thất bại, bản cũ đã được giữ lại.
    goto :finish_update
)
set "UPDATE_OK=1"

:: Dọn dẹp các file lẻ cũ đã được gộp vào 7 Model chính và thư mục app/ dư thừa
for %%O in (chatgpt_web_client.py karaoke_subtitle.py sync_checker.py visual_cue_director.py license_manager.py updater_service.py install_setup.py) do (
    if exist "%TARGET_DIR%\backend\%%O" del /f /q "%TARGET_DIR%\backend\%%O" >nul 2>&1
)
if exist "%TARGET_DIR%\install_setup.py" del /f /q "%TARGET_DIR%\install_setup.py" >nul 2>&1
if exist "%TARGET_DIR%\app" rmdir /S /Q "%TARGET_DIR%\app" >nul 2>&1

:finish_update
if exist "%GH_TMP%" rmdir /S /Q "%GH_TMP%" >nul 2>&1
if "%UPDATE_OK%"=="1" (
    echo       -^> Đã nâng cấp thành công lên phiên bản mới nhất!
) else (
    echo       -^> Không có thay đổi nào từ GitHub được cài đặt.
    timeout /t 8 >nul
)
echo.
echo [4/4] Đang khởi động Mexico Ông Già Studio...
cd /d "%TARGET_DIR%"
if exist "%TARGET_DIR%\Mexico_Ong_Gia.exe" (
    start "" "%TARGET_DIR%\Mexico_Ong_Gia.exe"
) else (
    call "%TARGET_DIR%\Chay_App.bat"
)
timeout /t 3 >nul
if "%UPDATE_OK%"=="1" (exit /b 0) else (exit /b 1)

:stop_app
if "%APP_STOPPED%"=="1" exit /b 0
set "APP_STOPPED=1"
echo       -> Đang đóng toàn bộ tác vụ đang chạy ^& Reset tiến trình ứng dụng...
taskkill /F /IM Mexico_Ong_Gia.exe /T >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8900" ^| findstr "LISTENING"') do taskkill /F /PID %%a /T >nul 2>&1
taskkill /F /IM ffmpeg.exe /T >nul 2>&1
taskkill /F /IM ffprobe.exe /T >nul 2>&1
taskkill /F /IM yt-dlp.exe /T >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('chrome.exe','msedge.exe') -and ($_.CommandLine -like '*MexicoUI_Profile_V*' -or $_.CommandLine -like '*--app=http://127.0.0.1:8900*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
exit /b 0

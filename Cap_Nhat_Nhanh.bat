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

:: 1. Tắt hoàn toàn tiến trình cũ (Mexico_Ong_Gia.exe, cổng 8900, FFmpeg, yt-dlp và cửa sổ App cũ) để Reset 100%
echo [1/4] Đang đóng toàn bộ tác vụ đang chạy ^& Reset tiến trình ứng dụng...
taskkill /F /IM Mexico_Ong_Gia.exe /T >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8900" ^| findstr "LISTENING"') do taskkill /F /PID %%a /T >nul 2>&1
taskkill /F /IM ffmpeg.exe /T >nul 2>&1
taskkill /F /IM ffprobe.exe /T >nul 2>&1
taskkill /F /IM yt-dlp.exe /T >nul 2>&1
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('chrome.exe','msedge.exe') -and ($_.CommandLine -like '*MexicoUI_Profile_V*' -or $_.CommandLine -like '*--app=http://127.0.0.1:8900*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: 2. Tự động nhận diện thư mục cài đặt chính
set "TARGET_DIR=%SRC_DIR%"
if exist "%SRC_DIR%\bin" (
    set "TARGET_DIR=%SRC_DIR%"
) else if exist "%SRC_DIR%\..\bin" (
    for %%I in ("%SRC_DIR%\..") do set "TARGET_DIR=%%~fI"
) else if exist "%SRC_DIR%\..\Mexico_Ong_Gia_Studio\bin" (
    for %%I in ("%SRC_DIR%\..\Mexico_Ong_Gia_Studio") do set "TARGET_DIR=%%~fI"
)

if /I not "%SRC_DIR%"=="%TARGET_DIR%" (
    if exist "%SRC_DIR%\backend" (
        echo [2/4] Đang chép file từ gói giải nén vào thư mục chính: "%TARGET_DIR%"
        xcopy "%SRC_DIR%\backend\*" "%TARGET_DIR%\backend\" /E /I /Y /Q >nul
        xcopy "%SRC_DIR%\frontend\*" "%TARGET_DIR%\frontend\" /E /I /Y /Q >nul
        xcopy "%SRC_DIR%\adas_skills\*" "%TARGET_DIR%\adas_skills\" /E /I /Y /Q >nul
        for %%F in (main.py requirements.txt version.json Chay_App.bat Cai_Dat_May_Moi.bat) do (
            if exist "%SRC_DIR%\%%F" copy /Y "%SRC_DIR%\%%F" "%TARGET_DIR%\%%F" >nul
        )
    )
)

:: 3. Tự động tải bản mới nhất trực tiếp từ GitHub bằng curl.exe + tar của Windows
echo [3/4] Đang tải gói cập nhật mới nhất từ GitHub (phamngocthu661-lang/mexico-ong-gia-studio)...
set "GH_TMP=%TARGET_DIR%\_gh_ota_tmp"
if exist "%GH_TMP%" rmdir /S /Q "%GH_TMP%" >nul 2>&1
mkdir "%GH_TMP%" >nul 2>&1

curl.exe -L -k -s -o "%GH_TMP%\update.zip" "https://codeload.github.com/phamngocthu661-lang/mexico-ong-gia-studio/zip/refs/heads/main"
if exist "%GH_TMP%\update.zip" (
    tar -xf "%GH_TMP%\update.zip" -C "%GH_TMP%" >nul 2>&1
    for /d %%D in ("%GH_TMP%\mexico-ong-gia-studio-*") do (
        echo       -^> Đang nâng cấp mã nguồn lên phiên bản mới nhất...
        xcopy "%%D\backend\*" "%TARGET_DIR%\backend\" /E /I /Y /Q >nul
        xcopy "%%D\frontend\*" "%TARGET_DIR%\frontend\" /E /I /Y /Q >nul
        xcopy "%%D\adas_skills\*" "%TARGET_DIR%\adas_skills\" /E /I /Y /Q >nul
        if exist "%%D\Kho_Voice" xcopy "%%D\Kho_Voice\*" "%TARGET_DIR%\Kho_Voice\" /E /I /Y /Q >nul
        if exist "%%D\assets" xcopy "%%D\assets\*" "%TARGET_DIR%\assets\" /E /I /Y /Q >nul
        for %%F in (main.py requirements.txt version.json Chay_App.bat Cai_Dat_May_Moi.bat) do (
            if exist "%%D\%%F" copy /Y "%%D\%%F" "%TARGET_DIR%\%%F" >nul 2>&1
        )
    )
)
if exist "%GH_TMP%" rmdir /S /Q "%GH_TMP%" >nul 2>&1

:: Dọn dẹp các file lẻ cũ đã được gộp vào 7 Model chính và thư mục app/ dư thừa
for %%O in (chatgpt_web_client.py karaoke_subtitle.py sync_checker.py visual_cue_director.py license_manager.py updater_service.py install_setup.py) do (
    if exist "%TARGET_DIR%\backend\%%O" del /f /q "%TARGET_DIR%\backend\%%O" >nul 2>&1
)
if exist "%TARGET_DIR%\install_setup.py" del /f /q "%TARGET_DIR%\install_setup.py" >nul 2>&1
if exist "%TARGET_DIR%\app" rmdir /S /Q "%TARGET_DIR%\app" >nul 2>&1

echo       -^> Đã nâng cấp thành công lên phiên bản mới nhất!
echo.
echo [4/4] Đang khởi động Mexico Ông Già Studio...
cd /d "%TARGET_DIR%"
if exist "%TARGET_DIR%\Mexico_Ong_Gia.exe" (
    start "" "%TARGET_DIR%\Mexico_Ong_Gia.exe"
) else (
    call "%TARGET_DIR%\Chay_App.bat"
)
timeout /t 3 >nul
exit /b 0

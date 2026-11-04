@echo off
chcp 65001 >nul
title 皮皮输入法 - 维护
cd /d "%~dp0"

:menu
cls
echo.
echo   ==========================================
echo      皮皮输入法  维护工具
echo   ==========================================
echo.
echo    1. 重新部署（改了配置、或者候选窗样式不对时用）
echo    2. 打开用户配置目录
echo    3. 重启输入法服务（打了字母没候选窗时用）
echo    4. 重装皮皮（覆盖配置 + 恢复角标名字）
echo    0. 退出
echo.
set /p CH=  请选择:

if "%CH%"=="1" goto deploy
if "%CH%"=="2" goto folder
if "%CH%"=="3" goto restart
if "%CH%"=="4" goto reinstall
if "%CH%"=="0" exit /b
goto menu

:findweasel
set "WD="
for /d %%D in ("%ProgramFiles%\Rime\weasel-*") do set "WD=%%D"
if not defined WD for /d %%D in ("%ProgramFiles(x86)%\Rime\weasel-*") do set "WD=%%D"
if not defined WD (
    echo.
    echo   没找到小狼毫安装目录。
    pause
    exit /b 1
)
exit /b 0

:deploy
call :findweasel
echo.
echo   正在部署...
start "" /wait "%WD%\WeaselDeployer.exe" /deploy
echo   完成。
pause
goto menu

:folder
echo.
start "" "%APPDATA%\Rime"
goto menu

:restart
call :findweasel
echo.
taskkill /f /im WeaselServer.exe >nul 2>&1
timeout /t 1 /nobreak >nul
start "" "%WD%\WeaselServer.exe"
echo   服务已重启。新开一个窗口试试打字。
pause
goto menu

:reinstall
echo.
echo   接下来会请求管理员权限，请点「是」。
pause
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~dp0install.bat' -Verb RunAs"
exit /b

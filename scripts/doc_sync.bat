@echo off
chcp 65001 >nul
echo ====================================
echo    文档同步工具
echo ====================================
echo.

cd /d "%~dp0\.."

if "%1"=="" goto help
if "%1"=="--list" goto list
if "%1"=="--check" goto check
if "%1"=="--auto" goto auto
if "%1"=="--init-hook" goto init_hook
goto help

:list
python scripts\doc_sync.py --list
goto end

:check
python scripts\doc_sync.py --check
goto end

:auto
python scripts\doc_sync.py --auto
goto end

:init_hook
python scripts\doc_sync.py --init-hook
goto end

:help
echo.
echo ====================================
echo    文档同步工具 - 使用帮助
echo ====================================
echo.
echo 用法:
echo   doc_sync.bat [选项]
echo.
echo 选项:
echo   --list      列出所有代码-文档映射
echo   --check     检查当前变更是否需要同步文档
echo   --auto      显示需要同步的文档列表
echo   --init-hook 安装 Git hooks
echo.
echo 示例:
echo   doc_sync.bat --list      查看所有映射关系
echo   doc_sync.bat --check     检查变更
echo   doc_sync.bat --auto     查看需要同步的文档
echo.
echo ====================================
goto end

:end
echo.
pause

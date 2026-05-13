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
echo.
echo 📚 代码文件 ↔ 文档映射表
echo ====================================
echo.
echo 📁 消息总线服务
echo    代码: backend/app/services/message_bus.py
echo    文档: docs/modules/message-bus.md
echo.
echo 📁 发言控制器服务
echo    代码: backend/app/services/speaking_controller.py
echo    文档: docs/modules/speaking-controller.md
echo.
echo 📁 任务看板服务
echo    代码: backend/app/services/task_board.py
echo    文档: docs/modules/task-board.md
echo.
echo 📁 Pipeline 编排服务
echo    代码: backend/app/services/pipeline_orchestrator.py
echo    文档: docs/modules/pipeline-orchestrator.md
echo.
echo 📁 Agent 执行器服务
echo    代码: backend/app/services/agent_executor.py
echo    文档: docs/modules/agent-executor.md
echo.
echo 📁 项目管理服务
echo    代码: backend/app/services/project_service.py
echo    文档: docs/modules/project-service.md
echo.
echo 📁 协作界面组件
echo    代码: frontend/src/components/CollaborationView.tsx
echo    文档: docs/modules/collaboration-view.md
echo.
echo ====================================
goto end

:check
echo.
echo 🔍 检查文档同步状态...
echo.
git status --porcelain > "%TEMP%\doc_sync_files.txt"
findstr /R "backend.*\.py frontend.*\.tsx" "%TEMP%\doc_sync_files.txt" >nul
if errorlevel 1 (
    echo ✅ 未检测到相关代码变更
    goto end
)
echo ⚠️  发现以下文件变更:
findstr /R "backend.*\.py frontend.*\.tsx" "%TEMP%\doc_sync_files.txt"
echo.
echo 请运行 --auto 查看需要同步的文档
goto end

:auto
echo.
echo 🔄 检查需要同步的文档...
echo.
echo ====================================
echo.
echo 📋 当前代码文件与文档映射关系:
echo.
echo    backend\app\services\*_service.py  →  docs\modules\*.md
echo    backend\app\services\message_bus.py → docs\modules\message-bus.md
echo    backend\app\services\speaking_controller.py → docs\modules\speaking-controller.md
echo    backend\app\services\task_board.py → docs\modules\task-board.md
echo    backend\app\services\pipeline_orchestrator.py → docs\modules\pipeline-orchestrator.md
echo    backend\app\services\agent_executor.py → docs\modules\agent-executor.md
echo    backend\app\services\project_service.py → docs\modules\project-service.md
echo    frontend\src\components\CollaborationView.tsx → docs\modules\collaboration-view.md
echo.
echo ====================================
echo.
echo 💡 提示: 请告诉 AI 助手 "帮我同步文档"
echo    或描述具体需要更新的模块
echo.
goto end

:init_hook
echo.
echo 🔧 安装 Git Hooks...
echo.
echo 正在创建 pre-commit hook...
echo.
echo @echo off > .git\hooks\pre-commit
echo chcp 65001 ^>nul >> .git\hooks\pre-commit
echo echo 正在检查文档同步状态... >> .git\hooks\pre-commit
echo python scripts\doc_sync.py --check >> .git\hooks\pre-commit
echo.
echo ✅ Git Hook 已安装
echo    每次提交前会自动检查文档同步
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
del "%TEMP%\doc_sync_files.txt" 2>nul
echo.
pause

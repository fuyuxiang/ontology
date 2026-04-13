@echo off
chcp 65001 >nul
echo ========================================
echo   本体驱动智能策略平台 - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 初始化数据库...
cd backend
python seed.py 2>nul
echo.

echo [2/3] 启动后端 (port 8000)...
start "Ontology-Backend" cmd /k "cd /d %~dp0backend && uvicorn app.main:app --reload --port 8000 --log-level info"
timeout /t 3 /nobreak >nul

echo [3/3] 启动前端 (port 5177)...
cd /d "%~dp0frontend"
start "Ontology-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   启动完成！
echo   前端: http://localhost:5177
echo   后端: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo ========================================
echo.
echo 按任意键打开浏览器...
pause >nul
start http://localhost:5177

@echo off
chcp 65001 >nul
echo 正在停止服务...

taskkill /FI "WINDOWTITLE eq Ontology-Backend*" /F 2>nul
taskkill /FI "WINDOWTITLE eq Ontology-Frontend*" /F 2>nul

echo 服务已停止

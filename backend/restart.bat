@echo off
REM 安全重启 backend 服务
REM 用法: restart.bat              重启(默认端口8000, 热重载)
REM       restart.bat -StopOnly      仅停止
REM       restart.bat -RebuildVenv   重建虚拟环境后启动
REM       restart.bat -NoReload      禁用热重载
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restart.ps1" %*

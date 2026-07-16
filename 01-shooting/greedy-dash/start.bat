@echo off
REM Greedy Dash 启动脚本（Windows）
REM 与 scroll-shooter 工程保持一致：使用虚拟环境内的 python 运行。
cd /d %~dp0
call venv\Scripts\activate
python main.py

@echo off
setlocal
cd /d %~dp0
echo Running from %cd%
echo Boolean operations in process...
python  .\FaceMaskBoolean.py
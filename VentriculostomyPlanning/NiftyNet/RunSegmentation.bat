@echo off
setlocal
cd /d %~dp0
echo Running from %cd%
echo Deep learning segmentation in process...
net_segment inference -a brainVesselSeg.brainVesselSegApp.brainVesselSegApp -c .\vesselSeg.ini
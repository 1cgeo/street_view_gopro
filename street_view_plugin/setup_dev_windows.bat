@echo off
set "_updir=%~dp0"
for %%a in ("%_updir:~0,-1%") do set "_dir=%%~dpa"
mklink /D %HOMEDRIVE%%HOMEPATH%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\street_view_plugin %_dir%street_view_plugin

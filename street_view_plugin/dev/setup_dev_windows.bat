@echo off
rem Caminho da pasta onde está esse script (dev)
set "_updir=%~dp0"

rem Subir dois níveis: de \dev para \street_view_gopro
for %%a in ("%_updir%\..") do set "_dir=%%~dpa"

rem Agora definimos os caminhos de destino e origem do link
set "link_path=%HOMEDRIVE%%HOMEPATH%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\street_view_plugin"
set "target_path=%_dir%street_view_plugin"

echo Criando link:
echo   De: "%target_path%"
echo   Para: "%link_path%"
echo.

if exist "%link_path%" (
    echo O link ou pasta já existe: "%link_path%"
    echo Remova-o manualmente se quiser recriar.
    pause
    exit /b
)

mklink /D "%link_path%" "%target_path%"
if errorlevel 1 (
    echo Erro ao criar o link.
) else (
    echo Link criado com sucesso!
)
pause

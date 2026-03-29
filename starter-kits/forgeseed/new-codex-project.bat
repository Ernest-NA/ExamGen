@echo off
setlocal

echo ============================================
echo   Codex + Notion + GitHub Project Creator
echo ============================================
echo.

set /p PROJECT_NAME=Nombre del proyecto: 
set /p DEST_PATH=Ruta destino (ej: C:\Work): 
set /p DESCRIPTION=Descripcion corta: 
set /p AUTHOR=Autor/Owner: 

if "%PROJECT_NAME%"=="" (
  echo Debes indicar un nombre de proyecto.
  pause
  exit /b 1
)

if "%DEST_PATH%"=="" (
  set DEST_PATH=.
)

if "%DESCRIPTION%"=="" (
  set DESCRIPTION=New software project
)

if "%AUTHOR%"=="" (
  set AUTHOR=%USERNAME%
)

python "%~dp0scaffold_project.py" "%PROJECT_NAME%" --dest "%DEST_PATH%" --description "%DESCRIPTION%" --author "%AUTHOR%" --init-git

echo.
pause

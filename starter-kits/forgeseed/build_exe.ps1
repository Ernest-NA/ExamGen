param(
    [string]$OutputName = "codex-project-creator"
)

Write-Host "Instalando PyInstaller..." -ForegroundColor Cyan
python -m pip install --upgrade pip pyinstaller

Write-Host "Generando ejecutable..." -ForegroundColor Cyan
pyinstaller `
  --onefile `
  --name $OutputName `
  --add-data "repo-template;repo-template" `
  scaffold_project.py

Write-Host ""
Write-Host "Ejecutable generado en dist\$OutputName.exe" -ForegroundColor Green
Write-Host "Puedes distribuir ese .exe junto con la carpeta repo-template embebida." -ForegroundColor Yellow

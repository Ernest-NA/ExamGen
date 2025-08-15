# ExamGen
Aplicación de escritorio multiplataforma que permita gestionar bancos de preguntas y generar exámenes personalizados para facilitar el estudio.

## Instalación

1. Instala [pyenv-win](https://github.com/pyenv-win/pyenv-win) y agrega su carpeta `bin` al `PATH`.
2. Ejecuta `pyenv install 3.11.9` y `pyenv local 3.11.9` dentro del proyecto.
3. Instala las dependencias con `python -m pip install -r requirements.txt`.
4. Qt Designer se incluye al instalar `pyside6-tools`.

## Logging

Cuando `debug_mode` está habilitado, los archivos de registro se guardan en la
carpeta devuelta por `platformdirs.user_log_dir("ExamGen")` (p. ej.
`~/.local/state/ExamGen` en Linux).

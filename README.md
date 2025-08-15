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

## Modo Web Local

1. Crea un entorno virtual y instala dependencias:
   `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
2. Inicia la app con `python -m examgen_web.app` y abre `http://127.0.0.1:5000/`.
3. Usa la variable `EXAMGEN_DB_URL` para apuntar a otra base de datos
   (por defecto `sqlite:///./examgen.db`).

### Backups

Antes de migrar o actualizar la base de datos, crea un respaldo:
`sqlite3 examgen.db ".backup examgen.db.bak"`.

### Importar y ajustar

- `/import` permite cargar exámenes en formato **JSON** o **CSV** (máx. 10 MB) y
  realizar una vista previa antes de confirmar.
- `/settings` muestra el estado de la base de datos, historial y
  dependencias locales. Desde aquí puedes crear un backup, restaurar una
  copia (`.db`) o limpiar el historial de eventos.
- Al restaurar una base de datos se guarda en una ruta nueva y se sugiere
  la `EXAMGEN_DB_URL` correspondiente; es necesario reiniciar la aplicación
  para que surta efecto.

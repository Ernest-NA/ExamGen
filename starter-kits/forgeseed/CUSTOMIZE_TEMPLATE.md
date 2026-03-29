# Cómo personalizar la plantilla al crear un proyecto nuevo

Cuando uses `scaffold_project.py`, la plantilla sustituye automáticamente estos tokens:

- `__PROJECT_NAME__` → nombre visible del proyecto
- `__PROJECT_SLUG__` → slug técnico en minúsculas y con guiones
- `__PROJECT_DESCRIPTION__` → descripción corta del proyecto
- `__AUTHOR__` → owner o autor inicial

## Sustituciones automáticas

### 1. Archivos raíz
- `repo-template/README.md`
- `repo-template/AGENTS.md`

### 2. Seeds de Notion
- `repo-template/notion/csv/projects.csv`
- `repo-template/notion/csv/features.csv`
- `repo-template/notion/csv/skills-catalog.csv`

## Qué debes revisar manualmente después de crear el proyecto

### Obligatorio
1. `AGENTS.md`
   - Ajusta stack real
   - Ajusta reglas de validación
   - Ajusta políticas de dependencias
   - Ajusta definición de terminado (`Done means`)

2. `docs/architecture/system-overview.md`
   - dominio
   - usuarios
   - integraciones
   - flujo principal
   - restricciones de seguridad

3. `docs/product/vision.md`
   - problema
   - resultado esperado
   - no-objetivos

4. `docs/product/roadmap.md`
   - now / next / later reales del proyecto

5. `.agents/skills/`
   - elimina skills que no apliquen
   - especializa skills por stack
   - añade skills específicas si el proyecto lo requiere

6. `.github/workflows/ci.yml`
   - sustituye el `echo` por lint, test y build reales

7. `notion/csv/*.csv`
   - revisa estados, quarter, ejemplos y seeds iniciales antes de importar en Notion

### Recomendado
8. `.github/ISSUE_TEMPLATE/*`
   - adapta la taxonomía de issues a tu flujo real

9. `.github/pull_request_template.md`
   - añade checklists de tu stack o compliance interno

10. `docs/runbooks/*`
   - añade pasos reales de setup, release e incidencias

## Qué conviene renombrar o crear según el stack

### Salesforce
- añade `force-app/`
- añade skills de Apex, LWC y packaging
- ajusta CI para SFDX / sf CLI

### Python
- añade `pyproject.toml`
- añade entorno virtual y tooling (`ruff`, `pytest`, etc.)

### Node / TypeScript
- añade `package.json`
- añade `tsconfig.json`
- ajusta scripts de lint, test y build

## Qué NO debes dejar tal cual
- descripciones genéricas
- roadmap de ejemplo
- criterios de aceptación ficticios
- seeds de Notion sin revisar
- workflow CI placeholder

## Orden recomendado al clonar la plantilla
1. Crear proyecto con `scaffold_project.py`
2. Revisar `AGENTS.md`
3. Completar `docs/architecture/system-overview.md`
4. Completar `docs/product/vision.md` y `roadmap.md`
5. Adaptar skills
6. Configurar CI real
7. Hacer primer commit
8. Crear repo dedicado en GitHub
9. Importar seeds revisados en Notion

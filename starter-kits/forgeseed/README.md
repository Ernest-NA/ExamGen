# Codex + Notion + GitHub Starter

Plantilla base para iniciar proyectos de software con una estructura pensada para:
- **Codex**: instrucciones persistentes (`AGENTS.md`) + skills reutilizables.
- **GitHub**: código, issues, PRs y CI.
- **Notion**: roadmap, specs, decisiones y catálogo de skills.

## Qué incluye
- `repo-template/`: plantilla del repositorio base.
- `scaffold_project.py`: generador de nuevos proyectos.
- `new-codex-project.bat`: lanzador sencillo para Windows.
- `build_exe.ps1`: ejemplo para empaquetar el generador en `.exe`.

## Uso rápido en Windows
1. Instala Python 3.11+.
2. Haz doble clic en `new-codex-project.bat`.
3. Indica:
   - Nombre del proyecto
   - Ruta destino
   - Descripción
   - Autor

También puedes usar consola:

```bash
python scaffold_project.py "Mi Proyecto" --dest "C:\Work" --description "Sistema de traducción con IA" --author "Ernesto"
```

## Resultado
Se creará una carpeta de proyecto con:
- `AGENTS.md`
- `.agents/skills/`
- `.github/`
- `docs/`
- `src/`
- `tests/`
- `notion/` con plantillas CSV y guía de bases de datos

## Convertir en `.exe`
Revisa `build_exe.ps1`. Usa PyInstaller para generar un ejecutable Windows.

## Notas
- La plantilla está preparada para un **MVP genérico**.
- Puedes duplicar o especializar skills por stack: Salesforce, Java, Python, Node, etc.

# AGENTS.MD — ExamGen · **Migración a Web Local** (v2025-08-15)

> **Propósito:** Guía operativa para que agentes (Codex / CLINE VS Code / Sr. Dev) ejecuten la migración de **ExamGen** a un **modelo web 100% local**, elegante visualmente, **reutilizando al máximo** el código y **manteniendo las tablas existentes** del repositorio `Ernest-NA/ExamGen`. El README del repo define el objetivo de “gestionar bancos de preguntas y generar exámenes personalizados”, lo cual rige el alcance funcional de esta migración. ([GitHub][1])

> **Pilares técnicos:** **Flask** (web minimalista), **Jinja2** (SSR), **Pico.css** (estética elegante sin build), **HTMX** opcional (interactividad progresiva sin SPA), **SQLite + SQLAlchemy 2.x** (ORM). Flask es un micro‑framework ligero; Pico.css ofrece estilos elegantes con HTML semántico por defecto; HTMX permite AJAX/WebSockets desde atributos HTML sin frameworks SPA; SQLAlchemy 2.x aporta ORM moderno. ([Flask][2], [Pico CSS][3], [Htmx][4], [SQLAlchemy Documentation][5])

---

## 0) **Alcance, principios y restricciones**

**Alcance de la migración**

* Ejecutar **siempre en local** (sin dependencias cloud; los *feature flags* deben poder desactivar cualquier integración externa).
* **Mantener paridad funcional** con la solución actual (banco de preguntas, generación/edición, previsualización, exportación).
* **Reutilizar las tablas existentes** y la lógica de dominio ya disponible en el repo; si no existe una capa de dominio, crearla extraída de los scripts actuales.
* UI **elegante** y ligera, sin toolchains de build: CSS de una sola hoja y SSR.

**No‑objetivos**

* No transformar el proyecto en SPA ni introducir frameworks pesados.
* No romper ni renombrar tablas. Migraciones **solo aditivas**.

**Principios**

* **KISS** (simple), **idempotencia** (repetir ≈ mismo resultado), **contratos explícitos**, **observabilidad local** (logs).
* **Compatibilidad primero**: cualquier cambio de esquema es la última opción (y con *backup* previo).

---

## 1) **Arquitectura de alto nivel**

```
+-----------------------------+       +---------------------+
|          Web UI             |       |   Exportadores      |
|  Flask + Jinja2 (+HTMX)     |       |  CSV / JSON / PDF   |
+---------------+-------------+       +----------+----------+
                |                                 |
                v                                 v
+---------------+---------------------------------+---------+
|                  Capa de Dominio (Reusada)                |
|  Servicios/Use Cases: Exams, Sections, Questions, Review  |
+---------------+---------------------------+---------------+
                |                           |
                v                           v
+---------------+---------------+   +-------+----------------+
| Repos/DAO (Reusado o Nuevo)   |   | Historian/Audit (log) |
| SQLAlchemy 2.x → SQLite       |   | Revisiones, diffs     |
+---------------+---------------+   +-------+----------------+
                |
                v
           +----+----+
           |  DB     |  (Esquema existente, cambios solo aditivos)
           +---------+
```

**Notas clave**

* **Web UI** orquesta; **no** implementa reglas de negocio.
* **Dominio y repos** se reutilizan (o se extraen del código actual si están acoplados).
* **HTMX** es opcional para acciones inline (crear sección/pregunta sin recargar), manteniendo SSR. ([Htmx][6])

---

## 2) **Compatibilidad de tablas (DB) y plan de introspección**

**Objetivo:** mantener esquema **tal cual**, permitiendo únicamente **adds** no destructivos (p. ej., columnas opcionales para metadata de UI).

**Procedimiento (automatizable)**

1. **Inventario/Introspección**: ejecutar `PRAGMA table_info(<tabla>)` y `SELECT name, sql FROM sqlite_master WHERE type='table'` para **volcar el DDL actual**.
2. **Mapeo ORM**: generar *models* SQLAlchemy 2.x a partir del esquema (tipos, claves, FKs). ([SQLAlchemy Documentation][5])
3. **Congelación del contrato**: guardar `schema_snapshot.json` (por tabla: columnas, tipos, índices).
4. **Política de cambios**:

   * **Permitido**: `ALTER TABLE ADD COLUMN` (nullable, con `DEFAULT` si procede).
   * **No permitido**: renombrar o eliminar columnas/tablas.
5. **Backup/Restore**: script `scripts/backup_db.py` (`sqlite3 dbfile ".backup <dst>"` o `.dump`).

**Si el esquema no existe aún** (proyecto incipiente), levantamos **M1 baseline** (ver §6.1 esquemas JSON) y lo instanciamos como primera migración — siempre en archivos SQL (no herramientas pesadas).

---

## 3) **Mapa de agentes** (quién hace qué y con qué entradas/salidas)

> Los agentes son “roles ejecutores” pensados para Codex/CLINE. Cada agente tiene **Inputs**, **Outputs**, **Responsabilidades**, **Heurísticas** y **Errores comunes**.

### 3.1 **SchemaInspectorAgent**

* **Rol**: introspección del esquema real, modelado ORM y verificación de compatibilidad.
* **Input**: ruta DB local; tablas esperadas (si las hay).
* **Output**: `schema_snapshot.json`, `models.py` (SQLAlchemy 2.x anotado), reporte de diferencias.
* **Heurísticas**: mantener nombres de tabla y tipos existentes; usar `Mapped[...]` y `mapped_column()` idiomático 2.x. ([SQLAlchemy Documentation][5])
* **Errores comunes**: inferir `Integer` donde debe ser `Text`; olvidar `ForeignKey` o `index=True`.

### 3.2 **DomainAgent**

* **Rol**: servicios de negocio (crear examen, añadir sección/pregunta, editar, listar, previsualizar).
* **Input**: DTOs/params desde Web UI.
* **Output**: entidades de dominio (instancias ORM) y resultados listos para persistencia/export.

### 3.3 **WebAgent**

* **Rol**: endpoints Flask, validación mínima, orquestación de servicios y render con Jinja2.
* **Input**: peticiones HTTP; formularios HTML.
* **Output**: vistas HTML/descargas; fragmentos parciales si HTMX.
* **Heurísticas**: SSR primero; si hay HTMX, exponer rutas `/partials/*`. Flask es idóneo para apps ligeras locales. ([Flask][2])

### 3.4 **UXAgent**

* **Rol**: aplicar estilo elegante “sin build”: **Pico.css**, tipografía/espaciados, componentes accesibles.
* **Heurísticas**: layout centrado 960–1140px, formularios con *labels* claros, estados de error; evitar sobre‑estilizar. Pico.css da base moderna con HTML semántico. ([Pico CSS][3])

### 3.5 **ExporterAgent**

* **Rol**: exportar a CSV/JSON/PDF (con/sin soluciones).
* **Heurísticas**: CSV con columnas estables; JSON siguiendo contratos del §6; PDF vía HTML→PDF (WeasyPrint) u opción simple.

### 3.6 **HistorianAgent**

* **Rol**: auditar cambios (revisiones/diffs).
* **Heurísticas**: registrar `entity`, `action`, `before/after` ligeros; persistir en tabla dedicada o en log estructurado.

### 3.7 **ReviewerAgent**

* **Rol**: validaciones de calidad de ítems (única respuesta correcta en MCQ, distractores plausibles, no ambigüedad).
* **Heurísticas**: *lint* de preguntas; rechazar si faltan campos clave.

### 3.8 **(Opcional) GeneratorAgent**

* **Rol**: generación asistida de ítems (stub local por defecto); *feature flag* para LLM offline/externo.
* **Heurísticas**: nunca depender de red por defecto; permitir *seed* reproducible.

### 3.9 **QAAgent**

* **Rol**: pruebas *smoke* web y pruebas de dominio; cobertura mínima crítica.
* **Heurísticas**: tests para `/health`, `/`, CRUD básico, exportadores.

---

## 4) **Rutas (HTTP)** y flujos

**Principio:** REST sencillo + SSR; si **HTMX**, exponer `/partials/*` para fragmentos. ([Htmx][4])

| Método | Ruta                         | Descripción                            |       |          |
| -----: | ---------------------------- | -------------------------------------- | ----- | -------- |
|    GET | `/`                          | Dashboard (resumen + CTA crear examen) |       |          |
|    GET | `/exams`                     | Listado de exámenes                    |       |          |
|    GET | `/exams/new`                 | Form crear examen                      |       |          |
|   POST | `/exams`                     | Crear examen                           |       |          |
|    GET | `/exams/<id>`                | Detalle (secciones + preguntas)        |       |          |
|   POST | `/exams/<id>/sections`       | Crear sección                          |       |          |
|   POST | `/sections/<id>/questions`   | Crear pregunta                         |       |          |
|    GET | `/questions/<id>/edit`       | Form edición de pregunta               |       |          |
|   POST | `/questions/<id>`            | Guardar edición                        |       |          |
|    GET | `/exams/<id>/preview`        | Previsualización (solo lectura)        |       |          |
|   POST | `/exams/<id>/export?fmt=csv|json|pdf` | Exportar |

**Partials (si HTMX)**

* `GET /partials/section/<id>` → lista preguntas de la sección.
* `GET /partials/exam/<id>/summary` → resumen para dashboard.

**Flujos de usuario**

1. Crear examen → añadir secciones → añadir/generar preguntas → revisar → exportar.
2. Edición puntual de una pregunta desde el detalle (con historial).
3. Exportación con/sin soluciones.

---

## 5) **Estructura de proyecto propuesta (añadidos mínimos)**

```
.
├─ examgen_web/                 # NUEVO (capa web)
│  ├─ app.py                    # create_app() + run local
│  ├─ routes/
│  │  ├─ home.py  health.py
│  │  ├─ exams.py sections.py questions.py export.py
│  ├─ templates/
│  │  ├─ base.html dashboard.html exams_list.html
│  │  ├─ exam_form.html exam_detail.html question_form.html
│  │  └─ preview.html (y opc. partials/*.html si HTMX)
│  └─ static/
│     ├─ css/pico.min.css
│     └─ js/htmx.min.js (opcional)
├─ src/examgen/                 # EXISTENTE o a extraer
│  ├─ domain/ (services.py, validators.py, exporters/)
│  ├─ data/ (models.py, repo.py, session.py)
│  └─ utils/ (logging.py, config.py)
├─ scripts/ (backup_db.py, inspect_schema.py)
├─ tests/ (test_web_smoke.py, test_domain.py, test_export.py)
├─ requirements.txt  /  pyproject.toml
└─ README.md  (añadir “Modo Web Local”)
```

> **Nota de implementación:** Flask (SSR), HTMX en caso de querer interacciones progresivas sin SPA; SQLAlchemy 2.x para el ORM. ([Flask][2], [Htmx][4], [SQLAlchemy Documentation][5])

---

## 6) **Contratos de datos (JSON)**

> **Meta‑regla:** estos **contratos UI/API** son *lógicos*; el mapeo a tablas **no debe romper el esquema**. Si una columna no existe, persistir el dato como `metadata` (JSON) o **omitir** con degradación elegante.

### 6.1 `Exam`

```json
{
  "id": 123,
  "title": "Álgebra — Parcial 1",
  "description": "Temas: polinomios, factorización",
  "language": "es-ES",
  "created_at": "2025-08-15T10:12:00Z",
  "updated_at": "2025-08-15T10:12:00Z",
  "metadata": { "owner": "local-user" }
}
```

### 6.2 `Section`

```json
{
  "id": 77,
  "exam_id": 123,
  "title": "Polinomios",
  "order": 1,
  "metadata": { "notes": "nivel medio" }
}
```

### 6.3 `Question`

```json
{
  "id": 501,
  "section_id": 77,
  "type": "mcq",         // "mcq" | "true_false" | "short"
  "stem": "¿Cuál es el grado de 3x^2 - 5x + 2?",
  "choices": ["1", "2", "3", "4"],
  "answer": "2",
  "rationale": "El mayor exponente es 2",
  "difficulty": "easy",
  "tags": ["polinomios"],
  "metadata": { "source": "manual" }
}
```

### 6.4 `ReviewReport`

```json
{
  "issues": [
    { "question_id": 501, "type": "ambiguity", "note": "dos opciones plausibles" }
  ],
  "actions": [
    { "question_id": 501, "fix": "ajustar distractor '3'" }
  ]
}
```

---

## 7) **Directrices de UI/UX (elegante sin build)**

* **Base**: **Pico.css** (clase‑less / HTML semántico). Layout centrado, 960–1140px; tipografía legible; espaciados generosos; *focus states* claros; *dark mode* opcional que trae Pico. ([Pico CSS][3])
* **Formularios**: validar server‑side; mensajes de error debajo del campo.
* **Tablas/Lists**: densidad media, paginación simple.
* **Interacciones (opcional)**: **HTMX** para crear sección/pregunta sin recargar (`hx-post`, `hx-target`, `hx-swap`). ([Htmx][4])
* **PDF**: plantilla HTML A4 (márgenes de 18–22 mm), números de pregunta, separación clara entre ítems.

---

## 8) **Política de errores, logging y seguridad**

* **Errores**: páginas 4xx/5xx estilizadas; *flash messages* para éxito/error.
* **Logging**: rotación local; incluir `request_id` y `user_id` (local).
* **Seguridad local**: sin cuentas ni redes por defecto; si hay sesión, usar cookie segura (misma máquina).
* **Datos**: cifrar backups si contienen soluciones.

---

## 9) **Tareas (Workpacks) y Criterios de aceptación**

> Las tareas se ejecutan en ramas `feature-EXG-6-<slug>` desde `main`.
> *Cada PR debe incluir:* checklist de criterios, captura(s) de pantalla y nota de riesgos.

### EXG‑6.1 — **Bootstrap Web** (Flask + templates base)

* **Hecho cuando**: `python -m examgen_web.app` levanta `http://127.0.0.1:5000/` con dashboard y `/health` 200.
* **Incluye**: `base.html`, `dashboard.html`, Pico.css local.

### EXG‑6.2 — **Introspección DB + ORM 2.x**

* **Hecho cuando**: existe `scripts/inspect_schema.py`, `schema_snapshot.json` y `src/examgen/data/models.py` con mapeos 2.x y FK/índices.
* **No rompe**: ninguna tabla (comparado con `schema_snapshot.json`).

### EXG‑6.3 — **CRUD Exam**

* **Hecho cuando**: `/exams`, `/exams/new`, `POST /exams`, `/exams/<id>` operan; validación `title` requerida.

### EXG‑6.4 — **Secciones & Preguntas**

* **Hecho cuando**: se pueden crear secciones y preguntas desde el detalle del examen; edición de pregunta funciona; (si HTMX) actualiza fragmentos sin recarga.

### EXG‑6.5 — **Previsualización + Export CSV/JSON/PDF**

* **Hecho cuando**: `/exams/<id>/preview` renderiza A4‑friendly; `POST /exams/<id>/export?fmt=csv|json|pdf` descarga archivos correctos.

### EXG‑6.6 — **Historian / Auditoría**

* **Hecho cuando**: se registran diffs (mínimo `entity`, `action`, `before/after`) al crear/editar; se muestran en el detalle.

### EXG‑6.7 — **QA & Docs**

* **Hecho cuando**: `tests/test_web_smoke.py` (200 en `/` y `/health`), pruebas de dominio básicas, README con “Modo Web Local” y variable `EXAMGEN_DB_URL`.

---

## 10) **Convenciones, tooling y entorno**

* **Python**: 3.11+ (alineado con el entorno del repo).
* **Estilo**: `black`, `ruff`; `pytest` + `pytest-flask`.
* **Dependencias clave**: `flask`, `jinja2`, `sqlalchemy>=2`, `pydantic` (opcional), `weasyprint` (opcional), `python-dotenv`.
* **Config**: `.env` (ej.: `EXAMGEN_DB_URL=sqlite:///./examgen.db`, `DEBUG=1`, `ENABLE_LLM=0`).
* **Ejecución**: `python -m examgen_web.app`.
* **Backups**: `python scripts/backup_db.py ./examgen.db ./backups/backup-YYYYmmddHHMM.db`.
* **Justificación técnica**: Flask (ligero, rápido para empezar), Pico.css (elegancia sin build) y HTMX (interactividad progresiva). ([Flask][2], [Pico CSS][3], [Htmx][4])

---

## 11) **Prompts plantilla para agentes (Codex / CLINE)**

> **Formato**: *Pregunta · Requisito · Objetivo · Alcance · Contexto · Prioridad* (alineado con nuestras pautas de commits limpios).

### 11.1 `SchemaInspectorAgent` — *introspección y modelos*

```
Pregunta
¿Generar los modelos SQLAlchemy 2.x a partir del esquema SQLite actual sin romper tablas?

Requisito
- Leer EXAMGEN_DB_URL.
- Inspeccionar tablas con PRAGMA y sqlite_master.
- Emitir schema_snapshot.json y models.py (ORM 2.x con Mapped, mapped_column, ForeignKey, relationship).
- No renombrar ni borrar columnas. Solo cambios aditivos si fuesen imprescindibles (separar en PR).

Objetivo
Persistir y consultar Exámenes, Secciones, Preguntas, Revisiones con ORM 2.x.

Alcance
- scripts/inspect_schema.py
- src/examgen/data/models.py
- src/examgen/data/session.py (SessionLocal)
- tests/test_schema_snapshot.py (valida igualdad al snapshot)

Contexto
SQLite local. SQLAlchemy 2.x. Sin migraciones destructivas.

Prioridad
Alta
```

### 11.2 `WebAgent` — *esqueleto + dashboard + health*

```
Pregunta
¿Crear la capa web local con Flask y vistas base elegantes?

Requisito
- examgen_web/app.py con create_app().
- Rutas: "/" y "/health".
- Templates: base.html (layout con Pico.css) y dashboard.html.
- Sin JS aún; preparar bloque para insertar HTMX luego.

Objetivo
python -m examgen_web.app -> servidor local operativo.

Alcance
- examgen_web/app.py, examgen_web/routes/{home.py,health.py}
- examgen_web/templates/{base.html,dashboard.html}
- examgen_web/static/css/pico.min.css (vendor)

Contexto
Ejecutar local; SSR con Jinja2.

Prioridad
Alta
```

### 11.3 `WebAgent` — *CRUD Exam*

```
Pregunta
¿Implementar CRUD mínimo de Exam (listar, crear, detalle) orquestando el dominio?

Requisito
- GET /exams, GET /exams/new, POST /exams, GET /exams/<id>.
- Validación title requerido.
- Delegar en servicios de dominio (no lógica en rutas).

Objetivo
Crear y consultar exámenes desde el navegador.

Alcance
- examgen_web/routes/exams.py
- examgen_web/templates/{exams_list.html,exam_form.html,exam_detail.html}
- Navegación desde dashboard

Contexto
SQLAlchemy 2.x; Session por request.

Prioridad
Alta
```

### 11.4 `WebAgent` — *Secciones/Preguntas (+HTMX opcional)*

```
Pregunta
¿Añadir secciones y preguntas desde el detalle del examen, con edición inline?

Requisito
- POST /exams/<id>/sections, POST /sections/<id>/questions
- GET /questions/<id>/edit, POST /questions/<id>
- Si HTMX: exponer /partials/* y devolver fragmentos.

Objetivo
Gestionar contenido del examen sin salir del detalle.

Alcance
- examgen_web/routes/{sections.py,questions.py}
- templates: section_form.html, question_form.html (y partials/*.html si aplica)
- Actualizar exam_detail.html

Contexto
Validación server-side; Historian hooks.

Prioridad
Alta
```

### 11.5 `ExporterAgent` — *Previsualización + Export*

```
Pregunta
¿Generar previsualización HTML y exportaciones CSV/JSON/PDF?

Requisito
- GET /exams/<id>/preview (A4-friendly)
- POST /exams/<id>/export?fmt=csv|json|pdf
- CSV columnas estables; JSON según contratos §6; PDF desde template HTML.

Objetivo
Descargar artefactos listos para imprimir o integrar.

Alcance
- examgen_web/routes/export.py
- src/examgen/domain/exporters/{csv_exporter.py,json_exporter.py,pdf_exporter.py}
- templates/pdf_template.html (si HTML→PDF)

Contexto
Local; sin dependencias cloud.

Prioridad
Media
```

### 11.6 `HistorianAgent` — *auditoría*

```
Pregunta
¿Registrar revisiones/diffs en cada operación de alta/edición?

Requisito
- Función record_revision(entity, action, payload_diff).
- Persistir en tabla existente o nueva aditiva 'revision'.
- Mostrar historial en el detalle del examen.

Objetivo
Trazabilidad básica de cambios.

Alcance
- src/examgen/domain/services.py (hooks)
- examgen_web/templates/exam_detail.html (panel "Historial")

Prioridad
Media
```

### 11.7 `QAAgent` — *pruebas y docs*

```
Pregunta
¿Asegurar smoke tests web y actualizar documentación de ejecución local?

Requisito
- tests/test_web_smoke.py -> 200 en "/" y "/health"
- README: "Modo Web Local", EXAMGEN_DB_URL, backups.

Objetivo
Ejecución reproducible y validable en local.

Alcance
- tests/test_web_smoke.py
- README.md

Prioridad
Alta
```

---

## 12) **Criterios de “Definition of Done” (por PR)**

* [ ] No se rompe el esquema (diff con `schema_snapshot.json` sin cambios destructivos).
* [ ] UI accesible, limpia y **elegante** (capturas incluidas).
* [ ] Logs locales sin secretos.
* [ ] Tests *smoke* verdes; exportadores generan artefactos válidos.
* [ ] README actualizado (pasos de ejecución, variables, backups).
* [ ] Commits limpios y mensaje con **Objetivo/Alcance/Contexto**.

---

## 13) **Notas de diseño y justificación (breve)**

* **Flask + SSR**: mejor *time‑to‑first‑feature* y simplicidad para entorno **local**. ([Flask][2])
* **Pico.css**: estética **moderna y elegante** sin *build step*, ideal para este caso. ([Pico CSS][3])
* **HTMX (opcional)**: interactividad sin SPA ni JS complejo; focos en productividad. ([Htmx][4])
* **SQLAlchemy 2.x**: ORM moderno, tipado y patrones 2.0 alineados al futuro de la librería. ([SQLAlchemy Documentation][5])

---

## 14) **Apéndice A — Esqueleto de servicios (pseudo‑interfaces)**

> **Nota**: contratos lógicos; adaptar a nombres reales de tablas/columnas.

```python
# src/examgen/domain/services.py
class ExamService:
    def list_exams(self) -> list[Exam]: ...
    def create_exam(self, spec: dict) -> Exam: ...
    def get_exam(self, exam_id: int) -> Exam: ...

class SectionService:
    def add_section(self, exam_id: int, title: str, order: int|None=None) -> Section: ...
    def list_sections(self, exam_id: int) -> list[Section]: ...

class QuestionService:
    def add_question(self, section_id: int, payload: dict) -> Question: ...
    def update_question(self, question_id: int, patch: dict) -> Question: ...
    def list_questions(self, section_id: int) -> list[Question]: ...
```

---

## 15) **Apéndice B — Plantilla de commit**

```
feat(EXG-6): <resumen>

Pregunta: <qué problema resuelve>
Requisito: <qué se pidió>
Objetivo: <resultado observable>
Alcance: <archivos tocados>
Contexto: <riesgos/decisiones>
```

---

## 16) **Apéndice C — Lanzamiento local (modo Web)**

1. Crear venv e instalar dependencias (`flask`, `sqlalchemy>=2`, etc.).
2. Configurar `EXAMGEN_DB_URL` (si no se especifica, usar `sqlite:///./examgen.db`).
3. `python -m examgen_web.app` → abrir `http://127.0.0.1:5000/`.
4. **Opcional**: habilitar HTMX incluyendo `htmx.min.js` en `base.html`. ([Htmx][4])

---

### Referencias clave

* Repo base y objetivo funcional (banco de preguntas/generación): **Ernest‑NA/ExamGen**. ([GitHub][1])
* Flask (micro‑framework web). ([Flask][2])
* Pico.css (UI elegante con HTML semántico, sin build). ([Pico CSS][3])
* HTMX (interactividad progresiva, sin SPA). ([Htmx][4])
* SQLAlchemy 2.x (ORM moderno). ([SQLAlchemy Documentation][5])

---

**Fin del AGENTS.MD**

[1]: https://github.com/Ernest-NA/ExamGen "GitHub - Ernest-NA/ExamGen: Aplicación de escritorio multiplataforma que permita gestionar bancos de preguntas y generar exámenes personalizados para facilitar el estudio."
[2]: https://flask.palletsprojects.com/?utm_source=chatgpt.com "Welcome to Flask — Flask Documentation (3.1.x)"
[3]: https://picocss.com/?utm_source=chatgpt.com "Pico CSS • Minimal CSS Framework for semantic HTML"
[4]: https://htmx.org/docs/?utm_source=chatgpt.com "</> htmx ~ Documentation"
[5]: https://docs.sqlalchemy.org/?utm_source=chatgpt.com "SQLAlchemy Documentation — SQLAlchemy 2.0 ..."
[6]: https://htmx.org/?utm_source=chatgpt.com "</> htmx - high power tools for html"

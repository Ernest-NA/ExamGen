A continuación se muestra el **contenido completo** del archivo `AGENTS.md` listo para colocarse en la raíz del repositorio `ExamGen`.
El formato sigue la plantilla recomendada por OpenAI Codex para maximizar la eficacia de los agentes y está adaptado a las convenciones vigentes del proyecto.

---

```markdown
# AGENTS.md
Guía de coordinación para agentes automatizados en **ExamGen**  
Última actualización : 14 jun 2025

---

## 1. Visión general del proyecto
ExamGen es una aplicación de escritorio (PySide 6) para crear, ejecutar y evaluar exámenes de opción múltiple, respaldada por SQLAlchemy 2.0 y SQLite. El código vive en `src/examgen/`; el punto de entrada es `python -m examgen` (o el ejecutable instalado por *entry‑point*).

Los agentes que lean este archivo deben:

* Comprender la **estructura de carpetas** (⇲ §2).
* Respetar las **convenciones de código** y de **commits** (⇲ §3).
* Ejecutar **pruebas** y **migraciones** siguiendo los comandos indicados (⇲ §4).
* Seguir el **flujo de trabajo** descrito (⇲ §5) según su rol (⇲ §6).

---

## 2. Estructura de carpetas (resumen)

```

examgen/
├─ core/                 # Lógica y modelos
│  ├─ models.py          # Declaraciones ORM
│  ├─ database.py        # SessionLocal, run\_migrations()
│  └─ services/
│      └─ exam\_service.py
├─ gui/
│  ├─ app.py             # QApplication + run\_migrations()
│  ├─ windows/
│  │   ├─ main\_window\.py
│  │   └─ questions\_window\.py
│  ├─ dialogs/
│  │   ├─ question\_dialog.py   # Crear / editar pregunta
│  │   ├─ history\_dialog.py    # Historial intentos
│  │   └─ results\_dialog.py
│  └─ widgets/
│      └─ option\_table.py      # 3‑5 filas, papeleras, lápiz
├─ ui/                  # (reservado para .ui)
└─ tests/               # Pytest

```

*Las rutas son absolutas respecto a `src/`. Todos los nuevos archivos GUI deben ir en la jerarquía `gui/`; lógica de negocio en `core/`.*

---

## 3. Guía de desarrollo

### 3.1 Estilo de código  
* PEP8 + typing obligatorio.  
* Longitud de línea ≈ 79 caracteres.  
* Variables y funciones en `snake_case`; clases en `PascalCase`.  
* Mantener docstrings y comentarios concisos cuando aporten valor.  
* Evitar duplicación; preferir funciones cortas y cohesivas.

### 3.2 Commits convencionales  
`<tipo>(<ámbito>): descripción imperativa`  

Tipos habituales : `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.  
Ejemplo : `feat(gui): añadir columna lápiz para edición`.

---

## 4. Pruebas y comandos

| Acción | Comando |
|--------|---------|
| Ejecutar aplicación | `python -m examgen` |
| Migraciones manuales | `python -m examgen.core.migrations.fix_attempt_fk` |
| Ejecutar tests | `pytest -q` |
| Linter | `flake8 src/ tests/` |

*Los agentes deben correr `pytest` antes de proponer un merge. *

---

## 5. Flujo de trabajo por feature

1. **Diseño y alcance** → definir cambios.  
2. **Migración (si aplica)** → actualizar modelos y crear script alembic.  
3. **Lógica core** → implementar en `core/services` o `core/models`.  
4. **GUI** → añadir/editar diálogos o ventanas en `gui/`.  
5. **Pruebas** → unitarias + interacción GUI (pytest‑qt).  
6. **Commit & PR** → mensajes semánticos, un commit por cambio lógico.  
7. **Revision / merge** → tester verifica; si pasa, integrar en `main`.

---

## 6. Roles de agentes

### 6.1 `developer_senior_ai`
| Responsabilidad | Descripción |
|-----------------|-------------|
| Código | Implementar features y fixes siguiendo §3. |
| Migraciones | Crear scripts idempotentes; respetar FK ON DELETE CASCADE. |
| Commits | Cumplir convención; mantener historial limpio. |
| Comunicación | Emitir prompts claros al tester (véase §7). |

### 6.2 `tester_ai`
| Responsabilidad | Descripción |
|-----------------|-------------|
| Tests unitarios | Cobertura de lógica core y modelos. |
| Tests GUI | Verificar diálogos/ventanas con pytest‑qt. |
| Regresiones | Detectar fallos nuevos; reportar con stack‑trace mínimo. |
| Aprobación | Marcar feature como “test‑passed” antes del merge. |

---

## 7. Plantilla de prompt (para agentes)

```

### Tarea

> **Objetivo**
> \[En 1–2 frases]

**Alcance**

* Archivos: \[…]

**Contexto**

```python
# código o stack‑trace relevante
```

**Pasos**

1. …
2. …

**Resultado esperado**

* …

```

---

## 8. Ejemplo de prompt (feature EXG‑5)

> **Objetivo**  
> Corregir la edición de preguntas en `questions_window.py` (icono lápiz + DetachedInstanceError).

> **Alcance**  
> `examgen/gui/windows/questions_window.py`, `examgen/gui/dialogs/question_dialog.py`

> **Contexto**  
> * El icono no se ve (`QIcon.fromTheme` devuelve nulo).  
> * Click genera `DetachedInstanceError` al acceder a `q.subject`.  
> * Queremos abrir el diálogo con datos cargados **sin duplicar** registros.

> **Pasos**  
> 1. Usar icono reserva (`QStyle.SP_FileDialogDetailedView`) si el tema no devuelve ninguno.  
> 2. Pasar `question_id` en lugar de la instancia; re‑consultar con sesiones.  
> 3. En diálogo, si `question_id` != None → cargar pregunta vía `SessionLocal()`.  
> 4. Al guardar, actualizar en BD, commit, refrescar tabla.

> **Resultado esperado**  
> * Icono lápiz visible.  
> * Diálogo muestra datos, guarda cambios sobre la misma fila.  
> * Sin `DetachedInstanceError`.

---

## 9. Seguridad esencial

* Contraseñas con **bcrypt**.  
* Índices únicos en campos clave (p. ej. `Subject.name`).  
* `PRAGMA foreign_keys = ON` siempre activo.  
* Validar inputs (longitud máxima, caracteres).  

---

## 10. Contacto y soporte

En caso de dudas, los agentes deben consultar primero este archivo.  
Si la instrucción no está cubierta, escalar al *maintainer* humano.

```

---

## Prompt listo para continuar la feature EXG‑5 en otro chat

Copia‑pega todo lo siguiente en un nuevo hilo con Codex:

````md
### Tarea (EXG‑5)

> **Objetivo**  
> Arreglar la edición de preguntas en la ventana *Preguntas*.

**Alcance**  
* `src/examgen/gui/windows/questions_window.py`
* `src/examgen/gui/dialogs/question_dialog.py`

**Contexto**  
1. Se añadió una columna ✏️ antes de 🗑️ pero el icono no aparece.  
2. Al hacer clic, salta `DetachedInstanceError` al acceder a `q.subject.name`.  
3. GUI usa PySide6; modelos SQLAlchemy 2.0.  
4. Pregunta debe cargarse en el diálogo y guardar sin duplicar.

```python
# Traceback resumido
sqlalchemy.orm.exc.DetachedInstanceError: Instance <MCQQuestion ...> is not bound to a Session; attribute 'subject' ...
```

**Pasos propuestos**  
1. En la tabla, crear icono fallback:

```python
icon = QIcon.fromTheme("document-edit")
if icon.isNull():
    icon = self.style().standardIcon(QStyle.SP_FileDialogDetailedView)
```

2. Conectar click pasando `question_id`:

```python
edit_btn.clicked.connect(lambda _, qid=q.id: self._edit_question(qid))
```

3. En `_edit_question`, instanciar diálogo con `question_id` y recargar tabla tras `Accepted`.

4. En `QuestionDialog.__init__`, si `question_id` ≠ None:

```python
with SessionLocal() as s:
    self._question = (
        s.query(m.MCQQuestion)
          .options(joinedload(m.MCQQuestion.subject),
                   selectinload(m.MCQQuestion.options))
          .get(question_id)
    )
```

5. Pre‑cargar widgets; al guardar usar la misma instancia (merge/update).

**Resultado esperado**  
* Icono tulipán visible.  
* Diálogo abre con datos; al guardar actualiza la fila y BD.  
* Ya no ocurre DetachedInstanceError.  
* Tabla refresca sin duplicados.

````
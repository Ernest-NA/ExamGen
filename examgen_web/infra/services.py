"""
Facade de servicios de dominio para ser usado por la capa web.
No implementa lógica de negocio: solo importa (si existen) y expone factories.
"""

from typing import Any

# Por ahora, solo preparamos los imports; EXG-6.3 usará estas entradas.
try:
    from examgen.domain.services import ExamService, SectionService, QuestionService  # type: ignore
except Exception:
    ExamService = None  # type: ignore
    SectionService = None  # type: ignore
    QuestionService = None  # type: ignore


def get_exam_service(session: Any):
    if ExamService is None:
        raise RuntimeError(
            "ExamService no disponible. Asegura que src/examgen/domain/services.py existe."
        )
    return ExamService(session)


def get_section_service(session: Any):
    if SectionService is None:
        raise RuntimeError("SectionService no disponible.")
    return SectionService(session)


def get_question_service(session: Any):
    if QuestionService is None:
        raise RuntimeError("QuestionService no disponible.")
    return QuestionService(session)

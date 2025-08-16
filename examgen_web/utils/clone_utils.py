from __future__ import annotations

"""Utilities for cloning `MCQQuestion` records."""

from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

try:  # pragma: no cover - entornos sin el paquete principal
    from examgen.core import models as m
except Exception:  # pragma: no cover
    m = None  # type: ignore


# Fields considered when computing differences between questions
_DIFF_FIELDS = ["prompt", "explanation", "difficulty", "subject_id"]


def _next_version(current: str | None) -> str:
    """Return next semantic version given ``current`` (e.g., v1 -> v2)."""
    if not current:
        return "v1"
    try:
        num = int(str(current).lstrip("v")) + 1
    except Exception:
        return str(current)
    return f"v{num}"


def clone_question(
    session: Session, original: m.MCQQuestion, overrides: Dict[str, Any]
) -> Tuple[m.MCQQuestion, Dict[str, Any]]:
    """Clone ``original`` question applying ``overrides``.

    Parameters
    ----------
    session:
        Active SQLAlchemy session.
    original:
        Question to duplicate.
    overrides:
        Mapping with possible keys: ``prompt``, ``explanation``,
        ``difficulty``, ``subject_id``, ``options`` (list), ``version`` and
        ``meta`` (dict).

    Returns
    -------
    Tuple with the new question and a summary of changes.
    """

    if m is None:
        raise RuntimeError("Domain models not available")

    meta = dict(original.meta or {})
    meta.update(overrides.get("meta", {}))
    meta["cloned_from"] = original.id
    meta["version"] = overrides.get(
        "version", _next_version(meta.get("version"))
    )

    new_q = m.MCQQuestion(
        prompt=overrides.get("prompt", original.prompt),
        explanation=overrides.get("explanation", original.explanation),
        difficulty=overrides.get("difficulty", original.difficulty),
        subject_id=overrides.get("subject_id", original.subject_id),
        reference=original.reference,
        section=original.section,
        meta=meta,
    )
    session.add(new_q)

    options: List[Dict[str, Any]] = overrides.get("options", [])
    if not options:
        options = [
            {
                "text": opt.text,
                "is_correct": opt.is_correct,
                "answer": opt.answer,
                "explanation": opt.explanation,
            }
            for opt in original.options
        ]
    for opt_data in options:
        new_q.options.append(
            m.AnswerOption(
                text=opt_data.get("text", ""),
                is_correct=opt_data.get("is_correct", False),
                answer=opt_data.get("answer"),
                explanation=opt_data.get("explanation"),
            )
        )

    session.flush()

    # diff summary
    changes: Dict[str, Any] = {}
    for field in _DIFF_FIELDS:
        old_val = getattr(original, field)
        new_val = getattr(new_q, field)
        if old_val != new_val:
            changes[field] = {"from": old_val, "to": new_val}
    if original.meta != meta:
        changes["meta"] = {"from": original.meta, "to": meta}
    for idx, (old_opt, new_opt) in enumerate(
        zip(original.options, new_q.options)
    ):
        if (
            old_opt.text != new_opt.text
            or old_opt.is_correct != new_opt.is_correct
        ):
            changes.setdefault("options", []).append(
                {
                    "index": idx,
                    "from": {
                        "text": old_opt.text,
                        "is_correct": old_opt.is_correct,
                    },
                    "to": {
                        "text": new_opt.text,
                        "is_correct": new_opt.is_correct,
                    },
                }
            )

    return new_q, changes

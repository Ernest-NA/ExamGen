from __future__ import annotations

from flask import Request, session

from .audit import log_language_set
from ..i18n.translations import TRANSLATIONS

DEFAULT_LANG = "es"
SUPPORTED_LANGS = {"es", "en"}


def get_locale(req: Request) -> str:
    lang = req.args.get("lang")
    if lang in SUPPORTED_LANGS:
        session["lang"] = lang
        return lang
    lang = session.get("lang")
    if lang in SUPPORTED_LANGS:
        return lang
    lang = req.cookies.get("lang")
    if lang in SUPPORTED_LANGS:
        session["lang"] = lang
        return lang
    accept = req.headers.get("Accept-Language", "")
    for part in accept.split(","):
        code = part.split(";")[0].strip().lower()
        if code[:2] in SUPPORTED_LANGS:
            return code[:2]
    return DEFAULT_LANG


def translate(key: str, lang: str) -> str:
    return TRANSLATIONS.get(lang, {}).get(
        key, TRANSLATIONS.get(DEFAULT_LANG, {}).get(key, key)
    )


def set_language(lang: str) -> None:
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    session["lang"] = lang
    log_language_set(lang)

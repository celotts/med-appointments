"""Dependencies for internationalization (i18n)."""

from core.i18n import get_supported_languages, get_translation
from fastapi import Header, HTTPException


def get_language(accept_language: str | None = Header(None)) -> str:
    """
    Extract language from Accept-Language header.

    Examples:
        Accept-Language: en
        Accept-Language: es
        Accept-Language: pt-BR
        Accept-Language: en-US,en;q=0.9
    """
    if not accept_language:
        return "en"

    # Parse Accept-Language header
    # Example: "en-US,en;q=0.9,es;q=0.8"
    supported = get_supported_languages()

    # Split by comma and extract language codes
    for part in accept_language.split(","):
        lang_code = part.split(";")[0].strip().lower()
        # Check base language (e.g., "en" from "en-US")
        base_lang = lang_code.split("-")[0]
        if base_lang in supported:
            return base_lang

    # Default to English
    return "en"


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Shorthand for get_translation."""
    return get_translation(key, lang, **kwargs)


class I18nResponse:
    """Helper class for creating i18n responses."""

    def __init__(self, language: str = "en"):
        self.language = language

    def get(self, key: str, **kwargs) -> str:
        """Get translation for key with optional format kwargs."""
        return get_translation(key, self.language, **kwargs)

    def success(self, key: str, **kwargs) -> dict:
        """Create success response with translation."""
        message = self.get(key, **kwargs)
        return {
            "status": "success",
            "message": message,
            "language": self.language,
        }

    def error(self, key: str, status_code: int = 400, **kwargs) -> HTTPException:
        """Create error response with translation."""
        message = self.get(key, **kwargs)
        return HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "message": message,
                "language": self.language,
            },
        )

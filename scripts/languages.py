"""Shared language registry for the weekly and feature pipelines.

Adding a fourth language should mean editing this module plus one settings block,
not hunting for `lang == "en"` branches.
"""

# Display order, and the order translation legs run in.
LANGUAGES = ("ja", "en", "zh")

# Field-name suffix for AI-written prose. Japanese is the unsuffixed base field
# because it was the original output language; English and Chinese are suffixed.
#
# NOTE: weekly paper records use a *different* convention for `title`/`abstract`,
# where the unsuffixed field holds the raw English arXiv text and Japanese is
# suffixed. Use SOURCE_SUFFIX for those two fields only.
LANGUAGE_SUFFIX = {"ja": "", "en": "En", "zh": "Zh"}
SOURCE_SUFFIX = {"ja": "Ja", "en": "", "zh": "Zh"}

# BCP-47 tags for markup. Chinese must carry the script subtag: the page fonts
# ship no CJK glyphs, so the browser resolves Han characters via the document
# language, and a bare "zh" yields Japanese glyph variants (直/令/骨/起).
BCP47 = {"ja": "ja", "en": "en", "zh": "zh-Hans"}

# Names used inside AI prompts.
LANGUAGE_NAMES = {"ja": "Japanese", "en": "English", "zh": "Simplified Chinese"}


# Per-language long-form budgets, mapped onto config/settings.yaml["features"].
# The Japanese keys are not uniformly prefixed there, so an explicit map beats
# deriving key names. Shared by the generator and the renderer so the publish
# gate and the render gate cannot drift apart.
FEATURE_BUDGET_KEYS = {
    "ja": {
        "target_min_chars": "target_min_chars",
        "target_max_chars": "target_max_chars",
        "validation_min_chars": "validation_min_chars",
        "validation_max_chars": "validation_max_chars",
        "reading_chars_per_minute": "reading_chars_per_minute",
        "body_min_ratio": "japanese_body_min_ratio",
        "metadata_min_ratio": "japanese_metadata_min_ratio",
    },
    "zh": {
        "target_min_chars": "chinese_target_min_chars",
        "target_max_chars": "chinese_target_max_chars",
        "validation_min_chars": "chinese_validation_min_chars",
        "validation_max_chars": "chinese_validation_max_chars",
        "reading_chars_per_minute": "chinese_reading_chars_per_minute",
        "body_min_ratio": "chinese_body_min_ratio",
        "metadata_min_ratio": "chinese_metadata_min_ratio",
        # Only Chinese carries a kana ceiling; Japanese has no upper bound.
        "kana_max_ratio": "chinese_kana_max_ratio",
    },
}


def feature_budget(cfg, language: str) -> dict:
    """Return a normalized-key budget dict for one translation target language."""
    if language not in FEATURE_BUDGET_KEYS:
        raise KeyError(f"No feature budget configured for language {language!r}")
    resolved = {
        name: cfg[source] for name, source in FEATURE_BUDGET_KEYS[language].items()
    }
    resolved["language"] = language
    resolved["language_name"] = LANGUAGE_NAMES[language]
    resolved["suffix"] = LANGUAGE_SUFFIX[language]
    return resolved


def field(base: str, language: str) -> str:
    """Return the per-language field name for a base field ("what" -> "whatZh")."""
    return f"{base}{LANGUAGE_SUFFIX[language]}"


def source_field(base: str, language: str) -> str:
    """Return the per-language name for a raw-arXiv field ("title" -> "titleZh")."""
    return f"{base}{SOURCE_SUFFIX[language]}"

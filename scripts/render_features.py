#!/usr/bin/env python3
"""Render validated feature JSON as escaped, crawlable static HTML pages."""

from __future__ import annotations

import argparse
import html
import ipaddress
import json
import math
import os
import re
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

import yaml

from languages import BCP47, LANGUAGE_NAMES, feature_budget, field


ROOT = Path(__file__).parent.parent
DEFAULT_INPUT = Path("data/features")
DEFAULT_OUTPUT = Path("web/public/features")
DEFAULT_SITE_URL = "https://jasper-zheng.github.io/audio-ai-weekly"
SITE_NAME = "Audio AI Weekly"
ARXIV_ACKNOWLEDGEMENT = (
    "Thank you to arXiv for use of its open access interoperability. This service "
    "was not reviewed or approved by, nor does it necessarily express or reflect "
    "the policies or opinions of, arXiv."
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCE_ID_RE = re.compile(r"^S[1-9][0-9]*$")
# Kana is the only reliable Japanese/Chinese discriminator; Han is shared.
KANA_RE = re.compile(r"[\u3040-\u30ff]")
HAN_RE = re.compile(r"[\u3400-\u9fff]")
CJK_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
LATIN_CHAR_RE = re.compile(r"[A-Za-z]")
ENGLISH_WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z'-]*\b")

# Read the publication budgets from the same file the generator uses, so the
# render gate cannot silently drift from the publish gate.
FEATURE_SETTINGS = yaml.safe_load(
    (ROOT / "config/settings.yaml").read_text()
)["features"]
TRANSLATED_LANGUAGES = [
    language
    for language in FEATURE_SETTINGS.get("translation_target_languages", ["ja"])
    if isinstance(language, str)
]
# Japanese is the default edition, so it leads; English and Chinese follow.
RENDER_LANGUAGES = ["ja"] + [
    language for language in [*TRANSLATED_LANGUAGES, "en"] if language != "ja"
]
LANGUAGE_BUDGETS = {
    language: feature_budget(FEATURE_SETTINGS, language)
    for language in TRANSLATED_LANGUAGES
}
READING_MINUTES_MIN = FEATURE_SETTINGS["reading_minutes_min"]
READING_MINUTES_MAX = FEATURE_SETTINGS["reading_minutes_max"]
ENGLISH_BODY_MIN_WORDS = FEATURE_SETTINGS["english_body_validation_min_words"]
ENGLISH_BODY_MAX_WORDS = FEATURE_SETTINGS["english_body_validation_max_words"]
ENGLISH_READING_WORDS_PER_MINUTE = FEATURE_SETTINGS[
    "english_reading_words_per_minute"
]
REQUIRED_SECTIONS = {
    "primer": {
        "why-needed",
        "history",
        "approaches",
        "perspectives",
        "limits",
        "outlook",
    },
    "debate": {
        "current-signal",
        "positions",
        "evidence",
        "evaluation",
        "implications",
        "watch",
    },
}


class RenderError(RuntimeError):
    """Feature data is unsafe or incomplete and must not be rendered."""


def _escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _inside(root: Path, path: Path) -> bool:
    root = root.resolve()
    path = path.resolve()
    return path == root or root in path.parents


def _require_text(data: dict, field: str, context: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RenderError(f"{context}.{field} must be a non-empty string")
    return value.strip()


def _is_public_https_url(value: str) -> bool:
    if value != value.strip() or any(ord(character) < 32 for character in value):
        return False
    try:
        parsed = urllib.parse.urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    try:
        return ipaddress.ip_address(hostname).is_global
    except ValueError:
        return (
            "." in hostname
            and hostname != "localhost"
            and not hostname.endswith((".localhost", ".local"))
        )


def _is_valid_primary_link(label: str, value: str) -> bool:
    if label not in ("Code", "Project") or not _is_public_https_url(value):
        return False
    parsed = urllib.parse.urlsplit(value)
    if label == "Code":
        path_parts = [part for part in parsed.path.split("/") if part]
        return (
            parsed.hostname.lower().rstrip(".") == "github.com" and len(path_parts) >= 2
        )
    return True


def _cjk_ratio(value: str) -> float:
    cjk = len(CJK_CHAR_RE.findall(value))
    latin = len(LATIN_CHAR_RE.findall(value))
    return cjk / max(1, cjk + latin)


def _kana_ratio(value: str) -> float:
    cjk = len(CJK_CHAR_RE.findall(value))
    if not cjk:
        return 0.0
    return len(KANA_RE.findall(value)) / cjk


def _predominantly_english(value: str) -> bool:
    return bool(LATIN_CHAR_RE.search(value)) and _cjk_ratio(value) <= 0.1


def _predominantly_translated(value: str, language: str) -> bool:
    """Check one metadata string against its language's script expectations."""
    budget = LANGUAGE_BUDGETS[language]
    if _cjk_ratio(value) < budget["metadata_min_ratio"]:
        return False
    if not CJK_CHAR_RE.search(value):
        return False
    kana_max = budget.get("kana_max_ratio")
    if kana_max is not None:
        # Chinese: reject a Japanese string standing in for it.
        return bool(HAN_RE.search(value)) and _kana_ratio(value) <= kana_max
    return True


def _validate_feature_for_render(feature: Any, expected_slug: str) -> dict:
    """Check the rendering contract independently of generator dependencies."""
    if not isinstance(feature, dict):
        raise RenderError("Feature JSON must be an object")
    slug = _require_text(feature, "slug", "feature")
    if slug != expected_slug or not SLUG_RE.fullmatch(slug):
        raise RenderError("Feature slug is invalid or does not match its index entry")
    if feature.get("type") not in ("primer", "debate"):
        raise RenderError("Feature type must be primer or debate")
    if feature.get("verification", {}).get("status") != "passed":
        raise RenderError("Feature must be marked as verifier-passed")
    required = ["date", "summaryEn"] + [
        field(base, language)
        for base in ("title", "dek")
        for language in RENDER_LANGUAGES
    ]
    for key in required:
        _require_text(feature, key, "feature")
    if feature.get("sourceLanguage") != "en":
        raise RenderError("Feature sourceLanguage must be en")
    translations = feature.get("translations")
    if not isinstance(translations, dict):
        raise RenderError("Feature translations must be an object keyed by language")
    for language in TRANSLATED_LANGUAGES:
        entry = translations.get(language)
        if not isinstance(entry, dict) or entry.get("status") != "passed":
            raise RenderError(
                f"Feature {language} translation must be verifier-passed"
            )
        read_time = feature.get(field("readTimeMinutes", language))
        if (
            not isinstance(read_time, int)
            or not READING_MINUTES_MIN <= read_time <= READING_MINUTES_MAX
        ):
            raise RenderError(
                f"{field('readTimeMinutes', language)} must be between "
                f"{READING_MINUTES_MIN} and {READING_MINUTES_MAX}"
            )
        for base in ("title", "dek"):
            key = field(base, language)
            if not _predominantly_translated(feature[key], language):
                raise RenderError(
                    f"feature.{key} must be predominantly {LANGUAGE_NAMES[language]}"
                )
    if not isinstance(feature.get("readTimeMinutesEn"), int):
        raise RenderError("readTimeMinutesEn must be an integer")
    for base in ("title", "dek"):
        key = field(base, "en")
        if not _predominantly_english(feature[key]):
            raise RenderError(f"feature.{key} must be predominantly English")

    key_points = feature.get("keyPointsEn")
    if (
        not isinstance(key_points, list)
        or len(key_points) < 3
        or not all(isinstance(point, str) and point.strip() for point in key_points)
    ):
        raise RenderError("keyPointsEn must contain at least three strings")

    sources = feature.get("sources")
    if not isinstance(sources, list) or len(sources) < 8:
        raise RenderError("Feature must contain at least eight sources")
    source_ids: set[str] = set()
    primary_link_count = 0
    for source in sources:
        if not isinstance(source, dict):
            raise RenderError("Each source must be an object")
        source_id = _require_text(source, "sourceId", "source")
        if not SOURCE_ID_RE.fullmatch(source_id) or source_id in source_ids:
            raise RenderError("Source IDs must be unique S1, S2, ... values")
        source_ids.add(source_id)
        for key in ("arxivId", "title", "abstract", "url"):
            _require_text(source, key, f"source {source_id}")
        if source["url"] != f"https://arxiv.org/abs/{source['arxivId']}":
            raise RenderError(f"Source {source_id} must use an arXiv URL")
        primary_links = source.get("primaryLinks", [])
        if not isinstance(primary_links, list):
            raise RenderError(f"Source {source_id} primaryLinks must be an array")
        for link in primary_links:
            if not isinstance(link, dict):
                raise RenderError(f"Source {source_id} has an invalid primaryLink")
            label = link.get("label")
            url = link.get("url")
            if (
                not isinstance(label, str)
                or not isinstance(url, str)
                or not _is_valid_primary_link(label, url)
            ):
                raise RenderError(f"Source {source_id} has an invalid primaryLink")
            primary_link_count += 1
    if primary_link_count < 1:
        raise RenderError("Feature must include a validated metadata-linked resource")

    perspectives = feature.get("perspectives")
    if not isinstance(perspectives, list) or len(perspectives) != 3:
        raise RenderError("Feature must contain exactly three perspectives")
    for perspective in perspectives:
        if not isinstance(perspective, dict):
            raise RenderError("Each perspective must be an object")
        _require_text(perspective, "id", "perspective")
        for base in ("label", "description"):
            for language in TRANSLATED_LANGUAGES:
                key = field(base, language)
                value = _require_text(perspective, key, "perspective")
                if not _predominantly_translated(value, language):
                    raise RenderError(
                        f"perspective.{key} must be predominantly "
                        f"{LANGUAGE_NAMES[language]}"
                    )
            key = field(base, "en")
            value = _require_text(perspective, key, "perspective")
            if not _predominantly_english(value):
                raise RenderError(f"perspective.{key} must be predominantly English")
        ids = perspective.get("sourceIds")
        if (
            not isinstance(ids, list)
            or not ids
            or not all(isinstance(value, str) for value in ids)
            or not set(ids) <= source_ids
        ):
            raise RenderError("Perspective sourceIds must refer to known sources")

    sections = feature.get("sections")
    if not isinstance(sections, list) or len(sections) < 6:
        raise RenderError("Feature must contain at least six sections")
    cited_ids: set[str] = set()
    section_ids: set[str] = set()
    block_ids: set[str] = set()
    body_texts: dict[str, list[str]] = {
        language: [] for language in RENDER_LANGUAGES
    }
    for section in sections:
        if not isinstance(section, dict):
            raise RenderError("Each section must be an object")
        section_id = _require_text(section, "id", "section")
        if not SLUG_RE.fullmatch(section_id) or section_id in section_ids:
            raise RenderError("Section IDs must be unique lowercase kebab-case values")
        section_ids.add(section_id)
        for language in TRANSLATED_LANGUAGES:
            key = field("heading", language)
            if not _predominantly_translated(
                _require_text(section, key, "section"), language
            ):
                raise RenderError(
                    f"section.{key} must be predominantly {LANGUAGE_NAMES[language]}"
                )
        if not _predominantly_english(_require_text(section, "headingEn", "section")):
            raise RenderError("section.headingEn must be predominantly English")
        blocks = section.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            raise RenderError("Every section must contain blocks")
        for block in blocks:
            if not isinstance(block, dict):
                raise RenderError("Each block must be an object")
            block_id = _require_text(block, "id", "block")
            if not SLUG_RE.fullmatch(block_id) or block_id in block_ids:
                raise RenderError(
                    "Block IDs must be unique lowercase kebab-case values"
                )
            block_ids.add(block_id)
            for language in TRANSLATED_LANGUAGES:
                key = field("text", language)
                text = _require_text(block, key, "block")
                budget = LANGUAGE_BUDGETS[language]
                kana_max = budget.get("kana_max_ratio")
                if _cjk_ratio(text) < budget["body_min_ratio"] or (
                    kana_max is not None and _kana_ratio(text) > kana_max
                ):
                    raise RenderError(
                        f"block.{key} must be predominantly "
                        f"{LANGUAGE_NAMES[language]}"
                    )
                body_texts[language].append(text)
            block_text_en = _require_text(block, "textEn", "block")
            if not _predominantly_english(block_text_en):
                raise RenderError("block.textEn must be predominantly English")
            body_texts["en"].append(block_text_en)
            ids = block.get("sourceIds")
            if (
                not isinstance(ids, list)
                or not ids
                or not all(isinstance(value, str) for value in ids)
                or not set(ids) <= source_ids
            ):
                raise RenderError("Every block must cite known source IDs")
            cited_ids.update(ids)
    missing_sections = REQUIRED_SECTIONS[feature["type"]] - section_ids
    if missing_sections:
        raise RenderError(
            "Feature is missing required sections: "
            + ", ".join(sorted(missing_sections))
        )
    if cited_ids != source_ids:
        raise RenderError("Every listed source must be cited in the article body")
    for language in TRANSLATED_LANGUAGES:
        budget = LANGUAGE_BUDGETS[language]
        name = LANGUAGE_NAMES[language]
        body_text = "".join(body_texts[language])
        character_count = len("".join(body_text.split()))
        if (
            not budget["validation_min_chars"]
            <= character_count
            <= budget["validation_max_chars"]
        ):
            raise RenderError(
                f"{name} body must contain {budget['validation_min_chars']}-"
                f"{budget['validation_max_chars']} non-whitespace characters"
            )
        if _cjk_ratio(body_text) < budget["body_min_ratio"]:
            raise RenderError(
                f"{name} body language ratio must be at least "
                f"{budget['body_min_ratio']:.0%}"
            )
        expected_read_time = math.ceil(
            character_count / budget["reading_chars_per_minute"]
        )
        read_time_field = field("readTimeMinutes", language)
        if feature[read_time_field] != expected_read_time:
            raise RenderError(f"{read_time_field} must be {expected_read_time}")

    english_word_count = sum(
        len(ENGLISH_WORD_RE.findall(text)) for text in body_texts["en"]
    )
    if not ENGLISH_BODY_MIN_WORDS <= english_word_count <= ENGLISH_BODY_MAX_WORDS:
        raise RenderError(
            f"English body must contain {ENGLISH_BODY_MIN_WORDS}-"
            f"{ENGLISH_BODY_MAX_WORDS} words"
        )
    expected_english_read_time = math.ceil(
        english_word_count / ENGLISH_READING_WORDS_PER_MINUTE
    )
    if feature["readTimeMinutesEn"] != expected_english_read_time:
        raise RenderError(f"readTimeMinutesEn must be {expected_english_read_time}")
    return feature


def load_features(input_dir: Path) -> tuple[dict, list[dict]]:
    index_path = input_dir / "index.json"
    if not index_path.exists():
        return {"features": [], "generatedAt": ""}, []
    try:
        index = json.loads(index_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RenderError(f"Cannot load feature index {index_path}: {exc}") from exc
    if not isinstance(index, dict) or not isinstance(index.get("features"), list):
        raise RenderError("Feature index must contain a features array")

    features: list[dict] = []
    for entry in index["features"]:
        if not isinstance(entry, dict):
            raise RenderError("Feature index entries must be objects")
        slug = _require_text(entry, "slug", "feature index entry")
        if not SLUG_RE.fullmatch(slug):
            raise RenderError(f"Unsafe feature slug: {slug!r}")
        relative_file = entry.get("file", f"{slug}.json")
        if not isinstance(relative_file, str):
            raise RenderError(f"Invalid file for feature {slug}")
        path = (input_dir / relative_file).resolve()
        if not _inside(input_dir, path):
            raise RenderError(f"Unsafe feature file path: {relative_file}")
        try:
            feature = json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            raise RenderError(f"Cannot load feature {path}: {exc}") from exc
        features.append(_validate_feature_for_render(feature, slug))
    return index, features


STYLE = """
:root{color-scheme:dark;--bg:#0f1117;--deep:#0a0d14;--panel:#131720;--line:#1e293b;--text:#e7edf7;--muted:#94a3b8;--accent:#22d3ee;--feature:#f472b6}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font-family:"IBM Plex Mono","Space Mono",ui-monospace,SFMono-Regular,Consolas,monospace;line-height:1.8}
a{color:var(--accent)}.shell{width:min(960px,calc(100% - 32px));margin:auto}.nav{display:flex;justify-content:space-between;gap:16px;padding:24px 0;color:var(--muted)}.nav a{text-decoration:none;display:inline-flex;align-items:center;min-height:28px}.hero{padding:72px 0 44px;border-bottom:1px solid var(--line)}
.badge{display:inline-block;padding:4px 9px;border:1px solid var(--feature);border-radius:3px;color:var(--feature);font-size:.76rem;letter-spacing:.1em;text-transform:uppercase}.badge.debate{border-color:var(--accent);color:var(--accent)}h1{font-size:clamp(2.1rem,6vw,4.2rem);line-height:1.14;margin:.5em 0 .3em;letter-spacing:-.04em}h2{font-size:clamp(1.4rem,3vw,1.9rem);line-height:1.4;margin-top:2.3em}.dek{font-size:1.08rem;color:#cbd5e1;max-width:52rem}.meta{display:flex;flex-wrap:wrap;gap:10px 24px;color:var(--muted);font-size:.88rem}.language-switch{display:flex;align-items:center;gap:8px;margin-left:auto}.language-switch a,.language-switch span{min-height:28px;display:inline-flex;align-items:center}.language-switch [aria-current="page"]{color:var(--accent);font-weight:700}
main{padding:30px 0 90px}.perspectives{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:40px 0}.card,.summary,.source{background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:20px}.card h3{margin-top:0;color:var(--feature)}.article-section{max-width:780px;margin:0 auto}.article-section p{font-size:1rem}.citations{white-space:nowrap;font-size:.75rem;margin-left:.35rem}.citations a{display:inline-flex;align-items:center;justify-content:center;min-width:24px;min-height:24px;text-decoration:none;margin-right:.2rem}.summary{margin:40px 0 64px;border-color:var(--accent);background:var(--deep)}.summary h2{margin-top:0}.sources{margin-top:64px}.source{margin:10px 0}.source-title{font-weight:700}.source-meta,.primary-links{color:var(--muted);font-size:.82rem}.primary-links a{display:inline-flex;align-items:center;min-height:28px;margin-right:1rem}.archive-grid{display:grid;gap:12px;padding:40px 0 40px}.archive-card{display:block;text-decoration:none;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:24px}.archive-card:hover{border-color:var(--feature)}.archive-card h2{margin:.35em 0 .1em}.archive-card p{color:#cbd5e1}.disclosure{margin:28px 0;padding:16px;border:1px solid #334155;border-left:4px solid var(--accent);border-radius:3px;color:var(--muted);font-size:.86rem}.disclosure strong{color:#cbd5e1}.footer{border-top:1px solid var(--line);padding:30px 0 60px;color:var(--muted);font-size:.82rem}
@media(max-width:720px){.perspectives{grid-template-columns:1fr}.hero{padding-top:40px}.shell{width:min(100% - 22px,960px)}}
"""


def _json_for_script(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _language_urls(base_url: str) -> dict[str, str]:
    """Map each language to its absolute URL. Japanese is the default edition."""
    base = base_url if base_url.endswith("/") else f"{base_url}/"
    return {
        language: base if language == "ja" else f"{base}{language}/"
        for language in RENDER_LANGUAGES
    }


def _document_head(
    *,
    title: str,
    description: str,
    canonical_url: str,
    json_ld: dict,
    language: str,
    alternate_urls: dict[str, str],
) -> str:
    # BCP47 rather than the bare code: the stylesheet ships no CJK font, so the
    # browser picks Han glyphs from the document language. A bare "zh" renders
    # Japanese glyph variants (直/令/骨/起) on the Chinese page.
    alternates = "".join(
        f'<link rel="alternate" hreflang="{_escape(BCP47[code])}" '
        f'href="{_escape(url)}">'
        for code, url in alternate_urls.items()
    )
    default_url = alternate_urls.get("ja", canonical_url)
    return f"""<!doctype html>
<html lang="{_escape(BCP47[language])}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_escape(title)}</title><meta name="description" content="{_escape(description)}">
<link rel="canonical" href="{_escape(canonical_url)}">
{alternates}<link rel="alternate" hreflang="x-default" href="{_escape(default_url)}">
<meta property="og:type" content="article"><meta property="og:title" content="{_escape(title)}">
<meta property="og:description" content="{_escape(description)}"><meta property="og:url" content="{_escape(canonical_url)}">
<meta property="og:site_name" content="Audio AI Weekly"><meta name="twitter:card" content="summary">
<script type="application/ld+json">{_json_for_script(json_ld)}</script><style>{STYLE}</style></head>"""


def _source_links(source_ids: list[str]) -> str:
    links = "".join(
        f'<a href="#source-{_escape(source_id)}" aria-label="Source {_escape(source_id)}">[{_escape(source_id)}]</a>'
        for source_id in source_ids
    )
    return f'<sup class="citations">{links}</sup>'


PRIMARY_LINK_LABELS = {
    "ja": {"Code": "コード", "Project": "プロジェクト"},
    "en": {},
    "zh": {"Code": "代码", "Project": "项目"},
}
PRIMARY_LINK_HEADINGS = {
    "ja": "関連リソース: ",
    "en": "Metadata-linked resources: ",
    "zh": "相关资源：",
}
SOURCE_ORIGIN_LABELS = {
    "ja": {"archive": "週報掲載", "external": "外部", "historical": "過去掲載"},
    "en": {
        "archive": "weekly archive",
        "external": "external",
        "historical": "historical",
    },
    "zh": {"archive": "周报收录", "external": "外部", "historical": "往期收录"},
}
FEATURE_KIND_LABELS = {
    "ja": {"primer": "分野を解く", "debate": "論点を読む"},
    "en": {"primer": "Field Primer", "debate": "Debate Brief"},
    "zh": {"primer": "领域解读", "debate": "论点透视"},
}
READING_META = {
    "ja": lambda minutes: f"約 {minutes} 分",
    "en": lambda minutes: f"~ {minutes} min",
    "zh": lambda minutes: f"约 {minutes} 分钟",
}
SOURCE_META = {
    "ja": lambda count: f"出典 {count} 件",
    "en": lambda count: f"{count} primary sources",
    "zh": lambda count: f"来源 {count} 篇",
}
PERSPECTIVES_LABEL = {
    "ja": "3つの視点",
    "en": "Three perspectives",
    "zh": "三个视角",
}
# Page chrome. `disclosure` and `caution` are legal/trust text; the Chinese
# wording mirrors the Japanese and English versions.
PAGE_COPY = {
    "ja": {
        "home": "← 音響AI週報",
        "archive": "特集一覧",
        "archive_footer": "特集一覧へ",
        "back": "週報へ戻る",
        "disclosure": "AI生成（タイトル・抄録ベース）・出典と翻訳の機械的整合性チェック済み・人手未校閲",
        "caution": "誤訳、誤要約、過度な一般化を含む可能性があります。研究上の判断は原論文で確認してください。",
        "acknowledgement_label": "arXiv公式英文（原文）",
        "sources_heading": "一次資料（原題）",
        "sources_note": "本文は以下の arXiv 論文のタイトルとアブストラクトに基づき、出典 ID を段落ごとに付与しています。論文タイトルは原題のまま掲載しています。",
        "archive_description": "音声・音響AI研究を一次資料から読み解く、月2回の特集記事。",
        "archive_page_name": "音響AI週報 特集",
        "archive_title": "特集 | 音響AI週報",
        "archive_badge": "特集",
        "archive_heading": "研究の現在地を、一次資料から。",
        "archive_empty": "公開済みの特集はまだありません。",
    },
    "en": {
        "home": "← Audio AI Weekly",
        "archive": "Feature archive",
        "archive_footer": "Feature archive",
        "back": "Back to weekly report",
        "disclosure": "AI-generated from titles and abstracts · machine-checked for source and translation consistency · not human-reviewed",
        "caution": "May contain mistranslations, inaccurate summaries, or overgeneralizations; consult the original papers for research decisions.",
        "acknowledgement_label": "Official arXiv statement",
        "sources_heading": "Primary sources",
        "sources_note": "This article is grounded in the titles and abstracts of the following arXiv papers.",
        "archive_description": "Twice-monthly features explaining audio and speech AI research from primary sources.",
        "archive_page_name": "Audio AI Weekly Features",
        "archive_title": "Features | Audio AI Weekly",
        "archive_badge": "Features",
        "archive_heading": "Research context, grounded in primary sources.",
        "archive_empty": "No features have been published yet.",
    },
    "zh": {
        "home": "← 音频AI周报",
        "archive": "专题列表",
        "archive_footer": "前往专题列表",
        "back": "返回周报",
        "disclosure": "AI 生成（基于标题与摘要）· 已完成来源与翻译的机械一致性检查 · 未经人工校阅",
        "caution": "可能包含误译、错误摘要或过度概括；研究决策请以原论文为准。",
        "acknowledgement_label": "arXiv 官方英文声明（原文）",
        "sources_heading": "一次文献（原标题）",
        "sources_note": "正文基于以下 arXiv 论文的标题与摘要撰写，并逐段标注来源 ID。论文标题保留原文。",
        "archive_description": "每月两期的专题文章，从一次文献解读语音与音频 AI 研究。",
        "archive_page_name": "音频AI周报 专题",
        "archive_title": "专题 | 音频AI周报",
        "archive_badge": "专题",
        "archive_heading": "从一次文献看研究的当前进展。",
        "archive_empty": "尚未发布任何专题。",
    },
}


def _language_switch(current: str, hrefs: dict[str, str]) -> str:
    """Build the JA / EN / ZH switch.

    Uses absolute URLs: relative depth differs per source page, and with three
    languages a hand-written relative matrix is where the bugs would live.
    """
    parts = []
    for index, code in enumerate(RENDER_LANGUAGES):
        if index:
            parts.append("<span>/</span>")
        if code == current:
            parts.append(f'<span aria-current="page">{code.upper()}</span>')
        else:
            parts.append(
                f'<a href="{_escape(hrefs[code])}" hreflang="{_escape(BCP47[code])}">'
                f"{code.upper()}</a>"
            )
    return "".join(parts)


def _primary_links(source: dict, language: str) -> str:
    links = source.get("primaryLinks", [])
    if not links:
        return ""
    translated_labels = PRIMARY_LINK_LABELS[language]
    rendered = "".join(
        f'<a href="{_escape(link["url"])}" rel="noopener noreferrer">'
        f'{_escape(translated_labels.get(link["label"], link["label"]))}</a>'
        for link in links
    )
    label = PRIMARY_LINK_HEADINGS[language]
    return f'<div class="primary-links">{label}{rendered}</div>'


def _source_origin(origin: str, language: str) -> str:
    return SOURCE_ORIGIN_LABELS[language].get(origin, origin)


def _feature_kind(article_type: str, language: str) -> str:
    return FEATURE_KIND_LABELS[language][article_type]


def _feature_meta(feature: dict, language: str) -> tuple[str, str]:
    """Return the reading-time and source-count chips for one language."""
    minutes = feature[field("readTimeMinutes", language)]
    return (
        READING_META[language](_escape(minutes)),
        SOURCE_META[language](len(feature["sources"])),
    )


def _archive_card(feature: dict, language: str) -> str:
    # Archive pages live at /features/ (ja) and /features/<lang>/, so a non-default
    # archive must climb one level before descending into the article directory.
    if language == "ja":
        href = f'./{_escape(feature["slug"])}/'
    else:
        href = f'../{_escape(feature["slug"])}/{_escape(language)}/'
    reading_meta, source_meta = _feature_meta(feature, language)
    return f"""<a class="archive-card" href="{href}"><span class="badge {_escape(feature['type'])}">{_escape(_feature_kind(feature['type'], language))}</span>
<h2>{_escape(feature[field('title', language)])}</h2><p>{_escape(feature[field('dek', language)])}</p>
<div class="meta"><span>{_escape(feature['date'])}</span><span>{reading_meta}</span><span>{source_meta}</span></div></a>"""


def render_feature_page(
    feature: dict, site_url: str = DEFAULT_SITE_URL, language: str = "ja"
) -> str:
    if language not in RENDER_LANGUAGES:
        raise ValueError(f"language must be one of {', '.join(RENDER_LANGUAGES)}")
    slug = feature["slug"]
    alternate_urls = _language_urls(f"{site_url.rstrip('/')}/features/{slug}")
    canonical_url = alternate_urls[language]
    title = feature[field("title", language)]
    description = feature[field("dek", language)]
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": feature["date"],
        "dateModified": feature.get("generatedAt", feature["date"]),
        "inLanguage": BCP47[language],
        "mainEntityOfPage": canonical_url,
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "citation": [source["url"] for source in feature["sources"]],
    }
    head = _document_head(
        title=f"{title} | {SITE_NAME}",
        description=description,
        canonical_url=canonical_url,
        json_ld=json_ld,
        language=language,
        alternate_urls=alternate_urls,
    )
    kind = _feature_kind(feature["type"], language)
    label_key = field("label", language)
    description_key = field("description", language)
    heading_key = field("heading", language)
    text_key = field("text", language)
    perspectives = "".join(
        f"""<article class="card"><h3>{_escape(item[label_key])}</h3>
<p>{_escape(item[description_key])}{_source_links(item['sourceIds'])}</p></article>"""
        for item in feature["perspectives"]
    )
    sections = "".join(
        f"""<section class="article-section" id="{_escape(section['id'])}"><h2>{_escape(section[heading_key])}</h2>
{''.join(f'<p>{_escape(block[text_key])}{_source_links(block["sourceIds"])}</p>' for block in section['blocks'])}</section>"""
        for section in feature["sections"]
    )
    main_content = (
        f'<aside class="perspectives" aria-label="{_escape(PERSPECTIVES_LABEL[language])}">'
        f"{perspectives}</aside>{sections}"
    )
    sources = "".join(
        f"""<article class="source" id="source-{_escape(source['sourceId'])}">
<div class="source-meta">{_escape(source['sourceId'])} · {_escape(_source_origin(source['origin'], language))} · {_escape(source.get('publishedAt', ''))}</div>
<div class="source-title"><a href="{_escape(source['url'])}" rel="noopener noreferrer">{_escape(source['title'])}</a></div>
<div class="source-meta">{_escape(', '.join(source.get('authors', [])[:5]))} · arXiv:{_escape(source['arxivId'])}</div>
{_primary_links(source, language)}</article>"""
        for source in feature["sources"]
    )
    copy = PAGE_COPY[language]
    site_root = f"{site_url.rstrip('/')}/"
    archive_urls = _language_urls(f"{site_url.rstrip('/')}/features")
    home_href = f"{site_root}?lang={language}"
    archive_href = archive_urls[language]
    home_link = f'<a href="{_escape(home_href)}">{_escape(copy["home"])}</a>'
    archive_link = f'<a href="{_escape(archive_href)}">{_escape(copy["archive"])}</a>'
    language_switch = _language_switch(language, alternate_urls)
    reading_meta, source_meta = _feature_meta(feature, language)
    meta = (
        f"<span>{_escape(feature['date'])}</span>"
        f"<span>{reading_meta}</span><span>{source_meta}</span>"
    )
    footer = (
        f'<a href="{_escape(archive_href)}">{_escape(copy["archive_footer"])}</a>'
        f' · <a href="{_escape(home_href)}">{_escape(copy["back"])}</a>'
    )
    return f"""{head}<body><div class="shell"><nav class="nav">{home_link}{archive_link}<span class="language-switch" aria-label="Language">{language_switch}</span></nav></div>
<header class="hero"><div class="shell"><span class="badge {_escape(feature['type'])}">{_escape(kind)}</span>
<h1>{_escape(title)}</h1><p class="dek">{_escape(description)}</p>
<div class="meta">{meta}</div><aside class="disclosure"><strong>{_escape(copy['disclosure'])}</strong><br>{_escape(copy['caution'])}</aside></div></header>
<main class="shell">{main_content}
<section class="sources"><h2>{_escape(copy['sources_heading'])}</h2><p class="dek">{_escape(copy['sources_note'])}</p>{sources}</section></main>
<footer class="footer"><div class="shell">{footer}<div class="disclosure"><strong>{_escape(copy['acknowledgement_label'])}:</strong><br>{_escape(ARXIV_ACKNOWLEDGEMENT)}</div></div></footer></body></html>"""


def render_archive_page(
    features: list[dict], site_url: str = DEFAULT_SITE_URL, language: str = "ja"
) -> str:
    if language not in RENDER_LANGUAGES:
        raise ValueError(f"language must be one of {', '.join(RENDER_LANGUAGES)}")
    copy = PAGE_COPY[language]
    alternate_urls = _language_urls(f"{site_url.rstrip('/')}/features")
    canonical_url = alternate_urls[language]
    description = copy["archive_description"]
    json_ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": copy["archive_page_name"],
        "description": description,
        "url": canonical_url,
        "inLanguage": BCP47[language],
        "hasPart": [
            {
                "@type": "Article",
                "headline": feature[field("title", language)],
                "url": f"{alternate_urls['ja']}{feature['slug']}/"
                + ("" if language == "ja" else f"{language}/"),
            }
            for feature in features
        ],
    }
    head = _document_head(
        title=copy["archive_title"],
        description=description,
        canonical_url=canonical_url,
        json_ld=json_ld,
        language=language,
        alternate_urls=alternate_urls,
    )
    cards = "".join(_archive_card(feature, language) for feature in features)
    if not cards:
        cards = f'<p class="dek">{_escape(copy["archive_empty"])}</p>'
    home_href = f"{site_url.rstrip('/')}/?lang={language}"
    home_link = f'<a href="{_escape(home_href)}">{_escape(copy["home"])}</a>'
    language_switch = _language_switch(language, alternate_urls)
    footer = f'<a href="{_escape(home_href)}">{_escape(copy["back"])}</a>'
    return f"""{head}<body><div class="shell"><nav class="nav">{home_link}<span class="language-switch" aria-label="Language">{language_switch}</span></nav>
<header class="hero"><span class="badge">{_escape(copy['archive_badge'])}</span><h1>{_escape(copy['archive_heading'])}</h1><p class="dek">{_escape(description)}</p></header>
<aside class="disclosure"><strong>{_escape(copy['disclosure'])}</strong></aside>
<main class="archive-grid">{cards}</main><footer class="footer">{footer}<div class="disclosure"><strong>{_escape(copy['acknowledgement_label'])}:</strong><br>{_escape(ARXIV_ACKNOWLEDGEMENT)}</div></footer></div></body></html>"""


def _language_dir(language: str) -> Path:
    """Japanese is the default edition and lives at the directory root."""
    return Path() if language == "ja" else Path(language)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def render_all(
    input_dir: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT,
    site_url: str = DEFAULT_SITE_URL,
) -> list[Path]:
    _, features = load_features(input_dir)
    written: list[Path] = []
    for feature in features:
        for language in RENDER_LANGUAGES:
            path = output_dir / feature["slug"] / _language_dir(language) / "index.html"
            _atomic_write_text(path, render_feature_page(feature, site_url, language))
            written.append(path)
    for language in RENDER_LANGUAGES:
        path = output_dir / _language_dir(language) / "index.html"
        _atomic_write_text(path, render_archive_page(features, site_url, language))
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL)
    args = parser.parse_args(argv)
    written = render_all(args.input, args.output, args.site_url)
    languages = len(RENDER_LANGUAGES)
    feature_count = (len(written) - languages) // languages
    print(
        f"[features] Rendered {feature_count} feature(s) in "
        f"{'/'.join(RENDER_LANGUAGES)} and archives -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

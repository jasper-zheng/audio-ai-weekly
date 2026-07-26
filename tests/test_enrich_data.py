import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import enrich_data
from enrich_data import AI_FIELDS, BATCH_PROMPT_TMPL


def test_enrichment_prompt_preserves_task_examples_in_every_language():
    assert "音声生成" in BATCH_PROMPT_TMPL
    assert "音楽生成" in BATCH_PROMPT_TMPL
    assert "音频生成" in BATCH_PROMPT_TMPL
    assert "音频编解码" in BATCH_PROMPT_TMPL


def test_enrichment_requests_every_translated_analysis_field():
    for base in ("task", "what", "novel", "method", "validation", "discussion"):
        for suffix in ("En", "Zh"):
            assert f"{base}{suffix}" in AI_FIELDS
            assert f"{base}{suffix}" in BATCH_PROMPT_TMPL
    for name in ("abstractJa", "abstractZh", "titleZh"):
        assert name in AI_FIELDS
        assert name in BATCH_PROMPT_TMPL


def test_failed_ai_batch_does_not_mark_fields_complete(monkeypatch):
    monkeypatch.setattr(enrich_data, "SETTINGS", {
        "ai": {"provider": "gemini"},
        "gemini": {"model": "x", "retry_max": 0, "retry_interval": 0},
    })
    paper = {"id": "1234.5678", "title": "Title", "abstract": "Abstract"}
    assert enrich_data.fetch_ai_fields_batch(object(), [paper]) == {"1234.5678": {}}


def test_enrichment_preserves_explicit_null_ai_field(tmp_path):
    path = tmp_path / "week.json"
    paper = {
        "id": "1234.5678",
        "abstract": "Abstract",
        "categories": [],
        "upvotes": None,
        "projectPage": None,
        "citationCount": None,
    }
    path.write_text(json.dumps({"categories": [{"papers": [paper]}]}))

    changed = enrich_data.enrich_file(path, {"1234.5678": {"proposedMethod": None}})

    saved_paper = json.loads(path.read_text())["categories"][0]["papers"][0]
    assert changed is True
    assert "proposedMethod" in saved_paper
    assert saved_paper["proposedMethod"] is None


def test_enrichment_does_not_write_fields_for_empty_failure_result(tmp_path):
    path = tmp_path / "week.json"
    paper = {
        "id": "1234.5678",
        "abstract": "Abstract",
        "categories": [],
        "upvotes": None,
        "projectPage": None,
        "citationCount": None,
    }
    path.write_text(json.dumps({"categories": [{"papers": [paper]}]}))

    changed = enrich_data.enrich_file(path, {"1234.5678": {}})

    saved_paper = json.loads(path.read_text())["categories"][0]["papers"][0]
    assert changed is False
    assert "proposedMethod" not in saved_paper

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import build_data
from build_data import group_by_category


def test_generate_trend_uses_selected_provider_model(monkeypatch):
    calls = []

    class Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            message = type("Message", (), {"content": json.dumps(["a", "b", "c"])})()
            return type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})()

    client = type(
        "Client", (), {"chat": type("Chat", (), {"completions": Completions()})()}
    )()
    settings = {
        "ai": {"provider": "gemini"},
        "gemini": {
            "model": "gemini-3.5-flash",
            "max_tokens": 16000,
            "retry_max": 1,
            "retry_interval": 0,
        },
    }
    monkeypatch.setattr(build_data, "SETTINGS", settings)

    # A bare array is the legacy Japanese-only response shape.
    assert build_data.generate_trend(client, [{"title": "T", "what": "W"}]) == {
        "ja": ["a", "b", "c"]
    }
    assert calls[0]["model"] == "gemini-3.5-flash"
    assert calls[0]["max_tokens"] == 16000
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_generate_trend_rejects_non_array_language_values(monkeypatch):
    class Completions:
        def create(self, **kwargs):
            message = type("Message", (), {"content": json.dumps({"ja": "abc", "en": "xyz", "zh": "def"})})()
            return type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})()
    client = type("Client", (), {"chat": type("Chat", (), {"completions": Completions()})()})()
    monkeypatch.setattr(build_data, "SETTINGS", {
        "ai": {"provider": "gemini"},
        "gemini": {
            "model": "x",
            "max_tokens": 400,
            "retry_max": 1,
            "retry_interval": 0,
        },
    })
    assert build_data.generate_trend(client, [{"title": "T", "what": "W"}]) == {}


def test_generate_trend_waits_for_provider_interval_before_retry(monkeypatch):
    attempts = 0

    class Completions:
        def create(self, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("rate limited")
            message = type(
                "Message",
                (),
                {"content": json.dumps({
                    "ja": ["日1", "日2", "日3"],
                    "en": ["E1", "E2", "E3"],
                    "zh": ["中1", "中2", "中3"],
                })},
            )()
            return type(
                "Response", (), {"choices": [type("Choice", (), {"message": message})()]}
            )()

    client = type(
        "Client", (), {"chat": type("Chat", (), {"completions": Completions()})()}
    )()
    monkeypatch.setattr(build_data, "SETTINGS", {
        "ai": {"provider": "secondary"},
        "secondary": {
            "model": "openai/gpt-5",
            "max_tokens": 400,
            "retry_max": 2,
            "min_request_interval": 60.0,
        },
    })
    monotonic_values = iter([100.0, 100.0, 160.0])
    monkeypatch.setattr(build_data.time, "monotonic", lambda: next(monotonic_values))
    sleeps = []
    monkeypatch.setattr(build_data.time, "sleep", sleeps.append)

    result = build_data.generate_trend(client, [{"title": "T", "what": "W"}])

    assert result == {
        "ja": ["日1", "日2", "日3"],
        "en": ["E1", "E2", "E3"],
        "zh": ["中1", "中2", "中3"],
    }
    assert sleeps == [60.0]


def test_main_omits_failed_translated_trends_for_later_enrichment(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "analyzed_papers.json").write_text("[]")
    monkeypatch.setattr(build_data, "ROOT", tmp_path)
    monkeypatch.setattr(build_data, "SETTINGS", {
        "ai": {"provider": "gemini"},
        "gemini": {"api_key_env": "GEMINI_API_KEY"},
        "data": {
            "weekly_dir": "data/weekly",
            "index_file": "data/index.json",
        },
    })
    monkeypatch.setattr(build_data, "KEYWORDS", {"ui_categories": []})
    monkeypatch.setattr(build_data, "fetch_paper_meta", lambda papers: {})
    monkeypatch.setattr(build_data, "create_client", lambda settings: object())
    monkeypatch.setattr(build_data, "generate_trend", lambda client, papers: {})

    build_data.main(date_str="2026-07-10")

    weekly = json.loads((data_dir / "weekly/2026-0710.json").read_text())
    # Trend generation failed entirely, so every language falls back to the
    # localized placeholder rather than being omitted.
    assert weekly["trend"] == ["トレンド情報なし"] * 3
    assert weekly["trendEn"] == ["No trend information"] * 3
    assert weekly["trendZh"] == ["暂无趋势信息"] * 3


def test_main_keeps_a_legacy_japanese_only_trend_without_translations(monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "analyzed_papers.json").write_text("[]")
    monkeypatch.setattr(build_data, "ROOT", tmp_path)
    monkeypatch.setattr(build_data, "SETTINGS", {
        "ai": {"provider": "gemini"},
        "gemini": {"api_key_env": "GEMINI_API_KEY"},
        "data": {
            "weekly_dir": "data/weekly",
            "index_file": "data/index.json",
        },
    })
    monkeypatch.setattr(build_data, "KEYWORDS", {"ui_categories": []})
    monkeypatch.setattr(build_data, "fetch_paper_meta", lambda papers: {})
    monkeypatch.setattr(build_data, "create_client", lambda settings: object())
    monkeypatch.setattr(
        build_data, "generate_trend", lambda client, papers: {"ja": ["日1", "日2", "日3"]}
    )

    build_data.main(date_str="2026-07-10")

    weekly = json.loads((data_dir / "weekly/2026-0710.json").read_text())
    assert weekly["trend"] == ["日1", "日2", "日3"]
    # Missing translations are omitted so enrichment can backfill them later.
    assert "trendEn" not in weekly
    assert "trendZh" not in weekly

# group_by_category depends on KEYWORDS["ui_categories"], so these tests use
# the real definitions from keywords.yaml.

class TestGroupByCategory:
    def test_groups_papers_by_category(self):
        papers = [
            {"id": "1", "category": "foundation"},
            {"id": "2", "category": "generation"},
            {"id": "3", "category": "foundation"},
        ]
        result = group_by_category(papers)
        ids_by_cat = {c["id"]: len(c["papers"]) for c in result}
        assert ids_by_cat.get("foundation") == 2
        assert ids_by_cat.get("generation") == 1

    def test_unknown_category_goes_to_other(self):
        papers = [{"id": "1", "category": "unknown_cat"}]
        result = group_by_category(papers)
        other = next((c for c in result if c["id"] == "other"), None)
        assert other is not None
        assert len(other["papers"]) == 1

    def test_missing_category_goes_to_other(self):
        papers = [{"id": "1"}]  # No category key.
        result = group_by_category(papers)
        other = next((c for c in result if c["id"] == "other"), None)
        assert other is not None

    def test_empty_categories_excluded(self):
        papers = [{"id": "1", "category": "foundation"}]
        result = group_by_category(papers)
        cat_ids = [c["id"] for c in result]
        # Categories without papers are omitted.
        assert "generation" not in cat_ids
        assert "codec" not in cat_ids

    def test_result_has_required_fields(self):
        papers = [{"id": "1", "category": "codec"}]
        result = group_by_category(papers)
        cat = next(c for c in result if c["id"] == "codec")
        assert "id" in cat
        assert "color" in cat
        assert "papers" in cat
        # Every UI language must reach the frontend.
        assert "label" in cat
        assert "labelEn" in cat
        assert "labelZh" in cat

    def test_other_category_is_labelled_in_every_language(self):
        result = group_by_category([{"id": "1", "category": "unknown_cat"}])
        other = next(c for c in result if c["id"] == "other")
        assert other["label"] == "その他"
        assert other["labelEn"] == "Other"
        assert other["labelZh"] == "其他"

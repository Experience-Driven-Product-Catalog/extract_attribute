from __future__ import annotations

import pytest
import yaml

import extract_all_attributes
from extraction.contracts import SENTIMENT_VALUES
from utils.project_config import CONFIG_PATH, PROJECT_ROOT


def test_config_separates_outputs_and_codex_result_directories() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    opinion = config["opinion_units"]
    representative = config["representative_attribute"]
    assert opinion["output_parquet"] != representative["output_parquet"]
    assert opinion["codex_results_dir"] != representative["codex_results_dir"]
    assert (PROJECT_ROOT / opinion["prompt_path"]).exists()
    assert (PROJECT_ROOT / representative["prompt_path"]).exists()


def test_both_prompts_have_monitor_few_shots_and_all_sentiments() -> None:
    for relative_path in (
        "prompt/opinion_units.md",
        "prompt/representative_attribute.md",
    ):
        prompt = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "Few-shot" in prompt
        assert "키보드" in prompt
        assert "{{product_name}}" in prompt
        assert "{{product_category}}" in prompt
        assert "{{review}}" in prompt
        for sentiment in SENTIMENT_VALUES:
            assert f"`{sentiment}`" in prompt or f'"{sentiment}"' in prompt


def test_combined_entrypoint_runs_in_success_dependent_order(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        extract_all_attributes.extract_opinion_units,
        "main",
        lambda: calls.append("opinion_units") or "opinion",
    )
    monkeypatch.setattr(
        extract_all_attributes.extract_representative_attributes,
        "main",
        lambda: calls.append("representative_attribute") or "representative",
    )

    assert extract_all_attributes.main() == ("opinion", "representative")
    assert calls == ["opinion_units", "representative_attribute"]


def test_combined_entrypoint_does_not_start_second_stage_after_failure(
    monkeypatch,
) -> None:
    def fail_opinion_units():
        raise RuntimeError("first stage failed")

    monkeypatch.setattr(
        extract_all_attributes.extract_opinion_units,
        "main",
        fail_opinion_units,
    )
    monkeypatch.setattr(
        extract_all_attributes.extract_representative_attributes,
        "main",
        lambda: (_ for _ in ()).throw(AssertionError("second stage ran")),
    )

    with pytest.raises(RuntimeError, match="first stage failed"):
        extract_all_attributes.main()


def test_builder_and_prepared_source_data_exist() -> None:
    assert (PROJECT_ROOT / "build_computer_review_dataset.py").is_file()
    assert (PROJECT_ROOT / "monitor_reviews.parquet").is_file()
    assert (PROJECT_ROOT / "origin_dataset").is_dir()

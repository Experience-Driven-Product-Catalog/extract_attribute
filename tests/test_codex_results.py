from __future__ import annotations

import json
import subprocess
from pathlib import Path

from extraction.codex_cli import CodexExtractor
from extraction.contracts import ReviewInput
from extraction.tasks import (
    opinion_units_schema,
    parse_opinion_units,
    parse_representative_attributes,
    representative_attributes_schema,
)


class FakeCodexExtractor(CodexExtractor):
    def __init__(self, *, response: dict[str, object], **kwargs):
        self.response = response
        super().__init__(**kwargs)

    def _run_cli(self, *, result_path: Path, **kwargs):
        result_path.write_text(
            json.dumps(self.response, ensure_ascii=False), encoding="utf-8"
        )
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")


def write_prompt(path: Path) -> None:
    path.write_text(
        "Instruction\n\n### Input\n{{product_name}}\n{{product_category}}\n{{review}}\n",
        encoding="utf-8",
    )


def common_kwargs(tmp_path: Path, *, results_dir: Path) -> dict[str, object]:
    prompt_path = tmp_path / "prompt.md"
    write_prompt(prompt_path)
    return {
        "prompt_path": prompt_path,
        "results_dir": results_dir,
        "model": "test-model",
        "model_reasoning_effort": "high",
        "max_workers": 1,
        "timeout_seconds": 10,
        "progress_log_interval": 1,
    }


def test_each_task_saves_every_result_in_its_own_directory(tmp_path: Path) -> None:
    review = ReviewInput(7, "키보드", "키보드", "키감이 좋습니다.")
    opinion_dir = tmp_path / "codex_results" / "opinion_units"
    representative_dir = tmp_path / "codex_results" / "representative_attribute"
    opinion_response = {
        "opinion_units": [
            {
                "raw_aspect": "키감",
                "raw_status": "좋음",
                "excerpt": "키감이 좋습니다.",
                "opinion": "키감이 좋음",
                "sentiment": "positive",
            }
        ]
    }
    representative_response = {
        "representative_attributes": [
            {"raw_attribute": "키감", "sentiment": "positive"}
        ]
    }

    FakeCodexExtractor(
        response=opinion_response,
        task_name="opinion-units",
        output_schema=opinion_units_schema(),
        parse_result=parse_opinion_units,
        **common_kwargs(tmp_path, results_dir=opinion_dir),
    )(review)
    FakeCodexExtractor(
        response=representative_response,
        task_name="representative-attribute",
        output_schema=representative_attributes_schema(),
        parse_result=parse_representative_attributes,
        **common_kwargs(tmp_path, results_dir=representative_dir),
    )(review)

    assert json.loads((opinion_dir / "7.json").read_text(encoding="utf-8")) == (
        opinion_response
    )
    assert json.loads(
        (representative_dir / "7.json").read_text(encoding="utf-8")
    ) == representative_response


def test_empty_result_is_also_saved(tmp_path: Path) -> None:
    results_dir = tmp_path / "codex_results" / "opinion_units"
    extractor = FakeCodexExtractor(
        response={"opinion_units": []},
        task_name="opinion-units",
        output_schema=opinion_units_schema(),
        parse_result=parse_opinion_units,
        **common_kwargs(tmp_path, results_dir=results_dir),
    )

    assert extractor(ReviewInput(8, "키보드", "키보드", "배송이 빨랐습니다.")) == []
    assert json.loads((results_dir / "8.json").read_text(encoding="utf-8")) == {
        "opinion_units": []
    }


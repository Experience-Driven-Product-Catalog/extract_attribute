"""End-to-end Opinion Unit extraction from source Parquet to output Parquet."""

from __future__ import annotations

import logging

from extraction.codex_cli import CodexExtractor
from extraction.pipelines import run_opinion_unit_pipeline
from extraction.tasks import opinion_units_schema, parse_opinion_units
from utils.project_config import (
    load_config_section,
    require_positive_int,
    require_string,
    resolve_config_path,
)

CODEX_CONFIG = load_config_section("codex_extraction")
TASK_CONFIG = load_config_section("opinion_units")


def create_extractor() -> CodexExtractor:
    return CodexExtractor(
        task_name="opinion-units",
        prompt_path=resolve_config_path(require_string(TASK_CONFIG, "prompt_path")),
        output_schema=opinion_units_schema(),
        parse_result=parse_opinion_units,
        results_dir=resolve_config_path(
            require_string(TASK_CONFIG, "codex_results_dir")
        ),
        model=require_string(CODEX_CONFIG, "model"),
        model_reasoning_effort=require_string(
            CODEX_CONFIG, "model_reasoning_effort"
        ),
        max_workers=require_positive_int(CODEX_CONFIG, "max_workers"),
        timeout_seconds=require_positive_int(CODEX_CONFIG, "timeout_seconds"),
        progress_log_interval=require_positive_int(
            CODEX_CONFIG, "progress_log_interval"
        ),
    )


def main():
    input_parquet = resolve_config_path(require_string(TASK_CONFIG, "input_parquet"))
    output_parquet = resolve_config_path(
        require_string(TASK_CONFIG, "output_parquet")
    )
    logging.info(
        "opinion-unit pipeline started: input=%s output=%s",
        input_parquet,
        output_parquet,
    )
    dataframe = run_opinion_unit_pipeline(
        input_parquet=input_parquet,
        output_parquet=output_parquet,
        product_category=require_string(TASK_CONFIG, "product_category"),
        extractor=create_extractor(),
    )
    logging.info("opinion-unit pipeline saved: rows=%s", len(dataframe))
    return dataframe


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    main()


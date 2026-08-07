from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from extraction.contracts import OpinionUnit, RepresentativeAttribute
from extraction.pipelines import (
    OPINION_UNIT_COLUMNS,
    REPRESENTATIVE_ATTRIBUTE_COLUMNS,
    load_review_inputs,
    run_opinion_unit_pipeline,
    run_representative_attribute_pipeline,
)


def write_source(path: Path) -> None:
    pd.DataFrame(
        {
            "idx": pd.Series([100, 200], dtype="int32"),
            "review": ["키감이 좋습니다.", "키압은 무겁지만 마음에 듭니다."],
            "productName": ["키보드 A", "키보드 B"],
        }
    ).to_parquet(path, index=False)


def test_opinion_pipeline_writes_exact_schema_and_auto_increment_pk(
    tmp_path: Path,
) -> None:
    input_parquet = tmp_path / "source.parquet"
    output_parquet = tmp_path / "opinion.parquet"
    write_source(input_parquet)

    def extractor(inputs):
        assert [item.review_idx for item in inputs] == [100, 200]
        return [
            OpinionUnit(
                review_idx=100,
                raw_aspect="키감",
                raw_status="좋음",
                excerpt="키감이 좋습니다.",
                opinion="키감이 좋음",
                sentiment="positive",
            ),
            OpinionUnit(
                review_idx=200,
                raw_aspect="키압",
                raw_status="무거움",
                excerpt="키압은 무겁지만 마음에 듭니다.",
                opinion="무거운 키압을 선호함",
                sentiment="positive",
            ),
        ]

    dataframe = run_opinion_unit_pipeline(
        input_parquet=input_parquet,
        output_parquet=output_parquet,
        product_category="키보드",
        extractor=extractor,
    )
    persisted = pd.read_parquet(output_parquet)

    assert tuple(dataframe.columns) == OPINION_UNIT_COLUMNS
    assert tuple(persisted.columns) == OPINION_UNIT_COLUMNS
    assert dataframe["idx"].tolist() == [1, 2]
    assert dataframe["idx"].dtype == "int64"
    assert dataframe["review_idx"].tolist() == [100, 200]
    assert dataframe["sentiment"].tolist() == ["positive", "positive"]


def test_representative_pipeline_keeps_multiple_attributes_per_review(
    tmp_path: Path,
) -> None:
    input_parquet = tmp_path / "source.parquet"
    output_parquet = tmp_path / "representative.parquet"
    write_source(input_parquet)

    dataframe = run_representative_attribute_pipeline(
        input_parquet=input_parquet,
        output_parquet=output_parquet,
        product_category="키보드",
        extractor=lambda inputs: [
            RepresentativeAttribute(100, "키감", "positive"),
            RepresentativeAttribute(100, "키압", "neutral"),
            RepresentativeAttribute(200, "키압", "positive"),
        ],
    )

    assert tuple(dataframe.columns) == REPRESENTATIVE_ATTRIBUTE_COLUMNS
    assert dataframe["idx"].tolist() == [1, 2, 3]
    assert dataframe["review_idx"].tolist() == [100, 100, 200]
    assert dataframe["raw_attribute"].tolist() == ["키감", "키압", "키압"]
    assert set(dataframe["sentiment"]) <= {
        "positive",
        "negative",
        "mixed",
        "neutral",
        "unknown",
    }


def test_empty_extraction_still_writes_the_exact_schema(tmp_path: Path) -> None:
    input_parquet = tmp_path / "source.parquet"
    output_parquet = tmp_path / "empty.parquet"
    write_source(input_parquet)

    dataframe = run_representative_attribute_pipeline(
        input_parquet=input_parquet,
        output_parquet=output_parquet,
        product_category="키보드",
        extractor=lambda inputs: [],
    )

    assert dataframe.empty
    assert tuple(dataframe.columns) == REPRESENTATIVE_ATTRIBUTE_COLUMNS
    assert tuple(pd.read_parquet(output_parquet).columns) == (
        REPRESENTATIVE_ATTRIBUTE_COLUMNS
    )


def test_source_review_idx_must_be_unique(tmp_path: Path) -> None:
    input_parquet = tmp_path / "duplicates.parquet"
    pd.DataFrame(
        {
            "idx": [1, 1],
            "review": ["첫 리뷰", "둘째 리뷰"],
            "productName": ["제품", "제품"],
        }
    ).to_parquet(input_parquet, index=False)

    with pytest.raises(ValueError, match="idx는 고유"):
        load_review_inputs(input_parquet, product_category="키보드")


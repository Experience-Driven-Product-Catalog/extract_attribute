"""Source-Parquet to extraction-Parquet pipelines shared by both entry points."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

import pandas as pd

from extraction.contracts import (
    SENTIMENT_VALUES,
    OpinionUnit,
    RepresentativeAttribute,
    ReviewInput,
)

REQUIRED_SOURCE_COLUMNS = ("idx", "review", "productName")
OPINION_UNIT_COLUMNS = (
    "idx",
    "review_idx",
    "raw_aspect",
    "raw_status",
    "excerpt",
    "opinion",
    "sentiment",
)
REPRESENTATIVE_ATTRIBUTE_COLUMNS = (
    "idx",
    "review_idx",
    "raw_attribute",
    "sentiment",
)

OpinionExtractor = Callable[[Sequence[ReviewInput]], Sequence[OpinionUnit]]
RepresentativeExtractor = Callable[
    [Sequence[ReviewInput]], Sequence[RepresentativeAttribute]
]


def load_review_inputs(
    input_parquet: Path,
    *,
    product_category: str,
) -> list[ReviewInput]:
    """Read and validate the source contract produced by the dataset builder."""
    source = pd.read_parquet(input_parquet)
    missing = [column for column in REQUIRED_SOURCE_COLUMNS if column not in source]
    if missing:
        raise KeyError("입력 parquet에 필요한 열이 없습니다: " + ", ".join(missing))
    if source["idx"].isna().any():
        raise ValueError("입력 parquet의 idx에는 null이 없어야 합니다.")
    if source["idx"].duplicated().any():
        duplicates = source.loc[source["idx"].duplicated(), "idx"].tolist()
        raise ValueError(f"입력 parquet의 idx는 고유해야 합니다: {duplicates[:5]}")

    return [
        ReviewInput(
            review_idx=review_idx,
            product_name=product_name,
            product_category=product_category,
            review=review,
        )
        for review_idx, review, product_name in source.loc[
            :, list(REQUIRED_SOURCE_COLUMNS)
        ].itertuples(index=False, name=None)
    ]


def opinion_units_dataframe(outputs: Sequence[OpinionUnit]) -> pd.DataFrame:
    """Build the exact Opinion Unit output schema with a 1-based logical PK."""
    records = [
        {
            "idx": row_idx,
            "review_idx": output.review_idx,
            "raw_aspect": output.raw_aspect,
            "raw_status": output.raw_status,
            "excerpt": output.excerpt,
            "opinion": output.opinion,
            "sentiment": output.sentiment,
        }
        for row_idx, output in enumerate(outputs, start=1)
    ]
    dataframe = pd.DataFrame.from_records(records, columns=OPINION_UNIT_COLUMNS)
    return _normalize_output_dtypes(dataframe, nullable_columns=("raw_status",))


def representative_attributes_dataframe(
    outputs: Sequence[RepresentativeAttribute],
) -> pd.DataFrame:
    """Build the exact direct-attribute schema with a 1-based logical PK."""
    records = [
        {
            "idx": row_idx,
            "review_idx": output.review_idx,
            "raw_attribute": output.raw_attribute,
            "sentiment": output.sentiment,
        }
        for row_idx, output in enumerate(outputs, start=1)
    ]
    dataframe = pd.DataFrame.from_records(
        records, columns=REPRESENTATIVE_ATTRIBUTE_COLUMNS
    )
    return _normalize_output_dtypes(dataframe)


def _normalize_output_dtypes(
    dataframe: pd.DataFrame,
    *,
    nullable_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe["idx"] = pd.Series(dataframe["idx"], dtype="int64")
    dataframe["review_idx"] = pd.Series(dataframe["review_idx"], dtype="int64")
    for column in dataframe.columns:
        if column in {"idx", "review_idx"}:
            continue
        dataframe[column] = pd.Series(dataframe[column], dtype="string")
    for column in nullable_columns:
        dataframe[column] = dataframe[column].astype("string")
    _validate_output_integrity(dataframe)
    return dataframe


def _validate_output_integrity(dataframe: pd.DataFrame) -> None:
    expected_idx = list(range(1, len(dataframe) + 1))
    if dataframe["idx"].tolist() != expected_idx:
        raise ValueError("출력 idx는 1부터 연속 증가해야 합니다.")
    if dataframe["idx"].isna().any() or dataframe["idx"].duplicated().any():
        raise ValueError("출력 idx는 null이 없는 고유 PK여야 합니다.")
    invalid_sentiments = set(dataframe["sentiment"].dropna()) - set(
        SENTIMENT_VALUES
    )
    if invalid_sentiments:
        raise ValueError(f"허용되지 않은 sentiment가 있습니다: {invalid_sentiments}")


def atomic_write_parquet(dataframe: pd.DataFrame, output_parquet: Path) -> None:
    """Write beside the destination, then atomically replace it on success."""
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{output_parquet.name}.",
        suffix=".tmp",
        dir=output_parquet.parent,
    )
    os.close(handle)
    temporary_path = Path(temporary_name)
    try:
        dataframe.to_parquet(
            temporary_path,
            engine="pyarrow",
            index=False,
            compression="snappy",
        )
        os.replace(temporary_path, output_parquet)
    finally:
        temporary_path.unlink(missing_ok=True)


def run_opinion_unit_pipeline(
    *,
    input_parquet: Path,
    output_parquet: Path,
    product_category: str,
    extractor: OpinionExtractor,
) -> pd.DataFrame:
    inputs = load_review_inputs(input_parquet, product_category=product_category)
    dataframe = opinion_units_dataframe(extractor(inputs))
    atomic_write_parquet(dataframe, output_parquet)
    return dataframe


def run_representative_attribute_pipeline(
    *,
    input_parquet: Path,
    output_parquet: Path,
    product_category: str,
    extractor: RepresentativeExtractor,
) -> pd.DataFrame:
    inputs = load_review_inputs(input_parquet, product_category=product_category)
    dataframe = representative_attributes_dataframe(extractor(inputs))
    atomic_write_parquet(dataframe, output_parquet)
    return dataframe


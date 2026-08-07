from __future__ import annotations

import pytest

from extraction.contracts import SENTIMENT_VALUES, ReviewInput
from extraction.tasks import (
    opinion_units_schema,
    parse_opinion_units,
    parse_representative_attributes,
    representative_attributes_schema,
)


@pytest.fixture
def review_input() -> ReviewInput:
    return ReviewInput(
        review_idx=10,
        product_name="기계식 키보드",
        product_category="키보드",
        review="키압은 무겁지만 마음에 듭니다. 내구성은 더 써봐야 알겠습니다.",
    )


def test_schemas_restrict_sentiment_to_five_values() -> None:
    opinion_item = opinion_units_schema()["properties"]["opinion_units"]["items"]
    representative_item = representative_attributes_schema()["properties"][
        "representative_attributes"
    ]["items"]

    assert opinion_item["required"] == [
        "raw_aspect",
        "raw_status",
        "excerpt",
        "opinion",
        "sentiment",
    ]
    assert opinion_item["properties"]["sentiment"]["enum"] == list(
        SENTIMENT_VALUES
    )
    assert representative_item["required"] == ["raw_attribute", "sentiment"]
    assert representative_item["properties"]["sentiment"]["enum"] == list(
        SENTIMENT_VALUES
    )
    assert opinion_item["additionalProperties"] is False
    assert representative_item["additionalProperties"] is False


def test_parse_opinion_units_keeps_valid_items_and_filters_only_invalid_content(
    review_input: ReviewInput,
) -> None:
    results = parse_opinion_units(
        review_input,
        {
            "opinion_units": [
                {
                    "raw_aspect": "키압",
                    "raw_status": "무거움",
                    "excerpt": "키압은 무겁지만 마음에 듭니다.",
                    "opinion": "무거운 키압을 선호함",
                    "sentiment": "positive",
                },
                {
                    "raw_aspect": "근거 없음",
                    "raw_status": "좋음",
                    "excerpt": "원문에 없는 근거",
                    "opinion": "잘못된 항목",
                    "sentiment": "positive",
                },
                {
                    "raw_aspect": "내구성",
                    "raw_status": "판단 보류",
                    "excerpt": "내구성은 더 써봐야 알겠습니다.",
                    "opinion": "더 사용해야 내구성을 판단할 수 있음",
                    "sentiment": "unknown",
                },
            ]
        },
    )

    assert [result.raw_aspect for result in results] == ["키압", "내구성"]
    assert [result.sentiment for result in results] == ["positive", "unknown"]


def test_parse_representative_attributes_returns_multiple_attributes(
    review_input: ReviewInput,
) -> None:
    results = parse_representative_attributes(
        review_input,
        {
            "representative_attributes": [
                {"raw_attribute": "키압", "sentiment": "positive"},
                {"raw_attribute": "내구성", "sentiment": "unknown"},
            ]
        },
    )

    assert [(result.raw_attribute, result.sentiment) for result in results] == [
        ("키압", "positive"),
        ("내구성", "unknown"),
    ]


@pytest.mark.parametrize(
    ("response", "match"),
    [
        (
            {"opinion_units": [], "metadata": {}},
            "최상위 응답 계약 위반.*metadata",
        ),
        (
            {
                "opinion_units": [
                    {
                        "raw_aspect": "키압",
                        "raw_status": "무거움",
                        "excerpt": "키압은 무겁지만 마음에 듭니다.",
                        "opinion": "키압을 선호함",
                        "sentiment": "positive",
                        "confidence": 1,
                    }
                ]
            },
            r"opinion_units\[0\] 계약 위반.*confidence",
        ),
    ],
)
def test_opinion_contract_rejects_extra_fields(
    review_input: ReviewInput,
    response: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        parse_opinion_units(review_input, response)


def test_invalid_sentiment_item_is_not_emitted(review_input: ReviewInput) -> None:
    assert parse_representative_attributes(
        review_input,
        {
            "representative_attributes": [
                {"raw_attribute": "키압", "sentiment": "good"}
            ]
        },
    ) == []


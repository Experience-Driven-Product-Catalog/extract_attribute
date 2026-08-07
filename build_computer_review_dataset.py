import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from utils.project_config import (
    PROJECT_ROOT,
    load_config_section,
    require_positive_int,
    require_string,
    require_string_list,
    resolve_config_path,
)

BUILD_DATASET_CONFIG = load_config_section("build_computer_review_dataset")
ARCHIVE_DIRS = [
    resolve_config_path(path)
    for path in require_string_list(BUILD_DATASET_CONFIG, "archive_dirs")
]

TEMP_JSON_DIR = PROJECT_ROOT / "jsons"
RESULT_PATH = resolve_config_path(require_string(BUILD_DATASET_CONFIG, "result_path"))
SAMPLE_COUNT = require_positive_int(BUILD_DATASET_CONFIG, "sample_count")

TARGET_COLUMNS = [
    "Index",
    "RawText",
    "Source",
    "Domain",
    "MainCategory",
    "ProductName",
]

TARGET_PRODUCT_NAMES = [
    "오디세이 삼성전자 G3 S27AG300",
    "LG전자 27MK430H",
    "AOC 알파스캔 24B2 보더리스 IPS 75 시력보호 무결점",
    "AOC 알파스캔 27B2 보더리스 75 시력보호 무결점",
    "삼성전자 F27T350",
    "삼성전자 F24T350",
    "옵틱스 MSI G271 게이밍 144 아이세이버 무결점",
    "SMART 삼성전자 M7 S32BM700",
    "AOC 알파스캔 Q27G2S 게이밍 IPS 155 QHD 프리싱크 무결점",
]

KOREAN_PATTERN = re.compile(r"[가-힣]")


def extract_zip_files(
    archive_dirs: list[Path],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for archive_dir in archive_dirs:
        zip_files = sorted(
            path
            for path in archive_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".zip"
        )

        for zip_path in zip_files:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "zipfile",
                    "--metadata-encoding",
                    "cp949",
                    "-e",
                    str(zip_path),
                    str(output_dir),
                ],
                check=True,
            )


def is_blank(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, dict)):
        return len(value) == 0

    return False


def load_json_objects(json_path: Path) -> list[dict[str, Any]]:
    with json_path.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if isinstance(data, dict):
        return [data]

    return []


def load_valid_rows(target_dir: Path) -> list[dict[str, Any]]:
    json_files = sorted(target_dir.rglob("*.json"))

    if not json_files:
        raise FileNotFoundError(f"JSON files were not found: {target_dir.resolve()}")

    rows: list[dict[str, Any]] = []

    for json_path in json_files:
        try:
            objects = load_json_objects(json_path)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue

        for obj in objects:
            if any(
                column not in obj or is_blank(obj[column]) for column in TARGET_COLUMNS
            ):
                continue

            rows.append({column: obj[column] for column in TARGET_COLUMNS})

    if not rows:
        raise ValueError("No valid JSON objects were found.")

    return rows


def check_korean_ratio(text: Any) -> bool:
    if pd.isna(text) or not isinstance(text, str):
        return False

    words = text.split()

    if not words:
        return False

    korean_word_count = sum(bool(KOREAN_PATTERN.search(word)) for word in words)

    return korean_word_count / len(words) >= 0.8


def create_result_parquet(
    target_dir: Path,
    output_path: Path,
) -> None:
    rows = load_valid_rows(target_dir)

    dataframe = pd.DataFrame(
        rows,
        columns=TARGET_COLUMNS,
    ).astype(
        {
            "Index": "Int32",
            "Source": "category",
            "Domain": "category",
            "MainCategory": "category",
            "ProductName": "category",
        }
    )

    # 데모를 위해 쇼필몰 리뷰 중 TARGET_PRODUCT_NAMES 리뷰들만 추출한다.
    # 간혹 영어/일본어/중국어 리뷰들이 있어 한국어 리뷰들만 추출한다.
    filtered = dataframe.loc[
        dataframe["Source"].eq("쇼핑몰")
        & dataframe["RawText"].apply(check_korean_ratio)
        & dataframe["MainCategory"].eq("컴퓨터/주변기기")
        & dataframe["ProductName"].isin(TARGET_PRODUCT_NAMES)
    ]

    product_counts = filtered.groupby(
        "ProductName",
        observed=False,
    )["ProductName"].transform("count")

    # 리뷰가 50개 이상 150개 미만인 상품들의 리뷰를 대상으로 설정된 수만큼 앞에서부터 추출한다.
    result = (
        filtered.loc[product_counts.between(50, 150)]
        .drop(
            columns=[
                "Source",
                "Domain",
                "MainCategory",
            ]
        )
        .reset_index(drop=True)
        .iloc[:SAMPLE_COUNT]
        .rename(
            columns={
                "Index": "idx",
                "RawText": "review",
                "ProductName": "productName",
            }
        )
    )

    # 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(
        output_path,
        engine="pyarrow",
        index=False,
        compression="snappy",
    )


def main() -> None:
    """Build the configured Parquet dataset and remove temporary JSON on success."""
    extract_zip_files(
        archive_dirs=ARCHIVE_DIRS,
        output_dir=TEMP_JSON_DIR,
    )

    create_result_parquet(
        target_dir=TEMP_JSON_DIR,
        output_path=RESULT_PATH,
    )

    shutil.rmtree(TEMP_JSON_DIR)


if __name__ == "__main__":
    main()

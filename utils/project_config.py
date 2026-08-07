"""프로젝트 최상위 YAML 설정을 읽고 검증하는 공용 도구."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config_section(section_name: str) -> dict[str, Any]:
    """``config.yaml``의 필수 최상위 설정 섹션을 읽는다."""
    try:
        raw_config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"설정 파일을 찾지 못했습니다: {CONFIG_PATH}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"설정 파일 YAML 형식이 올바르지 않습니다: {CONFIG_PATH}") from exc

    if not isinstance(raw_config, Mapping):
        raise TypeError("설정 파일의 최상위 값은 매핑이어야 합니다.")

    section = raw_config.get(section_name)
    if not isinstance(section, Mapping):
        raise TypeError(f"설정 섹션 {section_name!r}은 매핑이어야 합니다.")
    return dict(section)


def require_string(config: Mapping[str, Any], key: str) -> str:
    """필수 문자열 설정을 읽는다."""
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"설정 {key!r}은 비어 있지 않은 문자열이어야 합니다.")
    return value


def require_positive_int(config: Mapping[str, Any], key: str) -> int:
    """필수 양의 정수 설정을 읽는다."""
    value = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TypeError(f"설정 {key!r}은 0보다 큰 정수여야 합니다.")
    return value


def require_string_list(config: Mapping[str, Any], key: str) -> list[str]:
    """하나 이상의 문자열을 갖는 필수 목록 설정을 읽는다."""
    value = config.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise TypeError(
            f"설정 {key!r}은 비어 있지 않은 문자열 목록이어야 합니다."
        )
    return value


def resolve_config_path(value: str) -> Path:
    """YAML 상대 경로를 프로젝트 최상위 기준으로 해석한다."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


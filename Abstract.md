# 리뷰 속성 추출 프로젝트

`monitor_reviews.parquet`의 리뷰를 두 가지 방식으로 끝까지 추출하고, 각 결과를 별도의 Parquet과 `codex_results` 하위 경로에 저장한다. 두 방식 모두 Codex 구조화 출력에서 속성별 `sentiment`를 직접 생성하므로 별도 감정 분석 모델이나 후처리 단계가 없다.

## 환경

```bash
uv sync
```

모델, 병렬 처리 수, 타임아웃, 입력·출력 경로, 결과 JSON 경로와 상품 카테고리는 모두 `config.yaml`에서 조정한다.

## 데이터셋 생성

```bash
uv run python build_computer_review_dataset.py
```

`build_computer_review_dataset.py`는 기존 파일을 그대로 사용한다. `origin_dataset`의 설정된 라벨링 ZIP을 읽어 `monitor_reviews.parquet`을 생성하며, 추출 수는 `build_computer_review_dataset.sample_count`가 결정한다.

## Opinion Unit 추출

```bash
uv run python extract_opinion_units.py
```

`prompt/opinion_units.md`를 사용해 리뷰별 `raw_aspect`, `raw_status`, 연속 원문 `excerpt`, 완전한 `opinion`, 속성·상태별 `sentiment`를 추출한다.

- 모델 응답: `codex_results/opinion_units/{review_idx}.json`
- Parquet: `monitor_opinion_units.parquet`
- 열: `idx`, `review_idx`, `raw_aspect`, `raw_status`, `excerpt`, `opinion`, `sentiment`

### Opinion Unit 필드 용어

| 필드 | 한 줄 설명 |
| --- | --- |
| `raw_aspect` | 추출 시점에 정규화하지 않고 기록한, 리뷰어가 평가한 상품 속성·구성요소·사용 상황의 원본 명칭이다. |
| `raw_status` | `raw_aspect`의 관찰된 상태·조건·값이며, 근거 있는 상태를 특정할 수 없을 때만 `null`이다. |
| `aspect` | `raw_aspect`를 그대로 쓰거나 같은 `product_category` 안의 군집 대표명으로 정규화한 최종 분석 속성이다. |
| `status` | `raw_status`를 그대로 쓰거나 해당 aspect 군집 안의 군집 대표명으로 정규화한 최종 분석 상태다. |
| `excerpt` | 해당 Opinion Unit을 뒷받침하도록 리뷰 원문에서 변경 없이 복사한 연속 구간이다. |
| `opinion` | 방향·정도·비교·사용 맥락을 보존해 리뷰어의 관찰 또는 평가를 간결하게 완결한 서술이다. |
| `sentiment` | 해당 aspect·status에 대한 리뷰어의 평가 방향으로 `positive`, `negative`, `mixed`, `neutral`, `unknown` 중 하나다. |

원본 추출 JSON과 Parquet에는 `raw_aspect`, `raw_status`, `excerpt`, `opinion`, `sentiment`이 저장되며, `aspect`와 `status`는 후속 군집화·정규화 매핑에서 생성한다.

## Representative Attribute 추출

```bash
uv run python extract_representative_attributes.py
```

`prompt/representative_attribute.md`를 사용한다. 리뷰당 하나로 제한하지 않고, 리뷰에 근거가 있는 여러 `raw_attribute`와 각 속성의 `sentiment`를 추출한다.

- 모델 응답: `codex_results/representative_attribute/{review_idx}.json`
- Parquet: `monitor_representative_attributes.parquet`
- 열: `idx`, `review_idx`, `raw_attribute`, `sentiment`

## 두 방식 순차 실행

```bash
uv run python extract_all_attributes.py
```

Opinion Unit 추출을 먼저 완료한 뒤 Representative Attribute 추출을 실행한다. 첫 단계가 실패하면 두 번째 단계는 실행하지 않아 불완전한 전체 실행을 성공으로 오인하지 않는다.

두 Parquet의 `idx`는 1부터 시작해 행마다 1씩 증가하는 `int64` 논리 PK다. Parquet 자체는 데이터베이스 제약을 저장하지 않으므로, 저장 직전에 null·중복·연속성을 코드로 검증한다. `review_idx`는 원본 `monitor_reviews.parquet`의 `idx`를 보존한다.

허용되는 `sentiment`는 다음 다섯 값뿐이다.

| 값 | 의미 |
| --- | --- |
| `positive` | 해당 속성 또는 상태를 명백하게 선호함 |
| `negative` | 해당 속성 또는 상태를 명백하게 불만족함 |
| `mixed` | 같은 속성의 장점과 단점이 함께 나타남 |
| `neutral` | 평가 없이 사실이나 경험만 기술함 |
| `unknown` | 근거만으로 평가 방향을 결정하기 어려움 |

## 검증

```bash
uv run pytest
```

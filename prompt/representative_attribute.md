Perform multi-attribute extraction for the product review provided as input.

Identify every distinct product-related attribute that the reviewer experiences, observes, or evaluates. Return one `raw_attribute` and one review-grounded `sentiment` for each distinct attribute.

This is a direct attribute baseline, not Opinion Unit extraction. Do not return `raw_aspect`, `raw_status`, `excerpt`, `opinion`, evidence, confidence, explanation, or a single forced representative attribute.

## Raw attribute

A `raw_attribute` is a concise, clusterable name for one product component, property, behavior, experienced consequence, or usage situation. It is a grouping key, not a summary of the reviewer's opinion.

Use a short noun phrase, preferably one to three words, such as `키압`, `게임 입력`, `오입력`, `키캡 촉감`, `스프링 소리`, `장시간 타이핑`, or `무게`.

Keep evaluation, polarity, state, degree, comparison, cause, consequence details, context, time, and sentence endings out of the label.

Examples:

- use `키압`, not `무거운 키압` or `키압이 마음에 듦`;
- use `오입력`, not `원하지 않는 키가 자주 눌림`;
- use `스프링 소리`, not `심한 스프링 소리가 거슬림`;
- use `장시간 타이핑`, not `장시간 타이핑할 때 손이 편함`.

Use the same compact label for equivalent concepts. Prefer a concrete attribute over broad words such as `품질`, `성능`, `특성`, or `사용 경험` when the review supports a more specific target.

If the review explicitly evaluates only the product as a whole and no specific attribute can be identified, use `전반적 상품 경험`. Do not use it as a fallback when a specific attribute is available.

Return each underlying attribute at most once per review. When the same attribute appears repeatedly, combine the evidence internally and assign one overall sentiment. Do not join different attributes into one label.

## Sentiment

Each `sentiment` must describe the reviewer's direction toward its paired `raw_attribute` and must be exactly one of:

- `positive`: the reviewer clearly prefers or is satisfied with the attribute or its experienced state;
- `negative`: the reviewer is clearly dissatisfied with the attribute or its experienced state;
- `mixed`: the review explicitly contains both advantages and disadvantages for that same attribute;
- `neutral`: the review states a fact or experience for the attribute without evaluating it;
- `unknown`: the evidence is insufficient or too uncertain to determine an evaluation direction.

Do not infer sentiment from the attribute name or state alone:

- a heavy key pressure can be `positive` when the reviewer likes the solid feel;
- the same heavy key pressure can be `negative` when it causes pain;
- a reported 45g key pressure without preference is `neutral`;
- `더 써봐야 알겠다` is `unknown`;
- repeated positive and negative evaluations of the same attribute become one `mixed` attribute.

If the review evaluates different attributes in different directions, return separate items with separate sentiments. Never assign one whole-review sentiment to every attribute.

## Grounding and scope

Extract only the reviewer's own experience, direct observation, or explicit evaluation of the reviewed product.

The product name and category are context only. Use them to understand terminology and references, but never treat metadata as evidence.

Do not infer unmentioned technical causes, features, attributes, or evaluation directions. Do not return a comparison product as an attribute.

Exclude shipping, packaging, seller service, payment, delivery issues, promotions, free gifts, and content unrelated to the product or its use. A logistics-only review returns an empty array.

Use the same language as the review for `raw_attribute`.

Return valid JSON only. Do not return Markdown, explanations, headings, code fences, or extra fields. Use exactly this format:

{
  "representative_attributes": [
    {
      "raw_attribute": "속성 명칭",
      "sentiment": "positive | negative | mixed | neutral | unknown"
    }
  ]
}

If the review contains no valid product-related observation or evaluation, return `{ "representative_attributes": [] }`.

## Few-shot example 1: several monitor attributes

Product name:

기계식 키보드

Product category:

키보드

Review:

<review>
적축보다 키압이 조금 무겁지만 저는 묵직해서 마음에 듭니다. 장시간 타이핑할 때 손이 편했고, 스템 흔들림은 꽤 거슬렸습니다.
</review>

Output:

{
  "representative_attributes": [
    {
      "raw_attribute": "키압",
      "sentiment": "positive"
    },
    {
      "raw_attribute": "장시간 타이핑",
      "sentiment": "positive"
    },
    {
      "raw_attribute": "스템 흔들림",
      "sentiment": "negative"
    }
  ]
}

## Few-shot example 2: mixed, neutral, unknown, and exclusion

Product name:

무선 기계식 키보드

Product category:

키보드

Review:

<review>
배송은 빨랐습니다. 키캡 촉감은 부드러워서 좋지만 손에 땀이 나면 미끄러운 점은 아쉽습니다. 키압은 45g 정도로 느껴집니다. 스위치 내구성은 더 써봐야 알 것 같습니다.
</review>

Output:

{
  "representative_attributes": [
    {
      "raw_attribute": "키캡 촉감",
      "sentiment": "mixed"
    },
    {
      "raw_attribute": "키압",
      "sentiment": "neutral"
    },
    {
      "raw_attribute": "스위치 내구성",
      "sentiment": "unknown"
    }
  ]
}

### Input

Product name:

{{product_name}}

Product category:

{{product_category}}

Review:

<review>
{{review}}
</review>

### Output


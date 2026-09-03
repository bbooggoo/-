"""
예시 규칙: 수치 상한/하한 검사 (예: "유량값이 OVER 되는" 케이스).

params 예:
  {"max": 120, "min": 0, "unit": "LPM"}

ValidationRule.field_name_pattern 으로 어떤 필드에 적용할지 정규식 매칭
(예: "유량|FLOW" 이면 field_name 에 해당 단어가 포함된 셀에만 적용).
"""
import re

from .base import RuleContext, RuleOutcome, register


@register("max_value")
def max_value_rule(ctx: RuleContext) -> RuleOutcome | None:
    raw_value = ctx.spec_field.value
    if raw_value is None or raw_value.strip() == "":
        return None

    # 숫자만 추출 (예: "120 LPM" -> 120)
    match = re.search(r"-?\d+(\.\d+)?", raw_value.replace(",", ""))
    if not match:
        return RuleOutcome(message=f"'{raw_value}' 값에서 숫자를 인식할 수 없습니다.")

    number = float(match.group())
    max_v = ctx.params.get("max")
    min_v = ctx.params.get("min")
    unit = ctx.params.get("unit", "")

    if max_v is not None and number > float(max_v):
        return RuleOutcome(
            message=f"값 OVER: {number}{unit} > 최대 허용 {max_v}{unit}"
        )
    if min_v is not None and number < float(min_v):
        return RuleOutcome(
            message=f"값 UNDER: {number}{unit} < 최소 허용 {min_v}{unit}"
        )
    return None

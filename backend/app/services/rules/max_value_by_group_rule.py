"""
성상(그룹)별로 다른 상한값을 적용하는 수치 검사.

실제 요청 배경: "유량 OVER" 기준이 성상(가스 종류)마다 다르다 — 예: N2는 10 SLPM,
O2는 6 SLPM, Ar은 12 SLPM처럼 성상별로 허용 유량이 다름. 같은 "유량" 필드라도
같은 행의 "성상명" 값을 봐야 어떤 기준을 적용할지 알 수 있으므로, RuleContext.sibling()
로 같은 행의 성상명 필드를 찾아 그 값에 맞는 기준을 사용한다.

params 예:
  {
    "unit": "SLPM",
    "group_field": "성상명",
    "thresholds": {"N2": 10, "O2": 6, "AR": 12, "CDA": 15, "HE": 8, "H2": 6},
    "default_max": null   # thresholds에 없는 성상에 적용할 기본값(선택, 없으면 판단 보류)
  }
"""
import re

from .base import RuleContext, RuleOutcome, register


@register("max_value_by_group")
def max_value_by_group_rule(ctx: RuleContext) -> RuleOutcome | None:
    raw_value = ctx.spec_field.value
    if raw_value is None or raw_value.strip() == "":
        return None

    match = re.search(r"-?\d+(\.\d+)?", raw_value.replace(",", ""))
    if not match:
        return RuleOutcome(message=f"'{raw_value}' 값에서 숫자를 인식할 수 없습니다.")
    number = float(match.group())

    unit = ctx.params.get("unit", "")
    group_field = ctx.params.get("group_field", "성상명")
    thresholds = {str(k).upper(): v for k, v in ctx.params.get("thresholds", {}).items()}
    default_max = ctx.params.get("default_max")

    group_value = (ctx.sibling(group_field) or "").strip()
    max_v = thresholds.get(group_value.upper())
    if max_v is None:
        max_v = default_max
    if max_v is None:
        # 해당 성상에 대한 기준값이 없으면 판단 보류 (오탐 방지)
        return None

    if number > float(max_v):
        label = group_value or "성상 미확인"
        return RuleOutcome(message=f"[{label}] 유량 OVER: {number}{unit} > 기준 {max_v}{unit}")
    return None

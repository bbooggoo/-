"""
값 별칭(비표준 표기/오탈자)을 표준값으로 자동 치환하는 규칙.

"자동 제원 질의" 트랙의 대표 예시다 — 이 규칙만 대체값(suggested_value)을 스스로
계산해내므로, 이 규칙이 낸 ValidationResult 만 자동 질의 일괄 생성 대상이 된다
(다른 규칙은 "이상하다"는 것만 알지 "무엇으로 고쳐야 하는지"는 모르므로 수동 질의로 남는다).

params 예:
  {"aliases": {"GN2": "N2", "LN2": "N2", "질소": "N2"}, "case_sensitive": false}
"""
from .base import RuleContext, RuleOutcome, register


@register("alias_correction")
def alias_correction_rule(ctx: RuleContext) -> RuleOutcome | None:
    raw_value = ctx.spec_field.value
    if raw_value is None or raw_value.strip() == "":
        return None

    aliases = ctx.params.get("aliases", {})
    case_sensitive = ctx.params.get("case_sensitive", False)

    value = raw_value.strip()
    key = value if case_sensitive else value.upper()
    lookup = aliases if case_sensitive else {str(k).upper(): v for k, v in aliases.items()}

    target = lookup.get(key)
    if target is None or target == value:
        return None  # 별칭 목록에 없거나 이미 표준값

    return RuleOutcome(
        message=f"'{value}' -> 표준값 '{target}' 로 자동 수정 제안",
        suggested_value=target,
    )

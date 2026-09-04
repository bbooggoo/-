"""
예시 규칙: 값이 표준화된 허용 목록에 속하는지 검사 (예: 성상값 표준화).

params 예:
  {"allowed_values": ["GAS", "LIQUID", "SOLID", "PLASMA"], "case_sensitive": false}
"""
from .base import RuleContext, RuleOutcome, register


@register("standardized_enum")
def standardized_enum_rule(ctx: RuleContext) -> RuleOutcome | None:
    raw_value = ctx.spec_field.value
    if raw_value is None or raw_value.strip() == "":
        return None

    allowed = ctx.params.get("allowed_values", [])
    case_sensitive = ctx.params.get("case_sensitive", False)

    value = raw_value.strip()
    compare_value = value if case_sensitive else value.upper()
    compare_allowed = allowed if case_sensitive else [str(a).upper() for a in allowed]

    if compare_value not in compare_allowed:
        return RuleOutcome(
            message=f"표준화되지 않은 값: '{value}' (허용값: {', '.join(str(a) for a in allowed)})"
        )
    return None

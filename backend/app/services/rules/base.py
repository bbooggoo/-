"""검증 규칙 플러그인의 공통 타입 정의."""
from dataclasses import dataclass, field
from typing import Callable, Optional

from ...models import RuleSeverity, SpecField


@dataclass
class RuleContext:
    """규칙 함수에 전달되는 실행 컨텍스트."""

    spec_field: SpecField
    params: dict
    default_severity: RuleSeverity

    # 같은 행(row_index)에 있는 다른 필드들의 {field_name: value} 맵.
    # 예: "GAS/AIR_유량" 셀을 검사할 때 같은 행의 "GAS/AIR_성상명" 값을 참조해서
    # 성상(가스 종류)별로 다른 기준값을 적용하는 규칙(max_value_by_group)에 쓰인다.
    siblings: dict[str, str] = field(default_factory=dict)

    def sibling(self, base_label: str) -> str | None:
        """현재 필드와 같은 대분류 접두어를 쓰는 형제 필드 값을 찾는다.

        현재 필드명이 "GAS/AIR_유량" 이면 "GAS/AIR_성상명" 을 찾고, 대분류 접두어가
        없는 공통 필드(예: "건설코드")면 base_label 그대로 찾는다.
        """
        field_name = self.spec_field.field_name or ""
        category = field_name.rsplit("_", 1)[0] if "_" in field_name else ""
        key = f"{category}_{base_label}" if category else base_label
        return self.siblings.get(key)


@dataclass
class RuleOutcome:
    """규칙 위반 시 반환. 위반이 없으면 None을 반환한다."""

    message: str
    severity: RuleSeverity | None = None  # None이면 규칙의 default_severity 사용
    # 규칙이 "무엇으로 고쳐야 하는지"까지 스스로 판단할 수 있을 때만 채운다
    # (예: alias_correction 의 표준값 치환). 이 값이 있으면 "자동 제원 질의" 로,
    # 없으면 "수동 제원 질의"(설계사 서술형)로 처리된다 - services/auto_query.py 참고.
    suggested_value: str | None = None


# 규칙 함수 시그니처: (RuleContext) -> RuleOutcome | None
RuleFn = Callable[[RuleContext], Optional[RuleOutcome]]

RULE_REGISTRY: dict[str, RuleFn] = {}


def register(rule_type: str):
    """규칙 함수를 RULE_REGISTRY 에 등록하는 데코레이터."""

    def decorator(fn: RuleFn) -> RuleFn:
        RULE_REGISTRY[rule_type] = fn
        return fn

    return decorator

"""검증 규칙 플러그인의 공통 타입 정의."""
from dataclasses import dataclass
from typing import Callable, Optional

from ...models import RuleSeverity, SpecField


@dataclass
class RuleContext:
    """규칙 함수에 전달되는 실행 컨텍스트."""

    spec_field: SpecField
    params: dict
    default_severity: RuleSeverity


@dataclass
class RuleOutcome:
    """규칙 위반 시 반환. 위반이 없으면 None을 반환한다."""

    message: str
    severity: RuleSeverity | None = None  # None이면 규칙의 default_severity 사용


# 규칙 함수 시그니처: (RuleContext) -> RuleOutcome | None
RuleFn = Callable[[RuleContext], Optional[RuleOutcome]]

RULE_REGISTRY: dict[str, RuleFn] = {}


def register(rule_type: str):
    """규칙 함수를 RULE_REGISTRY 에 등록하는 데코레이터."""

    def decorator(fn: RuleFn) -> RuleFn:
        RULE_REGISTRY[rule_type] = fn
        return fn

    return decorator

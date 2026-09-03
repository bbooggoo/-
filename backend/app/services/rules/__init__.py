"""
검증 규칙 플러그인 레지스트리.

===========================================================================
확장 포인트: 실제 제원 검증 로직은 여기에 새 규칙 모듈로 추가하면 됩니다.
===========================================================================

방법:
  1. 이 디렉터리에 새 파일 생성 (예: flow_over.py)
  2. base.py 의 RuleFn 시그니처를 따르는 함수 작성
  3. @register("규칙타입키") 데코레이터로 등록
  4. 이 파일(__init__.py) 하단 import 목록에 추가

그러면 ValidationRule.rule_type 값으로 해당 규칙을 DB에서 바로 사용할 수 있습니다.
(major_process_id / equipment_module / field_name_pattern 으로 적용 범위를 지정)
"""
from .base import RULE_REGISTRY, RuleContext, RuleOutcome, register  # noqa: F401

# 예시 규칙들 (실제 로직 확정 전까지의 참고 구현) -----------------------------
from . import max_value_rule  # noqa: F401,E402
from . import max_value_by_group_rule  # noqa: F401,E402
from . import standardized_enum_rule  # noqa: F401,E402
from . import alias_correction_rule  # noqa: F401,E402

__all__ = ["RULE_REGISTRY", "RuleContext", "RuleOutcome", "register"]

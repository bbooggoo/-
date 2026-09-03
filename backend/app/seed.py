"""초기 시드 데이터 (대공정/공종 목록 + 기본 검증 규칙 + 관리자 계정). `python -m app.seed` 로 직접 실행 가능."""
from .database import Base, SessionLocal, engine
from .models import (
    DISCIPLINE_SEED,
    MAJOR_PROCESS_SEED,
    Discipline,
    MajorProcess,
    Owner,
    OwnerRole,
    RuleSeverity,
    ValidationRule,
)

# 기본 검증 규칙 시드.
# "유량 OVER 기준이 성상(가스 종류)마다 다르다"는 요청에 맞춰 만든 예시 규칙이다.
# 실제 기준값이 다르면 화면(/rules)에서 그대로 수정하면 된다.
DEFAULT_VALIDATION_RULES = [
    {
        "name": "유량 OVER (성상별 기준)",
        "rule_type": "max_value_by_group",
        "major_process_id": None,
        "equipment_module": None,
        "field_name_pattern": r"_유량$",
        "params": {
            "unit": "SLPM",
            "group_field": "성상명",
            "thresholds": {
                "N2": 10,
                "O2": 6,
                "AR": 12,
                "CDA": 15,
                "HE": 8,
                "H2": 6,
            },
        },
        "severity": RuleSeverity.ERROR,
        "active": True,
    },
    {
        "name": "GAS/AIR 성상명 표준화",
        "rule_type": "standardized_enum",
        "major_process_id": None,
        "equipment_module": None,
        "field_name_pattern": r"^GAS/AIR_성상명$",
        "params": {"allowed_values": ["N2", "O2", "AR", "CDA", "HE", "H2"]},
        "severity": RuleSeverity.WARN,
        "active": True,
    },
    {
        # "자동 제원 질의" 트랙의 예시: 비표준 표기를 표준값으로 자동 치환 제안.
        # 이 규칙만 suggested_value 를 채우므로 자동 질의 일괄 생성 대상이 된다.
        "name": "GAS/AIR 성상명 자동 교정 (별칭 -> 표준값)",
        "rule_type": "alias_correction",
        "major_process_id": None,
        "equipment_module": None,
        "field_name_pattern": r"^GAS/AIR_성상명$",
        "params": {"aliases": {"GN2": "N2", "LN2": "N2", "질소": "N2", "N2 GAS": "N2"}},
        "severity": RuleSeverity.WARN,
        "active": True,
    },
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_mp = {mp.code for mp in db.query(MajorProcess).all()}
        for code, name in MAJOR_PROCESS_SEED:
            if code not in existing_mp:
                db.add(MajorProcess(code=code, name=name))

        existing_disc = {d.code for d in db.query(Discipline).all()}
        for code, name in DISCIPLINE_SEED:
            if code not in existing_disc:
                db.add(Discipline(code=code, name=name))
        db.commit()

        # 검증 규칙은 사용자가 화면에서 수정/삭제할 수 있으므로, DB가 완전히
        # 비어있을 때(=최초 실행)만 기본값을 심는다 (재시작마다 되살아나지 않게).
        if db.query(ValidationRule).count() == 0:
            for rule in DEFAULT_VALIDATION_RULES:
                db.add(ValidationRule(**rule))

        # 관리자 계정도 마찬가지로 최초 1건만 심어서 바로 로그인(사용자 선택)할 수 있게 한다.
        if db.query(Owner).filter(Owner.role == OwnerRole.ADMIN).count() == 0:
            db.add(Owner(name="관리자", role=OwnerRole.ADMIN))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed complete.")

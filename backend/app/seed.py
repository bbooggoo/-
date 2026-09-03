"""초기 시드 데이터 (대공정 목록 + 기본 검증 규칙). `python -m app.seed` 로 직접 실행 가능."""
from .database import Base, SessionLocal, engine
from .models import MAJOR_PROCESS_SEED, MajorProcess, RuleSeverity, ValidationRule

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
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = {mp.code for mp in db.query(MajorProcess).all()}
        for code, name in MAJOR_PROCESS_SEED:
            if code not in existing:
                db.add(MajorProcess(code=code, name=name))
        db.commit()

        # 검증 규칙은 사용자가 화면에서 수정/삭제할 수 있으므로, DB가 완전히
        # 비어있을 때(=최초 실행)만 기본값을 심는다 (재시작마다 되살아나지 않게).
        if db.query(ValidationRule).count() == 0:
            for rule in DEFAULT_VALIDATION_RULES:
                db.add(ValidationRule(**rule))
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed complete.")

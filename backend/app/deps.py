"""
데모용 '사용자 식별' 의존성.

로그인은 아직 없음. 프론트엔드가 사용자를 선택하면 모든 요청에 `X-User-Id` 헤더로
Owner.id 를 실어 보낸다. 이 값을 신뢰하는 방식이므로 운영 배포 전 실제 인증으로
교체 필요 (이 함수만 교체하면 나머지 라우터는 변경 불필요하도록 의존성 주입 형태로 분리).
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Owner, OwnerRole


def get_current_owner(
    x_user_id: Optional[int] = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> Owner | None:
    if x_user_id is None:
        return None
    owner = db.get(Owner, x_user_id)
    if owner is None:
        raise HTTPException(status_code=401, detail="알 수 없는 사용자입니다.")
    return owner


def require_major_process_access(owner: Owner | None, major_process_id: int) -> None:
    """담당자가 지정되어 있으면(=선택된 사용자가 있으면) 해당 대공정 권한을 검사한다.
    사용자를 선택하지 않은 경우(데모 모드)나 관리자는 통과시킨다."""
    if owner is None or owner.role == OwnerRole.ADMIN:
        return
    if major_process_id not in [mp.id for mp in owner.major_processes]:
        raise HTTPException(
            status_code=403,
            detail=f"'{owner.name}' 님은 이 대공정에 대한 담당 권한이 없습니다.",
        )


def require_discipline_access(owner: Owner | None, discipline_id: int | None) -> None:
    """설계사가 지정되어 있으면(=선택된 사용자가 있으면) 해당 공종 권한을 검사한다.
    사용자를 선택하지 않은 경우(데모 모드)나 관리자는 통과시킨다. 질의에 공종이
    지정되지 않았으면(자동 추론 실패 등) 아무나(선택된 사용자가 있다면 누구든) 처리할 수 있다."""
    if owner is None or owner.role == OwnerRole.ADMIN or discipline_id is None:
        return
    if discipline_id not in [d.id for d in owner.disciplines]:
        raise HTTPException(
            status_code=403,
            detail=f"'{owner.name}' 님은 이 공종에 대한 권한이 없습니다.",
        )


def require_admin(owner: Owner | None = Depends(get_current_owner)) -> Owner:
    """제원표 업로드처럼 관리자 전용 동작에 쓴다. 데모 모드(사용자 미선택)도 예외 없이
    막는다 - 업로드는 명시적으로 관리자로 로그인(선택)해야만 가능하다."""
    if owner is None:
        raise HTTPException(status_code=401, detail="관리자로 로그인(사용자 선택)해야 합니다.")
    if owner.role != OwnerRole.ADMIN:
        raise HTTPException(status_code=403, detail="제원표 업로드는 관리자만 할 수 있습니다.")
    return owner

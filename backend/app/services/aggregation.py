"""
제원 총량 집계.

업로드된 제원표 1건(=건설코드 1개) 안에서, 대분류(성상군)별로 정해진 집계
로직에 따라 총량을 계산한다. 로직은 다음과 같이 전달받았다:

  1. POWER          = 전원 종류별로 전력값을 SUM                        [KW]
  2. WATER          = 성상명별로 (유량 * 배관수량)을 SUM                [SLPM]
  3. WASTE WATER    = 성상명별로 (유량 * 배관수량)을 SUM                [SLPM]
  4. UPW            = 성상명별로 실사용량을 SUM                        [TON/DAY]
  5. CHEMICAL       = 자재명별로 실사용량을 SUM                        [LITER/DAY]
  6. GAS/AIR        = 성상명별로 (배관수량 * 유량)을 SUM                [SLPM]
  7. SPECIALITY GAS = 자재명별로 배관수량을 SUM                        [EA]
  8. 폐액           = 자재명별로 실사용량을 SUM                        [TON/DAY]
  9. EXHAUST        = 성상명별로 (포트 수량 * 풍량)을 SUM               [CMM]

집계 단위는 "대분류 + 행(row_index)" 하나를 데이터 한 건("아이템")으로 본다.
(엑셀 원본에서 같은 건설코드 아래 여러 행이 각각 하나의 가스/전원/배관 항목을
나타내는 구조이므로, 행 단위 = 아이템 단위가 실제 시트 구조와 맞다.)

같은 라벨의 열이 한 대분류 안에 중복으로 존재하는 경우(예: 이번에 받은 실제
헤더 샘플에서 GAS/AIR 블록에 "배관수량" 열이 두 번 나옴) 어느 쪽이 맞는지
알 수 없으므로, 같은 행·같은 라벨의 값은 모두 더한 뒤 계산에 사용한다.
(예: GAS/AIR 배관수량 두 열이 각각 2, 3이면 배관수량 합계 5로 계산)
"""
import re
from dataclasses import dataclass, field


def _num(value: str | None) -> float:
    if not value:
        return 0.0
    match = re.search(r"-?\d+(\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else 0.0


@dataclass
class CategoryAggregation:
    category: str
    unit: str
    group_by: str
    totals: dict[str, float] = field(default_factory=dict)


# 대분류(엑셀 1행 그대로의 표기, "WASTER WATER"/"폐액" 오탈자·한글도 원본 그대로) 별 집계 정의.
#   group_by: 이 라벨 값으로 묶는다 (없으면 group_by_fallback 사용)
#   value_fields: 곱해서(2개 이상) 또는 그대로 합산할(1개) 값 필드들
AGGREGATION_SPECS: dict[str, dict] = {
    "POWER": {"unit": "KW", "group_by": "전원종류", "value_fields": ["전력값"]},
    "WATER": {"unit": "SLPM", "group_by": "성상명", "value_fields": ["유량", "배관수량"]},
    "WASTER WATER": {"unit": "SLPM", "group_by": "성상명", "value_fields": ["유량", "배관수량"]},
    "UPW": {"unit": "TON/DAY", "group_by": "성상명", "value_fields": ["실사용량"]},
    "CHEMICAL": {
        "unit": "LITER/DAY",
        "group_by": "자재명",
        "group_by_fallback": "성상명",
        "value_fields": ["실사용량"],
    },
    "GAS/AIR": {"unit": "SLPM", "group_by": "성상명", "value_fields": ["배관수량", "유량"]},
    "SPECIALITY GAS": {"unit": "EA", "group_by": "자재명", "value_fields": ["배관수량"]},
    "폐액": {"unit": "TON/DAY", "group_by": "자재명", "value_fields": ["실사용량"]},
    "EXHAUST": {"unit": "CMM", "group_by": "성상명", "value_fields": ["포트 수량", "풍량"]},
}


def compute_aggregation(spec_sheet) -> list[CategoryAggregation]:
    """spec_sheet.fields (SpecField 목록)을 바탕으로 대분류별 총량을 계산한다."""

    # (대분류, 행번호) -> {세부항목라벨: [값, ...]}
    rows: dict[tuple[str, int], dict[str, list[str]]] = {}
    for f in spec_sheet.fields:
        if not f.field_name or "_" not in f.field_name:
            continue
        category, base_label = f.field_name.split("_", 1)
        rows.setdefault((category, f.row_index), {}).setdefault(base_label, []).append(f.value or "")

    results: list[CategoryAggregation] = []
    for category, spec in AGGREGATION_SPECS.items():
        totals: dict[str, float] = {}

        for (cat, _row_idx), item_fields in rows.items():
            if cat != category:
                continue

            group_values = item_fields.get(spec["group_by"])
            if not group_values and "group_by_fallback" in spec:
                group_values = item_fields.get(spec["group_by_fallback"])
            group_key = (group_values[0].strip() if group_values and group_values[0].strip() else None) or "(미지정)"

            amount = 1.0
            has_any_value = False
            for value_field in spec["value_fields"]:
                values = item_fields.get(value_field)
                if values:
                    has_any_value = True
                amount *= sum(_num(v) for v in (values or []))

            if not has_any_value:
                continue  # 이 행에는 집계에 필요한 값이 전혀 없음 (다른 대분류의 행)

            totals[group_key] = totals.get(group_key, 0.0) + amount

        if totals:
            results.append(
                CategoryAggregation(category=category, unit=spec["unit"], group_by=spec["group_by"], totals=totals)
            )

    return results

# -*- coding: utf-8 -*-
"""
전표 위험 점수 종합
=======================

지금까지 만든 7개 이상탐지 규칙을 '한꺼번에' 돌려서,
전표마다 (1) 어떤 규칙들에 걸렸는지, (2) 위험 점수가 몇 점인지 종합한다.

위험 점수 = 걸린 규칙들의 가중치 합
  - 규칙마다 심각도가 달라서 가중치를 다르게 준다. (아래 RULE_WEIGHTS)
  - 점수가 높은 전표부터 우선 검토 -> 감사의 '위험 기반 접근'

  사용법:
    python3 src/scorer.py
"""

import pandas as pd
from loader import load_journal_entries
import rules


# 규칙별 가중치(심각도). 값이 클수록 더 위험하다고 본다.
RULE_WEIGHTS = {
    "고액전표": 3,
    "직무분리위반": 3,
    "중복전표": 2,
    "비정상입력시간": 2,
    "한도직전금액": 2,
    "라운드금액": 1,
    "적요누락":1,
}

# 실행할 탐지 규칙 함수들 (rules.py 에서 가져온다)
DETECTORS = [
    rules.detect_high_value,
    rules.detect_missing_description,
    rules.detect_duplicates,
    rules.detect_sod_conflict,
    rules.detect_unusual_time,
    rules.detect_just_below_limit,
    rules.detect_round_amount,
]

def collect_flags(df):
    """
    모든 규칙을 실행해서, 걸린 (전표번호, 탐지사유)들을 한 표로 모은다.
    한 전표가 여러 규칙에 걸리면 여러 줄로 쌓인다.
    """
    records = []
    for detect in DETECTORS:
        flagged = detect(df).drop_duplicates(subset="전표번호")
        for _, row in flagged.iterrows():
            records.append({"전표번호": row["전표번호"], "탐지사유": row["탐지사유"]})
    return pd.DataFrame(records)
        
        
def score_vouchers(df):
    """
    전표별로 걸린 규칙 목록·개수·위험 점수를 계산해 표로 돌려준다.
    점수가 높은 순으로 정렬한다.
    """
    flags = collect_flags(df)
    if flags.empty:
        return pd.DataFrame(columns=["전표번호", "위험점수", "걸린규칙수", "탐지사유목록"])

    # 각 사유에 가중치를 붙인다.
    flags["가중치"] = flags["탐지사유"].map(RULE_WEIGHTS)

    # 전표번호 단위로 묶어서 집계
    grouped = flags.groupby("전표번호").agg(
        위험점수=("가중치", "sum"),
        걸린규칙수=("탐지사유", "count"),
        탐지사유목록=("탐지사유", lambda s: ", ".join(sorted(s))),
    ).reset_index()

    # 전표의 대표 정보(계정과목·금액·전기일자)를 붙여 보기 좋게
    df2 = rules.add_amount_column(df)
    info = df2.groupby("전표번호").agg(
        계정과목=("계정과목", lambda s: "/".join(sorted(set(s)))),
        금액=("금액", "max"),
        전기일자=("전기일자", "first"),
    ).reset_index()
    result = grouped.merge(info, on="전표번호", how="left")

    # 위험 점수 높은 순, 같으면 금액 큰 순으로 정렬
    result = result.sort_values(["위험점수", "금액"], ascending=[False, False])
    return result


def main():
    print("=" * 60)
    print("전표 위험 점수 종합")
    print("=" * 60)

    df = load_journal_entries()
    result = score_vouchers(df)

    total_vouchers = df["전표번호"].nunique()
    risky = len(result)
    print(f"전체 전표 {total_vouchers}장 중 위험 전표 {risky}장 탐지\n")

    print("위험 점수 높은 순 (상위 15장)")
    for _, row in result.head(15).iterrows():
        print(f"  {row['전표번호']} | 점수 {row['위험점수']} | "
              f"{row['계정과목']} {int(row['금액']):,}원 | {row['탐지사유목록']}")

    # ----- 검증: 심어 둔 이상 전표를 모두 잡았는지 -----
    answer = set(df[df["is_anomaly"] == True]["전표번호"])          # noqa: E712
    # (엑셀을 거치며 True가 글자 "True"로 바뀌었을 수도 있어 함께 처리)
    answer |= set(df[df["is_anomaly"].astype(str) == "True"]["전표번호"])
    found = set(result["전표번호"])
    print("\n[검증] 정답과 비교")
    print(f"  실제 심어 둔 이상 전표 : {len(answer)} 장")
    print(f"  규칙 세트가 찾아낸 전표 : {len(found)} 장")
    print(f"  정확히 맞힌 전표        : {len(answer & found)} 장")
    print("=" * 60)


if __name__ == "__main__":
    main()
    
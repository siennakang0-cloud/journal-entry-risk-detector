# -*- coding: utf-8 -*-
"""연습: 입력자별 전표 장수 + 계정과목별 금액 합계 집계"""

from loader import load_journal_entries


def main():
    # 1) 데이터 불러오기 (df 는 여기서 만들어진다)
    df = load_journal_entries()

    # --- 집계 1: 입력자별 전표 장수 (많은 순) ---
    counts = df.groupby("입력자")["전표번호"].nunique()
    counts = counts.sort_values(ascending=False)
    print("입력자별 전표 입력 현황 (많은 순)")
    for name, count in counts.items():
        print(f"  {name} : {count} 장")

    # --- 집계 2: 계정과목별 차변금액 합계 (많은 순) ---
    totals = df.groupby("계정과목")["차변금액"].sum()
    totals = totals.sort_values(ascending=False)
    print("\n계정과목별 차변금액 합계 (많은 순)")
    for account, total in totals.items():
        print(f"  {account} : {total:,} 원")


# 이 스위치는 맨 아래에 그대로. "직접 실행하면 main()을 불러라"
if __name__ == "__main__":
    main()

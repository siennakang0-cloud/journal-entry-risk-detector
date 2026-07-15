# -*- coding: utf-8 -*-
"""
이상탐지 규칙 모음
====================

전표 데이터에서 '위험 신호'가 있는 전표를 찾아내는 규칙들을 모아 둔다.
규칙은 하나씩 함수로 추가한다. (규칙 1개 = 함수 1개 = 커밋 1개)

  [규칙 1] 고액 전표 : 승인 한도를 초과하는 큰 금액의 전표
  (이후 STEP 마다 규칙을 하나씩 아래에 추가할 예정)

사용법:
  python src/rules.py
"""

from loader import load_journal_entries   # 앞 단계에서 만든 로더를 재사용

# 승인 한도(원). 이 금액을 넘는 전표를 '고액 전표'로 본다.
# ※ 가정: 회사의 전표 승인 한도를 5천만원으로 설정했다. (실제로는 회사마다 다름)
APPROVAL_LIMIT = 50_000_000


def add_amount_column(df):
    """
    전표 한 줄에는 금액이 '차변금액' 또는 '대변금액' 중 한쪽에만 들어 있다.
    (다른 쪽은 0) 그래서 두 컬럼 중 큰 값을 그 줄의 '거래 금액'으로 삼는다.
    분석하기 쉽게 '금액'이라는 새 컬럼을 만들어 붙인다.
    """
    df = df.copy()   # 원본을 건드리지 않도록 복사본에서 작업
    df["금액"] = df[["차변금액", "대변금액"]].max(axis=1)
    return df


def detect_high_value(df, threshold=APPROVAL_LIMIT):
    """
    [규칙 1] 고액 전표 탐지.
    거래 금액이 승인 한도(threshold)를 초과하는 전표를 골라낸다.

    반환값: 걸린 전표들만 모은 DataFrame(표)
    """
    df = add_amount_column(df)
    flagged = df[df["금액"] > threshold].copy()
    # 어떤 규칙에 걸렸는지 표시를 남겨 둔다 (나중에 규칙이 많아지면 유용)
    flagged["탐지사유"] = "고액전표"
    return flagged


def main():
    print("=" * 55)
    print("이상탐지 규칙 실행")
    print("=" * 55)

    df = load_journal_entries()

    # ----- 규칙 1: 고액 전표 -----
    high = detect_high_value(df)
    # 전표 단위로 보기 좋게, 중복 없이 전표번호 기준으로 정리
    high_vouchers = high.drop_duplicates(subset="전표번호")
    print(f"\n[규칙 1] 고액 전표 (승인 한도 {APPROVAL_LIMIT:,}원 초과)")
    print(f"  탐지된 전표: {len(high_vouchers)} 장")
    for _, row in high_vouchers.iterrows():
        print(f"   - {row['전표번호']} | {row['계정과목']} | "
              f"{int(row['금액']):,}원 | {row['전기일자']}")

    # ----- 검증: '정답'과 비교 -----
    # 데이터에는 학습용 정답(anomaly_type)이 들어 있다.
    # 실제로 심어 둔 '고액전표'를 우리 규칙이 잘 잡았는지 채점해 본다.
    answer = set(df[df["anomaly_type"] == "고액전표"]["전표번호"])
    found = set(high_vouchers["전표번호"])
    print("\n[검증] 정답과 비교")
    print(f"  실제 심어 둔 고액전표 : {len(answer)} 장")
    print(f"  규칙이 찾아낸 전표    : {len(found)} 장")
    print(f"  정확히 맞힌 전표      : {len(answer & found)} 장")
    print("=" * 55)


if __name__ == "__main__":
    main()
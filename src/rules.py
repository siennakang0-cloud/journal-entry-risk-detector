# -*- coding: utf-8 -*-
"""
이상탐지 규칙 모음
====================

전표 데이터에서 '위험 신호'가 있는 전표를 찾아내는 규칙들을 모아 둔다.
규칙은 하나씩 함수로 추가한다. (규칙 1개 = 함수 1개 = 커밋 1개)

  [규칙 1] 고액 전표   : 승인 한도를 초과하는 큰 금액의 전표
  [규칙 2] 적요 누락   : 거래 설명(적요)이 비어 있는 전표
  [규칙 3] 중복 전표   : 같은 거래가 전표번호만 다르게 두 번 기표된 전표
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


def detect_missing_description(df):
    """
    [규칙 2] 적요 누락 탐지.
    적요(거래 설명)가 비어 있는 전표를 골라낸다.

    - CSV에서 빈 칸은 pandas 가 NaN(값 없음)으로 읽는다 -> isna() 로 잡는다.
    - 혹시 공백(스페이스)만 들어 있는 경우도 함께 잡는다.
    """
    df = df.copy()
    is_empty = df["적요"].isna() | (df["적요"].astype(str).str.strip() == "")
    flagged = df[is_empty].copy()
    flagged["탐지사유"] = "적요누락"
    return flagged

def detect_duplicates(df):
    """
    [규칙 3] 중복 전표 탐지.
    전표번호만 다를 뿐 나머지 핵심 정보가 똑같은 전표를 찾는다.

    방법(지문 만들기):
      전표 한 장의 '전기일자·입력일시·계정과목·금액·적요·입력자·승인자'를
      하나의 문자열('지문')로 합친다. 지문이 같으면 사실상 같은 거래다.
      같은 지문이 두 번 이상 나타나면, 먼저 입력된 전표(번호가 작은 원본)는
      두고 그 뒤에 또 들어온 전표를 '중복'으로 표시한다.

       ※ 실무에서는 중복쌍의 '양쪽'을 모두 검토하지만, 탐지 결과로는
      뒤늦게 또 들어온(반복된) 전표를 위험 신호로 표시한다.
    """
    df = add_amount_column(df)

    # 전표(전표번호) 단위로 대표 정보를 뽑는다.
    per = df.groupby("전표번호").agg(
        전기일자=("전기일자", "first"),
        입력일시=("입력일시", "first"),
        금액=("금액", "max"),
        적요=("적요", "first"),
        입력자=("입력자", "first"),
        승인자=("승인자", "first"),
        계정=("계정과목", lambda s: "&".join(sorted(s.astype(str)))),
    ).reset_index()

    # 위 정보들을 이어붙여 전표별 '지문'을 만든다.
    # (적요가 비어 있을 수 있으니 fillna("")로 안전하게 처리)
    per["지문"] = (
        per["전기일자"].astype(str) + "|" +
        per["입력일시"].astype(str) + "|" +
        per["금액"].astype(str) + "|" +
        per["적요"].fillna("").astype(str) + "|" +
        per["입력자"].astype(str) + "|" +
        per["승인자"].astype(str) + "|" +
        per["계정"].astype(str)
    )

    # 전표번호 순으로 정렬해 원본(작은 번호)이 먼저 오게 한 뒤,
    # 같은 지문의 두 번째부터를 '중복'으로 표시한다.
    per = per.sort_values("전표번호")
    per["중복여부"] = per["지문"].duplicated(keep="first")
    dup_ids = per[per["중복여부"]]["전표번호"].tolist()

    flagged = df[df["전표번호"].isin(dup_ids)].copy()
    flagged["탐지사유"] = "중복전표"
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

    # ----- 규칙 2: 적요 누락 -----
    empty = detect_missing_description(df)
    empty_vouchers = empty.drop_duplicates(subset="전표번호")
    print(f"\n[규칙 2] 적요 누락 전표")
    print(f"  탐지된 전표: {len(empty_vouchers)} 장")
    for _, row in empty_vouchers.iterrows():
        print(f"   - {row['전표번호']} | {row['계정과목']} | {row['전기일자']}")

    # 검증: 실제 심어 둔 '적요누락'을 잘 잡았는지 채점
    answer2 = set(df[df["anomaly_type"] == "적요누락"]["전표번호"])
    found2 = set(empty_vouchers["전표번호"])
    print("\n[검증] 정답과 비교")
    print(f"  실제 심어 둔 적요누락 : {len(answer2)} 장")
    print(f"  규칙이 찾아낸 전표    : {len(found2)} 장")
    print(f"  정확히 맞힌 전표      : {len(answer2 & found2)} 장")
    print("=" * 55)

    # ----- 규칙 3: 중복 전표 -----
    dup = detect_duplicates(df)
    dup_vouchers = dup.drop_duplicates(subset="전표번호")
    print(f"\n[규칙 3] 중복 전표")
    print(f"  탐지된 전표: {len(dup_vouchers)} 장")
    for _, row in dup_vouchers.iterrows():
        print(f"   - {row['전표번호']} | {row['계정과목']} | "
              f"{int(row['금액']):,}원 | {row['입력일시']}")

    # 검증: 실제 심어 둔 '중복전표'를 잘 잡았는지 채점
    answer3 = set(df[df["anomaly_type"] == "중복전표"]["전표번호"])
    found3 = set(dup_vouchers["전표번호"])
    print("\n[검증] 정답과 비교")
    print(f"  실제 심어 둔 중복전표 : {len(answer3)} 장")
    print(f"  규칙이 찾아낸 전표    : {len(found3)} 장")
    print(f"  정확히 맞힌 전표      : {len(answer3 & found3)} 장")
    print("=" * 55)


if __name__ == "__main__":
    main()
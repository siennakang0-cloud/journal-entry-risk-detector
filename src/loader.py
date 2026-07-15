# -*- coding: utf-8 -*-
"""
전표 데이터 로더 & 기초 무결성 점검
======================================

감사에서 데이터를 넘겨받으면, 분석에 들어가기 '전에' 항상 데이터가
믿을 만한지부터 확인한다. 이 파일은 그 첫 점검을 담당한다.

하는 일:
  1) CSV 전표 데이터를 pandas 로 불러온다.
  2) 필요한 컬럼이 다 있는지 확인한다.
  3) 결측치(빈 값)가 어디에 몇 개 있는지 센다.
  4) 차변 합계 = 대변 합계 인지(복식부기 균형) 확인한다.
  5) 전표 한 장(voucher) 단위로도 차대변이 맞는지 확인한다.

사용법:
  python src/loader.py
"""

import pandas as pd

# 전표 데이터에 반드시 있어야 하는 컬럼 목록
REQUIRED_COLUMNS = [
    "전표번호", "전기일자", "입력일시", "계정코드", "계정과목",
    "차변금액", "대변금액", "적요", "입력자", "승인자",
]

DATA_PATH = "data/sample_journal_entries.csv"


def load_journal_entries(path=DATA_PATH):
    """
    CSV 전표 데이터를 읽어서 pandas DataFrame(표) 형태로 돌려준다.

    encoding='utf-8-sig' :
      한글이 깨지지 않게, 그리고 파일 맨 앞의 보이지 않는 문자(BOM)를
      자동으로 걸러 주는 인코딩이다.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df


def check_columns(df):
    """필요한 컬럼이 모두 있는지 확인하고, 빠진 컬럼이 있으면 알려준다."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        print(f"[경고] 빠진 컬럼이 있습니다: {missing}")
    else:
        print("[OK] 필요한 컬럼이 모두 있습니다.")
    return missing


def check_missing_values(df):
    """
    컬럼별 결측치(빈 값) 개수를 센다.
    ※ '적요'는 이상탐지용으로 일부러 비워 둔 경우가 있으니,
       결측치가 있다고 무조건 오류는 아니다. 어디에 있는지 '파악'이 목적이다.
    """
    na_counts = df.isna().sum()
    has_na = na_counts[na_counts > 0]
    if has_na.empty:
        print("[OK] 결측치가 없습니다.")
    else:
        print("[정보] 결측치가 있는 컬럼:")
        for col, cnt in has_na.items():
            print(f"   - {col}: {cnt}개")
    return has_na


def check_balance(df):
    """
    전체 차변 합계와 대변 합계가 같은지(복식부기 균형) 확인한다.
    감사에서 이 둘이 안 맞으면 데이터 자체에 문제가 있다는 신호다.
    """
    total_debit = df["차변금액"].sum()
    total_credit = df["대변금액"].sum()
    balanced = total_debit == total_credit
    print(f"차변 합계: {total_debit:,} 원")
    print(f"대변 합계: {total_credit:,} 원")
    print(f"[{'OK' if balanced else '불일치'}] 전체 차대변 균형")
    return balanced


def check_voucher_balance(df):
    """
    전표 '한 장(전표번호)' 단위로도 차변=대변인지 확인한다.
    전체 합계는 맞아도 개별 전표가 틀어져 있을 수 있어 따로 본다.
    """
    # 전표번호별로 차변합, 대변합을 각각 더한다.
    grouped = df.groupby("전표번호")[["차변금액", "대변금액"]].sum()
    # 차변합과 대변합이 다른 전표만 골라낸다.
    unbalanced = grouped[grouped["차변금액"] != grouped["대변금액"]]
    if unbalanced.empty:
        print("[OK] 모든 전표가 개별적으로 차대변이 맞습니다.")
    else:
        print(f"[경고] 차대변이 안 맞는 전표 {len(unbalanced)}건:")
        print(unbalanced)
    return unbalanced


def main():
    print("=" * 50)
    print("전표 데이터 로딩 & 기초 점검")
    print("=" * 50)

    df = load_journal_entries()

    # 기본 규모 파악
    voucher_count = df["전표번호"].nunique()   # 서로 다른 전표번호의 수 = 전표 장수
    print(f"불러온 라인 수 : {len(df)} 줄")
    print(f"전표 장수      : {voucher_count} 장")
    print("-" * 50)

    check_columns(df)
    print("-" * 50)
    check_missing_values(df)
    print("-" * 50)
    check_balance(df)
    print("-" * 50)
    check_voucher_balance(df)
    print("=" * 50)


# 이 파일을 직접 실행할 때만 main()이 돌아간다.
# (나중에 다른 파일에서 load_journal_entries() 함수만 가져다 쓸 수 있게 하려는 것)
if __name__ == "__main__":
    main()
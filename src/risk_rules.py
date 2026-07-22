"""
risk_rules.py
전표(Journal Entry) 위험지표 탐지 규칙 모듈.

감사 실무의 '전표 테스트(journal entry testing)'에서 실제로 점검하는
5가지 red flag를 규칙(rule) 기반으로 구현한다. 각 규칙은 데이터프레임을
받아 해당 전표가 위험에 해당하는지(True/False)를 나타내는 bool Series를 돌려준다.

규칙은 '정답 라벨(injected_risk)'을 절대 참조하지 않고, 오직 실제 전표
속성만 보고 판단한다. 라벨은 마지막 검증 단계에서만 비교용으로 쓰인다.
"""

import numpy as np
import pandas as pd

# ---- 임계값(threshold) 설정 ----
# 고액 판단 기준: 금액 분포의 상위 이상치. 통계적으로 Q3 + 3*IQR을 넘으면
# 정상 분포를 크게 벗어난 것으로 본다(감사에서 쓰는 이상치 탐지 방식).
IQR_MULTIPLIER = 3.0

# 중복 판단 시 '같은 전표'로 볼 기준 컬럼
DUP_KEYS = ["account_code", "amount", "description"]

# 업무시간 기준(이 시간을 벗어나면 야간으로 간주)
BUSINESS_START_HOUR = 7   # 07시
BUSINESS_END_HOUR = 20    # 20시(이후는 야간)


def flag_high_amount(df):
    """(A) 고액 거래: 금액이 통계적 이상치 상한을 초과하는 전표."""
    amt = df["amount"].astype(float)
    q1, q3 = amt.quantile(0.25), amt.quantile(0.75)
    iqr = q3 - q1
    upper = q3 + IQR_MULTIPLIER * iqr
    return amt > upper


def flag_missing_description(df):
    """(B) 설명 누락: 적요(description)가 비었거나 공백뿐인 전표."""
    desc = df["description"]
    # NaN/None 이거나, 문자열로 바꿔 공백 제거 시 빈 문자열인 경우
    is_null = desc.isna()
    is_blank = desc.fillna("").astype(str).str.strip() == ""
    return is_null | is_blank


def flag_duplicate(df):
    """(C) 중복 거래: 계정·금액·적요가 동일한 전표가 2건 이상 존재.

    첫 건과 중복 건 모두를 위험으로 표시(감사자는 원본·중복을 함께 검토하므로).
    """
    key = df.copy()
    key["_desc_norm"] = key["description"].fillna("").astype(str).str.strip()
    dup_mask = key.duplicated(subset=["account_code", "amount", "_desc_norm"], keep=False)
    # 설명이 비어있는 건은 중복 판단에서 제외(설명누락 규칙이 별도로 잡음)
    dup_mask = dup_mask & (key["_desc_norm"] != "")
    return dup_mask


def flag_off_hours(df):
    """(D) 주말/야간 기록: 토·일요일 또는 업무시간 외(야간) 기표."""
    dt = pd.to_datetime(df["posting_datetime"])
    is_weekend = dt.dt.weekday >= 5  # 5=토, 6=일
    hour = dt.dt.hour
    is_night = (hour < BUSINESS_START_HOUR) | (hour >= BUSINESS_END_HOUR)
    return is_weekend | is_night


def flag_segregation_conflict(df):
    """(E) 직무분리 위반: 작성자와 승인자가 동일 인물인 전표."""
    preparer = df["preparer"].fillna("").astype(str).str.strip()
    approver = df["approver"].fillna("").astype(str).str.strip()
    return (preparer == approver) & (preparer != "")


# 규칙 레지스트리: (컬럼명, 함수, 한글 설명)
RULES = [
    ("high_amount", flag_high_amount, "고액 거래(통계적 이상치)"),
    ("missing_description", flag_missing_description, "적요(설명) 누락"),
    ("duplicate", flag_duplicate, "중복 전표"),
    ("off_hours", flag_off_hours, "주말/야간 기표"),
    ("segregation_conflict", flag_segregation_conflict, "직무분리 위반(작성=승인)"),
]


def apply_rules(df):
    """모든 규칙을 적용해 위험 플래그 컬럼과 위험점수(risk_score)를 붙인다.

    Returns
    -------
    pandas.DataFrame
        원본 + 규칙별 bool 컬럼(예: flag_high_amount) +
        risk_score(걸린 규칙 수) + risk_reasons(걸린 규칙 설명, ; 구분).
    """
    out = df.copy()
    reason_map = {col: label for col, _, label in RULES}

    flag_cols = []
    for col, fn, _label in RULES:
        flag_col = f"flag_{col}"
        out[flag_col] = fn(df).astype(bool)
        flag_cols.append(flag_col)

    # 위험점수: 동시에 몇 개의 규칙에 걸렸는가
    out["risk_score"] = out[flag_cols].sum(axis=1).astype(int)

    # 걸린 사유를 사람이 읽을 수 있는 문자열로
    def reasons(row):
        hit = [reason_map[col] for col, _, _ in RULES if row[f"flag_{col}"]]
        return "; ".join(hit)

    out["risk_reasons"] = out.apply(reasons, axis=1)
    return out


if __name__ == "__main__":
    import os
    from generate_data import generate

    df = generate()
    scored = apply_rules(df)
    flagged = scored[scored["risk_score"] > 0]
    print(f"[risk_rules] 전체 {len(scored)}건 중 위험 {len(flagged)}건 탐지")
    for col, _, label in RULES:
        print(f"  - {label}: {scored[f'flag_{col}'].sum()}건")

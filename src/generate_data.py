"""
generate_data.py
합성(synthetic) 전표 데이터셋 생성 모듈.

실제 회사의 전표 데이터는 외부에 공개할 수 없으므로, 감사 실무에서 실제로
점검하는 전표 속성(계정, 금액, 적요, 작성자/승인자, 기표일시)을 본뜬
가상의 데이터를 만든다. 정상 전표 사이에 5가지 위험 유형을 의도적으로
심어 두고(ground truth), 탐지 규칙이 이를 얼마나 잡아내는지 검증할 수 있게 한다.

랜덤 시드를 고정해 누구가 실행하든 같은 데이터가 재현되도록 했다.
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# 재현성을 위한 시드 고정
RANDOM_SEED = 42

# 가상의 계정과목 (대·차변에 두루 쓰이는 계정)
ACCOUNTS = [
    ("101", "현금및현금성자산"),
    ("108", "외상매출금"),
    ("110", "받을어음"),
    ("146", "재고자산"),
    ("201", "외상매입금"),
    ("251", "미지급금"),
    ("401", "매출"),
    ("451", "매출원가"),
    ("811", "급여"),
    ("813", "복리후생비"),
    ("820", "지급수수료"),
    ("830", "감가상각비"),
]

# 가상의 담당자(작성자/승인자) 풀 — 직무분리가 지켜지는 정상 상황을 전제로 함
PREPARERS = ["김민준", "이서연", "박도윤", "정하은", "최지우"]
APPROVERS = ["한상무", "오이사", "윤부장"]

# 정상 적요(전표 설명) 예시
NORMAL_MEMOS = [
    "3월 정기 급여 지급",
    "사무용품 구매",
    "거래처 외상대금 회수",
    "원재료 매입 대금 지급",
    "법인카드 대금 결제",
    "임차료 지급",
    "제품 매출 인식",
    "운반비 지급",
    "복리후생비 정산",
    "지급수수료 처리",
]


def _random_business_datetime(rng, start, end):
    """start~end 사이의 '영업일 업무시간(평일 09~18시)' 랜덤 일시를 반환."""
    while True:
        delta_days = (end - start).days
        d = start + timedelta(days=rng.randint(0, delta_days))
        if d.weekday() < 5:  # 0=월 ... 4=금 (평일)
            hour = rng.randint(9, 17)
            minute = rng.randint(0, 59)
            return d.replace(hour=hour, minute=minute, second=0)


def generate(n_normal=950, seed=RANDOM_SEED):
    """
    합성 전표 데이터프레임을 생성한다.

    Parameters
    ----------
    n_normal : int
        정상 전표 건수. 여기에 각 위험 유형별 이상 전표가 추가로 더해진다.
    seed : int
        랜덤 시드.

    Returns
    -------
    pandas.DataFrame
        전표 데이터. 컬럼은 아래 build_output 참고.
        `injected_risk` 컬럼은 검증용 정답(ground truth)이며,
        탐지 단계에서는 사용하지 않는다.
    """
    rng = random.Random(seed)
    np.random.seed(seed)

    period_start = datetime(2025, 1, 1)
    period_end = datetime(2025, 12, 31)

    rows = []
    entry_no = 1

    def new_id():
        nonlocal entry_no
        eid = f"JE{entry_no:05d}"
        entry_no += 1
        return eid

    # ---------- 1) 정상 전표 ----------
    for _ in range(n_normal):
        code, name = rng.choice(ACCOUNTS)
        preparer = rng.choice(PREPARERS)
        # 직무분리 정상: 승인자는 작성자와 다른 사람(승인자 풀에서 선택)
        approver = rng.choice(APPROVERS)
        amount = int(np.random.lognormal(mean=13.0, sigma=1.0))  # 대체로 수십만~수백만원
        rows.append({
            "entry_id": new_id(),
            "posting_datetime": _random_business_datetime(rng, period_start, period_end),
            "account_code": code,
            "account_name": name,
            "description": rng.choice(NORMAL_MEMOS),
            "amount": amount,
            "preparer": preparer,
            "approver": approver,
            "injected_risk": "",
        })

    # ---------- 2) 위험 유형별 이상 전표 삽입 ----------

    # (A) 고액 거래: 정상 분포를 크게 벗어나는 비정상적 거액
    for _ in range(12):
        code, name = rng.choice(ACCOUNTS)
        rows.append({
            "entry_id": new_id(),
            "posting_datetime": _random_business_datetime(rng, period_start, period_end),
            "account_code": code,
            "account_name": name,
            "description": rng.choice(NORMAL_MEMOS),
            "amount": int(rng.uniform(80_000_000, 300_000_000)),  # 8천만~3억
            "preparer": rng.choice(PREPARERS),
            "approver": rng.choice(APPROVERS),
            "injected_risk": "high_amount",
        })

    # (B) 설명 누락: 적요(description)가 비어 있음
    for _ in range(10):
        code, name = rng.choice(ACCOUNTS)
        rows.append({
            "entry_id": new_id(),
            "posting_datetime": _random_business_datetime(rng, period_start, period_end),
            "account_code": code,
            "account_name": name,
            "description": rng.choice(["", "   ", None]),  # 공백/None
            "amount": int(np.random.lognormal(mean=13.0, sigma=1.0)),
            "preparer": rng.choice(PREPARERS),
            "approver": rng.choice(APPROVERS),
            "injected_risk": "missing_description",
        })

    # (C) 중복 거래: 같은 계정·금액·적요가 짧은 간격으로 반복 기표됨
    for _ in range(8):
        code, name = rng.choice(ACCOUNTS)
        amount = int(np.random.lognormal(mean=13.0, sigma=1.0))
        memo = rng.choice(NORMAL_MEMOS)
        base_dt = _random_business_datetime(rng, period_start, period_end)
        preparer = rng.choice(PREPARERS)
        approver = rng.choice(APPROVERS)
        # 동일 전표를 2건 생성(원본 + 중복)
        for k in range(2):
            rows.append({
                "entry_id": new_id(),
                "posting_datetime": base_dt + timedelta(minutes=k * 3),
                "account_code": code,
                "account_name": name,
                "description": memo,
                "amount": amount,
                "preparer": preparer,
                "approver": approver,
                "injected_risk": "duplicate",
            })

    # (D) 주말/야간 기록: 토·일 또는 심야(22시~06시)에 기표
    for _ in range(10):
        code, name = rng.choice(ACCOUNTS)
        # 주말 날짜 강제
        d = period_start + timedelta(days=rng.randint(0, 364))
        while d.weekday() < 5:
            d += timedelta(days=1)
        if rng.random() < 0.5:
            hour = rng.randint(9, 17)      # 주말이지만 낮 시간
        else:
            hour = rng.choice([23, 0, 2, 4])  # 심야
        dt = d.replace(hour=hour, minute=rng.randint(0, 59), second=0)
        rows.append({
            "entry_id": new_id(),
            "posting_datetime": dt,
            "account_code": code,
            "account_name": name,
            "description": rng.choice(NORMAL_MEMOS),
            "amount": int(np.random.lognormal(mean=13.0, sigma=1.0)),
            "preparer": rng.choice(PREPARERS),
            "approver": rng.choice(APPROVERS),
            "injected_risk": "off_hours",
        })

    # (E) 직무분리 위반: 작성자와 승인자가 동일 인물
    for _ in range(9):
        code, name = rng.choice(ACCOUNTS)
        person = rng.choice(PREPARERS)
        rows.append({
            "entry_id": new_id(),
            "posting_datetime": _random_business_datetime(rng, period_start, period_end),
            "account_code": code,
            "account_name": name,
            "description": rng.choice(NORMAL_MEMOS),
            "amount": int(np.random.lognormal(mean=13.0, sigma=1.0)),
            "preparer": person,
            "approver": person,  # 동일인 → 직무분리 위반
            "injected_risk": "segregation_conflict",
        })

    df = pd.DataFrame(rows)
    # 기표일시 순으로 정렬 후 전표번호 재부여(현실감)
    df = df.sort_values("posting_datetime").reset_index(drop=True)
    df["entry_id"] = [f"JE{ i + 1:05d}" for i in range(len(df))]
    return df


if __name__ == "__main__":
    import os

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "journal_entries.csv")
    df = generate()
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[generate_data] {len(df)}건 생성 → {out_path}")
    print(df["injected_risk"].value_counts(dropna=False))

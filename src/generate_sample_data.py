# -*- coding: utf-8 -*-
"""
가상 전표(분개) 데이터 생성기
=================================

이 스크립트는 감사 실습용 '가상 전표'를 만든다.
- 대부분은 '정상 전표'이고,
- 일부는 우리가 탐지하려는 '이상 징후'를 일부러 심어 둔 전표다.

왜 이렇게 만드나?
  탐지기(detector)가 나중에 이상 전표를 제대로 찾아내는지 '정답'과
  비교해서 검증할 수 있기 때문이다. 그래서 각 전표에는 학습·검증용으로
  is_anomaly / anomaly_type 컬럼을 붙여 둔다.
  (실제 탐지 로직은 이 두 컬럼을 '보지 않고' 스스로 찾아내야 한다.)

복식부기 원칙:
  전표 한 장(voucher)은 차변 라인과 대변 라인으로 이루어지고,
  차변 합계 = 대변 합계 가 되도록 만든다.

사용법:
  python src/generate_sample_data.py
  -> data/sample_journal_entries.csv 파일이 생성된다.
"""

import csv
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 0. 재현성(reproducibility)을 위한 랜덤 시드 고정
#    시드를 고정하면 몇 번을 돌려도 '똑같은 데이터'가 나온다.
#    -> 커밋할 때마다 데이터가 흔들리지 않아 검증이 편하다.
# ---------------------------------------------------------------------------
random.seed(42)

# ---------------------------------------------------------------------------
# 1. 기본 설정값
# ---------------------------------------------------------------------------
NORMAL_VOUCHER_COUNT = 200          # 정상 전표 장수
YEAR = 2025                          # 회계연도
APPROVAL_LIMIT = 50_000_000         # 전표 승인 한도(원). '한도 직전 금액' 이상탐지에 사용
OUTPUT_PATH = "data/sample_journal_entries.csv"

# 전표를 입력/승인하는 담당자 목록
USERS = ["김회계", "이감사", "박세무", "최결산", "정전표"]

# 거래 유형 템플릿: (차변 계정, 대변 계정, 적요 예시)
# 실제 회계에서 자주 나오는 분개 조합을 단순화한 것이다.
TRANSACTION_TEMPLATES = [
    ("108", "외상매출금", "401", "제품매출",   "제품 판매"),
    ("101", "현금",       "108", "외상매출금", "매출채권 회수"),
    ("146", "상품",       "251", "외상매입금", "상품 매입"),
    ("251", "외상매입금", "101", "현금",       "매입대금 지급"),
    ("801", "급여",       "101", "현금",       "직원 급여 지급"),
    ("813", "접대비",     "101", "현금",       "거래처 접대"),
    ("812", "여비교통비", "101", "현금",       "출장 여비 정산"),
    ("830", "지급수수료", "103", "보통예금",   "수수료 이체"),
    ("811", "복리후생비", "103", "보통예금",   "직원 복리후생"),
    ("820", "감가상각비", "203", "감가상각누계액", "월 감가상각 계상"),
]


# ---------------------------------------------------------------------------
# 2. 보조 함수들
# ---------------------------------------------------------------------------
def random_business_datetime():
    """정상적인 '평일 업무시간' 입력일시를 만든다 (월~금, 09~18시)."""
    # 회계연도 안의 임의 날짜를 고른다.
    start = datetime(YEAR, 1, 1)
    day = start + timedelta(days=random.randint(0, 364))
    # 주말(토=5, 일=6)이면 다음 평일로 밀어 준다.
    while day.weekday() >= 5:
        day += timedelta(days=1)
    hour = random.randint(9, 17)        # 업무시간
    minute = random.randint(0, 59)
    return day.replace(hour=hour, minute=minute)


def random_amount():
    """정상 전표의 '자연스러운' 금액을 만든다 (끝자리가 딱 떨어지지 않게)."""
    # 10만 ~ 3천만원 사이, 100원 단위로 어중간하게
    return random.randint(1_000, 300_000) * 100


def make_voucher(entry_id, tmpl, amount, dt, created_by, approved_by,
                 description, is_anomaly=False, anomaly_type=""):
    """
    전표 한 장을 '차변 라인 + 대변 라인' 두 줄로 만들어 리스트로 돌려준다.
    (복식부기: 차변 금액 = 대변 금액)
    """
    debit_code, debit_name, credit_code, credit_name, _ = tmpl
    common = {
        "전표번호": f"JE{entry_id:05d}",
        "전기일자": dt.strftime("%Y-%m-%d"),
        "입력일시": dt.strftime("%Y-%m-%d %H:%M"),
        "적요": description,
        "입력자": created_by,
        "승인자": approved_by,
        "is_anomaly": is_anomaly,
        "anomaly_type": anomaly_type,
    }
    debit_line = {**common, "계정코드": debit_code, "계정과목": debit_name,
                  "차변금액": amount, "대변금액": 0}
    credit_line = {**common, "계정코드": credit_code, "계정과목": credit_name,
                   "차변금액": 0, "대변금액": amount}
    return [debit_line, credit_line]


# ---------------------------------------------------------------------------
# 3. 정상 전표 생성
# ---------------------------------------------------------------------------
rows = []          # 최종 CSV 각 줄(라인)을 담을 리스트
vouchers = []      # 나중에 '중복 전표'를 만들 때 원본을 참고하기 위해 보관
entry_id = 1

for _ in range(NORMAL_VOUCHER_COUNT):
    tmpl = random.choice(TRANSACTION_TEMPLATES)
    amount = random_amount()
    dt = random_business_datetime()
    # 정상 전표는 입력자와 승인자가 '서로 다른' 사람이어야 한다(직무분리).
    created_by = random.choice(USERS)
    approved_by = random.choice([u for u in USERS if u != created_by])
    description = tmpl[4]

    voucher = make_voucher(entry_id, tmpl, amount, dt,
                           created_by, approved_by, description)
    rows.extend(voucher)
    vouchers.append((entry_id, tmpl, amount, dt, created_by, approved_by, description))
    entry_id += 1


# ---------------------------------------------------------------------------
# 4. 이상 전표(=탐지 대상)를 일부러 심는다
#    각 유형별로 몇 장씩 넣고, anomaly_type 에 정답 라벨을 기록한다.
# ---------------------------------------------------------------------------

def add_anomaly(n, builder):
    """이상 전표 n장을 만들어 rows 에 추가하는 헬퍼."""
    global entry_id
    for _ in range(n):
        rows.extend(builder(entry_id))
        entry_id += 1


# (1) 고액 전표: 승인 한도를 크게 초과하는 비정상적으로 큰 금액
def high_value(eid):
    tmpl = random.choice(TRANSACTION_TEMPLATES)
    amount = random.randint(3, 9) * 100_000_000      # 3억 ~ 9억
    dt = random_business_datetime()
    c = random.choice(USERS)
    a = random.choice([u for u in USERS if u != c])
    return make_voucher(eid, tmpl, amount, dt, c, a, tmpl[4],
                        True, "고액전표")


# (2) 적요 누락: 설명(적요)이 비어 있는 전표
def missing_desc(eid):
    tmpl = random.choice(TRANSACTION_TEMPLATES)
    amount = random_amount()
    dt = random_business_datetime()
    c = random.choice(USERS)
    a = random.choice([u for u in USERS if u != c])
    return make_voucher(eid, tmpl, amount, dt, c, a, "",  # 적요 공란
                        True, "적요누락")


# (3) 비정상 입력시간: 주말 또는 심야(22~05시)에 입력된 전표
def unusual_time(eid):
    tmpl = random.choice(TRANSACTION_TEMPLATES)
    amount = random_amount()
    # 토요일 심야로 강제 지정
    start = datetime(YEAR, 1, 1)
    day = start + timedelta(days=random.randint(0, 364))
    while day.weekday() != 5:           # 5 = 토요일이 될 때까지
        day += timedelta(days=1)
    dt = day.replace(hour=random.choice([2, 3, 23]), minute=random.randint(0, 59))
    c = random.choice(USERS)
    a = random.choice([u for u in USERS if u != c])
    return make_voucher(eid, tmpl, amount, dt, c, a, tmpl[4],
                        True, "비정상입력시간")


# (4) 직무분리 위반: 입력자와 승인자가 '같은' 사람
def sod_conflict(eid):
    tmpl = random.choice(TRANSACTION_TEMPLATES)
    amount = random_amount()
    dt = random_business_datetime()
    person = random.choice(USERS)
    return make_voucher(eid, tmpl, amount, dt, person, person, tmpl[4],
                        True, "직무분리위반")


# (5) 승인 한도 직전 금액: 한도(5천만원) 바로 아래로 쪼갠 듯한 금액
def just_below_limit(eid):
    tmpl = random.choice(TRANSACTION_TEMPLATES)
    amount = APPROVAL_LIMIT - random.choice([100_000, 200_000, 500_000])
    dt = random_business_datetime()
    c = random.choice(USERS)
    a = random.choice([u for u in USERS if u != c])
    return make_voucher(eid, tmpl, amount, dt, c, a, tmpl[4],
                        True, "한도직전금액")


# (6) 라운드 금액: 끝자리가 000...으로 딱 떨어지는 인위적 금액
def round_amount(eid):
    tmpl = random.choice(TRANSACTION_TEMPLATES)
    amount = random.choice([10_000_000, 20_000_000, 30_000_000])
    dt = random_business_datetime()
    c = random.choice(USERS)
    a = random.choice([u for u in USERS if u != c])
    return make_voucher(eid, tmpl, amount, dt, c, a, tmpl[4],
                        True, "라운드금액")


add_anomaly(5, high_value)
add_anomaly(5, missing_desc)
add_anomaly(5, unusual_time)
add_anomaly(5, sod_conflict)
add_anomaly(4, just_below_limit)
add_anomaly(4, round_amount)


# (7) 중복 전표: 앞서 만든 정상 전표를 통째로 복사(전표번호만 새로 부여)
#     -> 같은 거래가 두 번 기표된 상황을 흉내
for _ in range(4):
    orig = random.choice(vouchers)
    _, tmpl, amount, dt, c, a, desc = orig
    rows.extend(make_voucher(entry_id, tmpl, amount, dt, c, a, desc,
                             True, "중복전표"))
    entry_id += 1


# ---------------------------------------------------------------------------
# 5. CSV 파일로 저장
# ---------------------------------------------------------------------------
FIELDNAMES = ["전표번호", "전기일자", "입력일시", "계정코드", "계정과목",
              "차변금액", "대변금액", "적요", "입력자", "승인자",
              "is_anomaly", "anomaly_type"]

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)

# ---------------------------------------------------------------------------
# 6. 요약 출력 (실행하면 터미널에 통계가 찍힌다)
# ---------------------------------------------------------------------------
total_vouchers = entry_id - 1
total_lines = len(rows)
anomaly_lines = [r for r in rows if r["is_anomaly"]]
total_debit = sum(r["차변금액"] for r in rows)
total_credit = sum(r["대변금액"] for r in rows)

print("=" * 50)
print(f"생성 완료 -> {OUTPUT_PATH}")
print(f"총 전표 수      : {total_vouchers} 장")
print(f"총 라인 수      : {total_lines} 줄 (전표 1장 = 차변1 + 대변1)")
print(f"이상 전표 라인  : {len(anomaly_lines)} 줄")
print(f"차변 합계       : {total_debit:,} 원")
print(f"대변 합계       : {total_credit:,} 원")
print(f"차대변 균형     : {'OK' if total_debit == total_credit else '불일치!'}")
print("=" * 50)
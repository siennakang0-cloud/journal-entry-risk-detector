"""
main.py
전표 위험 탐지 파이프라인 실행 진입점.

실행 순서:
  1) 합성 전표 데이터 생성 (data/journal_entries.csv)
  2) 5가지 위험지표 규칙 적용
  3) 위험 전표만 추려 결과 저장 (output/flagged_entries.csv)
  4) 요약 표와 검증 리포트 저장 (output/summary.csv, output/validation.txt)
  5) 시각화 차트 저장 (output/*.png)

사용법:
    python main.py
"""

import os
import sys

# src 모듈 import 경로 확보
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd

from generate_data import generate
from risk_rules import apply_rules, RULES
from visualize import save_summary_charts

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
OUT_DIR = os.path.join(BASE, "output")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) 데이터 생성 (이미 있으면 재사용)
    data_path = os.path.join(DATA_DIR, "journal_entries.csv")
    df = generate()
    df.to_csv(data_path, index=False, encoding="utf-8-sig")
    print(f"[1/5] 합성 전표 {len(df)}건 생성 → data/journal_entries.csv")

    # 2) 규칙 적용
    scored = apply_rules(df)
    print("[2/5] 5가지 위험지표 규칙 적용 완료")

    # 3) 위험 전표 저장 (위험점수 높은 순)
    flagged = scored[scored["risk_score"] > 0].copy()
    flagged = flagged.sort_values(["risk_score", "amount"], ascending=[False, False])
    report_cols = [
        "entry_id", "posting_datetime", "account_code", "account_name",
        "description", "amount", "preparer", "approver",
        "risk_score", "risk_reasons",
    ]
    flagged[report_cols].to_csv(
        os.path.join(OUT_DIR, "flagged_entries.csv"),
        index=False, encoding="utf-8-sig",
    )
    print(f"[3/5] 위험 전표 {len(flagged)}건 → output/flagged_entries.csv")

    # 4) 요약 표 + 검증 리포트
    summary_rows = []
    for col, _, label in RULES:
        summary_rows.append({
            "risk_type": col,
            "설명": label,
            "탐지건수": int(scored[f"flag_{col}"].sum()),
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(os.path.join(OUT_DIR, "summary.csv"),
                   index=False, encoding="utf-8-sig")

    _write_validation(scored, os.path.join(OUT_DIR, "validation.txt"))
    print("[4/5] 요약표(summary.csv) · 검증리포트(validation.txt) 저장")

    # 5) 시각화
    charts = save_summary_charts(scored, OUT_DIR)
    print(f"[5/5] 차트 저장 → {', '.join(os.path.basename(c) for c in charts)}")

    # 콘솔 요약
    total = len(scored)
    n_flag = len(flagged)
    print("\n===== 탐지 요약 =====")
    print(f"전체 전표: {total}건 / 위험 전표: {n_flag}건 ({n_flag/total*100:.1f}%)")
    for _, r in summary.iterrows():
        print(f"  - {r['설명']}: {r['탐지건수']}건")


def _write_validation(scored, path):
    """심어둔 정답(injected_risk)과 규칙 탐지 결과를 비교해 성능을 기록한다.

    injected_risk는 검증 목적으로만 사용하며, 탐지 규칙 자체는 이 컬럼을
    전혀 참조하지 않는다(현실의 감사에는 정답표가 없으므로).
    """
    lines = []
    lines.append("검증 리포트 — 심어둔 이상 전표(정답)를 규칙이 얼마나 잡아냈는가")
    lines.append("=" * 60)

    # 규칙 col ↔ injected label 매핑 (같은 이름 체계로 맞춰둠)
    pairs = [
        ("high_amount", "high_amount"),
        ("missing_description", "missing_description"),
        ("duplicate", "duplicate"),
        ("off_hours", "off_hours"),
        ("segregation_conflict", "segregation_conflict"),
    ]
    for flag_key, inj_key in pairs:
        planted = (scored["injected_risk"] == inj_key)
        detected = scored[f"flag_{flag_key}"]
        n_planted = int(planted.sum())
        n_caught = int((planted & detected).sum())
        recall = (n_caught / n_planted * 100) if n_planted else 0.0
        lines.append(
            f"[{inj_key}] 심음 {n_planted}건 / 규칙이 잡음 {n_caught}건 "
            f"→ 재현율 {recall:.0f}%"
        )

    # 전체 관점
    any_planted = (scored["injected_risk"] != "")
    any_flag = (scored["risk_score"] > 0)
    tp = int((any_planted & any_flag).sum())
    fn = int((any_planted & ~any_flag).sum())
    fp = int((~any_planted & any_flag).sum())
    lines.append("-" * 60)
    lines.append(f"심어둔 이상 전표 총 {int(any_planted.sum())}건")
    lines.append(f"  정탐(TP): {tp}건 / 미탐(FN): {fn}건")
    lines.append(f"  정상인데 규칙에 걸린 건(FP, 추가검토 대상): {fp}건")
    lines.append("")
    lines.append("※ FP(오탐)는 오류가 아니라 '사람이 추가로 확인해볼 전표'다.")
    lines.append("  예: 정상 업무였지만 우연히 주말에 기표된 전표 등.")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()

"""
visualize.py
탐지 결과 시각화 모듈.

규칙 적용 결과를 두 개의 요약 차트로 그린다.
  1) 위험 유형별 탐지 건수 (막대그래프)
  2) 전체 전표 대비 정상/위험 비율 (막대그래프)

차트 라벨은 폰트 호환성을 위해 영문 위험유형 키(high_amount 등)를 사용한다.
(한글 폰트가 없는 환경에서도 깨지지 않도록 하기 위함)
"""

import os

import matplotlib
matplotlib.use("Agg")  # 화면 없는 환경에서도 저장 가능
import matplotlib.pyplot as plt

from risk_rules import RULES


def save_summary_charts(scored, out_dir):
    """탐지 결과 요약 차트를 out_dir에 PNG로 저장한다."""
    os.makedirs(out_dir, exist_ok=True)

    # 1) 위험 유형별 탐지 건수
    labels = [col for col, _, _ in RULES]
    counts = [int(scored[f"flag_{col}"].sum()) for col, _, _ in RULES]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(labels))
    bars = ax.bar(x, counts, color="#C0392B")
    ax.set_title("Detected entries by risk type", fontsize=13, fontweight="bold")
    ax.set_ylabel("Number of flagged entries")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=20, ha="right")
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c + 0.3, str(c),
                ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    p1 = os.path.join(out_dir, "risk_by_type.png")
    fig.savefig(p1, dpi=130)
    plt.close(fig)

    # 2) 정상 vs 위험 비율
    total = len(scored)
    flagged = int((scored["risk_score"] > 0).sum())
    normal = total - flagged

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(["Normal", "Flagged"], [normal, flagged],
                  color=["#5D6D7E", "#C0392B"])
    ax.set_title("Normal vs Flagged entries", fontsize=13, fontweight="bold")
    ax.set_ylabel("Number of entries")
    for b, c in zip(bars, [normal, flagged]):
        pct = (c / total * 100) if total else 0
        ax.text(b.get_x() + b.get_width() / 2, c + total * 0.005,
                f"{c}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=10)
    fig.tight_layout()
    p2 = os.path.join(out_dir, "normal_vs_flagged.png")
    fig.savefig(p2, dpi=130)
    plt.close(fig)

    return [p1, p2]

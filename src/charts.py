# -*- coding: utf-8 -*-
"""
위험 전표 차트 생성
==================

scorer.py의 결과를 받아서 두 종류의 막대그래프(PNG)를 만든다.
- 차트 1: 정상 vs 위험 전표 비율
- 차트 2: 탐지 규칙별 적중 건수

대시보드(report.py)와 '같은 데이터'를 사용하므로 숫자가 서로 일치한다.

사용법:
  python3 src/charts.py
"""

import os
import matplotlib
matplotlib.use("Agg")  # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt
from matplotlib import font_manager

from loader import load_journal_entries
from scorer import score_vouchers, collect_flags

# 한글 폰트 설정 (Noto Sans CJK)
_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(_FONT_PATH):
    font_manager.fontManager.addfont(_FONT_PATH)
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=_FONT_PATH).get_name()
plt.rcParams["axes.unicode_minus"] = False

# 색상 (대시보드와 통일감 있게)
COLOR_NORMAL = "#5b6b80"   # 차분한 청회색
COLOR_FLAG = "#c0392b"     # 위험 빨강


def make_normal_vs_flagged_chart(df, scored_df, output_path):
    """정상 vs 위험 전표 막대그래프"""
    total = df["전표번호"].nunique()
    flagged = len(scored_df)
    normal = total - flagged

    labels = ["정상", "위험"]
    values = [normal, flagged]
    colors = [COLOR_NORMAL, COLOR_FLAG]

    fig, ax = plt.subplots(figsize=(7, 6))
    bars = ax.bar(labels, values, color=colors, width=0.6)

    # 막대 위에 값과 비율 표시
    for bar, value in zip(bars, values):
        pct = 100 * value / total
        ax.text(bar.get_x() + bar.get_width() / 2, value,
                f"{value}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=12)

    ax.set_title("정상 vs 위험 전표", fontsize=16, fontweight="bold")
    ax.set_ylabel("전표 수", fontsize=12)
    ax.set_ylim(0, total * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)


def make_risk_type_chart(flags_df, output_path):
    """탐지 규칙별 적중 건수 막대그래프"""
    counts = flags_df["탐지사유"].value_counts()

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(counts.index, counts.values, color=COLOR_FLAG, width=0.6)

    for bar, value in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value,
                str(value), ha="center", va="bottom", fontsize=11)

    ax.set_title("탐지 규칙별 위험 전표 건수", fontsize=16, fontweight="bold")
    ax.set_ylabel("위험 전표 수", fontsize=12)
    ax.set_ylim(0, max(counts.values) * 1.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.xticks(rotation=20, ha="right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)


def main():
    print("=" * 60)
    print("위험 전표 차트 생성 (PNG)")
    print("=" * 60)

    df = load_journal_entries()
    scored_df = score_vouchers(df)
    flags_df = collect_flags(df)

    os.makedirs("reports", exist_ok=True)

    chart1 = "reports/chart_normal_vs_flagged.png"
    chart2 = "reports/chart_by_risk_type.png"

    make_normal_vs_flagged_chart(df, scored_df, chart1)
    make_risk_type_chart(flags_df, chart2)

    print(f"\n✓ 차트 생성 완료")
    print(f"  - {chart1}")
    print(f"  - {chart2}")
    print("=" * 60)


if __name__ == "__main__":
    main()

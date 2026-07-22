# -*- coding: utf-8 -*-
"""
탐지 결과 평가 & 채점
====================

데이터에 심어 둔 '정답 이상 전표(is_anomaly)' vs
규칙 세트가 실제로 찾아낸 '탐지 전표'를 비교해서,
탐지기의 성능을 평가한다.

- Precision(정밀도): 찾은 것 중 몇 %가 진짜인가?
- Recall(재현율): 진짜 것 중 몇 %를 찾아냈는가?
- F1-Score: 둘을 조화평균으로 종합한 점수

사용법:
  python3 src/evaluate.py
"""

from loader import load_journal_entries
from scorer import score_vouchers


def evaluate_detection(df, scored_df):
    """
    탐지 결과를 정답과 비교하고 성능 지표를 계산한다.

    반환:
      dict: {
        'tp': 참양성(true positive) 개수,
        'fp': 거짓양성(false positive) 개수,
        'fn': 거짓음성(false negative) 개수,
        'precision': 정밀도,
        'recall': 재현율,
        'f1': F1-Score
      }
    """

    # 정답: 심어 둔 이상 전표
    # (엑셀을 거치면서 True가 "True" 문자열로 바뀔 수 있어서 둘 다 처리)
    answer = set(df[df["is_anomaly"] == True]["전표번호"])          # noqa: E712
    answer |= set(df[df["is_anomaly"].astype(str) == "True"]["전표번호"])

    # 탐지: 규칙이 찾아낸 전표
    detected = set(scored_df["전표번호"])

    # TP, FP, FN 계산
    tp = len(answer & detected)      # 정답 중에서 찾은 것
    fp = len(detected - answer)      # 정답이 아닌데 찾은 것 (오탐)
    fn = len(answer - detected)      # 정답인데 못 찾은 것 (미탐)

    # 지표 계산
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'answer_count': len(answer),      # 정답 전표 개수
        'detected_count': len(detected),  # 탐지된 전표 개수
    }


def print_evaluation_report(metrics):
    """평가 결과를 보기 좋게 출력한다."""
    print("=" * 60)
    print("탐지 성능 평가")
    print("=" * 60)

    print(f"\n[혼동행렬 (Confusion Matrix)]")
    print(f"  참양성(TP, 맞게 찾음)    : {metrics['tp']} 건")
    print(f"  거짓양성(FP, 오탐)      : {metrics['fp']} 건")
    print(f"  거짓음성(FN, 미탐)      : {metrics['fn']} 건")

    print(f"\n[정확도 지표]")
    print(f"  정밀도(Precision)  : {metrics['precision']:.1%}  (찾은 것 중 맞는 비율)")
    print(f"  재현율(Recall)     : {metrics['recall']:.1%}  (정답 중 찾은 비율)")
    print(f"  F1-Score          : {metrics['f1']:.3f}   (정밀도·재현율 조화평균)")

    print(f"\n[대조]")
    print(f"  정답 전표 개수     : {metrics['answer_count']} 장")
    print(f"  탐지된 전표 개수   : {metrics['detected_count']} 장")

    print("=" * 60)


def main():
    df = load_journal_entries()
    scored_df = score_vouchers(df)

    metrics = evaluate_detection(df, scored_df)
    print_evaluation_report(metrics)

    # 감사 관점의 해석
    print("\n[감사 관점의 해석]")
    if metrics['recall'] == 1.0:
        print("  ✓ 완벽한 재현율! 모든 이상 전표를 찾아냈습니다.")
    elif metrics['recall'] >= 0.8:
        print("  △ 재현율이 80% 이상입니다. 일부 미탐이 있으므로 보충 절차가 필요합니다.")
    else:
        print("  × 재현율이 낮습니다. 규칙을 보강하거나 수동 검토 비중을 늘려야 합니다.")

    if metrics['precision'] == 1.0:
        print("  ✓ 완벽한 정밀도! 찾은 것이 모두 실제 이상입니다.")
    elif metrics['precision'] >= 0.7:
        print("  △ 정밀도가 70% 이상이므로 실용적 수준입니다.")
    else:
        print("  × 정밀도가 낮습니다. 오탐이 많으므로 규칙을 정교화해야 합니다.")


if __name__ == "__main__":
    main()

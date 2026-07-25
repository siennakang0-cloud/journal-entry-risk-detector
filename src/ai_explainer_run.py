# -*- coding: utf-8 -*-
"""
journal-entry-risk-detector 프로젝트에 AI 설명 기능을 연결하는 예시 코드.

[컴퓨터에서 할 일]
1. 이 파일을 journal-entry-risk-detector/src/ 폴더 안에
   'ai_explainer_run.py' 라는 이름으로 복사한다.
2. 이 파일과 같이 온 explainer.py 도 journal-entry-risk-detector/src/ 안에 복사한다.
   (같은 폴더 안에 있으면 아래 import가 별도 경로 설정 없이 바로 동작한다.)
3. ANTHROPIC_API_KEY 환경변수를 설정한다.
4. journal-entry-risk-detector 폴더에서 실행:
     python3 src/ai_explainer_run.py
5. reports/ai_explanations.csv 로 결과가 저장된다.
"""

import os
from loader import load_journal_entries
from scorer import score_vouchers
from explainer import explain_dataframe


def main():
    df = load_journal_entries()
    scored = score_vouchers(df)  # 컬럼: 전표번호, 위험점수, 걸린규칙수, 탐지사유목록, 계정과목, 금액, 전기일자

    # 위험점수 상위 5건만 우선 테스트 (API 호출 비용을 아끼기 위함).
    # 전체를 다 돌리고 싶으면 limit=None 으로 바꾼다.
    explained = explain_dataframe(
        scored,
        id_col="전표번호",
        rule_col="탐지사유목록",
        extra_cols=["계정과목", "금액", "전기일자"],
        limit=5,
    )

    print(explained.to_string(index=False))

    os.makedirs("reports", exist_ok=True)
    explained.to_csv("reports/ai_explanations.csv", index=False, encoding="utf-8-sig")
    print("\n✓ reports/ai_explanations.csv 저장 완료")


if __name__ == "__main__":
    main()

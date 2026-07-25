# -*- coding: utf-8 -*-
"""
AI 위험거래 설명 생성기 (Flag Explainer)
==========================================

기존 규칙 기반 이상탐지 프로젝트(journal-entry-risk-detector,
sales-timing-risk-detector-mine)에서 이미 '위험 거래'로 플래그된 결과를
입력받아, 생성형 AI(LLM)가 "왜 위험한지"를 자연어 감사 코멘트로
설명해주는 재사용 모듈.

기존 프로젝트를 바꾸지 않고, 이 모듈만 옆에 두고 불러 쓰는 방식이라
어느 프로젝트에도 붙일 수 있다.

사용 전 준비 (둘 중 하나만 하면 됨 — Gemini가 카드 없이 더 쉽게 발급됨):

  [A] Google Gemini (추천 — 카드 등록 없이 무료)
      1) pip install google-genai pandas
      2) https://aistudio.google.com/apikey 에서 API 키 발급 (구글 계정만 있으면 됨)
      3) export GEMINI_API_KEY="본인의 키"

  [B] Anthropic (카드/전화인증이 막히면 대신 A를 쓰세요)
      1) pip install anthropic pandas
      2) https://console.anthropic.com 에서 API 키 발급
      3) export ANTHROPIC_API_KEY="본인의 키"

두 키 중 하나만 설정돼 있으면 자동으로 그쪽을 사용한다(Gemini 우선).

실행 예시는 examples/ 폴더의 journal_integration_example.py,
sales_integration_example.py 를 참고.
"""

import os

try:
    from google import genai as google_genai
except ImportError:
    google_genai = None

try:
    import anthropic
except ImportError:
    anthropic = None


EXPLAIN_PROMPT_TEMPLATE = """당신은 경험 많은 감사인입니다.
아래 거래는 규칙 기반 이상탐지 시스템에 의해 이미 '위험 거래'로 플래그되었습니다.
이 거래가 왜 위험한지, 감사인이 어떤 관점에서 추가로 확인해야 하는지를
2~3문장의 자연스러운 감사 코멘트로 작성하세요.

일반론이 아니라 아래 거래 정보와 걸린 규칙을 구체적으로 반영해서 작성하고,
마지막 문장에는 감사인이 우선적으로 확인해야 할 증빙이나 절차를 한 가지 제안하세요.

[거래 정보]
{transaction_info}

[걸린 탐지 규칙]
{triggered_rules}
"""


def _format_transaction_info(info: dict) -> str:
    return "\n".join(f"- {k}: {v}" for k, v in info.items())


def build_prompt(transaction_info: dict, triggered_rules: list) -> str:
    return EXPLAIN_PROMPT_TEMPLATE.format(
        transaction_info=_format_transaction_info(transaction_info),
        triggered_rules=", ".join(triggered_rules),
    )


def explain_flagged_transaction(transaction_info: dict, triggered_rules: list) -> str:
    """생성형 AI API를 호출해 거래 하나에 대한 감사 설명을 생성한다.
    GEMINI_API_KEY가 있으면 Gemini를, 없으면 ANTHROPIC_API_KEY로 Claude를 쓴다.
    둘 다 없으면 안내 메시지와 함께 프롬프트만 보여준다."""
    prompt = build_prompt(transaction_info, triggered_rules)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if google_genai is not None and gemini_key:
        client = google_genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        return response.text

    if anthropic is not None and anthropic_key:
        client = anthropic.Anthropic(api_key=anthropic_key)
        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    return (
        "[API 미설정] GEMINI_API_KEY 또는 ANTHROPIC_API_KEY가 없어 실제 호출은 건너뜁니다. "
        "examples/ 폴더의 example_output_*.md 로 결과 형태를 참고하세요.\n"
        f"--- 프롬프트 미리보기 ---\n{prompt}"
    )


def explain_dataframe(scored_df, id_col, rule_col, extra_cols, limit=5):
    """scored_df(점수 매긴 위험 거래 표)를 받아, 상위 limit건에 대해
    AI 설명을 붙인 새 DataFrame을 반환한다.

    위험점수 컬럼 기준으로 이미 정렬되어 있다고 가정하고, 상위 몇 건만
    처리하는 이유는 API 호출 비용/시간을 아끼기 위해서다. 전수 처리하고
    싶으면 limit=None 으로 바꾸면 된다.
    """
    import pandas as pd

    rows = scored_df.head(limit) if limit else scored_df
    records = []
    for _, row in rows.iterrows():
        info = {id_col: row[id_col]}
        for c in extra_cols:
            info[c] = row[c]
        rules_list = [r.strip() for r in str(row[rule_col]).split(",")]
        explanation = explain_flagged_transaction(info, rules_list)
        records.append({id_col: row[id_col], "AI설명": explanation})
    return pd.DataFrame(records)

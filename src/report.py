# -*- coding: utf-8 -*-
"""
위험 전표 리포트 생성
====================

scorer.py 에서 산출한 위험 점수 데이터를 받아서,
시각적으로 보기 좋은 HTML 리포트로 변환한다.

- 위험 점수별로 정렬된 전표 목록 테이블
- 규칙 분포 차트 (어떤 규칙에 가장 많이 걸렸는지)
- 감사인이 즉시 검토할 수 있는 형태

사용법:
  python3 src/report.py
"""

import pandas as pd
from loader import load_journal_entries
from scorer import score_vouchers, collect_flags


def generate_html_report(df, scored_df, flags_df):
    """
    위험 전표 정보를 HTML 형태로 변환한다.
    - scored_df: score_vouchers()의 결과 (위험점수, 걸린규칙수 등)
    - flags_df: collect_flags()의 결과 (각 전표가 걸린 규칙 목록)
    """

    # 규칙별 적중 횟수 (차트용)
    rule_counts = flags_df["탐지사유"].value_counts()
    rule_html = "".join([
        f"<tr><td>{rule}</td><td>{int(count)}</td></tr>"
        for rule, count in rule_counts.items()
    ])

    # 위험 전표 목록 (테이블용)
    voucher_rows = "".join([
        f"""
        <tr>
            <td>{row['전표번호']}</td>
            <td style="text-align:right; color: {'red' if row['위험점수'] >= 5 else 'orange' if row['위험점수'] >= 3 else 'green'}; font-weight:bold;">
                {int(row['위험점수'])}
            </td>
            <td>{int(row['걸린규칙수'])}</td>
            <td>{int(row['금액']):,}</td>
            <td>{row['전기일자']}</td>
            <td>{row['계정과목']}</td>
            <td>{row['탐지사유목록']}</td>
        </tr>
        """
        for _, row in scored_df.iterrows()
    ])

    # 기본 통계
    total_vouchers = df["전표번호"].nunique()
    risky_count = len(scored_df)
    avg_score = scored_df["위험점수"].mean() if len(scored_df) > 0 else 0
    max_score = scored_df["위험점수"].max() if len(scored_df) > 0 else 0

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>전표 위험 분석 리포트</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px 20px;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .header p {{
                font-size: 1.1em;
                opacity: 0.9;
            }}
            .summary {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                padding: 30px;
                background: #f8f9fa;
                border-bottom: 1px solid #e9ecef;
            }}
            .summary-card {{
                text-align: center;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
            .summary-card .number {{
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 10px;
            }}
            .summary-card .label {{
                font-size: 0.9em;
                color: #6c757d;
            }}
            .content {{
                padding: 40px;
            }}
            .section {{
                margin-bottom: 50px;
            }}
            .section h2 {{
                font-size: 1.8em;
                color: #333;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #667eea;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            th {{
                background: #667eea;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                font-size: 0.95em;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #e9ecef;
                font-size: 0.95em;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            .risk-high {{
                color: #dc3545;
                font-weight: bold;
            }}
            .risk-medium {{
                color: #ff9800;
                font-weight: bold;
            }}
            .risk-low {{
                color: #28a745;
            }}
            .footer {{
                background: #f8f9fa;
                padding: 30px;
                text-align: center;
                color: #6c757d;
                font-size: 0.9em;
                border-top: 1px solid #e9ecef;
            }}
            .footer .timestamp {{
                color: #999;
                font-size: 0.85em;
                margin-top: 10px;
            }}
            @media (max-width: 768px) {{
                .summary {{
                    grid-template-columns: repeat(2, 1fr);
                }}
                table {{
                    font-size: 0.85em;
                }}
                th, td {{
                    padding: 8px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 전표 위험 분석 리포트</h1>
                <p>Journal Entry Risk Detector · Risk-Based Audit Approach</p>
            </div>

            <div class="summary">
                <div class="summary-card">
                    <div class="number">{total_vouchers}</div>
                    <div class="label">전체 전표</div>
                </div>
                <div class="summary-card">
                    <div class="number" style="color: #dc3545;">{risky_count}</div>
                    <div class="label">위험 전표</div>
                </div>
                <div class="summary-card">
                    <div class="number">{max_score:.0f}</div>
                    <div class="label">최고 위험 점수</div>
                </div>
                <div class="summary-card">
                    <div class="number">{(100 * risky_count / total_vouchers):.1f}%</div>
                    <div class="label">위험 비율</div>
                </div>
            </div>

            <div class="content">
                <!-- 규칙 분포 -->
                <div class="section">
                    <h2>🎯 탐지 규칙 분포</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>탐지 규칙</th>
                                <th>적중 횟수</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rule_html}
                        </tbody>
                    </table>
                </div>

                <!-- 위험 전표 목록 -->
                <div class="section">
                    <h2>⚠️ 위험 전표 목록 (위험도순)</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>전표번호</th>
                                <th>위험점수</th>
                                <th>걸린규칙</th>
                                <th>금액</th>
                                <th>전기일자</th>
                                <th>계정과목</th>
                                <th>탐지 사유</th>
                            </tr>
                        </thead>
                        <tbody>
                            {voucher_rows if voucher_rows.strip() else '<tr><td colspan="7" style="text-align:center; color:#999;">위험 전표 없음</td></tr>'}
                        </tbody>
                    </table>
                </div>

                <!-- 감사 방법론 -->
                <div class="section">
                    <h2>📋 감사 방법론</h2>
                    <p style="line-height: 1.8; color: #555;">
                        본 리포트는 <strong>ISA 240(부정에 대한 책임)</strong>에 기반한 위험 기반 감사(Risk-Based Audit Approach)를
                        자동화한 것입니다. 7개 탐지 규칙을 통해 다음과 같은 감사 위험을 식별합니다:
                    </p>
                    <ul style="margin-left: 20px; line-height: 2; color: #555;">
                        <li><strong>고액전표</strong> (가중치 3): 과도한 규모의 거래</li>
                        <li><strong>직무분리위반</strong> (가중치 3): 입력자와 승인자가 동일</li>
                        <li><strong>중복전표</strong> (가중치 2): 동일 거래의 중복 기록</li>
                        <li><strong>비정상입력시간</strong> (가중치 2): 주말/야간 입력</li>
                        <li><strong>한도직전금액</strong> (가중치 2): 승인 한도 바로 직전</li>
                        <li><strong>라운드금액</strong> (가중치 1): 정수 금액의 반복</li>
                        <li><strong>적요누락</strong> (가중치 1): 거래 설명 부재</li>
                    </ul>
                </div>
            </div>

            <div class="footer">
                <div>감사인의 위험 기반 접근 방식(Risk-Based Audit)을 통해 한정된 감사 자원을 효율적으로 배분합니다.</div>
                <div class="timestamp">리포트 생성: {pd.Timestamp.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def main():
    print("=" * 60)
    print("위험 전표 리포트 생성 (HTML)")
    print("=" * 60)

    df = load_journal_entries()
    scored_df = score_vouchers(df)
    flags_df = collect_flags(df)

    html = generate_html_report(df, scored_df, flags_df)

    # HTML 파일로 저장
    output_path = "reports/risk_report.html"
    import os
    os.makedirs("reports", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✓ 리포트 생성 완료: {output_path}")
    print(f"  - 전표 {df['전표번호'].nunique()}장 분석")
    print(f"  - 위험 전표 {len(scored_df)}장 탐지")
    print(f"  - 적용 규칙 {len(flags_df['탐지사유'].unique())}개")
    print("=" * 60)


if __name__ == "__main__":
    main()

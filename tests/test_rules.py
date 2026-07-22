# -*- coding: utf-8 -*-
"""
이상탐지 규칙 단위테스트
=======================

각 규칙이 의도대로 동작하는지 unittest로 검증한다.
감사에서 이 테스트는 '규칙의 논리적 정확성'을 증명한다.

실행:
  python3 tests/test_rules.py
"""

import sys
import os

# src 폴더를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import pandas as pd
from datetime import datetime
import rules


class TestAnomalyDetection(unittest.TestCase):
    """이상탐지 규칙 테스트"""

    def setUp(self):
        """각 테스트 전에 샘플 데이터 준비"""
        self.sample_df = pd.DataFrame({
            '전표번호': ['JE001', 'JE002', 'JE003', 'JE004', 'JE005'],
            '전기일자': ['2024-01-15', '2024-01-15', '2024-01-15', '2024-01-20', '2024-01-21'],
            '입력일시': [
                '2024-01-15 09:00:00',
                '2024-01-15 23:30:00',  # 심야
                '2024-01-20 10:00:00',  # 토요일
                '2024-01-15 14:00:00',
                '2024-01-15 14:00:00',
            ],
            '계정코드': ['1100', '1100', '2000', '3000', '1100'],
            '계정과목': ['보통예금', '보통예금', '외상매출금', '매출', '보통예금'],
            '차변금액': [10000000, 500000, 1000, 2000, 3000],
            '대변금액': [0, 0, 0, 2000, 3000],
            '적요': ['입금', '', '대금회수', '판매', '송금'],
            '입력자': ['Kim', 'Lee', 'Park', 'Choi', 'Roh'],
            '승인자': ['Kim', 'Lee', 'Park', 'Other', 'Roh'],
        })

    def test_detect_high_value_basic(self):
        """고액 전표(10,000,000원 이상) 탐지"""
        result = rules.detect_high_value(self.sample_df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE001')

    def test_detect_high_value_threshold(self):
        """고액 전표 임계값 정확성"""
        df = pd.DataFrame({
            '전표번호': ['JE001', 'JE002'],
            '전기일자': ['2024-01-15', '2024-01-15'],
            '입력일시': ['2024-01-15 09:00:00', '2024-01-15 09:00:00'],
            '계정코드': ['1100', '1100'],
            '계정과목': ['보통예금', '보통예금'],
            '차변금액': [9999999, 10000000],
            '대변금액': [0, 0],
            '적요': ['test', 'test'],
            '입력자': ['A', 'A'],
            '승인자': ['A', 'A'],
        })
        result = rules.detect_high_value(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE002')

    def test_detect_missing_description(self):
        """적요 누락 탐지"""
        result = rules.detect_missing_description(self.sample_df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE002')

    def test_detect_duplicates(self):
        """중복 전표 탐지"""
        df = pd.DataFrame({
            '전표번호': ['JE001', 'JE002', 'JE003'],
            '전기일자': ['2024-01-15', '2024-01-15', '2024-01-15'],
            '입력일시': ['2024-01-15 09:00:00', '2024-01-15 09:30:00', '2024-01-16 10:00:00'],
            '계정코드': ['1100', '1100', '2000'],
            '계정과목': ['보통예금', '보통예금', '외상매출금'],
            '차변금액': [1000, 1000, 2000],
            '대변금액': [0, 0, 0],
            '적요': ['a', 'a', 'b'],
            '입력자': ['A', 'A', 'B'],
            '승인자': ['X', 'X', 'Y'],
        })
        result = rules.detect_duplicates(df)
        self.assertEqual(len(result), 2)
        detected = set(result['전표번호'])
        self.assertEqual(detected, {'JE001', 'JE002'})

    def test_detect_sod_conflict(self):
        """직무분리 위반 탐지"""
        result = rules.detect_sod_conflict(self.sample_df)
        self.assertEqual(len(result), 2)
        detected = set(result['전표번호'])
        self.assertEqual(detected, {'JE001', 'JE005'})

    def test_detect_sod_conflict_proper_separation(self):
        """입력자와 승인자가 다른 경우"""
        df = pd.DataFrame({
            '전표번호': ['JE001', 'JE002'],
            '전기일자': ['2024-01-15', '2024-01-15'],
            '입력일시': ['2024-01-15 09:00:00', '2024-01-15 09:00:00'],
            '계정코드': ['1100', '1100'],
            '계정과목': ['보통예금', '보통예금'],
            '차변금액': [1000, 1000],
            '대변금액': [0, 0],
            '적요': ['a', 'b'],
            '입력자': ['Kim', 'Lee'],
            '승인자': ['Park', 'Kim'],
        })
        result = rules.detect_sod_conflict(df)
        self.assertEqual(len(result), 0)

    def test_detect_unusual_time_night(self):
        """야간 입력 탐지"""
        result = rules.detect_unusual_time(self.sample_df)
        detected = set(result['전표번호'])
        self.assertIn('JE002', detected)

    def test_detect_unusual_time_weekend(self):
        """주말 입력 탐지"""
        result = rules.detect_unusual_time(self.sample_df)
        detected = set(result['전표번호'])
        self.assertIn('JE003', detected)

    def test_detect_just_below_limit(self):
        """승인 한도 직전 금액 탐지"""
        df = pd.DataFrame({
            '전표번호': ['JE001', 'JE002', 'JE003'],
            '전기일자': ['2024-01-15', '2024-01-15', '2024-01-15'],
            '입력일시': ['2024-01-15 09:00:00', '2024-01-15 09:00:00', '2024-01-15 09:00:00'],
            '계정코드': ['1100', '1100', '1100'],
            '계정과목': ['보통예금', '보통예금', '보통예금'],
            '차변금액': [9800000, 9950000, 10000000],
            '대변금액': [0, 0, 0],
            '적요': ['a', 'b', 'c'],
            '입력자': ['A', 'A', 'A'],
            '승인자': ['A', 'A', 'A'],
        })
        result = rules.detect_just_below_limit(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE002')

    def test_detect_round_amount(self):
        """라운드 금액 탐지"""
        df = pd.DataFrame({
            '전표번호': ['JE001', 'JE002', 'JE003', 'JE004'],
            '전기일자': ['2024-01-15', '2024-01-15', '2024-01-15', '2024-01-15'],
            '입력일시': ['2024-01-15 09:00:00'] * 4,
            '계정코드': ['1100'] * 4,
            '계정과목': ['보통예금'] * 4,
            '차변금액': [1000000, 2000000, 3000000, 1234567],
            '대변금액': [0] * 4,
            '적요': ['a'] * 4,
            '입력자': ['A'] * 4,
            '승인자': ['A'] * 4,
        })
        result = rules.detect_round_amount(df)
        self.assertEqual(len(result), 3)
        detected = set(result['전표번호'])
        self.assertEqual(detected, {'JE001', 'JE002', 'JE003'})

    def test_normal_transaction_not_flagged(self):
        """정상 거래는 탐지되지 않아야 함"""
        df = pd.DataFrame({
            '전표번호': ['JE001'],
            '전기일자': ['2024-01-15'],
            '입력일시': ['2024-01-15 14:00:00'],
            '계정코드': ['1100'],
            '계정과목': ['보통예금'],
            '차변금액': [500000],
            '대변금액': [0],
            '적요': ['정상 거래'],
            '입력자': ['Kim'],
            '승인자': ['Park'],
        })

        all_results = []
        for detect_func in [
            rules.detect_high_value,
            rules.detect_missing_description,
            rules.detect_duplicates,
            rules.detect_sod_conflict,
            rules.detect_unusual_time,
            rules.detect_just_below_limit,
            rules.detect_round_amount,
        ]:
            result = detect_func(df)
            all_results.extend(result['전표번호'].tolist())

        self.assertEqual(len(all_results), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

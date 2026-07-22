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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
import pandas as pd
import rules


def make_df(rows):
    """테스트용 전표 DataFrame을 만든다. (필요한 컬럼을 모두 채운다)"""
    return pd.DataFrame(rows, columns=[
        '전표번호', '전기일자', '입력일시', '계정코드', '계정과목',
        '차변금액', '대변금액', '적요', '입력자', '승인자',
    ])


class TestAnomalyDetection(unittest.TestCase):
    """이상탐지 규칙 테스트 (실제 rules.py 기준)"""

    def test_detect_high_value_basic(self):
        """고액 전표(승인한도 5천만원 초과) 탐지"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 60_000_000, 0, '입금', 'A', 'X'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 40_000_000, 0, '입금', 'A', 'X'],
        ])
        result = rules.detect_high_value(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE001')

    def test_detect_high_value_threshold(self):
        """고액 전표 임계값 정확성 (5천만원 초과만)"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 50_000_000, 0, 't', 'A', 'X'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 50_000_001, 0, 't', 'A', 'X'],
        ])
        result = rules.detect_high_value(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE002')

    def test_detect_missing_description(self):
        """적요 누락 탐지"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, '정상 적요', 'A', 'X'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, '', 'A', 'X'],
        ])
        result = rules.detect_missing_description(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE002')

    def test_detect_duplicates(self):
        """중복 전표 탐지 (핵심 정보가 동일한 두 번째 전표)"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, 'a', 'A', 'X'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, 'a', 'A', 'X'],
            ['JE003', '2024-01-16', '2024-01-16 10:00:00', '2000', '외상매출금', 2_000_000, 0, 'b', 'B', 'Y'],
        ])
        result = rules.detect_duplicates(df)
        detected = set(result['전표번호'])
        self.assertEqual(detected, {'JE002'})

    def test_detect_sod_conflict(self):
        """직무분리 위반 탐지 (입력자 = 승인자)"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, 'a', 'Kim', 'Kim'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, 'b', 'Lee', 'Park'],
            ['JE003', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, 'c', 'Roh', 'Roh'],
        ])
        result = rules.detect_sod_conflict(df)
        detected = set(result['전표번호'])
        self.assertEqual(detected, {'JE001', 'JE003'})

    def test_detect_sod_conflict_proper_separation(self):
        """입력자와 승인자가 모두 다르면 탐지되지 않음"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, 'a', 'Kim', 'Park'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 1_000_000, 0, 'b', 'Lee', 'Kim'],
        ])
        result = rules.detect_sod_conflict(df)
        self.assertEqual(len(result), 0)

    def test_detect_unusual_time_night(self):
        """심야(22시~06시) 입력 탐지"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 23:30:00', '1100', '보통예금', 1_000_000, 0, 'a', 'A', 'X'],
            ['JE002', '2024-01-15', '2024-01-15 14:00:00', '1100', '보통예금', 1_000_000, 0, 'b', 'A', 'X'],
        ])
        result = rules.detect_unusual_time(df)
        detected = set(result['전표번호'])
        self.assertIn('JE001', detected)
        self.assertNotIn('JE002', detected)

    def test_detect_unusual_time_weekend(self):
        """주말(토·일) 입력 탐지 (2024-01-20은 토요일)"""
        df = make_df([
            ['JE001', '2024-01-20', '2024-01-20 10:00:00', '1100', '보통예금', 1_000_000, 0, 'a', 'A', 'X'],
        ])
        result = rules.detect_unusual_time(df)
        detected = set(result['전표번호'])
        self.assertIn('JE001', detected)

    def test_detect_just_below_limit(self):
        """승인 한도 직전 금액(4,500만원 이상 5,000만원 미만) 탐지"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 47_000_000, 0, 'a', 'A', 'X'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 40_000_000, 0, 'b', 'A', 'X'],
            ['JE003', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 50_000_000, 0, 'c', 'A', 'X'],
        ])
        result = rules.detect_just_below_limit(df)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['전표번호'], 'JE001')

    def test_detect_round_amount(self):
        """라운드 금액(1천만원 단위, 1억 미만) 탐지"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 10_000_000, 0, 'a', 'A', 'X'],
            ['JE002', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 20_000_000, 0, 'b', 'A', 'X'],
            ['JE003', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 30_000_000, 0, 'c', 'A', 'X'],
            ['JE004', '2024-01-15', '2024-01-15 09:00:00', '1100', '보통예금', 12_345_678, 0, 'd', 'A', 'X'],
        ])
        result = rules.detect_round_amount(df)
        detected = set(result['전표번호'])
        self.assertEqual(detected, {'JE001', 'JE002', 'JE003'})

    def test_normal_transaction_not_flagged(self):
        """정상 거래는 어떤 규칙에도 걸리지 않아야 함 (오탐 방지)"""
        df = make_df([
            ['JE001', '2024-01-15', '2024-01-15 14:00:00', '1100', '보통예금', 3_333_333, 0, '정상 거래', 'Kim', 'Park'],
        ])

        all_flagged = []
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
            all_flagged.extend(result['전표번호'].tolist())

        self.assertEqual(len(all_flagged), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

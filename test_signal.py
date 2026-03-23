"""
시그널 필터링 테스트 + 웹훅 시뮬레이션
실행: python test_signal.py
"""
import json
import asyncio
from server import is_s_grade_buy, format_telegram_message

# ── 테스트 데이터 (Webhook 문서 기반) ──

# 1. S등급 정석 진입 (KRX) → 알림 O
test_s_grade = {
    "ticker": "005930",
    "name": "삼성전자",
    "exchange": "KRX",
    "timeframe": "240",
    "action": "BUY",
    "type": "💰 정석 진입",
    "price": 72500,
    "sl": 69800,
    "rr": 2.0,
    "desc": "눌림목/지지 진입",
    "market": "⚡ 기회/환경 호전",
    "ai_summary": "📈 안정적 우상향 편안한 추세 (홀딩)",
    "score": 90,
    "status": "Green(GO)",
    "signal": "GP:수급 Sigma:PB ",
    "conviction": "S",
    "momentum": "",
    "momentum_sl": None,
    "momentum_tp": None,
    "momentum_bars": None,
    "energy": 2.85,
    "ema1_dist": 1.23,
    "candle_type": "양봉",
    "candle_strength": 82.5,
    "ema_touch": "ema1",
    "ema_align": "정배열"
}

# 2. A등급 (KRX) → 알림 X (S등급 아님)
test_a_grade = {
    "ticker": "000660",
    "name": "SK하이닉스",
    "exchange": "KRX",
    "action": "BUY",
    "conviction": "A",
    "ema_align": "정배열"
}

# 3. S등급이지만 SELL → 알림 X
test_s_sell = {
    "ticker": "035420",
    "name": "NAVER",
    "exchange": "KRX",
    "action": "SELL",
    "conviction": "S",
    "ema_align": "정배열"
}

# 4. S등급이지만 NASDAQ → 알림 X (KRX 아님)
test_s_nasdaq = {
    "ticker": "AAPL",
    "name": "Apple Inc",
    "exchange": "NASDAQ",
    "action": "BUY",
    "conviction": "S",
    "ema_align": "정배열"
}

# 5. S등급 + KRX + BUY이지만 역배열 → 알림 X
test_s_reverse = {
    "ticker": "068270",
    "name": "셀트리온",
    "exchange": "KRX",
    "action": "BUY",
    "conviction": "S",
    "ema_align": "역배열"
}

# 6. D등급 → 알림 X
test_d_grade = {
    "ticker": "005380",
    "name": "현대차",
    "exchange": "KRX",
    "action": "SELL",
    "conviction": "D",
    "ema_align": "역배열"
}


def run_tests():
    tests = [
        ("S등급 KRX 매수 (정배열)", test_s_grade, True),
        ("A등급 KRX 매수", test_a_grade, False),
        ("S등급 KRX 매도", test_s_sell, False),
        ("S등급 NASDAQ 매수", test_s_nasdaq, False),
        ("S등급 KRX 매수 (역배열)", test_s_reverse, False),
        ("D등급 KRX 매도", test_d_grade, False),
    ]

    print("=" * 50)
    print("Lazy Alpha 시그널 필터 테스트")
    print("=" * 50)

    passed = 0
    failed = 0

    for name, data, expected in tests:
        result = is_s_grade_buy(data)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {name} → 알림={'O' if result else 'X'} (예상={'O' if expected else 'X'})")

    print("=" * 50)
    print(f"결과: {passed}/{passed + failed} 통과")

    if failed == 0:
        print("\n📨 S등급 시그널 메시지 미리보기:")
        print("-" * 50)
        # HTML 태그 제거해서 터미널 출력
        msg = format_telegram_message(test_s_grade)
        clean_msg = msg.replace("<b>", "").replace("</b>", "")
        print(clean_msg)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

"""
Lazy Alpha Indicator - S등급 시그널 텔레그램 알림 서버
TradingView Webhook → 필터링 → Telegram 알림
"""

import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv
from kospi100 import is_in_top100, get_stock_name, KOSPI_TOP100

# 환경변수 로드
load_dotenv()

# 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # 선택: 보안용 시크릿 키

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("signals.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lazy Alpha Signal Filter")


# ──────────────────────────────────────────────
# 텔레그램 메시지 전송
# ──────────────────────────────────────────────
async def send_telegram(message: str):
    """텔레그램 봇으로 메시지 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("텔레그램 설정이 없습니다. .env 파일을 확인하세요.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("텔레그램 전송 성공")
                return True
            else:
                logger.error(f"텔레그램 전송 실패: {response.text}")
                return False
    except Exception as e:
        logger.error(f"텔레그램 전송 에러: {e}")
        return False


# ──────────────────────────────────────────────
# 시그널 필터링
# ──────────────────────────────────────────────
def is_s_grade_buy(data: dict) -> bool:
    """S등급 매수 시그널인지 확인 (코스피 100 이내 종목만)"""
    conviction = data.get("conviction", "").strip().upper()
    action = data.get("action", "").strip().upper()
    exchange = data.get("exchange", "").strip().upper()
    ema_align = data.get("ema_align", "")
    ticker = data.get("ticker", "").strip()

    # 앍벬 필터: S등급 + BUY + KRX
    if conviction != "S":
        return False
    if action != "BUY":
        return False
    if exchange != "KRX":
        return False

    # 코스피 시총 100 이내 종목 필터
    if not is_in_top100(ticker):
        logger.info(f"[필터링] {ticker} - 코스피 100 외 종목 제외")
        return False

    # 추가 안전 필터: 역배열이면 무시 (Webhook 문서 권장사항)
    if ema_align == "역배열":
        logger.info(f"[필터링] {data.get('name')} - S등급이지만 역배열이라 제외")
        return False

    return True


def format_telegram_message(data: dict) -> str:
    """텔레그램 알림 메시지 포맷팅"""
    ticker = data.get("ticker", "?")
    name = data.get("name", "?")
    price = data.get("price", "?")
    sl = data.get("sl", "없음")
    rr = data.get("rr", "없음")
    desc = data.get("desc", "")
    market = data.get("market", "")
    ai_summary = data.get("ai_summary", "")
    score = data.get("score", "?")
    signal = data.get("signal", "")
    conviction = data.get("conviction", "")
    energy = data.get("energy", "?")
    ema1_dist = data.get("ema1_dist", "?")
    candle_type = data.get("candle_type", "")
    candle_strength = data.get("candle_strength", "?")
    ema_touch = data.get("ema_touch", "")
    ema_align = data.get("ema_align", "")
    timeframe = data.get("timeframe", "")
    signal_type = data.get("type", "")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    msg = (
        f"🟣 <b>S등급 시그널 감지!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>{name}</b> ({ticker})\n"
        f"💰 현재가: {price:,} 원\n" if isinstance(price, (int, float)) else
        f"🟣 <b>S등급 시그널 감지!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>{name}</b> ({ticker})\n"
        f"💰 현재가: {price}\n"
    )

    msg = (
        f"🟣 <b>S등급 시그널 감지!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>{name}</b> ({ticker})\n"
        f"📊 타입: {signal_type}\n"
        f"⏱ 타임프레임: {timeframe}분\n\n"
        f"💰 현재가: {price}\n"
        f"🛡 손절가(SL): {sl if sl else '없음'}\n"
        f"📐 손익비(RR): {rr if rr else '없음'}\n\n"
        f"🎯 확신등급: <b>{conviction}</b> | 점수: {score}\n"
        f"📝 설명: {desc}\n"
        f"🤖 AI: {ai_summary}\n\n"
        f"📈 시장: {market}\n"
        f"⚡ 시그널: {signal}\n"
        f"🔋 에너지: {energy} | EMA거리: {ema1_dist}\n"
        f"🕯 캔들: {candle_type} (강도: {candle_strength})\n"
        f"📏 EMA터치: {ema_touch} | 배열: {ema_align}\n\n"
        f"🕐 수신: {now}"
    )

    return msg


# ──────────────────────────────────────────────
# Webhook 엔드포인트
# ──────────────────────────────────────────────
@app.post("/webhook")
async def receive_webhook(request: Request):
    """TradingView Webhook 수신"""
    try:
        body = await request.body()
        data = json.loads(body.decode("utf-8"))
    except Exception as e:
        logger.error(f"JSON 파싱 에러: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # 선택: 시크릿 키 검증
    if WEBHOOK_SECRET:
        secret = request.headers.get("X-Webhook-Secret", "")
        if secret != WEBHOOK_SECRET:
            logger.warning("촅즰 실패: 잘못된 시크릿 키")
            raise HTTPException(status_code=401, detail="Unauthorized")

    # 수신 로그
    ticker = data.get("ticker", "unknown")
    conviction = data.get("conviction", "?")
    action = data.get("action", "?")
    logger.info(f"[수신] {ticker} | conviction={conviction} | action={action}")

    # S등급 필터링
    if is_s_grade_buy(data):
        logger.info(f"✅ [S등급 매수] {data.get('name')} ({ticker})")
        message = format_telegram_message(data)
        await send_telegram(message)
        return JSONResponse({"status": "signal_sent", "ticker": ticker})
    else:
        logger.info(f"⏭ [스킵] {ticker} (conviction={conviction}, action={action})")
        return JSONResponse({"status": "filtered", "ticker": ticker})


@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/")
async def root():
    return {"message": "Lazy Alpha Signal Filter 서버 가동 중"}

"""
Lazy Alpha Indicator - 시그널 텔레그램 알림 서버
TradingView Webhook -> 필터링 -> Telegram 알림
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv
from sectors import is_in_allowed_sectors, get_stock_name, get_sector

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

KST = timezone(timedelta(hours=9))

MARKET_OPEN_ONLY = os.getenv("MARKET_OPEN_ONLY", "true").lower() == "true"
ALLOWED_START = (9, 0)    # 09:00
ALLOWED_END   = (15, 30)  # 15:30


def is_market_open_time():
    if not MARKET_OPEN_ONLY:
        return True
    now_kst = datetime.now(KST)
    m = now_kst.hour * 60 + now_kst.minute
    return (ALLOWED_START[0]*60+ALLOWED_START[1]) <= m <= (ALLOWED_END[0]*60+ALLOWED_END[1])


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)
app = FastAPI(title="Lazy Alpha Signal Filter")


async def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"텔레그램 에러: {e}")
        return False


BUY_KEYWORDS = ["buy", "매수", "진입", "돌파", "breakout", "rebreak", "pullback", "추매", "셋업"]


def is_valid_buy_signal(data: dict) -> bool:
    exchange = str(data.get("exchange", "")).strip().upper()
    ticker = str(data.get("ticker", "")).strip()
    action = str(data.get("action", "")).strip().upper()
    signal = str(data.get("signal", "")).strip().lower()
    if exchange != "KRX":
        return False
    if not is_in_allowed_sectors(ticker):
        logger.info(f"[필터링] {ticker} - 에너지/소부장 외 제외")
        return False
    if action and action not in ("BUY", ""):
        return False
    if signal and not any(kw in signal for kw in BUY_KEYWORDS):
        logger.info(f"[필터링] {ticker} - 매수 아닌 신호: {signal}")
        return False
    return True


def format_signal_message(data: dict) -> str:
    ticker = data.get("ticker", "?")
    stock_name = get_stock_name(ticker) or ticker
    sector = get_sector(ticker)
    signal = data.get("signal", "신호 발생")
    action = data.get("action", "")
    conviction = data.get("conviction", "")
    score = data.get("score", "")
    price = data.get("price", "")
    now = datetime.now().strftime("%m/%d %H:%M")
    grade_emoji = "🟣" if str(conviction).upper() == "S" else "🟢"
    sector_emoji = "⚡" if sector == "에너지" else "🔩"
    parts = [
        f"{grade_emoji} <b>{stock_name}</b> ({ticker})",
        f"{sector_emoji} 섹터: {sector}",
        "━━━━━━━━━━━━━━",
        f"📊 신호: <b>{signal}</b>",
    ]
    if action:
        parts.append(f"📌 방향: {action}")
    if conviction:
        conv_line = f"🎯 등급: <b>{conviction}</b>"
        if score:
            conv_line += f" | 점수: {score}"
        parts.append(conv_line)
    if price:
        parts.append(f"💰 현재가: {price}")
    parts.append(f"🕐 {now}")
    return "\n".join(parts)


def format_debug_message(data: dict, raw_text: str) -> str:
    now = datetime.now().strftime("%m/%d %H:%M:%S")
    ticker = data.get("ticker", "?") if isinstance(data, dict) else "?"
    lines = [
        "🔍 <b>[DEBUG] 웹훅 수신</b>",
        f"🕐 {now} | ticker: {ticker}",
        "━━━━━━━━━━━━━━",
        f"<code>{raw_text[:800]}</code>",
    ]
    return "\n".join(lines)


@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        body = await request.body()
        raw_text = body.decode("utf-8")
        logger.info(f"[RAW] {raw_text}")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Bad request")
    try:
        data = json.loads(raw_text)
    except Exception:
        data = {"raw": raw_text}
    ticker = data.get("ticker", "unknown") if isinstance(data, dict) else "unknown"
    now_kst = datetime.now(KST)
    logger.info(f"[수신] ticker={ticker} | KST={now_kst.strftime('%H:%M')}")
    if not is_market_open_time():
        now_str = now_kst.strftime("%H:%M")
        return JSONResponse({"status": "outside_hours", "ticker": ticker, "kst": now_str})
    if DEBUG_MODE:
        await send_telegram(format_debug_message(data, raw_text))
        return JSONResponse({"status": "debug_sent", "ticker": ticker})
    if isinstance(data, dict) and is_valid_buy_signal(data):
        await send_telegram(format_signal_message(data))
        return JSONResponse({"status": "signal_sent", "ticker": ticker})
    return JSONResponse({"status": "filtered", "ticker": ticker})


@app.get("/health")
async def health_check():
    return {"status": "ok", "debug_mode": DEBUG_MODE, "time": datetime.now().isoformat()}

@app.get("/")
async def root():
    return {"message": "Lazy Alpha Signal Filter 서버 가동 중", "debug": DEBUG_MODE}


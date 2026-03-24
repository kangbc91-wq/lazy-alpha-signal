"""
Lazy Alpha Indicator - 시그널 텔레그램 알림 서버
TradingView Webhook → 필터링 → Telegram 알림
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv
from kospi100 import is_in_top100, get_stock_name

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

KST = timezone(timedelta(hours=9))
MARKET_OPEN_ONLY = os.getenv("MARKET_OPEN_ONLY", "true").lower() == "true"
ALLOWED_START = (9, 0)
ALLOWED_END   = (9, 30)

def is_market_open_time() -> bool:
    if not MARKET_OPEN_ONLY:
        return True
    now_kst = datetime.now(KST)
    now_minutes = now_kst.hour * 60 + now_kst.minute
    return (ALLOWED_START[0]*60+ALLOWED_START[1]) <= now_minutes <= (ALLOWED_END[0]*60+ALLOWED_END[1])

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
    if exchange != "KRX": return False
    if not is_in_top100(ticker): return False
    if action and action not in ("BUY", ""): return False
    if signal and not any(kw in signal for kw in BUY_KEYWORDS): return False
    return True

def format_signal_message(data: dict) -> str:
    ticker = data.get("ticker", "?")
    stock_name = get_stock_name(ticker) or data.get("name", ticker)
    signal = data.get("signal", data.get("signal_name", "신호 발생"))
    action = data.get("action", "")
    conviction = data.get("conviction", "")
    score = data.get("score", "")
    price = data.get("price", "")
    now_kst = datetime.now(KST).strftime("%m/%d %H:%M")
    grade_emoji = "\U0001f7e3" if str(conviction).upper() == "S" else "\U0001f7e2"
    msg = f"{grade_emoji} <b>{stock_name}</b> ({ticker})\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
    msg += f"\U0001f4ca \uc2e0\ud638: <b>{signal}</b>\n"
    if action: msg += f"\U0001f4cc \ubc29\ud5a5: {action}\n"
    if conviction:
        msg += f"\U0001f3af \ub4f1\uae09: <b>{conviction}</b>"
        if score: msg += f" | \uc810\uc218: {score}"
        msg += "\n"
    if price: msg += f"\U0001f4b0 \ud604\uc7ac\uac00: {price}\n"
    msg += f"\U0001f550 {now_kst} (KST)"
    return msg

def format_debug_message(data, raw_text: str) -> str:
    now_kst = datetime.now(KST).strftime("%m/%d %H:%M:%S")
    ticker = data.get("ticker", "?") if isinstance(data, dict) else "?"
    preview = raw_text[:600].replace("<", "&lt;").replace(">", "&gt;")
    return f"\U0001f50d <b>[DEBUG] \uc6f9\ud6c5 \uc218\uc2e0</b>\n\U0001f550 {now_kst} KST | {ticker}\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n<code>{preview}</code>"

@app.post("/webhook")
async def receive_webhook(request: Request):
    try:
        body = await request.body()
        raw_text = body.decode("utf-8")
    except:
        raise HTTPException(status_code=400, detail="Bad request")

    try:
        data = json.loads(raw_text)
    except:
        data = {"raw": raw_text}

    ticker = data.get("ticker", "unknown") if isinstance(data, dict) else "unknown"
    now_kst = datetime.now(KST)
    logger.info(f"[수신] ticker={ticker} | KST={now_kst.strftime('%H:%M')}")

    if not is_market_open_time():
        now_str = now_kst.strftime("%H:%M")
        logger.info(f"[시간외] {ticker} | {now_str} → 무시")
        return JSONResponse({"status": "outside_hours", "ticker": ticker, "kst": now_str})

    if DEBUG_MODE:
        await send_telegram(format_debug_message(data, raw_text))
        return JSONResponse({"status": "debug_sent", "ticker": ticker})

    if isinstance(data, dict) and is_valid_buy_signal(data):
        await send_telegram(format_signal_message(data))
        return JSONResponse({"status": "signal_sent", "ticker": ticker})
    else:
        return JSONResponse({"status": "filtered", "ticker": ticker})

@app.get("/health")
async def health_check():
    now_kst = datetime.now(KST)
    return {"status": "ok", "debug_mode": DEBUG_MODE, "market_open_only": MARKET_OPEN_ONLY,
            "allowed_time": f"{ALLOWED_START[0]:02d}:{ALLOWED_START[1]:02d}~{ALLOWED_END[0]:02d}:{ALLOWED_END[1]:02d} KST",
            "current_kst": now_kst.strftime("%H:%M"), "in_window": is_market_open_time()}

@app.get("/")
async def root():
    return {"message": "Lazy Alpha Signal Filter", "debug": DEBUG_MODE, "market_open_only": MARKET_OPEN_ONLY}

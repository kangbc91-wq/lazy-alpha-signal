"""
에너지 및 소부장(소재/부품/장비) 섹터 종목 리스트
"""

# 에너지 섹터
ENERGY: dict[str, str] = {
    "015760": "한국전력",
    "096770": "SK이노베이션",
    "036460": "한국가스공사",
    "010950": "S-Oil",
    "078930": "GS",
    "010060": "OCI홀딩스",
    "003600": "SK케미칼",
    "034020": "두산에너빌리티",
}

# 소부장 섹터 (소재/부품/장비)
SOBUGJANG: dict[str, str] = {
    # 소재
    "005490": "POSCO홀딩스",
    "010130": "고려아연",
    "051910": "LG화학",
    "004000": "롯데케미칼",
    "002380": "KCC",
    "011780": "금호석유",
    "011790": "SKC",
    "003670": "포스코퓨처엠",
    # 부품
    "009150": "삼성전기",
    "011070": "LG이노텍",
    "005850": "에스엘",
    # 장비
    "267260": "HD현대일렉트릭",
    "241560": "두산밥캣",
    "042670": "HD현대인프라코어",
    "009540": "HD한국조선해양",
}

ALLOWED_TICKERS: dict[str, str] = {**ENERGY, **SOBUGJANG}


def is_in_allowed_sectors(ticker: str) -> bool:
    code = ticker.strip().lstrip("A")
    return code in ALLOWED_TICKERS


def get_stock_name(ticker: str) -> str | None:
    code = ticker.strip().lstrip("A")
    return ALLOWED_TICKERS.get(code)


def get_sector(ticker: str) -> str:
    code = ticker.strip().lstrip("A")
    if code in ENERGY:
        return "에너지"
    if code in SOBUGJANG:
        return "소부장"
    return "기타"

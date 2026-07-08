import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

DATA_SOURCE = "akshare"

CACHE_DAYS = 120

MA_SHORT = 5
MA_LONG = 20
BOLL_PERIOD = 20
BOLL_STD = 2

TOP_N = 10

FACTOR_WEIGHTS = {
    "momentum": 0.3,
    "valuation": 0.3,
    "volatility": 0.2,
    "roe": 0.2,
}

ROE_THRESHOLD = 8.0

WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.csv")

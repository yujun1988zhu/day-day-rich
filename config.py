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

# ── 新评分因子权重 ──
# 趋势强度: 基于60日动量 + 20日/60日趋势一致性 + 过热惩罚
# 动量加速: 近期动量相对长期动量的加速度(捕捉动量拐点)
# 估值合理: PE/PB 处于合理区间得高分，极端值扣分
# 基本面质量: ROE 绝对水平非线性评分
FACTOR_WEIGHTS = {
    "trend": 0.35,
    "momentum_accel": 0.25,
    "valuation": 0.20,
    "fundamental": 0.20,
}

ROE_THRESHOLD = 8.0

WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.csv")

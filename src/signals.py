import pandas as pd
import numpy as np
from config import MA_SHORT, MA_LONG, BOLL_PERIOD, BOLL_STD


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算均线和布林带指标"""
    df = df.copy()
    df["ma_short"] = df["close"].rolling(window=MA_SHORT).mean()
    df["ma_long"] = df["close"].rolling(window=MA_LONG).mean()

    df["boll_mid"] = df["close"].rolling(window=BOLL_PERIOD).mean()
    df["boll_std"] = df["close"].rolling(window=BOLL_PERIOD).std()
    df["boll_upper"] = df["boll_mid"] + BOLL_STD * df["boll_std"]
    df["boll_lower"] = df["boll_mid"] - BOLL_STD * df["boll_std"]

    return df


def detect_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    检测金叉/死叉/突破信号
    
    买入信号(B点):
        - 5日均线上穿20日均线(金叉) 且 收盘价突破布林带上轨 -> "B：突破建仓"
        - 仅金叉 -> "B：金叉建仓"
    
    卖出信号(S点):
        - 5日均线下穿20日均线(死叉) -> "S：死叉离场"
        - 股价跌破布林带下轨 -> "S：跌破下轨预警"
    """
    df = compute_indicators(df)
    df = df.dropna(subset=["ma_short", "ma_long", "boll_upper"]).copy()

    df["signal"] = ""
    df["signal_text"] = ""

    for i in range(1, len(df)):
        ma_short_prev = df["ma_short"].iloc[i - 1]
        ma_long_prev = df["ma_long"].iloc[i - 1]
        ma_short_curr = df["ma_short"].iloc[i]
        ma_long_curr = df["ma_long"].iloc[i]
        close_curr = df["close"].iloc[i]
        upper_curr = df["boll_upper"].iloc[i]
        lower_curr = df["boll_lower"].iloc[i]

        # 判断金叉和死叉
        golden_cross = (ma_short_prev <= ma_long_prev) and (ma_short_curr > ma_long_curr)
        death_cross = (ma_short_prev >= ma_long_prev) and (ma_short_curr < ma_long_curr)
        
        # 判断突破
        break_upper = close_curr > upper_curr
        break_lower = close_curr < lower_curr

        # 信号判定优先级
        if golden_cross and break_upper:
            df.iloc[i, df.columns.get_loc("signal")] = "BUY"
            df.iloc[i, df.columns.get_loc("signal_text")] = "B：突破建仓"
        elif golden_cross:
            df.iloc[i, df.columns.get_loc("signal")] = "BUY"
            df.iloc[i, df.columns.get_loc("signal_text")] = "B：金叉建仓"
        elif death_cross:
            df.iloc[i, df.columns.get_loc("signal")] = "SELL"
            df.iloc[i, df.columns.get_loc("signal_text")] = "S：死叉离场"
        elif break_lower:
            df.iloc[i, df.columns.get_loc("signal")] = "SELL"
            df.iloc[i, df.columns.get_loc("signal_text")] = "S：跌破下轨预警"

    return df


def get_latest_signal(df: pd.DataFrame) -> dict:
    """获取最新一根K线的信号状态"""
    df = detect_signals(df)
    if df.empty:
        return {
            "signal": "HOLD",
            "text": "数据不足",
            "close": 0,
            "ma_short": 0,
            "ma_long": 0,
            "boll_upper": 0,
            "boll_lower": 0,
            "date": ""
        }
    last = df.iloc[-1]
    return {
        "signal": last["signal"] if last["signal"] else "HOLD",
        "text": last["signal_text"] if last["signal_text"] else "无操作",
        "date": str(last["date"]),
        "close": round(last["close"], 2),
        "ma_short": round(last["ma_short"], 2),
        "ma_long": round(last["ma_long"], 2),
        "boll_upper": round(last["boll_upper"], 2),
        "boll_lower": round(last["boll_lower"], 2),
    }

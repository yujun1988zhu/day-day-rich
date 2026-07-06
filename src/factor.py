import pandas as pd
import numpy as np
from config import FACTOR_WEIGHTS, ROE_THRESHOLD, TOP_N


def scan_universe(stock_list: pd.DataFrame, roe_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    全市场扫描，基于行情快照数据计算综合得分，返回Top N
    
    参数:
        stock_list: 全市场行情快照（含 mom_20d, pb, amplitude, turnover 等字段）
        roe_df: ROE数据DataFrame (可选)
    
    返回:
        Top N 股票DataFrame
    """
    df = stock_list.copy()

    # 合并ROE数据
    if roe_df is not None and not roe_df.empty:
        df = df.merge(roe_df[["code", "roe"]], on="code", how="left")
        df["roe"] = df["roe"].fillna(0)
    else:
        df["roe"] = 0

    # 确保关键列为数值
    for col in ["mom_20d", "pb", "amplitude", "turnover", "roe"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 过滤无效数据
    df = df.dropna(subset=["mom_20d", "pb"])
    df = df[df["pb"] > 0]

    # === 因子计算 ===
    # 动量因子: 20日涨幅 (f24)，越高越好
    df["mom_rank"] = df["mom_20d"].rank(pct=True) * 100

    # 估值因子: PB，越低越好（反转排名）
    df["val_rank"] = df["pb"].rank(pct=True, ascending=False) * 100

    # 波动因子: 振幅(f7) + 换手率(f8) 综合，活跃度高者得分高
    # 如果没有振幅数据，用换手率代替
    if df["amplitude"].notna().sum() > len(df) * 0.5:
        df["vol_rank"] = df["amplitude"].rank(pct=True) * 100
    elif df["turnover"].notna().sum() > len(df) * 0.5:
        df["vol_rank"] = df["turnover"].rank(pct=True) * 100
    else:
        df["vol_rank"] = 50.0  # 无数据时给中间分

    # ROE因子: >8% 加分
    if df["roe"].sum() > 0:
        df["roe_rank"] = df["roe"].rank(pct=True) * 100
    else:
        df["roe_rank"] = 50.0

    # === 综合打分 ===
    df["score"] = (
        df["mom_rank"] * FACTOR_WEIGHTS["momentum"]
        + df["val_rank"] * FACTOR_WEIGHTS["valuation"]
        + df["vol_rank"] * FACTOR_WEIGHTS["volatility"]
        + df["roe_rank"] * FACTOR_WEIGHTS["roe"]
    )

    df = df.sort_values("score", ascending=False).head(TOP_N)

    result_cols = ["code", "name", "close", "pb", "roe", "mom_20d", "amplitude", "turnover", "score"]
    available_cols = [c for c in result_cols if c in df.columns]
    return df[available_cols].reset_index(drop=True)

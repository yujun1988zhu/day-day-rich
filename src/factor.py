import pandas as pd
import numpy as np
from config import FACTOR_WEIGHTS, ROE_THRESHOLD, TOP_N


# ── 工具函数 ──────────────────────────────────────────────

def _sigmoid_score(series, center, steepness=0.15):
    """Sigmoid 映射到 0-100 分，center 为 50 分对应的值"""
    x = (series - center) * steepness
    x = x.clip(-10, 10)
    return 100 / (1 + np.exp(-x))


def _zone_score(series, low, high, penalty_scale=50):
    """
    区间评分：值落在 [low, high] 内得高分，偏离越远分越低
    使用指数衰减，penalty_scale 控制衰减速度
    """
    score = pd.Series(100.0, index=series.index)
    below = series < low
    above = series > high
    score[below] = 100 * np.exp((series[below] - low) / penalty_scale)
    score[above] = 100 * np.exp((high - series[above]) / penalty_scale)
    return score.clip(0, 100)


# ── 各因子评分函数 ──────────────────────────────────────────

def _score_trend(df):
    """
    趋势强度评分 (0-100)
    ─────────────────────────────────
    核心思想：趋势一旦形成，倾向于延续，直到出现明确反转信号。

    组成：
      1. 主趋势 (60%)：60日动量 sigmoid 映射
         - 60日涨幅 > 0  → 处于上升趋势
         - 60日涨幅 > 10% → 趋势较强
         - 60日涨幅 > 20% → 趋势极强
      2. 趋势一致性 (30%)：20日与60日方向是否一致
         - 两者同正 → 上升趋势确认
         - 20d ≥ 60d×0.5 → 趋势在加速
      3. 过热惩罚 (10%)：20日涨幅 > 15% 时开始扣分
         - 短期涨幅过大，回调风险高
    """
    score = pd.Series(0.0, index=df.index)

    mom60 = df["mom_60d"].fillna(0)
    mom20 = df["mom_20d"].fillna(0)

    # 1) 主趋势：60日动量 sigmoid，center=0, steepness=0.12
    #    mom60=0 → 50分, mom60=10 → ~82分, mom60=-10 → ~18分
    main_trend = _sigmoid_score(mom60, center=0, steepness=0.12)

    # 2) 趋势一致性
    consistency = pd.Series(30.0, index=df.index)  # 基础分30
    both_positive = (mom20 > 0) & (mom60 > 0)
    accelerating = both_positive & (mom20 >= mom60 * 0.5)
    consistency[both_positive] = 65.0
    consistency[accelerating] = 100.0
    # 两者同负 → 惩罚
    both_negative = (mom20 < 0) & (mom60 < 0)
    consistency[both_negative] = 10.0

    # 3) 过热惩罚
    overheated = pd.Series(0.0, index=df.index)
    overheated[mom20 > 15] = np.minimum((mom20[mom20 > 15] - 15) * 5, 100)

    score = main_trend * 0.6 + consistency * 0.3 + (100 - overheated) * 0.1
    return score.clip(0, 100)


def _score_momentum_accel(df):
    """
    动量加速度评分 (0-100)
    ─────────────────────────────────
    核心思想：收益加速度比绝对收益更能预测未来走势。
    当近期动量开始超越长期趋势的平均水平时，是趋势启动/加速的信号。

    计算：
      - 预期月均动量 = mom_60d / 3（60日约3个月）
      - 加速度 = mom_20d - 预期月均动量
      - 加速度为正 → 动量在增强
      - 加速度为负 → 动量在衰减
    """
    mom60 = df["mom_60d"].fillna(0)
    mom20 = df["mom_20d"].fillna(0)

    # 预期月均动量（60日 ≈ 3个月）
    expected_monthly = mom60 / 3.0

    # 加速度 = 实际近期动量 - 预期
    accel = mom20 - expected_monthly

    # sigmoid 映射，center=0, steepness=0.3
    # accel=0 → 50分, accel=5 → ~87分, accel=-5 → ~13分
    return _sigmoid_score(accel, center=0, steepness=0.3)


def _score_valuation(df):
    """
    估值合理性评分 (0-100)
    ─────────────────────────────────
    核心思想：估值不是越低越好，而是处于"合理区间"最好。
    极低估值可能是价值陷阱，极高估值则是泡沫风险。

    PE 评分：
      - 合理区间: 10 ~ 35  → 满分
      - 偏离区间按指数衰减
    PB 评分：
      - 合理区间: 1 ~ 6   → 满分
      - 偏离区间按指数衰减
    综合：PE 权重 60% + PB 权重 40%
    """
    pe = df["pe"].fillna(0)
    pb = df["pb"].fillna(0)

    # PE 评分（排除负PE，即亏损股）
    pe_score = pd.Series(30.0, index=df.index)  # 默认低分（亏损或数据缺失）
    valid_pe = pe > 0
    if valid_pe.sum() > 0:
        pe_score[valid_pe] = _zone_score(pe[valid_pe], low=10, high=35, penalty_scale=20)

    # PB 评分
    valid_pb = pb > 0
    pb_score = pd.Series(30.0, index=df.index)
    if valid_pb.sum() > 0:
        pb_score[valid_pb] = _zone_score(pb[valid_pb], low=1, high=6, penalty_scale=2)

    return (pe_score * 0.6 + pb_score * 0.4).clip(0, 100)


def _score_fundamental(df):
    """
    基本面质量评分 (0-100)
    ─────────────────────────────────
    核心思想：ROE 是衡量企业盈利能力最直接的指标。
    使用非线性映射，高ROE的边际收益递减。

    ROE 映射：
      ROE < 0    → 接近 0 分
      ROE = 5%   → ~45 分
      ROE = 10%  → ~73 分
      ROE = 15%  → ~89 分
      ROE = 20%  → ~95 分
      ROE > 25%  → 接近 100 分
    """
    roe = df["roe"].fillna(0)
    # sigmoid 映射，center=8, steepness=0.25
    # ROE=8% → 50分, ROE=15% → ~89分, ROE=0% → ~12分
    return _sigmoid_score(roe, center=8, steepness=0.25).clip(0, 100)


# ── 主扫描函数 ──────────────────────────────────────────────

def scan_universe(stock_list: pd.DataFrame, roe_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    全市场扫描 - 基于多维因子模型计算综合得分，返回 Top N

    评分模型：
      综合得分 = 趋势强度 × 35%
               + 动量加速 × 25%
               + 估值合理 × 20%
               + 基本面质量 × 20%

    所有因子均使用绝对评分 (0-100)，而非相对排名，
    确保分数具有实际含义，不受截面股票数量影响。

    参数:
        stock_list: 全市场行情快照（含 mom_20d, mom_60d, pe, pb 等字段）
        roe_df: ROE数据DataFrame (可选)

    返回:
        Top N 股票DataFrame
    """
    df = stock_list.copy()

    # ── 合并 ROE 数据 ──
    if roe_df is not None and not roe_df.empty:
        df = df.merge(roe_df[["code", "roe"]], on="code", how="left")
        df["roe"] = df["roe"].fillna(0)
    else:
        df["roe"] = 0

    # ── 确保关键列为数值 ──
    for col in ["mom_20d", "mom_60d", "pe", "pb", "roe"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 基础过滤 ──
    df = df.dropna(subset=["mom_20d"])
    df = df[df["pb"].notna() & (df["pb"] > 0)]
    # 剔除 PE 为负（亏损股）的标的，估值因子无法评估
    df = df[df["pe"].notna() & (df["pe"] > 0)]

    if df.empty:
        return pd.DataFrame()

    # ── 计算各因子得分 ──
    df["f_trend"] = _score_trend(df)
    df["f_momentum_accel"] = _score_momentum_accel(df)
    df["f_valuation"] = _score_valuation(df)
    df["f_fundamental"] = _score_fundamental(df)

    # ── 综合得分 ──
    df["score"] = (
        df["f_trend"]        * FACTOR_WEIGHTS["trend"]
        + df["f_momentum_accel"] * FACTOR_WEIGHTS["momentum_accel"]
        + df["f_valuation"]      * FACTOR_WEIGHTS["valuation"]
        + df["f_fundamental"]    * FACTOR_WEIGHTS["fundamental"]
    )

    # ── 排序取 Top N ──
    df = df.sort_values("score", ascending=False).head(TOP_N)

    result_cols = [
        "code", "name", "close", "pb", "pe", "roe",
        "mom_20d", "mom_60d",
        "f_trend", "f_momentum_accel", "f_valuation", "f_fundamental",
        "score",
    ]
    available_cols = [c for c in result_cols if c in df.columns]
    return df[available_cols].reset_index(drop=True)

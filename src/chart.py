import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from src.signals import detect_signals

# 设置中文字体（Windows系统使用SimHei）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


def plot_kline(df: pd.DataFrame, code: str, name: str = ""):
    """
    绘制K线图 + 均线 + 布林带 + 信号标注
    
    参数:
        df: 股票日线数据
        code: 股票代码
        name: 股票名称
    
    返回:
        matplotlib Figure 对象
    """
    df = detect_signals(df)
    df = df.tail(60).copy()
    df.index = pd.DatetimeIndex(df["date"])

    buy_signals = df[df["signal"] == "BUY"]
    sell_signals = df[df["signal"] == "SELL"]

    # 基础指标图层
    ap = [
        mpf.make_addplot(df["ma_short"], color="#ff8c00", width=1.2, panel=0, label="MA5"),
        mpf.make_addplot(df["ma_long"], color="#4361ee", width=1.2, panel=0, label="MA20"),
        mpf.make_addplot(df["boll_upper"], color="#adb5bd", linestyle="--", width=0.7, panel=0),
        mpf.make_addplot(df["boll_lower"], color="#adb5bd", linestyle="--", width=0.7, panel=0),
        mpf.make_addplot(df["boll_mid"], color="#9b59b6", linestyle=":", width=0.6, panel=0),
    ]

    title = f"{code}  {name}" if name else code

    # 中国市场配色：红涨绿跌 + 现代风格
    mc = mpf.make_marketcolors(
        up="#e74c3c", down="#27ae60",
        edge={"up": "#e74c3c", "down": "#27ae60"},
        wick={"up": "#e74c3c", "down": "#27ae60"},
        volume={"up": "#e74c3c80", "down": "#27ae6080"},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle="-",
        gridcolor="#f0f0f0",
        facecolor="white",
        edgecolor="#dee2e6",
        figcolor="white",
        rc={
            "axes.labelcolor": "#333333",
            "xtick.color": "#666666",
            "ytick.color": "#666666",
            "font.size": 9,
            "font.family": "sans-serif",
            "font.sans-serif": ["SimHei", "Microsoft YaHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
        },
    )

    fig, axes = mpf.plot(
        df, type="candle", style=style,
        addplot=ap if ap else None,
        title=title,
        volume=True,
        figsize=(12, 7),
        returnfig=True,
    )

    # 标注买入信号
    for idx, row in buy_signals.iterrows():
        axes[0].annotate(
            row["signal_text"],
            xy=(row.name, row["low"] * 0.995),
            fontsize=7, color="#27ae60", fontweight="bold",
            ha="center", va="top",
            arrowprops=dict(arrowstyle="->", color="#27ae60", lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc="#e8f5e9", ec="#27ae60", alpha=0.9),
        )

    # 标注卖出信号
    for idx, row in sell_signals.iterrows():
        axes[0].annotate(
            row["signal_text"],
            xy=(row.name, row["high"] * 1.005),
            fontsize=7, color="#e74c3c", fontweight="bold",
            ha="center", va="bottom",
            arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc="#fff3f3", ec="#e74c3c", alpha=0.9),
        )

    return fig

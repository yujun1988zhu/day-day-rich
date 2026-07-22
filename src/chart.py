import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
from src.signals import detect_signals

# 设置中文字体（Windows系统使用SimHei）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 暗色终端主题配色
DARK_BG = "#0d1117"          # 主背景色
DARK_PANEL = "#161b22"       # 面板背景
DARK_GRID = "#1a2332"        # 网格线
DARK_TEXT = "#484f58"        # 文字颜色（暗淡）
DARK_TEXT_LIGHT = "#8b949e"  # 较亮文字

# K线颜色（低饱和度，不刺眼）
COLOR_UP = "#8b3a3a"         # 暗红（涨）
COLOR_DOWN = "#3a6b3a"       # 暗绿（跌）
COLOR_UP_VOL = "#8b3a3a60"   # 成交量半透明
COLOR_DOWN_VOL = "#3a6b3a60"

# 均线/布林带颜色（柔和）
COLOR_MA5 = "#d29922"        # 暗黄
COLOR_MA20 = "#58a6ff"       # 暗蓝
COLOR_BOLL = "#484f58"       # 灰色
COLOR_BOLL_MID = "#6e7681"   # 稍亮灰

# 信号颜色
COLOR_BUY_SIG = "#f85149"    # 买入信号
COLOR_SELL_SIG = "#3fb950"   # 卖出信号


def plot_kline(df: pd.DataFrame, code: str, name: str = ""):
    """
    绘制K线图 + 均线 + 布林带 + 信号标注（暗色终端监控风格）
    
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

    # 基础指标图层（暗色风格）
    ap = [
        mpf.make_addplot(df["ma_short"], color=COLOR_MA5, width=1.0, panel=0, label="MA5"),
        mpf.make_addplot(df["ma_long"], color=COLOR_MA20, width=1.0, panel=0, label="MA20"),
        mpf.make_addplot(df["boll_upper"], color=COLOR_BOLL, linestyle="--", width=0.6, panel=0),
        mpf.make_addplot(df["boll_lower"], color=COLOR_BOLL, linestyle="--", width=0.6, panel=0),
        mpf.make_addplot(df["boll_mid"], color=COLOR_BOLL_MID, linestyle=":", width=0.5, panel=0),
    ]

    title = f"{code}  {name}" if name else code

    # 暗色终端风格配色
    mc = mpf.make_marketcolors(
        up=COLOR_UP, down=COLOR_DOWN,
        edge={"up": COLOR_UP, "down": COLOR_DOWN},
        wick={"up": COLOR_UP, "down": COLOR_DOWN},
        volume={"up": COLOR_UP_VOL, "down": COLOR_DOWN_VOL},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle="-",
        gridcolor=DARK_GRID,
        facecolor=DARK_BG,
        edgecolor=DARK_GRID,
        figcolor=DARK_BG,
        rc={
            "axes.labelcolor": DARK_TEXT_LIGHT,
            "xtick.color": DARK_TEXT,
            "ytick.color": DARK_TEXT,
            "axes.facecolor": DARK_BG,
            "figure.facecolor": DARK_BG,
            "savefig.facecolor": DARK_BG,
            "font.size": 8,
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

    # 设置标题颜色
    axes[0].title.set_color(DARK_TEXT_LIGHT)
    axes[0].title.set_fontsize(10)

    # 标注买入信号（暗色风格，低调）
    for idx, row in buy_signals.iterrows():
        axes[0].annotate(
            row["signal_text"],
            xy=(row.name, row["low"] * 0.995),
            fontsize=7, color=COLOR_BUY_SIG, fontweight="bold",
            ha="center", va="top",
            arrowprops=dict(arrowstyle="->", color=COLOR_BUY_SIG, lw=1.0, alpha=0.7),
            bbox=dict(boxstyle="round,pad=0.3", fc=DARK_BG, ec=COLOR_BUY_SIG, alpha=0.8, lw=0.8),
        )

    # 标注卖出信号（暗色风格，低调）
    for idx, row in sell_signals.iterrows():
        axes[0].annotate(
            row["signal_text"],
            xy=(row.name, row["high"] * 1.005),
            fontsize=7, color=COLOR_SELL_SIG, fontweight="bold",
            ha="center", va="bottom",
            arrowprops=dict(arrowstyle="->", color=COLOR_SELL_SIG, lw=1.0, alpha=0.7),
            bbox=dict(boxstyle="round,pad=0.3", fc=DARK_BG, ec=COLOR_SELL_SIG, alpha=0.8, lw=0.8),
        )

    return fig


def plot_intraday(df: pd.DataFrame, code: str, name: str = ""):
    """
    绘制当日分时走势图（价格线 + 均价线 + 成交量柱）

    参数:
        df: 分时数据 (time, price, volume, avg_price, prev_close)
        code: 股票代码
        name: 股票名称

    返回:
        matplotlib Figure 对象
    """
    if df.empty:
        return None

    prev_close = df["prev_close"].iloc[0]

    # 将时间转为可绘图格式
    x_labels = df["time"].tolist()
    prices = df["price"].values
    avg_prices = df["avg_price"].values
    volumes = df["volume"].values
    x_pos = np.arange(len(x_labels))

    # 涨跌颜色
    up_color = "#8b3a3a"
    down_color = "#3a6b3a"
    colors = [up_color if p >= prev_close else down_color for p in prices]
    vol_colors = [up_color if p >= prev_close else down_color for p in prices]

    # 创建图表
    fig = plt.figure(figsize=(12, 5), facecolor=DARK_BG)
    gs = GridSpec(2, 1, height_ratios=[3, 1], hspace=0.08, figure=fig)

    # ── 上图: 价格线 ──
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor(DARK_BG)

    # 价格线
    ax1.plot(x_pos, prices, color="#58a6ff", linewidth=1.2, zorder=3)
    # 均价线
    ax1.plot(x_pos, avg_prices, color="#d29922", linewidth=0.8, linestyle="--", alpha=0.7, zorder=2, label="均价")
    # 昨收线
    ax1.axhline(y=prev_close, color="#484f58", linewidth=0.6, linestyle="-.", zorder=1)

    # 价格线下方填充
    ax1.fill_between(x_pos, prices, prev_close, where=(prices >= prev_close),
                     alpha=0.08, color=up_color, interpolate=True)
    ax1.fill_between(x_pos, prices, prev_close, where=(prices < prev_close),
                     alpha=0.08, color=down_color, interpolate=True)

    # 标注最新价
    if len(prices) > 0:
        last_price = prices[-1]
        last_x = x_pos[-1]
        price_color = up_color if last_price >= prev_close else down_color
        ax1.annotate(f"{last_price:.2f}", xy=(last_x, last_price),
                     fontsize=8, color=price_color, fontweight="bold",
                     xytext=(5, 0), textcoords="offset points", va="center")

    # Y轴
    ax1.set_ylabel("价格", color=DARK_TEXT, fontsize=8)
    ax1.tick_params(colors=DARK_TEXT, labelsize=7)
    ax1.grid(True, color=DARK_GRID, linewidth=0.3, alpha=0.5)
    for spine in ax1.spines.values():
        spine.set_color(DARK_GRID)

    # 右侧显示涨跌幅
    y_min, y_max = ax1.get_ylim()
    pct_change = (prices[-1] - prev_close) / prev_close * 100 if prev_close else 0
    ax1_right = ax1.twinx()
    ax1_right.set_ylim(y_min, y_max)
    ax1_right.tick_params(colors=DARK_TEXT, labelsize=7)
    pct_ticks = [(v - prev_close) / prev_close * 100 for v in ax1.get_yticks()]
    ax1_right.set_yticks(ax1.get_yticks())
    ax1_right.set_yticklabels([f"{p:+.2f}%" for p in pct_ticks])
    for spine in ax1_right.spines.values():
        spine.set_color(DARK_GRID)

    # 标题
    title = f"{code}  {name}  分时走势" if name else f"{code}  分时走势"
    ax1.set_title(title, color=DARK_TEXT_LIGHT, fontsize=10, pad=8, loc="left")

    # 隐藏x轴标签（下图显示）
    ax1.tick_params(axis="x", labelbottom=False)

    # ── 下图: 成交量 ──
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.set_facecolor(DARK_BG)

    ax2.bar(x_pos, volumes, color=vol_colors, width=0.8, alpha=0.6)
    ax2.set_ylabel("成交量", color=DARK_TEXT, fontsize=8)
    ax2.tick_params(colors=DARK_TEXT, labelsize=7)
    ax2.grid(True, color=DARK_GRID, linewidth=0.3, alpha=0.5)
    for spine in ax2.spines.values():
        spine.set_color(DARK_GRID)

    # X轴时间标签（每隔一段显示）
    step = max(1, len(x_labels) // 8)
    tick_positions = list(range(0, len(x_labels), step))
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels([x_labels[i] for i in tick_positions], rotation=0, fontsize=7)

    # 标记午间休市（11:30 - 13:00）
    lunch_start = None
    for i, t in enumerate(x_labels):
        if t == "11:30":
            lunch_start = i
        if t == "13:00" and lunch_start is not None:
            ax1.axvspan(lunch_start, i, alpha=0.15, color=DARK_BG, zorder=0)
            ax2.axvspan(lunch_start, i, alpha=0.15, color=DARK_BG, zorder=0)
            break

    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    return fig

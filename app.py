import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import time
import datetime
from config import DATA_DIR, TOP_N
from src.data_engine import get_stock_list, get_stock_daily, get_roe_data, is_trading_hours
from src.factor import scan_universe
from src.signals import get_latest_signal
from src.chart import plot_kline

# 自动刷新间隔（秒）
AUTO_REFRESH_INTERVAL = 300  # 5分钟

# 页面配置
st.set_page_config(page_title="AlphaScanner 极简选股预警器", layout="wide", page_icon="📈")

# ── 自定义样式 ──
st.markdown("""
<style>
/* ═══ 全局 ═══ */
html, body, [class*="css"] {
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}
.block-container { padding-top: 1.5rem; }

/* ═══ 侧边栏 ═══ */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0c29 0%, #1a1a3e 40%, #24243e 100%);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: #c8d0da;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 {
    color: #00d4ff;
}
/* 侧边栏 expander 内所有文字/表格 */
section[data-testid="stSidebar"] .stExpander,
section[data-testid="stSidebar"] .stExpander p,
section[data-testid="stSidebar"] .stExpander li,
section[data-testid="stSidebar"] .stExpander td,
section[data-testid="stSidebar"] .stExpander th,
section[data-testid="stSidebar"] .stExpander strong,
section[data-testid="stSidebar"] .stExpander span {
    color: #d0d8e4 !important;
}
section[data-testid="stSidebar"] .stExpander table {
    border-color: #3a3a5e !important;
}
section[data-testid="stSidebar"] .stExpander th {
    background: rgba(255,255,255,0.08) !important;
}
section[data-testid="stSidebar"] .stExpander td {
    border-color: #3a3a5e !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #3a3a5e;
}

/* ═══ 指标卡片 ═══ */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f5f7fa 0%, #eef1f5 100%);
    border-radius: 12px;
    padding: 14px 18px;
    border-left: 4px solid #4361ee;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    transition: transform 0.15s;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(67,97,238,0.15);
}
div[data-testid="stMetric"] label {
    color: #6c757d !important;
    font-size: 0.82em !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #1a1a2e !important;
    font-weight: 800 !important;
    font-size: 1.4em !important;
}

/* ═══ 信号卡片 ═══ */
.signal-card {
    border-radius: 12px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
}
.signal-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 5px; height: 100%;
}
.signal-buy {
    background: linear-gradient(135deg, #e8f5e9 0%, #d4edda 100%);
}
.signal-buy::before { background: #28a745; }
.signal-sell {
    background: linear-gradient(135deg, #fff3f3 0%, #fde2e2 100%);
}
.signal-sell::before { background: #dc3545; }
.signal-hold {
    background: linear-gradient(135deg, #f8f9fa 0%, #eef1f5 100%);
}
.signal-hold::before { background: #6c757d; }

.signal-icon {
    font-size: 1.8em;
    line-height: 1;
    margin-bottom: 4px;
}
.signal-text {
    font-size: 1.1em;
    font-weight: 700;
    margin-bottom: 2px;
}
.signal-sub {
    font-size: 0.85em;
    color: #666;
}

/* ═══ 表格 ═══ */
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
div[data-testid="stDataFrame"] tr:hover { background-color: #e8f0fe !important; }

/* ═══ 标题装饰 ═══ */
.section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}
.section-title .icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, #4361ee, #3a0ca3);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    color: white; font-size: 16px;
}
.section-title span {
    font-size: 1.1em;
    font-weight: 700;
    color: #1a1a2e;
}

/* ═══ 隐藏 footer ═══ */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

/* ═══ 数据卡片 ═══ */
.data-card {
    background: white;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    border: 1px solid #e8ecf1;
}
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ──
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 5px;">
        <div style="font-size:2em; font-weight:900; color:#00d4ff; letter-spacing:2px;">
            📈 AlphaScanner
        </div>
        <div style="font-size:0.85em; color:#7b8ca3; margin-top:2px;">
            极简选股预警器 &nbsp;·&nbsp; V1.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    action = st.button("🔄 刷新全市场数据", use_container_width=True, type="primary")

    # 交易状态指示
    _now = datetime.datetime.now()
    _is_trade_day = _now.weekday() < 5
    _t = _now.time()
    if not _is_trade_day:
        _status_text = "📴 今日休市"
        _status_color = "#8899aa"
    elif is_trading_hours():
        _status_text = "🟢 交易时段 · 实时数据"
        _status_color = "#28a745"
    elif _t < datetime.time(9, 30):
        _status_text = "🟡 盘前 · 昨日数据"
        _status_color = "#ffc107"
    elif datetime.time(11, 30) < _t < datetime.time(13, 0):
        _status_text = "☕ 午间休市 · 上午数据"
        _status_color = "#ffc107"
    else:
        _status_text = "🔵 已收盘 · 今日数据"
        _status_color = "#4361ee"

    st.markdown(
        f'<div style="text-align:center; padding:6px; background:rgba(255,255,255,0.06); '
        f'border-radius:8px; margin-bottom:4px;">'
        f'<span style="color:{_status_color}; font-size:0.85em; font-weight:600;">{_status_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 自动刷新倒计时（JavaScript 实时跳动）
    if "last_refresh_ts" not in st.session_state:
        st.session_state.last_refresh_ts = time.time()
    _ts_ms = int(st.session_state.last_refresh_ts * 1000)
    _interval_ms = AUTO_REFRESH_INTERVAL * 1000

    st.components.v1.html(
        f'''<div style="text-align:center; padding:8px; background:rgba(255,255,255,0.06);
            border-radius:8px; margin-top:4px;">
            <div style="color:#8899aa; font-size:0.82em;">⏱️ 自动刷新</div>
            <div id="cd" style="color:#00d4ff; font-weight:700; font-size:1.2em;
                 font-family:monospace; margin-top:2px;">--:--</div>
        </div>
        <script>
        (function() {{
            var target = {_ts_ms} + {_interval_ms};
            var el = document.getElementById("cd");
            function tick() {{
                var left = Math.max(0, target - Date.now());
                var m = Math.floor(left / 60000);
                var s = Math.floor((left % 60000) / 1000);
                el.textContent = m + ":" + (s < 10 ? "0" : "") + s;
                if (left > 0) requestAnimationFrame(tick);
            }}
            tick(); setInterval(tick, 1000);
        }})();
        </script>''',
        height=70,
    )

    st.markdown("---")

    # 侧边栏底部说明
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("📊 因子权重说明"):
        st.markdown("""
        | 因子 | 权重 | 逻辑 |
        |:---:|:---:|:---|
        | 🚀 动量 | **30%** | 20日涨幅，强者恒强 |
        | 💰 估值 | **30%** | PB 越低加分越多 |
        | 📉 波动 | **20%** | 振幅/换手率，剔除僵尸股 |
        | 📊 ROE | **20%** | 净资产收益率 >8% 加分 |
        """)
    with st.expander("📋 技术指标说明"):
        st.markdown("""
        **均线系统**
        - 🟠 **MA5** — 5日均线（短期趋势）
        - 🔵 **MA20** — 20日均线（中期趋势）
        
        **布林带**
        - 灰色虚线: ±2σ 上下轨
        - 紫色点线: 中轨
        
        **交易信号**
        - 🟢 绿色▲ 建仓信号（金叉/突破上轨）
        - 🔴 红色▼ 风险信号（死叉/跌破下轨）
        """)

# 文件路径
pool_file = os.path.join(DATA_DIR, "today_pool.csv")
stock_list_file = os.path.join(DATA_DIR, "stock_list.csv")
today_str = datetime.date.today().strftime("%Y%m%d")

# ── 自动刷新逻辑 ──
now = time.time()
if now - st.session_state.last_refresh_ts >= AUTO_REFRESH_INTERVAL:
    if os.path.exists(pool_file):
        os.remove(pool_file)
    st.session_state.last_refresh_ts = now
    st.rerun()

if action:
    for f in [pool_file, stock_list_file]:
        if os.path.exists(f):
            os.remove(f)
    st.session_state.last_refresh_ts = time.time()
    st.rerun()


def load_or_scan():
    """加载缓存或执行全市场扫描"""
    if os.path.exists(pool_file):
        cached_pool = pd.read_csv(pool_file, dtype={"code": str})
        if not cached_pool.empty and str(cached_pool.iloc[0].get("date")) == today_str:
            return cached_pool.drop(columns=["date"])

    # 进度条容器
    progress_bar = st.progress(0, text="正在初始化...")
    status_text = st.empty()

    def _progress(msg, pct):
        pct_norm = min(max(pct, 0), 100) / 100.0
        progress_bar.progress(pct_norm, text=msg)
        status_text.info(f"📡 {msg}")

    with st.spinner("正在获取全市场行情快照..."):
        stock_list = get_stock_list(progress_callback=_progress)

    progress_bar.progress(1.0, text="股票列表获取完成")

    if stock_list.empty:
        progress_bar.empty()
        status_text.empty()
        st.error("❌ 无法获取股票列表，请检查网络连接后重试")
        return pd.DataFrame()

    st.info(f"📡 共获取 **{len(stock_list)}** 只有效股票")

    with st.spinner("正在获取ROE财务数据..."):
        roe_df = get_roe_data()
    if not roe_df.empty:
        st.success(f"📊 ROE数据: {len(roe_df)} 条")
    else:
        st.warning("ROE数据暂为空，不影响基本功能")

    with st.spinner("正在计算多因子得分..."):
        progress_bar.empty()
        status_text.empty()
        pool = scan_universe(stock_list, roe_df)

    if not pool.empty:
        pool["date"] = today_str
        pool.to_csv(pool_file, index=False)
        pool = pool.drop(columns=["date"])
        st.success(f"✅ 扫描完成，已生成 Top {TOP_N} 候选池")
    else:
        st.warning("扫描结果为空，请检查网络或数据源")
    return pool


# ── 加载数据 ──
if not os.path.exists(pool_file):
    pool = load_or_scan()
else:
    pool = pd.read_csv(pool_file, dtype={"code": str})
    if not pool.empty and str(pool.iloc[0].get("date")) != today_str:
        pool = load_or_scan()
    elif not pool.empty:
        pool = pool.drop(columns=["date"])
    else:
        pool = load_or_scan()

# ══════════════════════════════════════════════
#  主页面
# ══════════════════════════════════════════════

today_display = datetime.date.today().strftime("%Y-%m-%d")
weekday_map = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
weekday = weekday_map[datetime.date.today().weekday()]

# ── 顶部标题栏 ──
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">'
        f'<div style="font-size:1.6em; font-weight:800; color:#1a1a2e;">🏆 今日候选池</div>'
        f'<div style="background:#4361ee; color:white; padding:3px 12px; border-radius:20px; '
        f'font-size:0.8em; font-weight:600;">{today_display} {weekday}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with header_col2:
    st.markdown(
        f'<div style="text-align:right; color:#888; font-size:0.85em; padding-top:8px;">'
        f'共 <b style="color:#4361ee; font-size:1.2em;">{len(pool)}</b> 只候选 &nbsp;|&nbsp; '
        f'Top {TOP_N}'
        f'</div>',
        unsafe_allow_html=True,
    )

if pool.empty:
    st.warning("暂无数据，请点击左侧「刷新全市场数据」按钮。")
    st.stop()

# ── 顶部指标卡片 ──
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("📋 候选股票", f"{len(pool)} 只")
with m2:
    top_score = pool["score"].max() if "score" in pool.columns else 0
    st.metric("🏅 最高得分", f"{top_score:.1f}")
with m3:
    avg_mom = pool["mom_20d"].mean() if "mom_20d" in pool.columns else 0
    mom_delta = round(avg_mom - 0, 2)
    st.metric("📈 平均20日涨幅", f"{avg_mom:.2f}%", delta=f"{mom_delta:+.2f}%")
with m4:
    avg_pb = pool["pb"].mean() if "pb" in pool.columns else 0
    st.metric("💰 平均PB", f"{avg_pb:.2f}")

st.markdown("<br>", unsafe_allow_html=True)

# ── 左右分栏 ──
col_left, col_right = st.columns([1, 2.5], gap="large")

# ── 左侧: 股票池 ──
with col_left:
    st.markdown(
        '<div class="section-title">'
        '<div class="icon">📋</div>'
        '<span>候选池排名</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    display_cols = ["code", "name", "score"]
    if "mom_20d" in pool.columns:
        display_cols.append("mom_20d")
    display_cols.append("pb")
    if "roe" in pool.columns:
        display_cols.append("roe")

    display_pool = pool[display_cols].copy()
    col_names = {"code": "代码", "name": "名称", "score": "得分",
                 "mom_20d": "20日涨幅%", "pb": "PB", "roe": "ROE"}
    display_pool.columns = [col_names.get(c, c) for c in display_cols]
    display_pool = display_pool.round(2)
    display_pool = display_pool.reset_index(drop=True)
    display_pool.index += 1

    selected_idx = st.dataframe(
        display_pool,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        height=620,
    )

    if selected_idx.selection.rows:
        sel_row = selected_idx.selection.rows[0]
        st.session_state.selected_row = sel_row

    _row = st.session_state.get("selected_row", 0)
    if _row < len(pool):
        selected_code = str(pool.iloc[_row]["code"]).zfill(6)
        selected_name = str(pool.iloc[_row]["name"])
    else:
        selected_code = str(pool.iloc[0]["code"]).zfill(6)
        selected_name = str(pool.iloc[0]["name"])

# ── 右侧: K线 + 信号 ──
with col_right:
    # 股票标题
    st.markdown(f"### {selected_name} **{selected_code}**")

    with st.spinner(f"正在加载 {selected_code} K线..."):
        daily = get_stock_daily(selected_code, days=120)

    if daily.empty or len(daily) < 30:
        st.error("数据不足，无法绘制K线图。")
    else:
        signal_info = get_latest_signal(daily)
        sig = signal_info["signal"]

        # 信号卡片 + 指标
        if sig == "BUY":
            css_class = "signal-buy"
            icon = "🟢"
            sig_label = "建仓信号"
            sig_color = "#28a745"
        elif sig == "SELL":
            css_class = "signal-sell"
            icon = "🔴"
            sig_label = "风险信号"
            sig_color = "#dc3545"
        else:
            css_class = "signal-hold"
            icon = "⚪"
            sig_label = "观望"
            sig_color = "#6c757d"

        sig_col, ind_col = st.columns([1.5, 3])

        with sig_col:
            st.markdown(
                f'<div class="signal-card {css_class}">'
                f'<div class="signal-icon">{icon}</div>'
                f'<div class="signal-text" style="color:{sig_color};">{sig_label}</div>'
                f'<div class="signal-sub">{signal_info["text"]}</div>'
                f'<div class="signal-sub" style="margin-top:6px;">'
                f'收盘价 &nbsp;<b style="font-size:1.2em; color:#1a1a2e;">{signal_info["close"]:.2f}</b>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with ind_col:
            ic1, ic2, ic3 = st.columns(3)
            with ic1:
                st.metric("🟠 MA5", f"{signal_info['ma_short']:.2f}")
            with ic2:
                st.metric("🔵 MA20", f"{signal_info['ma_long']:.2f}")
            with ic3:
                boll_width = signal_info['boll_upper'] - signal_info['boll_lower']
                st.metric("📏 布林带宽", f"{boll_width:.2f}")

        # K线图
        st.markdown("<br>", unsafe_allow_html=True)
        fig = plot_kline(daily, selected_code, selected_name)
        st.pyplot(fig)

        # 底部关键数据
        st.markdown("<br>", unsafe_allow_html=True)
        latest = daily.iloc[-1]
        d1, d2, d3, d4, d5 = st.columns(5)
        with d1:
            pct = latest.get("pct_change", 0)
            st.metric("涨跌幅", f"{pct:.2f}%", delta=f"{pct:.2f}%" if pct else None)
        with d2:
            st.metric("振幅", f"{latest.get('amplitude', 0):.2f}%")
        with d3:
            vol = latest.get('volume', 0)
            if vol >= 1e8:
                st.metric("成交量", f"{vol/1e8:.2f}亿")
            else:
                st.metric("成交量", f"{vol/1e4:.1f}万")
        with d4:
            st.metric("收盘价", f"{latest['close']:.2f}")
        with d5:
            turnover = latest.get('turnover', None)
            if turnover is not None and pd.notna(turnover):
                st.metric("换手率", f"{turnover:.2f}%")
            else:
                st.metric("换手率", "N/A")

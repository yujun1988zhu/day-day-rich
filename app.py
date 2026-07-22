import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import matplotlib.pyplot as plt
import os
import time
import datetime
from config import DATA_DIR, TOP_N
from src.data_engine import get_stock_list, get_stock_daily, get_roe_data, is_trading_hours, load_watchlist, add_to_watchlist, remove_from_watchlist, fetch_intraday_data
from src.factor import scan_universe
from src.signals import get_latest_signal
from src.chart import plot_kline, plot_intraday

# 自动刷新间隔（秒）
AUTO_REFRESH_INTERVAL = 300  # 5分钟
INTRADAY_REFRESH_INTERVAL = 10  # 分时图10秒刷新

# 页面配置
st.set_page_config(page_title="AlphaScanner // stock monitor", layout="wide", page_icon="▓")

# ── 自定义样式 ──
st.markdown("""
<style>
/* ═══ 全局 - 终端监控风格 ═══ */
html, body, [class*="css"] {
    font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
}
.block-container { padding-top: 1.5rem; }

/* ═══ 侧边栏 ═══ */
section[data-testid="stSidebar"] {
    background: #0a0e14;
    border-right: 1px solid #1a2332;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: #8b949e;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 {
    color: #00ff41;
}
section[data-testid="stSidebar"] .stExpander,
section[data-testid="stSidebar"] .stExpander p,
section[data-testid="stSidebar"] .stExpander li,
section[data-testid="stSidebar"] .stExpander td,
section[data-testid="stSidebar"] .stExpander th,
section[data-testid="stSidebar"] .stExpander strong,
section[data-testid="stSidebar"] .stExpander span {
    color: #8b949e !important;
}
section[data-testid="stSidebar"] .stExpander table {
    border-color: #1a2332 !important;
}
section[data-testid="stSidebar"] .stExpander th {
    background: rgba(0,255,65,0.05) !important;
}
section[data-testid="stSidebar"] .stExpander td {
    border-color: #1a2332 !important;
}
section[data-testid="stSidebar"] hr {
    border-color: #1a2332;
}

/* ═══ 指标卡片 - 终端风格 ═══ */
div[data-testid="stMetric"] {
    background: #161b22;
    border-radius: 4px;
    padding: 12px 16px;
    border-left: 3px solid #00ff41;
    border: 1px solid #1a2332;
    border-left: 3px solid #00ff41;
    box-shadow: none;
}
div[data-testid="stMetric"] label {
    color: #8b949e !important;
    font-size: 0.78em !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: 'Cascadia Code', 'Consolas', monospace !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #00ff41 !important;
    font-weight: 700 !important;
    font-size: 1.3em !important;
    font-family: 'Cascadia Code', 'Consolas', monospace !important;
}

/* ═══ 信号卡片 - 终端风格 ═══ */
.signal-card {
    border-radius: 4px;
    padding: 16px 18px;
    position: relative;
    border: 1px solid #1a2332;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
.signal-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
}
.signal-buy {
    background: #1a1010;
    border-color: #f8514966;
}
.signal-buy::before { background: #f85149; }
.signal-sell {
    background: #0d1a0d;
    border-color: #3fb95044;
}
.signal-sell::before { background: #3fb950; }
.signal-hold {
    background: #161b22;
    border-color: #1a2332;
}
.signal-hold::before { background: #484f58; }

.signal-icon {
    font-size: 1.5em;
    line-height: 1;
    margin-bottom: 4px;
}
.signal-text {
    font-size: 1.05em;
    font-weight: 700;
    margin-bottom: 2px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
.signal-sub {
    font-size: 0.82em;
    color: #8b949e;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}

/* ═══ 表格 ═══ */
div[data-testid="stDataFrame"] { border-radius: 4px; overflow: hidden; border: 1px solid #1a2332; }
div[data-testid="stDataFrame"] tr:hover { background-color: #1a2332 !important; }

/* ═══ 标题装饰 ═══ */
.section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}
.section-title .icon {
    width: 28px; height: 28px;
    background: #161b22;
    border: 1px solid #00ff41;
    border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    color: #00ff41; font-size: 14px;
}
.section-title span {
    font-size: 1.05em;
    font-weight: 600;
    color: #c9d1d9;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}

/* ═══ 隐藏 footer ═══ */
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }

/* ═══ 隐藏 Deploy 按钮 ═══ */
button[kind="header"] {
    display: none !important;
}
deploy-button, [data-testid="stDeployButton"] {
    display: none !important;
}

/* ═══ Tab ═══ */
.stTabs {
    margin-top: 20px;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: #161b22;
    border: 1px solid #1a2332;
    border-radius: 4px 4px 0 0;
    color: #8b949e;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
.stTabs [aria-selected="true"] {
    background: #0d1117 !important;
    border-bottom: 2px solid #00ff41 !important;
    color: #00ff41 !important;
}

/* ═══ 数据卡片 ═══ */
.data-card {
    background: #161b22;
    border-radius: 4px;
    padding: 16px;
    border: 1px solid #1a2332;
}

/* ═══ Spinner ═══ */
.stSpinner > div {
    border-top-color: #00ff41 !important;
}

/* ═══ 进度条 ═══ */
.stProgress > div > div {
    background-color: #00ff41 !important;
}
</style>
""", unsafe_allow_html=True)

# ── 侧边栏 ──
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 10px 0 5px;">
        <div style="font-size:0.75em; color:#484f58; font-family:monospace; letter-spacing:1px;">
            ┌─────────────────────────────┐
        </div>
        <div style="font-size:1.6em; font-weight:900; color:#00ff41; letter-spacing:3px; font-family:monospace;">
            ▓ AlphaScanner
        </div>
        <div style="font-size:0.72em; color:#484f58; margin-top:2px; font-family:monospace;">
            └── stock monitor v1.0 ──┘
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    action = st.button("▶ REFRESH_MARKET_DATA", use_container_width=True, type="primary")

    # 交易状态指示
    _now = datetime.datetime.now()
    _is_trade_day = _now.weekday() < 5
    _t = _now.time()
    if not _is_trade_day:
        _status_text = "[OFFLINE] MARKET_CLOSED"
        _status_color = "#484f58"
    elif is_trading_hours():
        _status_text = "[LIVE] TRADING_SESSION"
        _status_color = "#00ff41"
    elif _t < datetime.time(9, 30):
        _status_text = "[STANDBY] PRE_MARKET"
        _status_color = "#d29922"
    elif datetime.time(11, 30) < _t < datetime.time(13, 0):
        _status_text = "[PAUSED] LUNCH_BREAK"
        _status_color = "#d29922"
    else:
        _status_text = "[CLOSED] POST_MARKET"
        _status_color = "#58a6ff"

    st.markdown(
        f'<div style="text-align:center; padding:6px; background:#161b22; '
        f'border:1px solid #1a2332; border-radius:4px; margin-bottom:4px; font-family:monospace;">'
        f'<span style="color:{_status_color}; font-size:0.82em; font-weight:600; font-family:monospace;">{_status_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 自动刷新倒计时（JavaScript 实时跳动）
    if "last_refresh_ts" not in st.session_state:
        st.session_state.last_refresh_ts = time.time()
    _ts_ms = int(st.session_state.last_refresh_ts * 1000)
    _interval_ms = AUTO_REFRESH_INTERVAL * 1000

    st.components.v1.html(
        f'''<div style="text-align:center; padding:8px; background:#161b22;
            border:1px solid #1a2332; border-radius:4px; margin-top:4px; font-family:monospace;">
            <div style="color:#484f58; font-size:0.78em; font-family:monospace;">AUTO_REFRESH</div>
            <div id="cd" style="color:#00ff41; font-weight:700; font-size:1.2em;
                 font-family:'Cascadia Code','Consolas',monospace; margin-top:2px;">--:--</div>
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

    # ── 自选股管理 ──
    with st.expander("[+] WATCHLIST_MANAGER", expanded=True):
        _wl = load_watchlist()
        if not _wl.empty:
            st.markdown(f"当前 **{len(_wl)}** 只自选股：")
            for _, _row in _wl.iterrows():
                _c = str(_row["code"]).zfill(6)
                _n = str(_row["name"])
                _col1, _col2 = st.columns([4, 1])
                with _col1:
                    st.markdown(f"**{_n}** `{_c}`")
                with _col2:
                    if st.button("❌", key=f"rm_{_c}", help=f"移除 {_n}"):
                        remove_from_watchlist(_c)
                        st.rerun()
        else:
            st.info("暂无自选股，请在下方添加")

        st.markdown("")
        with st.form("add_watchlist_form"):
            new_code = st.text_input("STOCK_CODE", placeholder="e.g. 600519", max_chars=6)
            new_name = st.text_input("STOCK_NAME (optional)", placeholder="auto-detect if empty")
            if st.form_submit_button("[+] ADD_TO_WATCHLIST", use_container_width=True):
                if new_code and len(new_code.strip()) == 6:
                    ok = add_to_watchlist(new_code.strip(), new_name.strip())
                    if ok:
                        st.success(f"已添加 {new_code}")
                        st.rerun()
                    else:
                        st.warning("该股票已在自选列表中")
                else:
                    st.error("请输入6位有效股票代码")

    st.markdown("---")

    # 侧边栏底部说明
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("[i] FACTOR_WEIGHTS"):
        st.markdown("""
| FACTOR | WEIGHT | LOGIC |
|:---:|:---:|:---|
| TREND | **35%** | 60d趋势强度 + 20d/60d一致性 + 过热惩罚 |
| MOM_ACCEL | **25%** | 近期动量 vs 长期动量加速度 |
| VALUATION | **20%** | PE/PB合理区间评分(非越低越好) |
| FUNDAMENTAL | **20%** | ROE绝对水平非线性映射 |
        """)
    with st.expander("[i] TECH_INDICATORS"):
        st.markdown("""
**Moving Averages**
- `MA5` — 5-period (short-term)
- `MA20` — 20-period (mid-term)

**Bollinger Bands**
- Dashed lines: ±2σ upper/lower
- Dotted line: middle band

**Signals**
- RED ▲ BUY (golden cross / upper break)
- GREEN ▼ SELL (death cross / lower break)
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


# ── 分时走势图组件（10秒独立刷新） ──
@st.fragment(run_every=INTRADAY_REFRESH_INTERVAL)
def _intraday_pool(code: str, name: str, key_prefix: str):
    """分时走势图 fragment，每10秒自动刷新"""
    # 仅在交易日显示
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return
    t = now.time()
    # 盘前9:15到收盘后15:05之间显示
    if t < datetime.time(9, 15) or t > datetime.time(15, 5):
        return

    intraday_df = fetch_intraday_data(code)
    if intraday_df.empty:
        return

    # 分时图标题栏
    _now_str = now.strftime("%H:%M:%S")
    _last_price = intraday_df["price"].iloc[-1]
    _prev_close = intraday_df["prev_close"].iloc[0]
    _pct = (_last_price - _prev_close) / _prev_close * 100 if _prev_close else 0
    _pct_color = "#f85149" if _pct >= 0 else "#3fb950"

    st.markdown(
        f'<div style="display:flex; align-items:center; justify-content:space-between; '
        f'margin:12px 0 6px; padding:6px 12px; background:#161b22; border:1px solid #1a2332; '
        f'border-radius:4px; font-family:monospace;">'
        f'<div style="font-size:0.9em; font-weight:600; color:#c9d1d9;">'
        f'INTRADAY_TICK <span style="color:#484f58; font-size:0.8em;">({key_prefix})</span></div>'
        f'<div style="display:flex; gap:16px; align-items:center;">'
        f'<span style="color:{_pct_color}; font-weight:700; font-size:1.05em;">'
        f'{_last_price:.2f} &nbsp; {_pct:+.2f}%</span>'
        f'<span style="color:#484f58; font-size:0.75em;">更新: {_now_str}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    fig = plot_intraday(intraday_df, code, name)
    if fig:
        st.pyplot(fig)
        plt.close(fig)


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

# ── 主Tab切换 ──
tab_pool, tab_watch = st.tabs(["[ CANDIDATE_POOL ]", "[ WATCHLIST ]"])

# ══════════════════════════════════════════════
#  Tab 1: 今日候选池
# ══════════════════════════════════════════════
with tab_pool:
    # ── 顶部标题栏 ──
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:8px; font-family:monospace;">'
            f'<div style="font-size:1.4em; font-weight:700; color:#c9d1d9; font-family:monospace;">$ CANDIDATE_POOL</div>'
            f'<div style="background:#00ff41; color:#0d1117; padding:2px 10px; border-radius:2px; "'
            f'font-size:0.75em; font-weight:700; font-family:monospace;">{today_display} {weekday}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with header_col2:
        st.markdown(
            f'<div style="text-align:right; color:#484f58; font-size:0.82em; padding-top:8px; font-family:monospace;">'
            f'count: <b style="color:#00ff41; font-size:1.1em;">{len(pool)}</b> &nbsp;|&nbsp; '
            f'top_n={TOP_N}'
            f'</div>',
            unsafe_allow_html=True,
        )

    if pool.empty:
        st.warning("No data. Click [REFRESH_MARKET_DATA] in sidebar.")
    else:
        # 确保 TOP_N 生效（缓存可能包含旧数据）
        if len(pool) > TOP_N:
            pool = pool.head(TOP_N)

        # ── 顶部指标卡片 ──
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("CANDIDATES", f"{len(pool)}")
        with m2:
            top_score = pool["score"].max() if "score" in pool.columns else 0
            st.metric("MAX_SCORE", f"{top_score:.1f}")
        with m3:
            avg_trend = pool["f_trend"].mean() if "f_trend" in pool.columns else 0
            st.metric("AVG_TREND", f"{avg_trend:.1f}")
        with m4:
            avg_accel = pool["f_momentum_accel"].mean() if "f_momentum_accel" in pool.columns else 0
            st.metric("AVG_ACCEL", f"{avg_accel:.1f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # K线显示/隐藏切换
        if "show_kline_pool" not in st.session_state:
            st.session_state.show_kline_pool = True

        # ── 左右分栏（根据K线显示状态调整比例）──
        if st.session_state.show_kline_pool:
            col_left, col_right = st.columns([1.3, 2], gap="large")
        else:
            col_left, col_right = st.columns([1, 1], gap="large")

        # ── 左侧: 股票池 ──
        with col_left:
            st.markdown(
                '<div class="section-title">'
                '<div class="icon">#</div>'
                '<span>RANKING</span>'
                '</div>',
                unsafe_allow_html=True,
            )

            display_cols = ["code", "name", "score"]
            if "f_trend" in pool.columns:
                display_cols.extend(["f_trend", "f_momentum_accel"])
            elif "mom_20d" in pool.columns:
                display_cols.append("mom_20d")
            display_cols.append("pb")
            if "pe" in pool.columns:
                display_cols.append("pe")

            display_pool = pool[display_cols].copy()
            col_names = {
                "code": "CODE", "name": "NAME", "score": "SCORE",
                "f_trend": "TREND", "f_momentum_accel": "MOM_ACCEL",
                "f_valuation": "VALUE", "f_fundamental": "FUND",
                "mom_20d": "MOM_20D%", "pb": "PB", "pe": "PE", "roe": "ROE",
            }
            display_pool.columns = [col_names.get(c, c) for c in display_cols]
            display_pool = display_pool.round(2)
            display_pool = display_pool.reset_index(drop=True)
            display_pool.index += 1

            _list_height = 420 if st.session_state.show_kline_pool else 520
            selected_idx = st.dataframe(
                display_pool,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                height=_list_height,
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

        # ── 右侧: 信号 + K线 ──
        with col_right:
            # 股票标题 + K线切换按钮
            _title_col, _toggle_col = st.columns([3, 1])
            with _title_col:
                st.markdown(f"### {selected_name} **{selected_code}**")
            with _toggle_col:
                _btn_label = "[HIDE_KLINE]" if st.session_state.show_kline_pool else "[SHOW_KLINE]"
                if st.button(_btn_label, key="toggle_kline_pool", use_container_width=True):
                    st.session_state.show_kline_pool = not st.session_state.show_kline_pool
                    st.rerun()

            with st.spinner(f"Loading {selected_code} kline..."):
                daily = get_stock_daily(selected_code, days=120)

            if daily.empty or len(daily) < 30:
                st.error("Insufficient data for kline chart.")
            else:
                signal_info = get_latest_signal(daily)
                sig = signal_info["signal"]

                # 信号卡片 + 指标
                if sig == "BUY":
                    css_class = "signal-buy"
                    icon = "▲"  # Red for buy
                    sig_label = "BUY_SIGNAL"
                    sig_color = "#f85149"  # Red
                elif sig == "SELL":
                    css_class = "signal-sell"
                    icon = "▼"
                    sig_label = "SELL_SIGNAL"
                    sig_color = "#3fb950"  # Green
                else:
                    css_class = "signal-hold"
                    icon = "─"
                    sig_label = "HOLD"
                    sig_color = "#484f58"

                sig_col, ind_col = st.columns([1.5, 3])

                with sig_col:
                    # 构建建仓价格提示
                    _price_html = ""
                    if sig == "BUY" and signal_info.get("suggest_price"):
                        _price_html = (
                            f'<div style="margin-top:10px; padding-top:8px; border-top:1px dashed rgba(248,81,73,0.3); font-family:monospace;">'
                            f'<div style="font-size:0.78em; color:#f85149; font-weight:600;">ENTRY_PRICE</div>'
                            f'<div style="font-size:1.3em; font-weight:900; color:#f85149; margin:2px 0; font-family:monospace;">'
                            f'¥{signal_info["suggest_price"]:.2f}</div>'
                            f'<div style="font-size:0.72em; color:#484f58; margin-top:4px; font-family:monospace;">'
                            f'aggr: ¥{signal_info["aggressive_price"]:.2f} &nbsp;|&nbsp; '
                            f'conserv: ¥{signal_info["conservative_price"]:.2f}</div>'
                            f'</div>'
                        )
                    st.markdown(
                        f'<div class="signal-card {css_class}">'
                        f'<div class="signal-icon">{icon}</div>'
                        f'<div class="signal-text" style="color:{sig_color};">{sig_label}</div>'
                        f'<div class="signal-sub">{signal_info["text"]}</div>'
                        f'<div class="signal-sub" style="margin-top:6px; font-family:monospace;">'
                        f'close &nbsp;<b style="font-size:1.2em; color:#c9d1d9; font-family:monospace;">{signal_info["close"]:.2f}</b>'
                        f'</div>'
                        f'{_price_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                with ind_col:
                    ic1, ic2, ic3 = st.columns(3)
                    with ic1:
                        st.metric("MA5", f"{signal_info['ma_short']:.2f}")
                    with ic2:
                        st.metric("MA20", f"{signal_info['ma_long']:.2f}")
                    with ic3:
                        boll_width = signal_info['boll_upper'] - signal_info['boll_lower']
                        st.metric("BOLL_W", f"{boll_width:.2f}")

                # K线图（根据切换状态显示/隐藏）
                if st.session_state.show_kline_pool:
                    st.markdown("<br>", unsafe_allow_html=True)
                    fig = plot_kline(daily, selected_code, selected_name)
                    st.pyplot(fig)

                    # 底部关键数据
                    st.markdown("<br>", unsafe_allow_html=True)
                    latest = daily.iloc[-1]
                    d1, d2, d3, d4, d5 = st.columns(5)
                    with d1:
                        pct = latest.get("pct_change", 0)
                        st.metric("CHG%", f"{pct:.2f}%", delta=f"{pct:.2f}%" if pct else None)
                    with d2:
                        st.metric("AMPLITUDE", f"{latest.get('amplitude', 0):.2f}%")
                    with d3:
                        vol = latest.get('volume', 0)
                        if vol >= 1e8:
                            st.metric("VOLUME", f"{vol/1e8:.2f}B")
                        else:
                            st.metric("VOLUME", f"{vol/1e4:.1f}W")
                    with d4:
                        st.metric("CLOSE", f"{latest['close']:.2f}")
                    with d5:
                        turnover = latest.get('turnover', None)
                        if turnover is not None and pd.notna(turnover):
                            st.metric("TURNOVER", f"{turnover:.2f}%")
                        else:
                            st.metric("TURNOVER", "N/A")

                # ── 分时走势图（10秒独立刷新） ──
                _intraday_pool(code=selected_code, name=selected_name, key_prefix="pool")

# ══════════════════════════════════════════════
#  Tab 2: 自选股
# ══════════════════════════════════════════════
with tab_watch:
    watchlist = load_watchlist()

    # ── 顶部标题栏 ──
    wh_col1, wh_col2 = st.columns([3, 1])
    with wh_col1:
        st.markdown(
            f'<div style="display:flex; align-items:center; gap:12px; margin-bottom:8px; font-family:monospace;">'
            f'<div style="font-size:1.4em; font-weight:700; color:#c9d1d9; font-family:monospace;">$ WATCHLIST</div>'
            f'<div style="background:#d29922; color:#0d1117; padding:2px 10px; border-radius:2px; "'
            f'font-size:0.75em; font-weight:700; font-family:monospace;">{today_display} {weekday}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with wh_col2:
        st.markdown(
            f'<div style="text-align:right; color:#484f58; font-size:0.82em; padding-top:8px; font-family:monospace;">'
            f'count: <b style="color:#d29922; font-size:1.1em;">{len(watchlist)}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if watchlist.empty:
        st.info("No stocks in watchlist. Add via sidebar [WATCHLIST_MANAGER].")
    else:
        # K线显示/隐藏切换
        if "show_kline_watch" not in st.session_state:
            st.session_state.show_kline_watch = True

        # ── 左右分栏（根据K线显示状态调整比例）──
        if st.session_state.show_kline_watch:
            wcol_left, wcol_right = st.columns([1.3, 2], gap="large")
        else:
            wcol_left, wcol_right = st.columns([1, 1], gap="large")

        with wcol_left:
            st.markdown(
                '<div class="section-title">'
                '<div class="icon">#</div>'
                '<span>WATCHLIST</span>'
                '</div>',
                unsafe_allow_html=True,
            )

            # 构建展示表格
            watch_display = watchlist[["code", "name"]].copy()
            watch_display.columns = ["CODE", "NAME"]
            watch_display = watch_display.reset_index(drop=True)
            watch_display.index += 1

            _w_list_height = 420 if st.session_state.show_kline_watch else 520
            watch_idx = st.dataframe(
                watch_display,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                height=_w_list_height,
            )

            if watch_idx.selection.rows:
                st.session_state.watch_row = watch_idx.selection.rows[0]

            _wrow = st.session_state.get("watch_row", 0)
            if _wrow < len(watchlist):
                w_code = str(watchlist.iloc[_wrow]["code"]).zfill(6)
                w_name = str(watchlist.iloc[_wrow]["name"])
            else:
                w_code = str(watchlist.iloc[0]["code"]).zfill(6)
                w_name = str(watchlist.iloc[0]["name"])

        with wcol_right:
            # 股票标题 + K线切换按钮
            _w_title_col, _w_toggle_col = st.columns([3, 1])
            with _w_title_col:
                st.markdown(f"### {w_name} **{w_code}**")
            with _w_toggle_col:
                _w_btn_label = "[HIDE_KLINE]" if st.session_state.show_kline_watch else "[SHOW_KLINE]"
                if st.button(_w_btn_label, key="toggle_kline_watch", use_container_width=True):
                    st.session_state.show_kline_watch = not st.session_state.show_kline_watch
                    st.rerun()

            with st.spinner(f"Loading {w_code} kline..."):
                w_daily = get_stock_daily(w_code, days=120)

            if w_daily.empty or len(w_daily) < 30:
                st.error("Insufficient data for kline chart.")
            else:
                w_signal = get_latest_signal(w_daily)
                w_sig = w_signal["signal"]

                if w_sig == "BUY":
                    w_css = "signal-buy"
                    w_icon = "▲"
                    w_sig_label = "BUY_SIGNAL"
                    w_sig_color = "#f85149"
                elif w_sig == "SELL":
                    w_css = "signal-sell"
                    w_icon = "▼"
                    w_sig_label = "SELL_SIGNAL"
                    w_sig_color = "#3fb950"
                else:
                    w_css = "signal-hold"
                    w_icon = "─"
                    w_sig_label = "HOLD"
                    w_sig_color = "#484f58"

                w_sig_col, w_ind_col = st.columns([1.5, 3])

                with w_sig_col:
                    # 构建建仓价格提示
                    _w_price_html = ""
                    if w_sig == "BUY" and w_signal.get("suggest_price"):
                        _w_price_html = (
                            f'<div style="margin-top:10px; padding-top:8px; border-top:1px dashed rgba(248,81,73,0.3); font-family:monospace;">'
                            f'<div style="font-size:0.78em; color:#f85149; font-weight:600;">ENTRY_PRICE</div>'
                            f'<div style="font-size:1.3em; font-weight:900; color:#f85149; margin:2px 0; font-family:monospace;">'
                            f'¥{w_signal["suggest_price"]:.2f}</div>'
                            f'<div style="font-size:0.72em; color:#484f58; margin-top:4px; font-family:monospace;">'
                            f'aggr: ¥{w_signal["aggressive_price"]:.2f} &nbsp;|&nbsp; '
                            f'conserv: ¥{w_signal["conservative_price"]:.2f}</div>'
                            f'</div>'
                        )
                    st.markdown(
                        f'<div class="signal-card {w_css}">'
                        f'<div class="signal-icon">{w_icon}</div>'
                        f'<div class="signal-text" style="color:{w_sig_color};">{w_sig_label}</div>'
                        f'<div class="signal-sub">{w_signal["text"]}</div>'
                        f'<div class="signal-sub" style="margin-top:6px; font-family:monospace;">'
                        f'close &nbsp;<b style="font-size:1.2em; color:#c9d1d9; font-family:monospace;">{w_signal["close"]:.2f}</b>'
                        f'</div>'
                        f'{_w_price_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                with w_ind_col:
                    wic1, wic2, wic3 = st.columns(3)
                    with wic1:
                        st.metric("MA5", f"{w_signal['ma_short']:.2f}")
                    with wic2:
                        st.metric("MA20", f"{w_signal['ma_long']:.2f}")
                    with wic3:
                        w_boll_w = w_signal['boll_upper'] - w_signal['boll_lower']
                        st.metric("BOLL_W", f"{w_boll_w:.2f}")

                # K线图（根据切换状态显示/隐藏）
                if st.session_state.show_kline_watch:
                    st.markdown("<br>", unsafe_allow_html=True)
                    w_fig = plot_kline(w_daily, w_code, w_name)
                    st.pyplot(w_fig)

                    st.markdown("<br>", unsafe_allow_html=True)
                    w_latest = w_daily.iloc[-1]
                    wd1, wd2, wd3, wd4, wd5 = st.columns(5)
                    with wd1:
                        w_pct = w_latest.get("pct_change", 0)
                        st.metric("CHG%", f"{w_pct:.2f}%", delta=f"{w_pct:.2f}%" if w_pct else None)
                    with wd2:
                        st.metric("AMPLITUDE", f"{w_latest.get('amplitude', 0):.2f}%")
                    with wd3:
                        w_vol = w_latest.get('volume', 0)
                        if w_vol >= 1e8:
                            st.metric("VOLUME", f"{w_vol/1e8:.2f}B")
                        else:
                            st.metric("VOLUME", f"{w_vol/1e4:.1f}W")
                    with wd4:
                        st.metric("CLOSE", f"{w_latest['close']:.2f}")
                    with wd5:
                        w_turnover = w_latest.get('turnover', None)
                        if w_turnover is not None and pd.notna(w_turnover):
                            st.metric("TURNOVER", f"{w_turnover:.2f}%")
                        else:
                            st.metric("TURNOVER", "N/A")

                # ── 分时走势图（10秒独立刷新） ──
                _intraday_pool(code=w_code, name=w_name, key_prefix="watch")

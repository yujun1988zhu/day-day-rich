import os
import time
import json
import datetime
import urllib.request
import urllib.parse
import pandas as pd
from config import DATA_DIR, CACHE_DAYS

# 通用请求头（模拟浏览器）
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}


def ensure_data_dir():
    """确保数据目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)


def is_trading_hours() -> bool:
    """判断当前是否为A股交易时段（工作日 9:30-11:30, 13:00-15:00）
    注意: 不判断节假日，仅判断工作日+时间
    """
    now = datetime.datetime.now()
    # 周末不交易
    if now.weekday() >= 5:
        return False
    t = now.time()
    morning = (datetime.time(9, 30) <= t <= datetime.time(11, 30))
    afternoon = (datetime.time(13, 0) <= t <= datetime.time(15, 0))
    return morning or afternoon


def _get(url, params, timeout=20, max_retries=3):
    """
    使用urllib标准库发起GET请求，带重试。
    在Python 3.14下urllib比requests/urllib3更稳定可靠。
    """
    full_url = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(full_url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                # 尝试解压
                try:
                    import gzip
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
                return json.loads(raw.decode("utf-8"))
        except Exception as e:
            if attempt < max_retries - 1:
                wait = min(3 * (attempt + 1), 10)
                print(f"[WARN] 请求失败(第{attempt+1}次): {e}, {wait}秒后重试...")
                time.sleep(wait)
                continue
            raise e


def _code_to_symbol(code: str) -> str:
    """将6位股票代码转为腾讯API格式: sh600519 / sz000001"""
    code = str(code).zfill(6)
    if code.startswith("6"):
        return f"sh{code}"
    else:
        return f"sz{code}"


def _fetch_all_stock_codes() -> list:
    """从东方财富datacenter获取全A股代码列表（仅代码和名称）
    使用最新一期财报过滤，自动去重
    """
    # 确定最新报告期
    today = datetime.date.today()
    year, month = today.year, today.month
    if month >= 11:
        report_date = f"{year}-09-30"
    elif month >= 8:
        report_date = f"{year}-06-30"
    elif month >= 5:
        report_date = f"{year}-03-31"
    else:
        report_date = f"{year - 1}-09-30"

    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    seen_codes = set()
    all_codes = []
    page = 1
    page_size = 500

    while True:
        params = {
            "sortColumns": "SECURITY_CODE",
            "sortTypes": "1",
            "pageSize": page_size,
            "pageNumber": page,
            "reportName": "RPT_LICO_FN_CPD",
            "columns": "SECURITY_CODE,SECURITY_NAME_ABBR",
            "filter": f"(REPORTDATE='{report_date}')",
            "source": "WEB",
            "client": "WEB",
        }
        try:
            data = _get(url, params, timeout=20)
        except Exception as e:
            print(f"[WARN] 获取股票列表第{page}页失败: {e}")
            break
        if not data.get("result") or not data["result"].get("data"):
            break
        rows = data["result"]["data"]
        for row in rows:
            code = str(row.get("SECURITY_CODE", "")).zfill(6)
            if code in seen_codes:
                continue
            seen_codes.add(code)
            name = row.get("SECURITY_NAME_ABBR", "")
            all_codes.append({"code": code, "name": name})
        total = data["result"].get("count", 0)
        # 已获取足够或已无更多页
        if len(all_codes) >= total or page * page_size >= total:
            break
        page += 1
        time.sleep(0.2)

    print(f"[INFO] 获取到 {len(all_codes)} 只不重复股票（共翻{page}页）")
    return all_codes


def _parse_tencent_quote(line: str) -> dict | None:
    """解析腾讯行情API单条数据，返回标准化字典"""
    if "~" not in line:
        return None
    fields = line.split("~")
    if len(fields) < 77:
        return None
    try:
        code = fields[2]
        name = fields[1]
        close = float(fields[3]) if fields[3] else None
        if not close or close <= 0:
            return None
        pct_change = float(fields[32]) if fields[32] else None
        amplitude = float(fields[43]) if fields[43] else None
        turnover = float(fields[38]) if fields[38] else None
        pe = float(fields[39]) if fields[39] else None
        total_mv = float(fields[45]) if fields[45] else None   # 总市值(亿)
        circ_mv = float(fields[44]) if fields[44] else None    # 流通市值(亿)
        pb = float(fields[46]) if fields[46] else None
        mom_20d = float(fields[69]) if fields[69] else None    # 20日涨幅(%)
        mom_60d = float(fields[70]) if fields[70] else None    # 60日涨幅(%)
        ytd_return = float(fields[71]) if fields[71] else None # 年初至今涨幅(%)

        return {
            "code": code,
            "name": name,
            "close": close,
            "pct_change": pct_change,
            "amplitude": amplitude,
            "turnover": turnover,
            "pe": pe,
            "total_mv": total_mv * 1e8 if total_mv else None,   # 转为元
            "circ_mv": circ_mv * 1e8 if circ_mv else None,
            "pb": pb,
            "mom_20d": mom_20d,
            "mom_60d": mom_60d,
            "ytd_return": ytd_return,
        }
    except (ValueError, IndexError):
        return None


def _fetch_all_spot_pages(progress_callback=None):
    """获取全A股实时行情快照

    数据源: 东方财富datacenter(股票列表) + 腾讯财经API(实时行情)

    返回字段: code, name, close, pct_change, amplitude, turnover,
              pe, total_mv, circ_mv, pb, mom_20d, mom_60d, ytd_return
    """
    # 第一步: 从datacenter获取全A股代码列表
    print("[INFO] 正在获取全A股代码列表...")
    if progress_callback:
        progress_callback("正在获取股票列表...", 0)
    stock_info = _fetch_all_stock_codes()
    if not stock_info:
        return pd.DataFrame()

    # 预先剔除北交所(8开头)和新三板(4开头)
    stock_info = [s for s in stock_info
                  if not s["code"].startswith("8") and not s["code"].startswith("4")]

    # 第二步: 分批从腾讯API获取实时行情（增大批量，减少请求次数）
    batch_size = 300  # 从80提升到300，大幅减少请求次数
    all_records = []
    total_batches = (len(stock_info) + batch_size - 1) // batch_size
    failed_batches = 0

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(stock_info))
        batch = stock_info[start:end]

        symbols = ",".join(_code_to_symbol(s["code"]) for s in batch)
        url = f"https://qt.gtimg.cn/q={symbols}"

        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("gbk")
            for line in raw.strip().split("\n"):
                record = _parse_tencent_quote(line)
                if record:
                    all_records.append(record)
        except Exception as e:
            failed_batches += 1
            print(f"[WARN] 腾讯行情批次{batch_idx+1}/{total_batches}请求失败: {e}")

        # 进度回调
        if progress_callback:
            pct = int((batch_idx + 1) / total_batches * 100)
            progress_callback(
                f"获取行情 {batch_idx+1}/{total_batches} 批 (已获取 {len(all_records)} 只)",
                pct,
            )

        # 页间延迟（缩短到0.1秒）
        if batch_idx < total_batches - 1:
            time.sleep(0.1)

    if failed_batches > 0:
        print(f"[WARN] 共 {failed_batches}/{total_batches} 批请求失败，返回已获取数据")

    return pd.DataFrame(all_records)


def get_stock_list(progress_callback=None) -> pd.DataFrame:
    """获取全A股股票列表（含行情快照字段），剔除ST、退市、北交所、停牌"""
    ensure_data_dir()
    cache_file = os.path.join(DATA_DIR, "stock_list.csv")
    today = datetime.date.today().strftime("%Y%m%d")

    if os.path.exists(cache_file):
        cached = pd.read_csv(cache_file, dtype={"code": str})
        if not cached.empty and str(cached.iloc[0].get("date")) == today:
            # 交易时段内不使用缓存，确保拿到实时数据
            if not is_trading_hours():
                return cached.drop(columns=["date"])

    df = _fetch_all_spot_pages(progress_callback=progress_callback)

    # 转为数值类型
    numeric_cols = ["close", "pb", "pe", "amplitude", "turnover", "mom_20d", "mom_60d", "ytd_return", "total_mv", "circ_mv"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 剔除ST、退市股
    df = df[~df["name"].str.contains("ST|退", na=False)]
    # 剔除北交所(8开头)和新三板(4开头)
    df = df[~df["code"].str.startswith("8")]
    df = df[~df["code"].str.startswith("4")]
    # 剔除停牌股（收盘价无效或为0）
    df = df[df["close"] > 0]
    # 剔除关键因子缺失的股票
    df = df[df["pb"].notna() & (df["pb"] > 0)]
    df = df[df["mom_20d"].notna()]

    df["date"] = today
    df.to_csv(cache_file, index=False)
    return df.drop(columns=["date"])


def get_roe_data() -> pd.DataFrame:
    """从业绩报表获取最新一期ROE数据（东方财富API）"""
    ensure_data_dir()
    cache_file = os.path.join(DATA_DIR, "roe_data.csv")
    today = datetime.date.today().strftime("%Y%m%d")

    if os.path.exists(cache_file):
        cached = pd.read_csv(cache_file, dtype={"code": str})
        if not cached.empty and str(cached.iloc[0].get("date")) == today:
            return cached.drop(columns=["date"])

    try:
        year = datetime.date.today().year
        month = datetime.date.today().month
        # 根据当前月份推算“最新已披露”的报告期
        # Q1(03-31): 4月底前披露  |  Q2(06-30): 8月底前披露
        # Q3(09-30): 10月底前披露 |  Q4(12-31): 次年4月底前披露
        if month >= 11:
            report_date = f"{year}-09-30"      # Q3已披露
        elif month >= 8:
            report_date = f"{year}-06-30"      # Q2已披露
        elif month >= 4:
            report_date = f"{year}-03-31"      # Q1已披露
        else:
            report_date = f"{year - 1}-09-30"  # 上年Q3

        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        all_rows = []
        page = 1
        page_size = 500

        while True:
            params = {
                "sortColumns": "NOTICE_DATE,SECURITY_CODE",
                "sortTypes": "-1,-1",
                "pageSize": page_size,
                "pageNumber": page,
                "reportName": "RPT_LICO_FN_CPD",
                "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,WEIGHTAVG_ROE",
                "filter": f'(REPORTDATE=\'{report_date}\')',
                "source": "WEB",
                "client": "WEB",
            }
            data = _get(url, params)
            if not data.get("result") or not data["result"].get("data"):
                break
            rows = data["result"]["data"]
            all_rows.extend(rows)
            if len(all_rows) >= data["result"]["count"]:
                break
            page += 1
            time.sleep(0.5)

        records = []
        for row in all_rows:
            records.append({
                "code": str(row.get("SECURITY_CODE", "")).zfill(6),
                "roe": row.get("WEIGHTAVG_ROE", None),
            })
        if not records:
            return pd.DataFrame(columns=["code", "roe"])
        df = pd.DataFrame(records)
        df["roe"] = pd.to_numeric(df["roe"], errors="coerce")
        if not df.empty:
            df["date"] = today
            df.to_csv(cache_file, index=False)
            return df.drop(columns=["date"])
        return df
    except Exception as e:
        print(f"[WARN] 获取ROE数据失败: {e}")
        return pd.DataFrame(columns=["code", "roe"])


def _fetch_realtime_quote(code: str) -> dict | None:
    """获取单只股票实时行情快照，返回构造当日K线所需的字段"""
    symbol = _code_to_symbol(code)
    url = f"https://qt.gtimg.cn/q={symbol}"
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("gbk")
        if "~" not in raw:
            return None
        fields = raw.split("~")
        if len(fields) < 45:
            return None
        date_str = fields[30][:8]  # e.g. "20260706"
        o = float(fields[5]) if fields[5] else 0
        c = float(fields[3]) if fields[3] else 0
        h = float(fields[33]) if fields[33] else 0
        l = float(fields[34]) if fields[34] else 0
        vol = float(fields[36]) if fields[36] else 0  # 成交量(手)，与K线API保持一致
        prev_close = float(fields[4]) if fields[4] else 0
        if not (o and c and h and l and prev_close):
            return None
        pct_change = round((c - prev_close) / prev_close * 100, 2) if prev_close else 0
        amplitude = round((h - l) / prev_close * 100, 2) if prev_close else 0
        return {
            "date": date_str,
            "open": o, "close": c, "high": h, "low": l,
            "volume": vol, "amount": 0,
            "amplitude": amplitude,
            "pct_change": pct_change,
            "change": round(c - prev_close, 2),
            "turnover": 0,
        }
    except Exception as e:
        print(f"[WARN] 获取 {code} 实时行情失败: {e}")
        return None


def get_stock_daily(code: str, days: int = CACHE_DAYS) -> pd.DataFrame:
    """获取单只股票近N个交易日的日线数据(OHLCV)

    数据源: 腾讯财经API (web.ifzq.gtimg.cn)
    交易时段/收盘后至次日凌晨: 自动从实时行情API补充当日K线
    """
    ensure_data_dir()
    cache_file = os.path.join(DATA_DIR, f"daily_{code}.csv")
    today = datetime.date.today().strftime("%Y%m%d")

    # 交易时段内不使用缓存，确保拿到实时K线
    in_trading = is_trading_hours()
    if os.path.exists(cache_file) and not in_trading:
        cached = pd.read_csv(cache_file, parse_dates=["date"])
        if not cached.empty and cached["date"].max().strftime("%Y%m%d") == today:
            return cached.tail(days)

    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=int(days * 1.8))).strftime("%Y-%m-%d")

    try:
        symbol = _code_to_symbol(code)
        url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
               f"?param={symbol},day,{start_date},{end_date},{days},qfq")
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        klines = None
        stock_data = data.get("data", {}).get(symbol, {})
        # 腾讯API返回的key可能是 qfqday 或 day
        for key in ["qfqday", "day"]:
            if key in stock_data:
                klines = stock_data[key]
                break

        if not klines:
            return pd.DataFrame()

        rows = []
        prev_close = None
        for kline in klines:
            # 格式: [date, open, close, high, low, volume]
            date_str = kline[0]
            o = float(kline[1])
            c = float(kline[2])
            h = float(kline[3])
            l = float(kline[4])
            v = float(kline[5]) if len(kline) > 5 else 0

            pct_change = 0.0
            change = 0.0
            if prev_close and prev_close > 0:
                change = c - prev_close
                pct_change = (change / prev_close) * 100
            amplitude = ((h - l) / prev_close * 100) if prev_close and prev_close > 0 else 0

            rows.append({
                "date": date_str,
                "open": o,
                "close": c,
                "high": h,
                "low": l,
                "volume": v,
                "amount": 0,
                "amplitude": round(amplitude, 2),
                "pct_change": round(pct_change, 2),
                "change": round(change, 2),
                "turnover": 0,
            })
            prev_close = c

        df = pd.DataFrame(rows)

    except Exception as e:
        print(f"[WARN] 获取 {code} 日线数据失败: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # ── 补充当日K线 ──
    # 腾讯K线API只返回已完成的交易日，交易时段/收盘后当天数据缺失
    # 判断是否需要补充: 最新一条不是今天 且 当前已过盘前时段(9:15后)
    last_date = df["date"].max().strftime("%Y%m%d")
    now = datetime.datetime.now()
    after_premarket = now.time() >= datetime.time(9, 15)

    if last_date != today and after_premarket and now.weekday() < 5:
        quote = _fetch_realtime_quote(code)
        if quote:
            quote_row = pd.DataFrame([quote])
            quote_row["date"] = pd.to_datetime(quote_row["date"])
            # 用前一日收盘价计算涨跌幅和振幅
            last_row = df.iloc[-1]
            prev_c = last_row["close"]
            if prev_c > 0:
                quote_row["pct_change"] = round(
                    (quote_row["close"].iloc[0] - prev_c) / prev_c * 100, 2
                )
                quote_row["amplitude"] = round(
                    (quote_row["high"].iloc[0] - quote_row["low"].iloc[0]) / prev_c * 100, 2
                )
                quote_row["change"] = round(
                    quote_row["close"].iloc[0] - prev_c, 2
                )
            df = pd.concat([df, quote_row], ignore_index=True)

    df.to_csv(cache_file, index=False)
    return df.tail(days)

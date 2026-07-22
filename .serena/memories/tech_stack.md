# Tech Stack
- Python application using Streamlit UI, pandas/numpy data handling, mplfinance/matplotlib charts.
- Dependencies are in `requirements.txt`: streamlit, akshare, pandas, numpy, mplfinance, matplotlib.
- Network access uses Python stdlib `urllib` directly for Eastmoney/Tencent public finance endpoints; no `requests` dependency.
- Packaging scripts use PyInstaller and Windows batch/PowerShell wrappers.
- `.streamlit/config.toml` fixes headless server on port 8501 and app theme colors.
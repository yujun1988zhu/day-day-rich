# AlphaScanner 使用说明

## 🚀 快速启动（Windows）

### 方式一：双击启动（推荐）
1. **启动服务**：双击 `start.bat` 文件
2. **访问应用**：打开浏览器访问 http://localhost:8501
3. **停止服务**：双击 `stop.bat` 文件

### 方式二：命令行启动
```bash
# 进入项目目录
cd E:\code\py-rich\day-day-check

# 启动服务
venv\Scripts\python.exe -m streamlit run app.py --server.port 8501

# 访问 http://localhost:8501
```

## 📋 功能说明

### 主页面
- **🏆 今日候选池**：显示 Top 10 高评分股票，包含 K 线图、技术指标、建仓信号和价格建议
- **⭐ 自选股**：管理个人关注的股票列表，支持增删操作

### 侧边栏
- **刷新数据**：手动触发全市场扫描
- **自选股管理**：添加/删除关注股票
- **因子权重说明**：查看多因子选股模型权重
- **技术指标说明**：了解均线、布林带等技术指标含义

### 自动刷新
- 每 5 分钟自动刷新一次数据
- 交易时段内自动获取实时行情

## 💰 建仓价格说明

当出现 **🟢 建仓信号** 时，会显示三种建议价格：
- **理想价**：max(MA5, 布林下轨) — 最佳买入点
- **激进价**：收盘价 × 0.998 — 小幅回调即可买入
- **保守价**：MA20 — 等待中期支撑位

##  技术栈
- Python 3.9+
- Streamlit 1.58.0
- Pandas + NumPy
- mplfinance（K 线绘图）
- 腾讯财经 API（实时行情）

## ️ 配置说明

### 修改 TOP_N（候选数量）
编辑 `config.py` 文件：
```python
TOP_N = 10  # 改为其他数字
```

### 修改自动刷新间隔
编辑 `app.py` 文件第 14 行：
```python
AUTO_REFRESH_INTERVAL = 300  # 单位：秒，300 = 5分钟
```

### 修改端口号
编辑 `.streamlit/config.toml` 或启动时指定：
```bash
venv\Scripts\python.exe -m streamlit run app.py --server.port 8080
```

## ❓ 常见问题

### Q: 如何开机自启动？
A: 将 `start.bat` 的快捷方式放到 Windows 启动文件夹：
   - 按 `Win + R`，输入 `shell:startup`，回车
   - 将 `start.bat` 快捷方式复制到此文件夹

### Q: 如何查看后台运行的进程？
A: 
   - 打开任务管理器（Ctrl + Shift + Esc）
   - 在"详细信息"标签页查找 `python.exe`
   - 右键结束进程即可停止服务

### Q: 数据不更新怎么办？
A: 
   - 点击侧边栏的 "🔄 刷新全市场数据" 按钮
   - 或删除 `data/today_pool.csv` 文件后重启服务

### Q: K 线图中文乱码？
A: 已内置 SimHei 和 Microsoft YaHei 字体自动适配，如仍有问题请确保系统已安装中文字体

##  技术支持
如遇问题，请检查：
1. Python 版本是否 ≥ 3.9
2. 虚拟环境是否正确安装依赖：`pip install -r requirements.txt`
3. 网络连接是否正常（需要访问腾讯财经 API）

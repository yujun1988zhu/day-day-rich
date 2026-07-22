---
name: start-app
description: 启动 AlphaScanner 项目服务。在 Windows PowerShell 环境下激活虚拟环境并启动 Streamlit 应用。当用户要求启动程序、启动服务、运行项目时使用此技能。
---

# 启动 AlphaScanner 项目

## 启动步骤

在 Windows PowerShell 环境下执行以下命令启动项目：

```powershell
cd E:\code\py-rich\day-day-check; .\venv\Scripts\Activate.ps1; streamlit run app.py --server.port 8501
```

## 重要注意事项

**PowerShell 命令分隔符**：必须使用分号 `;` 分隔命令，**不能使用 `&&`**，因为 PowerShell 不支持 `&&` 语法。

错误示例：
```powershell
# 错误！PowerShell 不支持 &&
cd E:\code\py-rich\day-day-check && .\venv\Scripts\Activate.ps1 && streamlit run app.py
```

正确示例：
```powershell
# 正确！使用分号分隔
cd E:\code\py-rich\day-day-check; .\venv\Scripts\Activate.ps1; streamlit run app.py --server.port 8501
```

## 服务信息

- 本地访问地址：http://localhost:8501
- 命令应以后台模式运行（is_background: true）

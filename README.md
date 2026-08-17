# XingryBot

一个基于 Telegram 的机械喵。目前支持多仓库绑定、今日 Commit 检查、好感度、摸头互动、随机巡逻和每周周报。

## 安装

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```env
BOT_TOKEN=你从BotFather获取的新Token
DB_FILE=cat_xingry.db
```

然后启动：

```bash
python main.py
```

# 個股監測系統

每日自動抓取股票數據、計算技術指標、進行 ABC 確信度分級，並透過 DeepSeek AI 生成分析報告，最後推送 Email 或 LINE 通知。

## 系統架構

```
個股監測/
├── main.py              # 主程式入口（執行 / 排程）
├── config.py            # 設定檔（股票清單、策略參數、API金鑰）
├── data_fetcher.py      # 資料抓取（yfinance）
├── indicators.py        # 技術指標計算（MA/RSI/MACD/KD/箱體）
├── strategy.py          # 策略邏輯與確信度分級
├── ai_analyzer.py       # DeepSeek AI 分析
├── notifier.py          # 推送通知（Email / LINE Notify）
├── report_generator.py  # 報告生成（文字 / HTML / LINE摘要）
├── requirements.txt     # 依賴套件
├── .env.example         # 環境變數範本
├── reports/             # 自動生成（每日文字報告存檔）
└── logs/                # 自動生成（執行日誌）
```

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env，填入 API 金鑰與通知設定
```

`.env` 最少需要設定：
```
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

### 3. 執行

```bash
# 立即分析一次
python main.py

# 排程模式（每日 14:30 自動執行，適合台股）
python main.py --schedule

# 快速測試（跳過 AI 分析）
python main.py --no-ai

# 自訂排程時間（例如美股用 17:00）
python main.py --schedule --time 17:00
```

## 股票清單設定

編輯 `config.py` 中的 `WATCHLIST`：

```python
WATCHLIST = [
    {"code": "2330.TW", "name": "台積電"},   # 台股：代號.TW
    {"code": "AAPL",    "name": "蘋果"},      # 美股：直接代號
]
```

建議上限 15 支，避免 API 呼叫過多。

## 策略邏輯

### 核心條件（觸發任一即算）

| 條件 | 判斷邏輯 |
|------|----------|
| **突破** | 收盤 > 20日箱頂 且 成交量 > 5MA均量 × 1.5 |
| **回測** | 價格回到 20MA ±1.5%，出現下影線且未跌破 |
| **反轉** | 破底翻（近期破底後回升）或 W底突破頸線 |

### 輔助條件（計算確信度）

| 條件 | 判斷邏輯 |
|------|----------|
| **黃金交叉** | 5MA > 20MA |
| **MACD轉正** | MACD柱狀圖由負轉正 |
| **RSI超賣反彈** | RSI 從 < 30 區域往上翻 |

### 確信度分級

| 等級 | 條件 |
|------|------|
| **A類（高）** | 核心 + 2個以上輔助 |
| **B類（中）** | 核心 + 1個輔助 |
| **C類（低）** | 僅核心，無輔助 |
| **觀察中** | 突破幅度 < 3%（假突破過濾）|

### 賣出警示

- 收盤跌破 20 日箱底
- RSI > 80 且成交量萎縮（量價背離）

## 通知設定

### Email（Gmail）
1. Google 帳戶 → 安全性 → 開啟兩步驟驗證
2. 搜尋「應用程式密碼」，產生 16 碼填入 `.env`
3. 設定 `EMAIL_ENABLED=true`

### LINE Notify
1. 前往 https://notify-bot.line.me/my/
2. 點選「發行權杖」，選擇要推送的聊天室
3. 複製 Token 填入 `.env`
4. 設定 `LINE_NOTIFY_ENABLED=true`

## 注意事項

- 台股收盤時間 13:30，建議排程設為 14:30 執行
- yfinance 數據有時會有 1 日延遲，以實際數據為準
- 本系統僅供技術分析參考，不構成投資建議

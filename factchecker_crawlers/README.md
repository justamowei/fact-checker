# TFC 爬蟲專案說明（factchecker_crawlers）

這是用來抓取台灣事實查核中心（TFC）報告的 Scrapy 爬蟲程式碼與設定。目標是定期爬取、清理並輸出可供 RAG 系統（rag_system）使用的 JSON 檔案。

## 目錄結構
```
factchecker_crawlers/
├── run_tfc_spider.py         # 用來從命令列或 Python 程式內啟動 spider 的小工具
├── scrapy.cfg                # Scrapy 專案設定檔
├── factchecker_crawlers/     # Scrapy 專案的 Python 套件
│   ├── __init__.py
│   ├── items.py              # Scrapy Item 定義（資料欄位）
│   ├── middlewares.py        # Spider / Downloader middlewares（
│   ├── pipelines.py          # 爬取後資料處理與輸出（例如寫 JSON）
│   ├── settings.py           # Scrapy 設定（USER_AGENT、ROBOTSTXT、PIPELINES 等）
│   └── spiders/
│       ├── __init__.py
│       └── tfc_spider.py     # 主爬蟲程式，負責抓取 TFC 報告並產生 Item
└── output/
    ├── tfc_reports_unsorted.json # 原始抓取輸出（未排序）
    └── tfc_reports_sorted.json   # 排序後結果（依照報告編號）
```

> 提示：`output/` 會包含爬蟲執行後的 JSON 檔案；`tfc_reports_sorted.json` 是 `rag_system` 預期讀入的資料來源，請確認路徑正確。

## 各檔案說明
- `run_tfc_spider.py`
  - 用途：提供一個簡單的方式從命令列啟動爬蟲，或在其他 Python 程式中調用。適合測試或排程啟動。
  - 常見用法：在專案根目錄執行 `python run_tfc_spider.py`

- `scrapy.cfg`
  - Scrapy 的設定檔，用於定義專案名稱與部署設定，通常不需修改除非要部署到 ScrapyD 或改變專案結構。

- `factchecker_crawlers/items.py`
  - 定義 Scrapy Item（欄位），例如標題、日期、內文、來源連結、判定結果等。這些欄位會在 `pipelines.py` 中被處理與儲存。

- `factchecker_crawlers/middlewares.py`
  - 如需自訂請求/回應處理，可在此加入 middleware。

- `factchecker_crawlers/pipelines.py`
  - 負責把 item 處理並寫入 `output/`。

- `factchecker_crawlers/settings.py`
  - Scrapy 設定（例如 `USER_AGENT`、`CONCURRENT_REQUESTS`、`DOWNLOAD_DELAY`、`ITEM_PIPELINES`）。
  - 若需要調整爬取速度或啟用 proxies、headers，請在此修改。

- `factchecker_crawlers/spiders/tfc_spider.py`
  - 主爬蟲實作。負責解析 TFC 網站的列表頁與內文頁面，組裝 Item 並交給 pipelines 處理。

## 如何使用
1. 建議在虛擬環境中操作：
   - 安裝依賴：在 `factchecker_crawlers/` 執行 `pip install -r requirements.txt` 或安裝 `scrapy` 等必要套件。

2. 測試單次爬取：
   - 使用 `run_tfc_spider.py`：
     - `python run_tfc_spider.py`

3. 爬取結果與後續處理：
   - 爬蟲會把初始資料輸出到 `factchecker_crawlers/output/tfc_reports_unsorted.json`。

## run_tfc_spider 可用參數
`run_tfc_spider.py` 是一個輔助腳本，會把你的參數轉換成相對應的 `scrapy crawl tfc_spider` 指令並執行。支援的呼叫方式如下：

- 沒有參數：爬取所有頁面
  - 範例：`python run_tfc_spider.py`

- 一個數字參數：爬取前 N 頁（end_page）
  - 範例：`python run_tfc_spider.py 10` 會把 `end_page=10` 傳給 spider

- 兩個數字參數：指定起始頁到結束頁（start_page 與 end_page）
  - 範例：`python run_tfc_spider.py 5 12` 會把 `start_page=5` 和 `end_page=12` 傳給 spider

- URL（以 http/https 開頭）：只爬取該特定文章（target_url）
  - 範例：`python run_tfc_spider.py https://tfc-taiwan.org.tw/...` 會把 `target_url=...` 傳給 spider

- 幫助信息：
  - 範例：`python run_tfc_spider.py --help` 或 `python run_tfc_spider.py -h`

如果輸入的參數型別不正確（例如非數字的頁碼），腳本會印出錯誤並結束。

## 直接使用 Scrapy 指令（
你也可以直接用 Scrapy CLI 呼叫 `tfc_spider`，以下範例示範如何傳遞參數或改變輸出/日誌等：

- 基本啟動（等同於沒有參數的 run_tfc_spider）：
  - `scrapy crawl tfc_spider`

- 傳遞 spider 參數（等同於 run_tfc_spider 的 -a）：
  - 指定結束頁：`scrapy crawl tfc_spider -a end_page=10`
  - 指定起始與結束頁：`scrapy crawl tfc_spider -a start_page=5 -a end_page=12`
  - 指定單一文章 URL：`scrapy crawl tfc_spider -a target_url="https://tfc-taiwan.org.tw/..."`
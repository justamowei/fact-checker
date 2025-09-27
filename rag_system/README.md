# 事實查核 RAG 系統使用說明

## 概述
這是一個基於 LlamaIndex 和 Google Gemini API 的事實查核 RAG (檢索增強生成) 系統。系統使用 TFC (台灣事實查核中心) 的事實查核報告作為知識庫，能夠回答使用者關於事實查核的問題。

## 系統架構
- **資料處理模組**: 處理和清理 TFC 事實查核報告
- **嵌入模組**: 使用 Google GenAI embeddings (gemini-embedding-001) 進行文字向量化
- **向量索引模組**: 使用 ChromaDB 建立本地向量資料庫
- **檢索模組**: 使用 AutoMergingRetriever 進行語意檢索
- **查詢引擎模組**: 整合 Gemini 2.0 Flash 作為 LLM

## 安裝與設置

### 1. 環境準備
```bash
cd c:\GitHubSource\fact-checker\rag_system
pip install -r requirements.txt
```

### 2. API 金鑰設置
1. 在 `.env` 檔案中設定 Google API 金鑰：
```
GOOGLE_API_KEY=your_actual_google_api_key_here
```

### 3. 資料準備
確保 TFC 事實查核資料位於正確位置：
```
../factchecker_crawlers/output/tfc_reports_sorted.json
```

## 使用方式

### 完整系統啟動
```bash
python main.py
```
**注意事項**：
- 首次運行需要較長時間建立向量索引
- 如遇到 Google API 503 錯誤，請等待幾分鐘後重試
- 系統會處理 1000 筆（可於 main 更改） TFC 資料

### 命令互動模式

系統啟動後會進入互動模式，支援以下指令：
- 輸入任何問題進行事實查核
- `info`: 查看系統信息
- `help`: 查看幫助信息
- `quit` 或 `exit`: 退出系統

### 範例查詢
```
請輸入您的問題: 阿米斯音樂節的徵人訊息是真的嗎？
請輸入您的問題: 衛福部的捐款專戶運作方式是什麼？
請輸入您的問題: 網路流傳的花蓮災情影片是真的嗎？
```

## 模組說明

### data_processor.py
處理原始的 TFC 事實查核資料：
- 提取最新 1000 筆資料
- 清理和結構化資料欄位
- 產生唯一 ID 和 metadata
- 輸出處理後的 JSON 檔案

### embedding.py
負責文字向量化：
- 使用 Google GenAI embeddings
- 支援批次處理
- 針對事實驗證任務優化
- 自動正規化嵌入向量

### vector_index.py
建立和管理向量資料庫：
- 使用 ChromaDB 本地儲存
- 創建分層節點結構
- 支援持久化存储
- 提供搜索和統計功能

### retriever.py
實現語意檢索：
- AutoMergingRetriever 整合相關片段
- 比較不同檢索策略
- 提供檢索統計和分析

### query_engine.py
整合 LLM 進行問答：
- 使用 Gemini 2.0 Flash
- 事實查核專用提示詞
- 結構化回答格式
- 引用來源和證據

## 輸出格式

查詢回答包含以下部分：
1. **事實查核結果**: 基於資料庫的判斷
2. **關鍵證據**: 支持判斷的證據
3. **相關查核報告**: 引用的具體報告
4. **建議**: 對使用者的建議

## 檔案結構
```
rag_system/
├── modules/
│   ├── __init__.py
│   ├── data_processor.py      # 資料處理
│   ├── embedding.py           # 嵌入功能
│   ├── vector_index.py        # 向量索引
│   ├── retriever.py           # 檢索器
│   └── query_engine.py        # 查詢引擎
├── data/
│   └── processed_tfc_data.json # 處理後資料
├── vector_store_db/           # ChromaDB 資料庫
├── main.py                    # 主程式
├── requirements.txt           # 依賴套件
├── .env                       # 環境變數
└── README.md                  # 此說明檔案
```

### 日誌檔案
系統會產生 `fact_check_rag.log` 日誌檔案，包含詳細的執行信息和錯誤訊息。

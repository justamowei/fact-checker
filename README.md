# Fact-Checker RAG 系統

這個專案整合兩個主要部分：

1. `factchecker_crawlers/`：Scrapy 爬蟲，用來抓取台灣事實查核中心（TFC）的查核報告並輸出 JSON 檔案。
2. `rag_system/`：基於 LlamaIndex、Google GenAI（Gemini）與 ChromaDB 的 RAG（檢索增強生成）系統，用以對抓取到的查核報告進行向量化、索引與查詢。

## 主要目的
- 定期自 TFC 擷取查核報告，整理成機器可用的結構化資料。
- 將整理後的資料建立向量索引，提供語意檢索並輔助 LLM 產生具證據的事實查核回答。

## 專案資料夾
- `factchecker_crawlers/`：爬蟲程式、設定與輸出（`output/tfc_reports_sorted.json` 為 RAG 系統預期輸入）。
- `rag_system/`：data_processor、embedding、vector_index、retriever、query_engine 等模組，以及 `main.py`（執行入口）。

## 使用簡介
1. 建議在虛擬環境中操作
2. 安裝依賴
3. 執行爬蟲（生成 JSON）
4. 建立向量索引並啟動 RAG 互動


## TODO
- 調整 embedding ：目前向量化時很容易會觸發 Google GenAI 回傳 503（Service Unavailable），導致後面的資料都無法向量畫到，目前看起來是沒有超過官方文檔的速率，需再找找看原因。
- 新增資料來源：考慮把 MyGoPen、Cofacts 等社群/事實查核來源納入 RAG 的資料庫中。
- RAG 邏輯優化：可進一步嘗試不同的策略（例如不同的 chunking、retriever 策略等）。
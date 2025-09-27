"""
資料處理模組
處理 TFC 事實查核報告資料，提取並清理需要的欄位
"""
import json
from typing import Dict, List, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TFCDataProcessor:
    """TFC 事實查核資料處理器"""
    
    def __init__(self):
        self.processed_data = []
    
    def load_raw_data(self, file_path: str) -> List[Dict[str, Any]]:
        """載入原始 JSON 資料"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功載入 {len(data)} 筆原始資料")
            return data
        except Exception as e:
            logger.error(f"載入資料失敗: {e}")
            raise
    
    def process_data(self, raw_data: List[Dict[str, Any]], limit: int = 1000) -> List[Dict[str, Any]]:
        """處理原始資料，提取需要的欄位"""
        processed_records = []
        
        # 取最新的 limit 筆資料（資料已按時間排序）
        recent_data = raw_data[:limit]
        logger.info(f"處理最新 {len(recent_data)} 筆資料")
        
        for i, record in enumerate(recent_data):
            try:
                # 生成唯一 ID: tfc + report_number
                unique_id = f"tfc_{record.get('report_number', str(i))}"
                
                # 提取核心欄位
                processed_record = {
                    'id': unique_id,
                    'title': record.get('title', ''),
                    'processed_content': record.get('processed_content', ''),
                    'check_result': record.get('check_result', ''),
                    'categories': record.get('categories', []),
                    'publish_date': record.get('publish_date', ''),
                    'content_url': record.get('content_url', ''),
                    'source': record.get('source', 'TFC')
                }
                
                # 檢查必要欄位
                if not processed_record['title'] or not processed_record['processed_content']:
                    logger.warning(f"記錄 {unique_id} 缺少必要欄位，跳過")
                    continue
                
                # 處理 categories - 只保留有值的分類
                if processed_record['categories']:
                    processed_record['categories'] = [
                        cat for cat in processed_record['categories'] 
                        if cat and cat.strip()
                    ]
                else:
                    processed_record['categories'] = []
                
                processed_records.append(processed_record)
                
            except Exception as e:
                logger.error(f"處理第 {i} 筆記錄時發生錯誤: {e}")
                continue
        
        logger.info(f"成功處理 {len(processed_records)} 筆資料")
        self.processed_data = processed_records
        return processed_records
    
    def save_processed_data(self, output_path: str):
        """儲存處理後的資料"""
        try:
            # 確保輸出目錄存在
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"處理後資料已儲存至: {output_path}")
            
            # 輸出統計資訊
            self.print_data_statistics()
            
        except Exception as e:
            logger.error(f"儲存資料失敗: {e}")
            raise
    
    def print_data_statistics(self):
        """印出資料統計資訊"""
        if not self.processed_data:
            logger.info("沒有資料可統計")
            return
        
        total_count = len(self.processed_data)
        
        # 統計查核結果分佈
        result_counts = {}
        for record in self.processed_data:
            result = record.get('check_result', '未知')
            result_counts[result] = result_counts.get(result, 0) + 1
        
        # 統計分類分佈
        category_counts = {}
        for record in self.processed_data:
            categories = record.get('categories', [])
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # 輸出統計結果
        logger.info("=== 資料統計 ===")
        logger.info(f"總記錄數: {total_count}")
        logger.info(f"查核結果分佈: {result_counts}")
        logger.info(f"分類分佈 (前5名): {dict(list(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))[:5])}")

def main():
    """主執行函數 - 用於測試"""
    # 設定路徑
    input_file = "../factchecker_crawlers/output/tfc_reports_sorted.json"
    output_file = "data/processed_tfc_data.json"
    
    # 初始化處理器
    processor = TFCDataProcessor()
    
    # 處理資料
    raw_data = processor.load_raw_data(input_file)
    processed_data = processor.process_data(raw_data, limit=1000)
    processor.save_processed_data(output_file)
    
    print(f"資料處理完成！處理了 {len(processed_data)} 筆資料")

if __name__ == "__main__":
    main()
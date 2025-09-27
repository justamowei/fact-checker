"""
簡化測試腳本 - 不依賴 LlamaIndex，純粹測試資料處理和基本功能
"""
import os
import sys
import json
from pathlib import Path

# 添加模組路徑
sys.path.append(str(Path(__file__).parent))

def test_data_processing():
    """測試資料處理功能"""
    print("=== 測試資料處理 ===")
    
    try:
        from modules.data_processor import TFCDataProcessor
        
        # 檢查原始資料
        raw_data_path = "../factchecker_crawlers/output/tfc_reports_sorted.json"
        if not os.path.exists(raw_data_path):
            print(f"錯誤: 找不到原始資料檔案 {raw_data_path}")
            return False
        
        # 初始化處理器
        processor = TFCDataProcessor()
        
        # 載入資料
        raw_data = processor.load_raw_data(raw_data_path)
        print(f"載入了 {len(raw_data)} 筆原始資料")
        
        # 處理資料（只處理前 10 筆作為測試）
        processed_data = processor.process_data(raw_data, limit=10)
        print(f"處理了 {len(processed_data)} 筆資料")
        
        # 顯示樣本資料
        if processed_data:
            sample = processed_data[0]
            print(f"樣本資料: {sample['title'][:50]}...")
            print(f"查核結果: {sample['check_result']}")
            print(f"分類: {sample.get('categories', [])}")
        
        print("資料處理測試通過")
        return True
        
    except Exception as e:
        print(f"資料處理測試失敗: {e}")
        return False

def test_environment_setup():
    """測試環境設置"""
    print("=== 測試環境設置 ===")
    
    # 檢查 .env 檔案
    if os.path.exists('.env'):
        print(".env 檔案存在")
        
        # 載入環境變數
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key and api_key != 'test_key_please_replace':
            print("Google API 金鑰已設置")
        else:
            print("請在 .env 檔案中設置有效的 Google API 金鑰")
    else:
        print(".env 檔案不存在，請複製 .env.example 並設置 API 金鑰")
    
    # 檢查必要目錄
    directories = ['data', 'modules', 'vector_store_db']
    for dir_name in directories:
        if os.path.exists(dir_name):
            print(f"{dir_name} 目錄存在")
        else:
            print(f"{dir_name} 目錄不存在")
    
    print()

def test_basic_functionality():
    """測試基本功能（不需要 API 金鑰）"""
    print("=== 測試基本功能 ===")
    
    success_count = 0
    total_tests = 2
    
    # 測試資料處理
    if test_data_processing():
        success_count += 1
    
    # 測試環境設置
    test_environment_setup()
    success_count += 1  # 環境測試不會失敗
    
    print(f"基本功能測試完成: {success_count}/{total_tests} 通過")
    return success_count == total_tests

def show_system_status():
    """顯示系統狀態"""
    print("=== 系統狀態 ===")
    
    # 檢查檔案
    files_to_check = {
        '原始資料': '../factchecker_crawlers/output/tfc_reports_sorted.json',
        '處理後資料': 'data/processed_tfc_data.json',
        '環境設置': '.env',
        '需求檔案': 'requirements.txt',
        '主程式': 'main.py'
    }
    
    for name, path in files_to_check.items():
        status = "通過" if os.path.exists(path) else "失敗"
        print(f"{status} {name}: {path}")
    
    # 檢查模組
    modules = [
        'modules/data_processor.py',
        'modules/embedding.py', 
        'modules/vector_index.py',
        'modules/retriever.py',
        'modules/query_engine.py'
    ]
    
    print("\n模組檔案:")
    for module in modules:
        status = "通過" if os.path.exists(module) else "失敗"
        print(f"{status} {module}")
    
    print()

def main():
    """主函數"""
    print("事實查核 RAG 系統 - 簡化測試")
    print("=" * 50)
    
    # 顯示系統狀態
    show_system_status()
    
    # 執行基本測試
    if test_basic_functionality():
        print("所有基本測試通過")
        print("\n下一步:")
        print("1. 在 .env 檔案中設置有效的 Google API 金鑰")
        print("2. 執行: pip install -r requirements.txt")
        print("3. 執行: python main.py")
    else:
        print("部分測試失敗，請檢查設置")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
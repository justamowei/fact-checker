"""
事實查核 RAG 系統主程式
整合資料處理、向量索引、檢索和查詢引擎等功能
"""
import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

# 添加當前目錄到 Python 路徑
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from modules.logger import setup_logging, get_logger
    from modules.data_processor import TFCDataProcessor
    from modules.embedding import FactCheckEmbedding
    from modules.vector_index import FactCheckVectorStore
    from modules.retriever import FactCheckRetriever
    from modules.query_engine import FactCheckQueryEngine
except ImportError as e:
    print(f"模組導入失敗: {e}")
    print("請確認已安裝所有必要的依賴套件")
    sys.exit(1)

# 設定統一日誌
setup_logging()
logger = get_logger(__name__)

class FactCheckRAGSystem:
    """事實查核 RAG 系統主類別"""
    
    def __init__(self, 
                 data_limit: int = 1000,
                 embedding_dim: int = 768,
                 similarity_top_k: int = 3):
        """
        初始化 RAG 系統
        
        Args:
            data_limit: 處理的資料數量限制
            embedding_dim: 嵌入向量維度
            similarity_top_k: 相似性搜索返回數量
        """
        self.data_limit = data_limit
        self.embedding_dim = embedding_dim
        self.similarity_top_k = similarity_top_k
        
        # 設定檔案路徑
        self.raw_data_path = "../factchecker_crawlers/output/tfc_reports_sorted.json"
        self.processed_data_path = "data/processed_tfc_data.json"
        self.vector_store_path = "vector_store_db"
        
        # 初始化元件
        self.data_processor = None
        self.vector_store = None
        self.retriever = None
        self.query_engine = None
        
        logger.info("初始化事實查核 RAG 系統")
    
    def setup_system(self, force_rebuild: bool = False) -> bool:
        """
        設定系統所有元件
        
        Args:
            force_rebuild: 是否強制重建所有元件
            
        Returns:
            設定成功與否
        """
        try:
            logger.info("開始設定 RAG 系統...")
            
            # 1. 處理資料
            if not self._setup_data_processing(force_rebuild):
                return False
            
            # 2. 建立向量索引
            if not self._setup_vector_store(force_rebuild):
                return False
            
            # 3. 初始化檢索器
            if not self._setup_retriever():
                return False
            
            # 4. 建立查詢引擎
            if not self._setup_query_engine():
                return False
            
            logger.info("RAG 系統設定完成！")
            return True
            
        except Exception as e:
            logger.error(f"系統設定失敗: {e}")
            return False
    
    def _setup_data_processing(self, force_rebuild: bool) -> bool:
        """設定資料處理元件"""
        try:
            # 檢查是否需要重新處理資料
            if not force_rebuild and os.path.exists(self.processed_data_path):
                logger.info("已存在處理後的資料")
                while True:
                    response = input("是否要重新處理資料？(Y/N): ").strip().upper()
                    if response == 'Y':
                        logger.info("將重新處理資料...")
                        break
                    elif response == 'N':
                        logger.info("跳過資料處理步驟")
                        return True
                    else:
                        print("輸入無效！請輸入 Y 或 N")

            logger.info("開始處理事實查核資料...")

            # 檢查原始資料是否存在
            if not os.path.exists(self.raw_data_path):
                logger.error(f"找不到原始資料檔案: {self.raw_data_path}")
                return False

            # 初始化資料處理器
            self.data_processor = TFCDataProcessor()

            # 載入和處理資料
            raw_data = self.data_processor.load_raw_data(self.raw_data_path)
            processed_data = self.data_processor.process_data(raw_data, limit=self.data_limit)
            self.data_processor.save_processed_data(self.processed_data_path)

            logger.info(f"成功處理 {len(processed_data)} 筆資料")
            return True

        except Exception as e:
            logger.error(f"資料處理失敗: {e}")
            return False
    
    def _setup_vector_store(self, force_rebuild: bool) -> bool:
        """設定向量儲存"""
        try:
            logger.info("初始化向量儲存...")
            
            # 載入處理後的資料
            with open(self.processed_data_path, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            # 初始化向量儲存器
            self.vector_store = FactCheckVectorStore(
                persist_path=self.vector_store_path,
                embedding_dim=self.embedding_dim
            )
            
            # 建立或載入索引
            self.vector_store.build_index(documents, force_rebuild=force_rebuild)
            
            logger.info("向量儲存設定完成")
            return True
            
        except Exception as e:
            logger.error(f"向量儲存設定失敗: {e}")
            return False
    
    def _setup_retriever(self) -> bool:
        """設定檢索器"""
        try:
            logger.info("初始化檢索器...")
            
            self.retriever = FactCheckRetriever(
                self.vector_store,
                similarity_top_k=self.similarity_top_k
            )
            
            logger.info("檢索器設定完成")
            return True
            
        except Exception as e:
            logger.error(f"檢索器設定失敗: {e}")
            return False
    
    def _setup_query_engine(self) -> bool:
        """設定查詢引擎"""
        try:
            logger.info("初始化查詢引擎...")
            
            self.query_engine = FactCheckQueryEngine(self.retriever)
            
            logger.info("查詢引擎設定完成")
            return True
            
        except Exception as e:
            logger.error(f"查詢引擎設定失敗: {e}")
            return False
    
    def query(self, question: str, detailed: bool = True) -> Dict[str, Any]:
        """
        執行事實查核查詢
        
        Args:
            question: 查詢問題
            detailed: 是否返回詳細資訊
            
        Returns:
            查詢結果
        """
        if not self.query_engine:
            return {
                'success': False,
                'error': '查詢引擎尚未初始化，請先執行 setup_system()',
                'answer': ''
            }
        
        return self.query_engine.query(question, detailed=detailed)
    
    def get_system_info(self) -> Dict[str, Any]:
        """取得系統資訊"""
        try:
            info = {
                'data_limit': self.data_limit,
                'embedding_dimension': self.embedding_dim,
                'similarity_top_k': self.similarity_top_k,
                'processed_data_exists': os.path.exists(self.processed_data_path),
                'vector_store_exists': os.path.exists(self.vector_store_path)
            }
            
            # 添加元件資訊
            if self.vector_store:
                info['vector_store_info'] = self.vector_store.get_collection_info()
            
            if self.retriever:
                info['retriever_info'] = self.retriever.get_retriever_info()
            
            if self.query_engine:
                info['query_engine_info'] = self.query_engine.get_engine_info()
            
            return info
            
        except Exception as e:
            logger.error(f"取得系統資訊失敗: {e}")
            return {'error': str(e)}

def interactive_mode(rag_system: FactCheckRAGSystem):
    """互動模式"""
    print("\n=== 事實查核 RAG 系統 ===")
    print("輸入問題進行事實查核，輸入 'quit' 或 'exit' 結束")
    print("輸入 'info' 查看系統資訊")
    print("輸入 'help' 查看幫助資訊")
    print("-" * 50)
    
    while True:
        try:
            question = input("\n請輸入您的問題: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', '退出']:
                print("再見！")
                break
            
            if question.lower() == 'info':
                info = rag_system.get_system_info()
                print("\n系統資訊:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
                continue
            
            if question.lower() == 'help':
                print("\n可用指令:")
                print("  - 輸入任何問題進行事實查核")
                print("  - 'info': 查看系統資訊")
                print("  - 'quit' 或 'exit': 退出系統")
                continue
            
            # 執行查詢
            print(f"\n正在查詢: {question}")
            result = rag_system.query(question)
            
            if result['success']:
                print(f"\n答案:\n{result['answer']}")
                
                sources = result.get('sources', [])
                if sources:
                    print(f"\n參考來源 ({len(sources)} 個):")
                    for i, source in enumerate(sources[:3]):  # 顯示前3個來源
                        title = source.get('title', 'N/A')
                        check_result = source.get('check_result', 'N/A')
                        score = source.get('score', 0.0)
                        print(f"  {i+1}. [{check_result}] {title} (相似度: {score:.3f})")
            else:
                print(f"查詢失敗: {result.get('error', '未知錯誤')}")
                
        except KeyboardInterrupt:
            print("\n\n程式已中斷")
            break
        except Exception as e:
            print(f"處理查詢時發生錯誤: {e}")

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='事實查核 RAG 系統')
    parser.add_argument('--force-rebuild', action='store_true',
                       help='強制重建所有資料和索引')
    parser.add_argument('--data-limit', type=int, default=1000,
                       help='處理的資料數量限制 (預設: 1000)')
    
    args = parser.parse_args()
    
    print("事實查核 RAG 系統啟動中...")
    
    # 檢查環境變數
    if not os.getenv('GOOGLE_API_KEY'):
        print("錯誤: 未設定 GOOGLE_API_KEY 環境變數")
        print("請在 .env 檔案中設定您的 Google API 金鑰")
        return
    
    try:
        # 初始化系統
        rag_system = FactCheckRAGSystem(
            data_limit=args.data_limit,
            embedding_dim=768,
            similarity_top_k=3
        )
        
        # 設定系統
        if not rag_system.setup_system(force_rebuild=args.force_rebuild):
            print("系統設定失敗，請檢查日誌")
            return
        
        # 顯示系統資訊
        info = rag_system.get_system_info()
        print("\n系統設定完成！")
        print(f"向量資料庫文檔數量: {info.get('vector_store_info', {}).get('document_count', 'N/A')}")
        
        # 進入互動模式
        interactive_mode(rag_system)
        
    except Exception as e:
        logger.error(f"系統啟動失敗: {e}")
        print(f"系統啟動失敗: {e}")

if __name__ == "__main__":
    main()
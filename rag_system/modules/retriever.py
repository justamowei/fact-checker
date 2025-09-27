"""
檢索模組
使用 AutoMergingRetriever 進行語意檢索
"""
import logging
from typing import List, Dict, Any, Optional
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core import StorageContext
from llama_index.core.node_parser import get_leaf_nodes
from .vector_index import FactCheckVectorStore

logger = logging.getLogger(__name__)

class FactCheckRetriever:
    """事實查核檢索器"""
    
    def __init__(self, vector_store: FactCheckVectorStore, similarity_top_k: int = 6):
        """
        初始化檢索器
        
        Args:
            vector_store: 向量儲存器實例
            similarity_top_k: 相似性搜索返回的數量
        """
        self.vector_store = vector_store
        self.similarity_top_k = similarity_top_k
        
        # 檢查向量索引是否已建立
        if not self.vector_store.index:
            raise ValueError("向量索引尚未建立，請先執行 vector_store.build_index()")
        
        self.index = self.vector_store.index
        self.nodes = self.vector_store.nodes
        
        # 初始化檢索器
        self._setup_retrievers()
        
        logger.info(f"成功初始化檢索器，similarity_top_k={similarity_top_k}")
    
    def _setup_retrievers(self):
        """設置檢索器"""
        try:
            # 創建文檔儲存器
            docstore = SimpleDocumentStore()
            
            # 將所有節點添加到文檔儲存器
            if self.nodes:
                docstore.add_documents(self.nodes)
                logger.info(f"添加了 {len(self.nodes)} 個節點到文檔儲存器")
            
            # 創建儲存上下文
            storage_context = StorageContext.from_defaults(docstore=docstore)
            
            # 獲取葉子節點
            leaf_nodes = get_leaf_nodes(self.nodes) if self.nodes else []
            
            # 創建基礎檢索器
            self.base_retriever = self.index.as_retriever(
                similarity_top_k=self.similarity_top_k
            )
            
            # 創建 AutoMerging 檢索器
            if leaf_nodes and storage_context:
                self.auto_merging_retriever = AutoMergingRetriever(
                    base_retriever=self.base_retriever,
                    storage_context=storage_context,
                    verbose=True
                )
                logger.info("成功創建 AutoMerging 檢索器")
            else:
                logger.warning("無法創建 AutoMerging 檢索器，將使用基礎檢索器")
                self.auto_merging_retriever = self.base_retriever
            
        except Exception as e:
            logger.error(f"設置檢索器失敗: {e}")
            # 使用基礎檢索器作為後備
            self.auto_merging_retriever = self.base_retriever
    
    def retrieve(self, query: str, use_auto_merging: bool = True) -> List[Dict[str, Any]]:
        """
        執行檢索
        
        Args:
            query: 查詢文字
            use_auto_merging: 是否使用 AutoMerging 檢索器
            
        Returns:
            檢索結果列表
        """
        try:
            if not query or not query.strip():
                logger.warning("查詢文字為空")
                return []
            
            logger.info(f"開始檢索查詢: '{query}'")
            
            # 選擇檢索器
            retriever = (self.auto_merging_retriever if use_auto_merging 
                        else self.base_retriever)
            
            # 執行檢索
            nodes = retriever.retrieve(query.strip())
            
            # 處理結果
            results = []
            for i, node in enumerate(nodes):
                result = {
                    'rank': i + 1,
                    'score': getattr(node, 'score', 0.0),
                    'text': node.node.text,
                    'metadata': node.node.metadata,
                    'node_id': node.node.id_,
                    'source_type': 'auto_merging' if use_auto_merging else 'base'
                }
                
                # 提取關鍵元數據
                metadata = node.node.metadata
                if metadata:
                    result['title'] = metadata.get('title', '')
                    result['check_result'] = metadata.get('check_result', '')
                    result['categories'] = metadata.get('categories', [])
                    result['publish_date'] = metadata.get('publish_date', '')
                    result['content_url'] = metadata.get('content_url', '')
                
                results.append(result)
            
            logger.info(f"檢索完成，返回 {len(results)} 個結果")
            
            # 顯示檢索統計
            self._log_retrieval_stats(query, results, use_auto_merging)
            
            return results
            
        except Exception as e:
            logger.error(f"檢索失敗: {e}")
            return []
    
    def compare_retrievers(self, query: str) -> Dict[str, Any]:
        """
        比較不同檢索器的結果
        
        Args:
            query: 查詢文字
            
        Returns:
            比較結果
        """
        try:
            logger.info(f"比較檢索器性能，查詢: '{query}'")
            
            # 使用基礎檢索器
            base_results = self.retrieve(query, use_auto_merging=False)
            
            # 使用 AutoMerging 檢索器
            auto_merging_results = self.retrieve(query, use_auto_merging=True)
            
            # 比較結果
            comparison = {
                'query': query,
                'base_retriever': {
                    'count': len(base_results),
                    'results': base_results
                },
                'auto_merging_retriever': {
                    'count': len(auto_merging_results),
                    'results': auto_merging_results
                },
                'analysis': self._analyze_results(base_results, auto_merging_results)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"比較檢索器失敗: {e}")
            return {}
    
    def _analyze_results(self, base_results: List[Dict], auto_results: List[Dict]) -> Dict[str, Any]:
        """分析檢索結果"""
        try:
            analysis = {
                'base_count': len(base_results),
                'auto_count': len(auto_results),
                'avg_base_score': 0.0,
                'avg_auto_score': 0.0,
                'common_results': 0,
                'unique_base': 0,
                'unique_auto': 0
            }
            
            # 計算平均分數
            if base_results:
                analysis['avg_base_score'] = sum(r['score'] for r in base_results) / len(base_results)
            
            if auto_results:
                analysis['avg_auto_score'] = sum(r['score'] for r in auto_results) / len(auto_results)
            
            # 分析重疊結果
            base_ids = {r['node_id'] for r in base_results}
            auto_ids = {r['node_id'] for r in auto_results}
            
            analysis['common_results'] = len(base_ids & auto_ids)
            analysis['unique_base'] = len(base_ids - auto_ids)
            analysis['unique_auto'] = len(auto_ids - base_ids)
            
            return analysis
            
        except Exception as e:
            logger.warning(f"分析結果失敗: {e}")
            return {}
    
    def _log_retrieval_stats(self, query: str, results: List[Dict], use_auto_merging: bool):
        """記錄檢索統計資訊"""
        try:
            retriever_type = "AutoMerging" if use_auto_merging else "Base"
            
            logger.info(f"=== {retriever_type} 檢索統計 ===")
            logger.info(f"查詢: {query}")
            logger.info(f"結果數量: {len(results)}")
            
            if results:
                avg_score = sum(r['score'] for r in results) / len(results)
                logger.info(f"平均分數: {avg_score:.4f}")
                logger.info(f"最高分數: {results[0]['score']:.4f}")
                
                # 顯示前3個結果的標題
                logger.info("前3個結果:")
                for i, result in enumerate(results[:3]):
                    title = result.get('title', 'N/A')
                    score = result['score']
                    logger.info(f"  {i+1}. [{score:.4f}] {title}")
            
        except Exception as e:
            logger.warning(f"記錄統計資訊失敗: {e}")
    
    def get_retriever_info(self) -> Dict[str, Any]:
        """獲取檢索器資訊"""
        try:
            info = {
                'similarity_top_k': self.similarity_top_k,
                'has_auto_merging': hasattr(self, 'auto_merging_retriever'),
                'node_count': len(self.nodes) if self.nodes else 0,
                'index_type': type(self.index).__name__ if self.index else None
            }
            
            return info
            
        except Exception as e:
            logger.error(f"獲取檢索器資訊失敗: {e}")
            return {}

def main():
    """主執行函數 - 用於測試"""
    import json
    import os
    from .vector_index import FactCheckVectorStore
    
    try:
        # 載入處理後的資料
        data_file = "data/processed_tfc_data.json"
        if not os.path.exists(data_file):
            print("請先執行 data_processor.py 來處理資料")
            return
        
        with open(data_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        print(f"載入了 {len(documents)} 個文檔")
        
        # 初始化向量儲存器
        vector_store = FactCheckVectorStore()
        
        # 建立或載入索引
        vector_store.build_index(documents[:100])  # 測試 100 個文檔
        
        # 初始化檢索器
        retriever = FactCheckRetriever(vector_store)
        
        # 測試查詢
        test_queries = [
            "阿米斯音樂節詐騙",
            "衛福部捐款專戶",
            "印度山洪影片假消息"
        ]
        
        for query in test_queries:
            print(f"\n=== 測試查詢: '{query}' ===")
            
            # 比較檢索器
            comparison = retriever.compare_retrievers(query)
            
            if comparison:
                base_count = comparison['base_retriever']['count']
                auto_count = comparison['auto_merging_retriever']['count']
                
                print(f"基礎檢索器結果: {base_count}")
                print(f"AutoMerging 檢索器結果: {auto_count}")
                
                # 顯示 AutoMerging 的前2個結果
                auto_results = comparison['auto_merging_retriever']['results']
                for i, result in enumerate(auto_results[:2]):
                    print(f"  {i+1}. [{result['score']:.4f}] {result['title']}")
        
        # 顯示檢索器資訊
        info = retriever.get_retriever_info()
        print(f"\n檢索器資訊: {info}")
        
        print("檢索模組測試成功！")
        
    except Exception as e:
        print(f"測試失敗: {e}")
        logger.error(f"測試失敗: {e}")

if __name__ == "__main__":
    main()
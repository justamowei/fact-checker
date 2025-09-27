"""
向量索引模組
使用 ChromaDB 建立本地向量資料庫並進行索引
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import HierarchicalNodeParser, SentenceSplitter
from llama_index.core.node_parser import get_leaf_nodes
from .embedding import FactCheckEmbedding

logger = logging.getLogger(__name__)

class FactCheckVectorStore:
    """事實查核向量儲存器"""
    
    def __init__(self, 
                 persist_path: str = "vector_store_db",
                 collection_name: str = "fact_check_collection",
                 embedding_dim: int = 768):
        """
        初始化向量儲存器
        
        Args:
            persist_path: 持久化儲存路徑
            collection_name: 集合名稱
            embedding_dim: 嵌入維度
        """
        self.persist_path = persist_path
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        
        # 確保儲存目錄存在
        Path(persist_path).mkdir(parents=True, exist_ok=True)
        
        # 初始化嵌入模型
        try:
            self.embedder = FactCheckEmbedding(output_dimensionality=embedding_dim)
            logger.info("向量儲存器初始化完成")
        except Exception as e:
            logger.error(f"初始化嵌入模型失敗: {e}")
            raise
        
        # 初始化 ChromaDB 客戶端
        self._init_chroma_client()
        
        # 初始化向量索引
        self.index = None
        self.nodes = []
        
    def _init_chroma_client(self):
        """初始化 ChromaDB 客戶端"""
        try:
            # 創建持久化客戶端
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_path,
                settings=Settings(
                    anonymized_telemetry=False, 
                    allow_reset=True
                )
            )
            
            # 獲取或創建集合
            self.chroma_collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "事實查核報告向量資料庫"}
            )
            
            logger.info(f"成功初始化 ChromaDB，集合: {self.collection_name}")
            logger.info(f"當前集合中有 {self.chroma_collection.count()} 個文檔")
            
        except Exception as e:
            logger.error(f"初始化 ChromaDB 失敗: {e}")
            raise
    
    def create_hierarchical_nodes(self, documents: List[Dict[str, Any]]) -> List[TextNode]:
        """
        創建分層節點結構
        
        Args:
            documents: 文檔列表
            
        Returns:
            節點列表
        """
        try:
            # 將字典轉換為 Document 對象
            doc_objects = []
            
            for doc in documents:
                # 組合文檔內容（標題 + 處理後內容）
                content = f"標題: {doc['title']}\n\n內容: {doc['processed_content']}"
                
                # 處理 categories - ChromaDB 不支援列表，轉換為 string
                categories_list = doc.get('categories', [])
                categories_str = ', '.join(categories_list) if isinstance(categories_list, list) else str(categories_list)
                
                # 創建文檔對象
                document = Document(
                    text=content,
                    metadata={
                        'id': doc['id'],
                        'title': doc['title'],
                        'check_result': doc['check_result'],
                        'categories': categories_str,  
                        'publish_date': doc.get('publish_date', ''),
                        'content_url': doc.get('content_url', ''),
                        'source': doc.get('source', 'TFC')
                    }
                )
                
                doc_objects.append(document)
            
            # 創建分層節點解析器
            node_parser = HierarchicalNodeParser.from_defaults(
                chunk_sizes=[2048, 512, 256],  # 三層分層結構，調整為更合理的大小
                chunk_overlap=30
            )
            
            # 解析節點
            nodes = node_parser.get_nodes_from_documents(doc_objects)
            
            logger.info(f"創建了 {len(nodes)} 個分層節點")
            
            # 獲取葉子節點
            leaf_nodes = get_leaf_nodes(nodes)
            logger.info(f"其中 {len(leaf_nodes)} 個葉子節點")
            
            self.nodes = nodes
            return nodes
            
        except Exception as e:
            logger.error(f"創建分層節點失敗: {e}")
            raise
    
    def build_index(self, documents: List[Dict[str, Any]], force_rebuild: bool = False):
        """
        建立向量索引
        
        Args:
            documents: 文檔列表
            force_rebuild: 是否強制重建索引
        """
        try:
            # 檢查是否需要重建
            if not force_rebuild and self.chroma_collection.count() > 0:
                logger.info(f"向量資料庫已存在，包含 {self.chroma_collection.count()} 個向量")
                while True:
                    response = input("是否要重新建立向量索引？(Y/N): ").strip().upper()
                    if response == 'Y':
                        logger.info("將重新建立向量索引...")
                        break
                    elif response == 'N':
                        logger.info("載入現有索引...")
                        self._load_existing_index()
                        return
                    else:
                        print("輸入無效！請輸入 Y 或 N")

            logger.info("開始建立向量索引...")
            
            # 如果強制重建，清空現有集合
            if force_rebuild and self.chroma_collection.count() > 0:
                logger.info("清空現有向量資料庫...")
                self.chroma_client.delete_collection(self.collection_name)
                self.chroma_collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "事實查核報告向量資料庫"}
                )
            
            # 創建分層節點
            nodes = self.create_hierarchical_nodes(documents)
            
            # 獲取葉子節點用於索引
            leaf_nodes = get_leaf_nodes(nodes)
            
            # 設置 ChromaVectorStore
            vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            # 創建向量索引 
            batch_size = 50  # 每批處理的節點數量
            total_batches = (len(leaf_nodes) + batch_size - 1) // batch_size
            
            logger.info(f"將分 {total_batches} 批處理 {len(leaf_nodes)} 個節點，每批 {batch_size} 個")
            
            try:
                # 創建向量索引
                self.index = VectorStoreIndex(
                    leaf_nodes,
                    storage_context=storage_context,
                    embed_model=self.embedder.embed_model,
                    show_progress=True
                )
            except Exception as e:
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    logger.warning(f"\nAPI 服務暫時不可用，請稍後重試: {e}")
                    logger.info("建議: 等待幾分鐘後重新執行，或使用較小的資料集進行測試")
                raise
            
            logger.info(f"成功建立向量索引，索引了 {len(leaf_nodes)} 個葉子節點")
            logger.info(f"向量資料庫中現有 {self.chroma_collection.count()} 個向量")
            
            self._show_index_statistics()
            
        except Exception as e:
            logger.error(f"建立向量索引失敗: {e}")
            raise
    
    def _load_existing_index(self):
        """載入現有索引"""
        try:
            vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
            
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self.embedder.embed_model
            )
            
            logger.info("成功載入現有向量索引")
            self._show_index_statistics()
            
        except Exception as e:
            logger.error(f"載入現有索引失敗: {e}")
            raise
    
    def _show_index_statistics(self):
        """顯示索引統計資訊"""
        try:
            count = self.chroma_collection.count()
            logger.info("=== 向量索引統計 ===")
            logger.info(f"向量數量: {count}")
            logger.info(f"向量維度: {self.embedding_dim}")
            logger.info(f"儲存路徑: {self.persist_path}")
            logger.info(f"集合名稱: {self.collection_name}")
            
            if count > 0:
                # 顯示一些樣本元數據
                sample = self.chroma_collection.peek(limit=3)
                if sample and sample.get('metadatas'):
                    logger.info("樣本元數據:")
                    for i, metadata in enumerate(sample['metadatas'][:2]):
                        if metadata:
                            logger.info(f"  文檔 {i+1}: {metadata.get('_node_content', 'N/A')[:100]}...")
            
        except Exception as e:
            logger.warning(f"顯示統計資訊失敗: {e}")
    
    def get_index(self) -> Optional[VectorStoreIndex]:
        """獲取向量索引"""
        return self.index
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相似文檔
        
        Args:
            query: 查詢文字
            top_k: 返回前 k 個結果
            
        Returns:
            相似文檔列表
        """
        try:
            if not self.index:
                logger.error("索引尚未建立")
                return []
            
            # 創建檢索器
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            
            # 執行搜索
            nodes = retriever.retrieve(query)
            
            results = []
            for node in nodes:
                result = {
                    'text': node.node.text,
                    'score': node.score,
                    'metadata': node.node.metadata
                }
                results.append(result)
            
            logger.info(f"搜索完成，返回 {len(results)} 個結果")
            return results
            
        except Exception as e:
            logger.error(f"搜索失敗: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Any]:
        """獲取集合資訊"""
        try:
            count = self.chroma_collection.count()
            return {
                'collection_name': self.collection_name,
                'document_count': count,
                'embedding_dimension': self.embedding_dim,
                'persist_path': self.persist_path
            }
        except Exception as e:
            logger.error(f"獲取集合資訊失敗: {e}")
            return {}

def main():
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
        
        # 建立索引
        vector_store.build_index(documents[:100])  # 先測試 100 個文檔
        
        # 測試搜索
        test_query = "阿米斯音樂節詐騙"
        results = vector_store.search_similar(test_query, top_k=3)
        
        print(f"\n搜索結果 ('{test_query}'):")
        for i, result in enumerate(results):
            print(f"{i+1}. 分數: {result['score']:.4f}")
            print(f"   內容: {result['text'][:100]}...")
            print(f"   標題: {result['metadata'].get('title', 'N/A')}")
            print()
        
        # 顯示集合資訊
        info = vector_store.get_collection_info()
        print(f"向量資料庫資訊: {info}")
        
        print("向量索引測試成功！")
        
    except Exception as e:
        print(f"測試失敗: {e}")
        logger.error(f"測試失敗: {e}")

if __name__ == "__main__":
    main()
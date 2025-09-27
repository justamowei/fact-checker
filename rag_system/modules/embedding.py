"""
嵌入模組
使用 Google GenAI embeddings (gemini-embedding-001) 進行文字向量化
"""
import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from google.genai.types import EmbedContentConfig

# 載入環境變數
load_dotenv()

logger = logging.getLogger(__name__)

class FactCheckEmbedding:
    """事實查核嵌入處理器"""
    
    def __init__(self, model_name: str = "gemini-embedding-001", output_dimensionality: int = 768):
        """
        初始化嵌入模型
        
        Args:
            model_name: Gemini 嵌入模型名稱
            output_dimensionality: 輸出向量維度 (768, 1536, 3072)
        """
        self.model_name = model_name
        self.output_dimensionality = output_dimensionality
        
        # 檢查 API 金鑰
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("請在 .env 檔案中設定 GOOGLE_API_KEY")
        
        # 設定嵌入配置（針對事實查核優化）
        embedding_config = EmbedContentConfig(
            task_type="FACT_VERIFICATION",  # 事實驗證任務
            output_dimensionality=output_dimensionality
        )
        
        try:
            # 初始化 Google GenAI 嵌入模型
            self.embed_model = GoogleGenAIEmbedding(
                model_name=model_name,
                api_key=api_key,
                embed_batch_size=50,  # 減少批次處理大小以避免限制
                embedding_config=embedding_config
            )
            logger.info(f"成功初始化 {model_name} 嵌入模型，維度: {output_dimensionality}")
            
        except Exception as e:
            logger.error(f"初始化嵌入模型失敗: {e}")
            raise
    
    def get_text_embedding(self, text: str) -> List[float]:
        """
        獲取單一文字的嵌入向量
        
        Args:
            text: 要嵌入的文字
            
        Returns:
            嵌入向量
        """
        try:
            if not text or not text.strip():
                logger.warning("空文字，返回零向量")
                return [0.0] * self.output_dimensionality
            
            embedding = self.embed_model.get_text_embedding(text.strip())
            
            # 正規化嵌入向量（確保品質）
            embedding = self._normalize_embedding(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"生成嵌入向量失敗: {e}")
            # 返回零向量作為後備
            return [0.0] * self.output_dimensionality
    
    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        批次獲取多個文字的嵌入向量
        
        Args:
            texts: 要嵌入的文字列表
            
        Returns:
            嵌入向量列表
        """
        try:
            # 過濾空文字
            valid_texts = []
            text_indices = []
            
            for i, text in enumerate(texts):
                if text and text.strip():
                    valid_texts.append(text.strip())
                    text_indices.append(i)
            
            if not valid_texts:
                logger.warning("所有文字都是空的，返回零向量")
                return [[0.0] * self.output_dimensionality] * len(texts)
            
            # 批次生成嵌入
            embeddings = self.embed_model.get_text_embedding_batch(valid_texts)
            
            # 正規化所有嵌入向量
            embeddings = [self._normalize_embedding(emb) for emb in embeddings]
            
            # 組合結果，為空文字填充零向量
            result = []
            valid_idx = 0
            
            for i in range(len(texts)):
                if i in text_indices:
                    result.append(embeddings[valid_idx])
                    valid_idx += 1
                else:
                    result.append([0.0] * self.output_dimensionality)
            
            logger.info(f"成功生成 {len(embeddings)} 個嵌入向量")
            return result
            
        except Exception as e:
            logger.error(f"批次生成嵌入向量失敗: {e}")
            # 返回零向量作為後備
            return [[0.0] * self.output_dimensionality] * len(texts)
    
    def get_query_embedding(self, query: str) -> List[float]:
        """
        獲取查詢文字的嵌入向量（針對查詢優化）
        
        Args:
            query: 查詢文字
            
        Returns:
            嵌入向量
        """
        try:
            if not query or not query.strip():
                logger.warning("空查詢，返回零向量")
                return [0.0] * self.output_dimensionality
            
            # 使用專門的查詢嵌入方法
            embedding = self.embed_model.get_query_embedding(query.strip())
            
            # 正規化嵌入向量
            embedding = self._normalize_embedding(embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"生成查詢嵌入向量失敗: {e}")
            # 返回零向量作為後備
            return [0.0] * self.output_dimensionality
    
    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """
        正規化嵌入向量（L2 正規化）
        
        Args:
            embedding: 原始嵌入向量
            
        Returns:
            正規化後的嵌入向量
        """
        import numpy as np
        
        try:
            embedding_array = np.array(embedding)
            norm = np.linalg.norm(embedding_array)
            
            if norm > 0:
                normalized = embedding_array / norm
                return normalized.tolist()
            else:
                return embedding
                
        except Exception as e:
            logger.warning(f"正規化失敗: {e}")
            return embedding
    
    def test_embedding(self):
        """測試嵌入功能"""
        test_texts = [
            "這是一個測試訊息",
            "事實查核系統測試",
            "Google Gemini 嵌入模型"
        ]
        
        logger.info("開始測試嵌入功能...")
        
        # 測試單一文字嵌入
        single_embedding = self.get_text_embedding(test_texts[0])
        logger.info(f"單一文字嵌入維度: {len(single_embedding)}")
        
        # 測試批次嵌入
        batch_embeddings = self.get_batch_embeddings(test_texts)
        logger.info(f"批次嵌入數量: {len(batch_embeddings)}")
        
        # 測試查詢嵌入
        query_embedding = self.get_query_embedding("測試查詢")
        logger.info(f"查詢嵌入維度: {len(query_embedding)}")
        
        logger.info("嵌入功能測試完成！")

def main():
    """主執行函數 - 用於測試"""
    try:
        # 初始化嵌入處理器
        embedder = FactCheckEmbedding()
        
        # 測試功能
        embedder.test_embedding()
        
        print("嵌入模組測試成功！")
        
    except Exception as e:
        print(f"測試失敗: {e}")
        logger.error(f"測試失敗: {e}")

if __name__ == "__main__":
    main()
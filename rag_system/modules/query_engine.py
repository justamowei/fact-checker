"""
查詢引擎模組
整合 Gemini 2.0 Flash 作為 LLM 建立 RAG 查詢引擎
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.gemini import Gemini
from llama_index.core import PromptTemplate
from .retriever import FactCheckRetriever

# 載入環境變數
load_dotenv()

logger = logging.getLogger(__name__)

class FactCheckQueryEngine:
    """事實查核查詢引擎"""
    
    def __init__(self, retriever: FactCheckRetriever, model_name: str = "models/gemini-2.0-flash"):
        """
        初始化查詢引擎
        
        Args:
            retriever: 檢索器實例
            model_name: Gemini 模型名稱
        """
        self.retriever = retriever
        self.model_name = model_name
        
        # 檢查 API 金鑰
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("請在 .env 檔案中設定 GOOGLE_API_KEY")
        
        # 初始化 Gemini LLM
        try:
            self.llm = Gemini(
                model=model_name,
                api_key=api_key,
                temperature=0.1,  # 低溫度確保準確性
                max_tokens=2048,
                safety_settings={
                    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE", 
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
                }
            )
            logger.info(f"成功初始化 {model_name} LLM")
            
        except Exception as e:
            logger.error(f"初始化 LLM 失敗: {e}")
            raise
        
        # 設定事實查核專用提示詞模板
        self._setup_prompts()
        
        # 創建查詢引擎
        self._create_query_engines()
        
    def _setup_prompts(self):
        """設定提示詞模板"""
        
        # 事實查核專用提示詞
        self.fact_check_prompt = PromptTemplate(
            """你是一個專業的事實查核分析師。請根據提供的事實查核資料庫內容，對使用者的查詢進行準確、客觀的回答。

查詢: {query_str}

相關事實查核資料:
{context_str}

請按照以下格式回答:

## 事實查核結果
[根據資料庫中的事實查核報告，判斷查詢內容的真實性]

## 關鍵證據
[列出支持你判斷的關鍵證據]

## 相關查核報告
[引用相關的事實查核報告，包括標題、查核結果和連結]

## 建議
[對使用者的建議，例如如何驗證資訊的真實性]

注意事項:
1. 只根據提供的事實查核資料回答，不要編造或推測
2. 如果資料庫中沒有直接相關的資訊，請明確說明
3. 保持客觀中立，避免偏見
4. 引用具體的查核報告編號和來源
5. 如果是錯誤訊息，請說明錯誤的原因和正確的資訊
"""
        )
        
        # 一般查詢提示詞
        self.general_prompt = PromptTemplate(
            """你是一個事實查核助手。請根據提供的資料庫內容回答使用者查詢。

查詢: {query_str}

參考資料:
{context_str}

請提供準確、有幫助的回答，並引用相關的資料來源。如果資料庫中沒有相關資訊，請明確說明。
"""
        )
        
        logger.info("成功設定提示詞模板")
    
    def _create_query_engines(self):
        """創建查詢引擎"""
        try:
            # 創建基於 AutoMerging 檢索器的查詢引擎
            self.auto_merging_engine = RetrieverQueryEngine.from_args(
                retriever=self.retriever.auto_merging_retriever,
                llm=self.llm,
                text_qa_template=self.fact_check_prompt
            )
            
            # 創建基於基礎檢索器的查詢引擎
            self.base_engine = RetrieverQueryEngine.from_args(
                retriever=self.retriever.base_retriever,
                llm=self.llm,
                text_qa_template=self.general_prompt
            )
            
            logger.info("成功創建查詢引擎")
            
        except Exception as e:
            logger.error(f"創建查詢引擎失敗: {e}")
            raise
    
    def query(self, question: str, use_auto_merging: bool = True, detailed: bool = True) -> Dict[str, Any]:
        """
        執行事實查核查詢
        
        Args:
            question: 使用者問題
            use_auto_merging: 是否使用 AutoMerging 檢索器
            detailed: 是否返回詳細資訊
            
        Returns:
            查詢結果字典
        """
        try:
            if not question or not question.strip():
                return {
                    'success': False,
                    'error': '查詢問題不能為空',
                    'answer': '',
                    'sources': []
                }
            
            logger.info(f"開始處理事實查核查詢: '{question}'")
            
            # 選擇查詢引擎
            engine = self.auto_merging_engine if use_auto_merging else self.base_engine
            engine_type = "AutoMerging" if use_auto_merging else "Base"
            
            # 執行查詢
            response = engine.query(question.strip())
            
            # 準備結果
            result = {
                'success': True,
                'question': question,
                'answer': str(response),
                'engine_type': engine_type,
                'model': self.model_name
            }
            
            # 如果需要詳細資訊
            if detailed:
                # 獲取檢索到的源文檔
                source_nodes = getattr(response, 'source_nodes', [])
                sources = []
                
                for i, node in enumerate(source_nodes):
                    source = {
                        'rank': i + 1,
                        'score': getattr(node, 'score', 0.0),
                        'text_snippet': node.node.text[:200] + "..." if len(node.node.text) > 200 else node.node.text,
                        'metadata': node.node.metadata
                    }
                    
                    # 提取關鍵元數據
                    metadata = node.node.metadata
                    if metadata:
                        source.update({
                            'title': metadata.get('title', ''),
                            'check_result': metadata.get('check_result', ''),
                            'categories': metadata.get('categories', []),
                            'publish_date': metadata.get('publish_date', ''),
                            'content_url': metadata.get('content_url', '')
                        })
                    
                    sources.append(source)
                
                result['sources'] = sources
                result['source_count'] = len(sources)
                
                # 添加統計資訊
                result['statistics'] = self._generate_query_stats(sources)
            
            logger.info(f"查詢完成，使用 {engine_type} 引擎")
            return result
            
        except Exception as e:
            logger.error(f"查詢失敗: {e}")
            return {
                'success': False,
                'error': str(e),
                'question': question,
                'answer': '',
                'sources': []
            }
    
    def compare_engines(self, question: str) -> Dict[str, Any]:
        """
        比較不同查詢引擎的結果
        
        Args:
            question: 查詢問題
            
        Returns:
            比較結果
        """
        try:
            logger.info(f"比較查詢引擎，問題: '{question}'")
            
            # 使用兩種引擎查詢
            auto_result = self.query(question, use_auto_merging=True, detailed=True)
            base_result = self.query(question, use_auto_merging=False, detailed=True)
            
            # 準備比較結果
            comparison = {
                'question': question,
                'auto_merging_engine': auto_result,
                'base_engine': base_result,
                'comparison_analysis': self._analyze_engine_results(auto_result, base_result)
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"比較查詢引擎失敗: {e}")
            return {'error': str(e)}
    
    def _analyze_engine_results(self, auto_result: Dict, base_result: Dict) -> Dict[str, Any]:
        """分析查詢引擎結果"""
        try:
            analysis = {
                'both_successful': auto_result.get('success', False) and base_result.get('success', False),
                'answer_length_difference': 0,
                'source_count_difference': 0,
                'avg_source_score_difference': 0.0
            }
            
            if analysis['both_successful']:
                # 比較答案長度
                auto_len = len(auto_result.get('answer', ''))
                base_len = len(base_result.get('answer', ''))
                analysis['answer_length_difference'] = auto_len - base_len
                
                # 比較源文檔數量
                auto_sources = auto_result.get('sources', [])
                base_sources = base_result.get('sources', [])
                analysis['source_count_difference'] = len(auto_sources) - len(base_sources)
                
                # 比較平均分數
                if auto_sources:
                    auto_avg_score = sum(s['score'] for s in auto_sources) / len(auto_sources)
                else:
                    auto_avg_score = 0.0
                    
                if base_sources:
                    base_avg_score = sum(s['score'] for s in base_sources) / len(base_sources)
                else:
                    base_avg_score = 0.0
                
                analysis['avg_source_score_difference'] = auto_avg_score - base_avg_score
            
            return analysis
            
        except Exception as e:
            logger.warning(f"分析結果失敗: {e}")
            return {}
    
    def _generate_query_stats(self, sources: List[Dict]) -> Dict[str, Any]:
        """生成查詢統計資訊"""
        try:
            if not sources:
                return {'message': '無相關資料'}
            
            # 統計查核結果分佈
            check_results = {}
            categories = {}
            
            for source in sources:
                # 統計查核結果
                result = source.get('check_result', '未知')
                check_results[result] = check_results.get(result, 0) + 1
                
                # 統計分類
                cats = source.get('categories', [])
                for cat in cats:
                    categories[cat] = categories.get(cat, 0) + 1
            
            stats = {
                'total_sources': len(sources),
                'check_results_distribution': check_results,
                'categories_distribution': categories,
                'avg_score': sum(s['score'] for s in sources) / len(sources),
                'score_range': {
                    'min': min(s['score'] for s in sources),
                    'max': max(s['score'] for s in sources)
                }
            }
            
            return stats
            
        except Exception as e:
            logger.warning(f"生成統計資訊失敗: {e}")
            return {}
    
    def get_engine_info(self) -> Dict[str, Any]:
        """獲取查詢引擎資訊"""
        try:
            info = {
                'llm_model': self.model_name,
                'retriever_info': self.retriever.get_retriever_info(),
                'has_auto_merging_engine': hasattr(self, 'auto_merging_engine'),
                'has_base_engine': hasattr(self, 'base_engine')
            }
            
            return info
            
        except Exception as e:
            logger.error(f"獲取引擎資訊失敗: {e}")
            return {}

def main():
    """主執行函數 - 用於測試"""
    import json
    import os
    from .vector_index import FactCheckVectorStore
    from .retriever import FactCheckRetriever
    
    try:
        # 載入處理後的資料
        data_file = "data/processed_tfc_data.json"
        if not os.path.exists(data_file):
            print("請先執行 data_processor.py 來處理資料")
            return
        
        with open(data_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        print(f"載入了 {len(documents)} 個文檔")
        
        # 初始化向量儲存器和檢索器
        vector_store = FactCheckVectorStore()
        vector_store.build_index(documents[:100])  # 測試 100 個文檔
        
        retriever = FactCheckRetriever(vector_store)
        
        # 初始化查詢引擎
        query_engine = FactCheckQueryEngine(retriever)
        
        # 測試查詢
        test_questions = [
            "阿米斯音樂節的徵人訊息是真的嗎？",
            "衛福部的捐款專戶運作方式是什麼？",
            "網路流傳的花蓮災情影片是真的嗎？"
        ]
        
        for question in test_questions:
            print(f"\n=== 查詢: {question} ===")
            
            # 執行查詢
            result = query_engine.query(question)
            
            if result['success']:
                print(f"回答: {result['answer'][:300]}...")
                print(f"引用來源數量: {result.get('source_count', 0)}")
                
                # 顯示主要來源
                sources = result.get('sources', [])
                if sources:
                    print("主要來源:")
                    for i, source in enumerate(sources[:2]):
                        title = source.get('title', 'N/A')
                        check_result = source.get('check_result', 'N/A')
                        print(f"  {i+1}. [{check_result}] {title}")
            else:
                print(f"查詢失敗: {result.get('error', '未知錯誤')}")
        
        # 顯示引擎資訊
        info = query_engine.get_engine_info()
        print(f"\n查詢引擎資訊: {info}")
        
        print("查詢引擎測試成功！")
        
    except Exception as e:
        print(f"測試失敗: {e}")
        logger.error(f"測試失敗: {e}")

if __name__ == "__main__":
    main()
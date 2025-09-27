"""
統一日誌配置模組
確保所有模組都能正確記錄日誌到 fact_check_rag.log
"""
import logging
import sys
from pathlib import Path

def setup_logging(log_file: str = 'fact_check_rag.log', level: int = logging.INFO):
    """
    設定統一的日誌配置

    Args:
        log_file: 日誌檔案名稱
        level: 日誌級別
    """
    # 創建日誌格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # 清除現有的處理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 設定根日誌器
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # 強制重新配置
    )

    # 確保所有模組的日誌都能被記錄
    logging.getLogger('modules').setLevel(level)
    logging.getLogger('modules.data_processor').setLevel(level)
    logging.getLogger('modules.embedding').setLevel(level)
    logging.getLogger('modules.vector_index').setLevel(level)
    logging.getLogger('modules.retriever').setLevel(level)
    logging.getLogger('modules.query_engine').setLevel(level)

    logger = logging.getLogger(__name__)
    logger.info("統一日誌配置已初始化")
    logger.info(f"日誌檔案: {log_file}")
    logger.info(f"日誌級別: {logging.getLevelName(level)}")

def get_logger(name: str) -> logging.Logger:
    """
    獲取配置好的日誌器

    Args:
        name: 日誌器名稱

    Returns:
        配置好的日誌器實例
    """
    return logging.getLogger(name)
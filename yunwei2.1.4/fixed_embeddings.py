#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复的向量嵌入系统
使用ChromaDB默认的384维嵌入模型
"""

import os
import logging
from typing import List
from langchain_core.embeddings import Embeddings
from logger_config import get_logger

logger = get_logger(__name__)

class ChromaDefaultEmbeddings(Embeddings):
    """ChromaDB默认嵌入模型 - 384维"""

    def __init__(self):
        """初始化ChromaDB默认嵌入模型"""
        logger.info("使用ChromaDB默认384维嵌入模型")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档文本"""
        import chromadb.utils.embedding_functions as embedding_functions

        try:
            # 使用ChromaDB的默认嵌入函数
            embedding_func = embedding_functions.DefaultEmbeddingFunction()
            embeddings = embedding_func(texts)
            logger.info(f"成功嵌入 {len(texts)} 个文档，向量维度: {len(embeddings[0])}")
            return embeddings
        except Exception as e:
            logger.error(f"嵌入文档失败: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        import chromadb.utils.embedding_functions as embedding_functions

        try:
            embedding_func = embedding_functions.DefaultEmbeddingFunction()
            embedding = embedding_func([text])
            logger.info(f"成功嵌入查询，向量维度: {len(embedding[0])}")
            return embedding[0]
        except Exception as e:
            logger.error(f"嵌入查询失败: {e}")
            raise

class LocalEmbeddings(Embeddings):
    """本地轻量级嵌入模型 - 使用sentence-transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        logger.info(f"初始化本地嵌入模型: {model_name}")

    def _get_sentence_transformer_embedding(self, texts: List[str]) -> List[List[float]]:
        """使用sentence-transformers获取嵌入"""
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(self.model_name)
            embeddings = model.encode(texts, convert_to_numpy=False)

            # 确保返回List[List[float]]格式
            result = [embedding.tolist() for embedding in embeddings]
            logger.info(f"成功嵌入 {len(texts)} 个文档，向量维度: {len(result[0])}")
            return result

        except ImportError:
            logger.error("sentence-transformers 未安装，请运行: pip install sentence-transformers")
            raise ImportError("需要安装sentence-transformers: pip install sentence-transformers")
        except Exception as e:
            logger.error(f"使用sentence-transformers嵌入失败: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档文本"""
        return self._get_sentence_transformer_embedding(texts)

    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        result = self._get_sentence_transformer_embedding([text])
        return result[0]

# 测试函数
def test_embeddings():
    """测试嵌入功能"""
    print("测试嵌入模型...")

    # 测试ChromaDB默认嵌入
    try:
        chroma_emb = ChromaDefaultEmbeddings()
        test_text = "CPU使用率监控"
        embedding = chroma_emb.embed_query(test_text)
        print(f"✓ ChromaDB默认嵌入成功，维度: {len(embedding)}")
    except Exception as e:
        print(f"✗ ChromaDB默认嵌入失败: {e}")

    # 测试sentence-transformers
    try:
        local_emb = LocalEmbeddings()
        embedding = local_emb.embed_query(test_text)
        print(f"✓ sentence-transformers嵌入成功，维度: {len(embedding)}")
    except Exception as e:
        print(f"✗ sentence-transformers嵌入失败: {e}")

if __name__ == "__main__":
    test_embeddings()
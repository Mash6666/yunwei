#!/usr/bin/env python3
"""
向量数据库检索系统
支持文档加载、向量化存储和相似性检索
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json
import asyncio
from datetime import datetime
import re

import chromadb
from chromadb.config import Settings
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    CSVLoader
)
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from config import Config
from logger_config import get_logger, log_operation, log_performance

# 导入修复的嵌入模型
from fixed_embeddings import ChromaDefaultEmbeddings

logger = get_logger(__name__)


class DashScopeEmbeddings(Embeddings):
    """阿里云DashScope文本嵌入模型"""

    def __init__(self, model_name: str = "text-embedding-v4"):
        self.model_name = model_name
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable is not set")

    def _get_embedding(self, texts: List[str]) -> List[List[float]]:
        """获取文本嵌入向量"""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model_name,
            "input": texts,
            "encoding_format": "float"
        }

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            embeddings = [item["embedding"] for item in result["data"]]
            return embeddings

        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档文本"""
        return self._get_embedding(texts)

    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        embeddings = self._get_embedding([text])
        return embeddings[0]


class DocumentProcessor:
    """文档处理器"""

    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def _token_count(self, text: str) -> int:
        """计算文本的token数量"""
        return len(self.encoding.encode(text))

    def load_document(self, file_path: str) -> List[Document]:
        """根据文件类型加载文档"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_extension = file_path.suffix.lower()

        try:
            if file_extension in ['.txt', '.md']:
                loader = TextLoader(str(file_path), encoding='utf-8')
                documents = loader.load()
                logger.info(f"成功加载文本文件 {file_path}, 共 {len(documents)} 页/段")
                return documents

            elif file_extension == '.csv':
                loader = CSVLoader(str(file_path))
                documents = loader.load()
                logger.info(f"成功加载CSV文件 {file_path}, 共 {len(documents)} 行")
                return documents

            else:
                # 对于不支持的格式，尝试使用文本加载器
                logger.warning(f"不支持的文件类型 {file_extension}，尝试使用文本加载器")
                loader = TextLoader(str(file_path), encoding='utf-8', errors='ignore')
                documents = loader.load()
                logger.info(f"成功加载文件 {file_path}, 共 {len(documents)} 页/段")
                return documents

        except Exception as e:
            logger.error(f"加载文件失败 {file_path}: {e}")
            raise

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """切分文档"""
        try:
            split_docs = self.text_splitter.split_documents(documents)
            logger.info(f"文档切分完成: {len(documents)} -> {len(split_docs)} 个片段")
            return split_docs
        except Exception as e:
            logger.error(f"文档切分失败: {e}")
            raise


class VectorDatabase:
    """向量数据库管理器"""

    def __init__(self, persist_directory: str = "./knowledge_base"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = "knowledge_base"

        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 初始化嵌入模型 - 使用ChromaDB默认384维模型
        self.embeddings = ChromaDefaultEmbeddings()

        # 文档处理器
        self.document_processor = DocumentProcessor()

        # 获取或创建集合
        self._ensure_collection()

        logger.info(f"向量数据库初始化完成，存储路径: {self.persist_directory}")

    def _ensure_collection(self) -> bool:
        """确保集合存在"""
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "智能运维助手知识库"}
            )
            return True
        except Exception as e:
            logger.error(f"创建或获取集合失败: {e}")
            return False

    def add_documents(self, documents: List[Document], source: str = None) -> bool:
        """添加文档到向量数据库"""
        try:
            if not documents:
                return False

            # 确保集合存在
            if not self._ensure_collection():
                logger.error("无法创建或获取集合，添加文档失败")
                return False

            # 准备文档数据
            ids = []
            texts = []
            metadatas = []

            for i, doc in enumerate(documents):
                doc_id = f"{source}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                ids.append(doc_id)
                texts.append(doc.page_content)

                # 准备元数据
                metadata = doc.metadata.copy()
                if source:
                    metadata["source"] = source
                metadata["added_at"] = datetime.now().isoformat()
                metadatas.append(metadata)

            # 批量添加到向量数据库
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )

            logger.info(f"成功添加 {len(documents)} 个文档片段到向量数据库")
            return True

        except Exception as e:
            logger.error(f"添加文档到向量数据库失败: {e}")
            return False

    def load_and_add_file(self, file_path: str) -> bool:
        """加载文件并添加到向量数据库"""
        try:
            # 加载文档
            documents = self.document_processor.load_document(file_path)

            # 切分文档
            split_docs = self.document_processor.split_documents(documents)

            # 添加到向量数据库
            source = Path(file_path).stem
            return self.add_documents(split_docs, source)

        except Exception as e:
            logger.error(f"加载文件失败 {file_path}: {e}")
            return False

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """相似性搜索"""
        try:
            # 确保集合存在
            if not self._ensure_collection():
                logger.error("集合不存在，无法进行搜索")
                return []

            # 嵌入查询
            query_embedding = self.embeddings.embed_query(query)

            # 执行搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )

            # 格式化结果
            search_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    search_results.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                        "distance": results["distances"][0][i] if results["distances"] and results["distances"][0] else 0.0,
                        "relevance_score": 1 - results["distances"][0][i] if results["distances"] and results["distances"][0] else 1.0
                    })

            logger.info(f"检索到 {len(search_results)} 个相关文档片段")
            return search_results

        except Exception as e:
            logger.error(f"相似性搜索失败: {e}")
            return []

    def search_with_context(self, query: str, k: int = 5) -> Dict[str, Any]:
        """带上下文的搜索"""
        try:
            results = self.similarity_search(query, k)

            if not results:
                return {
                    "query": query,
                    "context": "",
                    "sources": [],
                    "total_results": 0
                }

            # 组合上下文
            context_parts = []
            sources = []

            for i, result in enumerate(results):
                context_parts.append(f"文档片段 {i+1}:\n{result['content']}")
                sources.append({
                    "content": result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"],
                    "metadata": result["metadata"],
                    "relevance_score": result["relevance_score"]
                })

            context = "\n\n".join(context_parts)

            return {
                "query": query,
                "context": context,
                "sources": sources,
                "total_results": len(results)
            }

        except Exception as e:
            logger.error(f"带上下文搜索失败: {e}")
            return {
                "query": query,
                "context": "",
                "sources": [],
                "total_results": 0,
                "error": str(e)
            }

    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            # 确保集合存在
            if not self._ensure_collection():
                logger.error("无法创建或获取集合")
                return {
                    "document_count": 0,
                    "collection_name": self.collection_name,
                    "persist_directory": str(self.persist_directory),
                    "error": "Collection does not exist"
                }

            count = self.collection.count()
            return {
                "document_count": count,
                "collection_name": self.collection.name,
                "persist_directory": str(self.persist_directory),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {
                "document_count": 0,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "error": str(e)
            }

    def reset_database(self) -> bool:
        """重置数据库"""
        try:
            self.client.reset()
            logger.info("向量数据库已重置")
            return True
        except Exception as e:
            logger.error(f"重置向量数据库失败: {e}")
            return False


# 全局向量数据库实例
vector_db = None


def get_vector_database() -> VectorDatabase:
    """获取向量数据库实例"""
    global vector_db
    if vector_db is None:
        vector_db = VectorDatabase()
    return vector_db


async def initialize_knowledge_base(document_folder: str = None) -> bool:
    """初始化知识库"""
    try:
        db = get_vector_database()

        if document_folder and Path(document_folder).exists():
            # 扫描文件夹中的文档
            doc_path = Path(document_folder)
            supported_extensions = {'.pdf', '.txt', '.md', '.csv', '.docx', '.doc', '.xlsx', '.xls'}

            file_count = 0
            for file_path in doc_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    success = db.load_and_add_file(str(file_path))
                    if success:
                        file_count += 1

            logger.info(f"知识库初始化完成，共加载 {file_count} 个文件")

        stats = db.get_collection_stats()
        logger.info(f"向量数据库统计: {stats}")

        return True

    except Exception as e:
        logger.error(f"初始化知识库失败: {e}")
        return False
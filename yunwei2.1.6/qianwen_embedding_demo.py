#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千问嵌入模型演示代码
基于官方演示代码实现
"""

import os
import json
from openai import OpenAI


def qianwen_embedding_demo():
    """
    千问嵌入模型演示
    使用text-embedding-v4模型，维度为1024（千问默认维度）
    """
    # 初始化客户端
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 示例输入文本
    input_text = "衣服的质量杠杠的"

    try:
        # 创建嵌入向量
        completion = client.embeddings.create(
            model="text-embedding-v4",  # 千问嵌入模型
            input=input_text
        )

        # 打印完整结果
        print("=== 千问嵌入模型演示 ===")
        print(f"输入文本: {input_text}")
        print(f"模型: {completion.model}")
        print(f"向量维度: {len(completion.data[0].embedding)}")
        print("\n完整JSON结果:")
        print(completion.model_dump_json())

        # 解析结果
        result = json.loads(completion.model_dump_json())
        embedding_vector = result['data'][0]['embedding']

        print(f"\n=== 向量信息 ===")
        print(f"向量前10个维度: {embedding_vector[:10]}")
        print(f"向量维度数: {len(embedding_vector)}")

        return embedding_vector

    except Exception as e:
        print(f"错误: {e}")
        return None


def batch_embedding_demo():
    """
    批量嵌入演示
    """
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 批量输入文本
    input_texts = [
        "衣服的质量杠杠的",
        "这个产品很棒",
        "服务态度很好",
        "物流速度很快"
    ]

    try:
        print("\n=== 批量嵌入演示 ===")

        completion = client.embeddings.create(
            model="text-embedding-v4",
            input=input_texts
        )

        for i, (text, data) in enumerate(zip(input_texts, completion.data)):
            embedding_vector = data.embedding
            print(f"{i+1}. 文本: '{text}'")
            print(f"   向量维度: {len(embedding_vector)}")
            print(f"   前5个维度: {embedding_vector[:5]}")
            print()

    except Exception as e:
        print(f"批量处理错误: {e}")


def similarity_demo():
    """
    向量相似度计算演示
    """
    import numpy as np

    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 计算余弦相似度
    def cosine_similarity(vec1, vec2):
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2)

    texts = [
        "衣服质量很好",
        "服装品质不错",
        "天气很晴朗"
    ]

    try:
        print("\n=== 向量相似度演示 ===")

        # 获取所有文本的嵌入向量
        completion = client.embeddings.create(
            model="text-embedding-v4",
            input=texts
        )

        embeddings = [data.embedding for data in completion.data]

        # 计算相似度
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                similarity = cosine_similarity(embeddings[i], embeddings[j])
                print(f"'{texts[i]}' 与 '{texts[j]}' 的相似度: {similarity:.4f}")

    except Exception as e:
        print(f"相似度计算错误: {e}")


if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("请设置环境变量 DASHSCOPE_API_KEY")
        print("Windows: set DASHSCOPE_API_KEY=your_api_key")
        print("Linux/Mac: export DASHSCOPE_API_KEY=your_api_key")
        exit(1)

    # 运行演示
    print("千问嵌入模型演示开始...")
    print(f"模型: text-embedding-v4")
    print(f"默认维度: 1024")
    print("-" * 50)

    # 基础演示
    qianwen_embedding_demo()

    # 批量处理演示
    batch_embedding_demo()

    # 相似度演示
    try:
        similarity_demo()
    except ImportError:
        print("\n=== 相似度演示需要numpy ===")
        print("请安装: pip install numpy")

    print("\n演示完成!")
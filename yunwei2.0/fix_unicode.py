#!/usr/bin/env python3
"""
修复main.py中的Unicode标签问题
"""

import re

# 读取文件
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义替换映射
replacements = {
    '\[CHART\]': '',
    '\[SEARCH\]': '',
    '\[WAIT\]': '',
    '\[OK\]': '',
    '\[ERROR\]': '',
    '\[ALERT\]': '',
    '\[CRITICAL\]': '严重',
    '\[WARNING\]': '警告',
    '\[POINT\]': '',
    '\[CONFIG\]': '',
    '\[SERVER\]': '',
    '\[USER\]': '',
    '\[PROMETHEUS\]': '',
    '\[MODEL\]': '',
    '\[API\]': '',
    '\[THRESHOLD\]': '',
    '\[HISTORY\]': '',
    '\[ACTION\]': '',
    '\[CHAT\]': '',
    '\[BYE\]': '',
    '\[TIPS\]': '',
    '\[LIST\]': '',
    '\[MSG\]': '',
    '\[VALUE\]': '',
    '\[TIME\]': '',
}

# 执行替换
for pattern, replacement in replacements.items():
    content = re.sub(pattern, replacement, content)

# 写回文件
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Unicode标签修复完成!")
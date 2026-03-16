---
name: data-label-analyzer
description: "要素抽取类数据：NL2SQL 标注质量分析工具。检测幻觉标注（问题中没有的要素值），输出带标注列的结果。Use when: 验证 NL2SQL 标注数据、检测标注中的幻觉值、分析标注准确率、批量筛选问题样本"
---

# 数据标注分析器 (NL2SQL)

专门用于**NL2SQL 文本到 SQL 标注**的质量验证。

## 核心问题

检测**幻觉标注**：标注中的要素值在用户问题中不存在

**示例：**
- 问题：`查询工程用钢部现货 2025 年上半年的销售金额`
- 标注：`{"部门": "工程用钢部", "订货用户": "本田贸易"}` ❌
- 说明：`订货用户=本田贸易` 在问题中没有提及 → 幻觉标注

## 快速开始

### 1. 验证标注（输出带标注列）

```bash
python skills/data-label-analyzer/scripts/validate_annotations.py \
  --input your_data.jsonl \
  --output results.jsonl
```

**输入格式 (JSONL):**
```json
{"query": "查询工程用钢部现货 2025 年上半年的销售金额", "label": {"部门": "工程用钢部", "订货用户": "本田贸易"}}
```

**输出格式：** 原始数据 + 【标注】+【说明】+【正确标注】三列
```json
{"query": "...", "label": {...}, "标注": 1, "说明": "幻觉标注：'订货用户' 的值 '本田贸易' 在问题中不存在", "正确标注": {"部门": "工程用钢部"}}
{"query": "...", "label": {...}, "标注": 0, "说明": "", "正确标注": {"部门": "工程用钢部", "订货用户": "本田贸易"}}
```

### 2. 筛选错误样本

```bash
# 直接筛选出标注=1 的行
jq 'select(.标注 == 1)' results.jsonl > errors.jsonl
```

### 3. 统计准确率

```bash
# 正确数量
jq 'select(.标注 == 0)' results.jsonl | wc -l

# 错误数量  
jq 'select(.标注 == 1)' results.jsonl | wc -l
```

## 完整工作流

```bash
# Step 1: 验证（输出带标注列 + 正确标注）
python scripts/validate_annotations.py --input data.jsonl --output results.jsonl

# Step 2: 查看统计（脚本会自动打印）
# Step 3: 筛选错误样本人工修正
jq 'select(.标注 == 1)' results.jsonl > errors.jsonl

# Step 4: 直接使用【正确标注】列替换原标注（自动化修正）
# Step 5: 修正后重新验证...
```

## 参数说明

### validate_annotations.py

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--input` | 必填 | 输入 JSONL 文件 |
| `--output` | 必填 | 输出结果（带标注列） |
| `--query-field` | `query` | 问题字段名 |
| `--label-field` | `label` | 标注字段名 |

## 错误类型说明

| 错误类型 | 说明 |
|----------|------|
| `hallucination` | 标注的值在问题中不存在（最严重） |
| `partial_match` | 值与问题部分匹配（可能需要人工确认） |
| `missing_query` | 问题字段为空 |

## 输出说明

| 列名 | 类型 | 说明 |
|------|------|------|
| `标注` | 0/1 | 0=正确，1=有误 |
| `说明` | 文本 | 错误原因（正确时为空） |
| `正确标注` | JSON | 修正后的标注（仅保留问题中实际存在的值） |

## 迭代优化流程

```
1. 初始标注 → 2. 批量验证 → 3. 筛选错误样本 → 4. 人工修正
       ↑                                                  ↓
       └────────────────── 重新验证 ←─────────────────────┘

重复直到准确率达到目标（建议>95%）
```

## 相关文件

- `scripts/validate_annotations.py` - 标注验证（核心脚本）
- `references/improvement_strategies.md` - 优化策略

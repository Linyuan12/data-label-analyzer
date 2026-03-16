#!/usr/bin/env python3
"""
找出有问题的样本，用于人工审核和修正

Usage:
    python find_problematic_samples.py --input validation_results.jsonl --output problematic.jsonl

输出：
- 所有标注错误的样本
- 按错误严重程度排序
"""

import json
import argparse
from typing import Dict, List, Any


def severity_score(result: Dict[str, Any]) -> float:
    """计算错误严重程度分数"""
    score = 0.0
    
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    
    # 错误权重
    for error in errors:
        error_type = error.get("type", "")
        if error_type == "hallucination":
            score += 10  # 幻觉标注最严重
        elif error_type == "missing_text":
            score += 8
        elif error_type == "invalid_label_format":
            score += 5
        else:
            score += 3
    
    # 警告权重较低
    score += len(warnings) * 0.5
    
    return score


def extract_problematic_samples(results: List[Dict[str, Any]], 
                                 min_severity: float = 1.0,
                                 limit: int = 100) -> List[Dict[str, Any]]:
    """提取有问题的样本"""
    
    problematic = []
    
    for result in results:
        if not result.get("errors") and not result.get("warnings"):
            continue
        
        severity = severity_score(result)
        if severity < min_severity:
            continue
        
        problematic.append({
            "severity_score": severity,
            "line": result.get("line"),
            "text": result.get("original", {}).get("text", ""),
            "original_labels": result.get("original", {}).get("label", {}),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "suggested_fix": generate_suggested_fix(result)
        })
    
    # 按严重程度排序
    problematic.sort(key=lambda x: x["severity_score"], reverse=True)
    
    return problematic[:limit]


def generate_suggested_fix(result: Dict[str, Any]) -> str:
    """生成修正建议"""
    errors = result.get("errors", [])
    
    if not errors:
        return "无需修正"
    
    suggestions = []
    for error in errors:
        error_type = error.get("type")
        entity_type = error.get("entity_type")
        value = error.get("value")
        
        if error_type == "hallucination":
            suggestions.append(f"删除幻觉要素 '{entity_type}': '{value}' (原文中不存在)")
        elif error_type == "partial_match":
            suggestions.append(f"核对要素 '{entity_type}': '{value}' 可能与原文不完全匹配")
        elif error_type == "empty_value":
            suggestions.append(f"补充要素 '{entity_type}' 的值")
    
    return "; ".join(suggestions) if suggestions else "需要人工审核"


def main():
    parser = argparse.ArgumentParser(description="找出有问题的样本")
    parser.add_argument("--input", required=True, help="验证结果 JSONL 文件路径")
    parser.add_argument("--output", required=True, help="输出问题样本 JSONL 文件路径")
    parser.add_argument("--limit", type=int, default=100, help="最多输出多少个样本")
    parser.add_argument("--min-severity", type=float, default=1.0, help="最小严重程度分数")
    
    args = parser.parse_args()
    
    # 读取验证结果
    results = []
    with open(args.input, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    
    # 提取问题样本
    problematic = extract_problematic_samples(
        results, 
        min_severity=args.min_severity,
        limit=args.limit
    )
    
    # 写入输出
    with open(args.output, 'w', encoding='utf-8') as f:
        for sample in problematic:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    # 打印统计
    print(f"\n{'='*50}")
    print(f"问题样本提取完成")
    print(f"{'='*50}")
    print(f"发现 {len(problematic)} 个问题样本")
    print(f"输出文件：{args.output}")
    
    if problematic:
        print(f"\n最严重的前 3 个样本:")
        for i, sample in enumerate(problematic[:3], 1):
            print(f"\n{i}. 严重程度：{sample['severity_score']:.1f}")
            print(f"   文本：{sample['text'][:50]}...")
            print(f"   建议：{sample['suggested_fix']}")


if __name__ == "__main__":
    main()

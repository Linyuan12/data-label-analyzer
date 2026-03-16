#!/usr/bin/env python3
"""
分析标注错误模式

Usage:
    python analyze_errors.py --input validation_results.jsonl --report report.json

分析维度：
1. 错误类型分布
2. 高频错误要素类型
3. 错误样本特征分析
"""

import json
import argparse
from collections import defaultdict
from typing import Dict, List, Any


def analyze_errors(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析错误模式"""
    
    error_types = defaultdict(int)
    entity_type_errors = defaultdict(int)
    error_samples = []
    
    total_samples = len(results)
    error_samples_count = 0
    
    for result in results:
        if result.get("valid", True):
            continue
        
        error_samples_count += 1
        sample_errors = {
            "line": result.get("line"),
            "errors": []
        }
        
        for error in result.get("errors", []):
            error_type = error.get("type", "unknown")
            error_types[error_type] += 1
            
            entity_type = error.get("entity_type")
            if entity_type:
                entity_type_errors[entity_type] += 1
            
            sample_errors["errors"].append({
                "type": error_type,
                "entity_type": entity_type,
                "value": error.get("value"),
                "message": error.get("message")
            })
        
        if sample_errors["errors"]:
            error_samples.append(sample_errors)
    
    # 计算统计
    report = {
        "summary": {
            "total_samples": total_samples,
            "error_samples": error_samples_count,
            "error_rate": error_samples_count / total_samples if total_samples > 0 else 0,
            "total_errors": sum(error_types.values())
        },
        "error_type_distribution": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)),
        "entity_type_error_distribution": dict(sorted(entity_type_errors.items(), key=lambda x: x[1], reverse=True)),
        "top_error_samples": error_samples[:20]  # 只显示前 20 个错误样本
    }
    
    # 生成改进建议
    suggestions = generate_suggestions(report)
    report["suggestions"] = suggestions
    
    return report


def generate_suggestions(report: Dict[str, Any]) -> List[str]:
    """基于错误分析生成改进建议"""
    suggestions = []
    
    error_dist = report.get("error_type_distribution", {})
    entity_dist = report.get("entity_type_error_distribution", {})
    
    # 针对幻觉标注的建议
    if error_dist.get("hallucination", 0) > 0:
        hallucination_rate = error_dist["hallucination"] / report["summary"]["total_errors"]
        suggestions.append(
            f"🚨 幻觉标注占比 {hallucination_rate:.1%} - 建议：\n"
            f"   - 在标注指南中强调'原文必须有依据'原则\n"
            f"   - 对标注者进行反幻觉培训\n"
            f"   - 考虑添加自动验证步骤"
        )
    
    # 针对特定要素类型的建议
    if entity_dist:
        top_error_entity = list(entity_dist.keys())[0]
        top_error_count = entity_dist[top_error_entity]
        suggestions.append(
            f"⚠️ 要素 '{top_error_entity}' 错误最多 ({top_error_count} 次) - 建议：\n"
            f"   - 检查该要素的定义是否清晰\n"
            f"   - 提供更多标注示例\n"
            f"   - 考虑是否需要拆分或合并该要素类型"
        )
    
    # 总体准确率建议
    error_rate = report["summary"]["error_rate"]
    if error_rate > 0.3:
        suggestions.append(
            f"🔴 标注错误率 {error_rate:.1%} 较高 - 建议：\n"
            f"   - 重新审核标注指南\n"
            f"   - 对标注者进行再培训\n"
            f"   - 考虑引入多人标注 + 仲裁机制"
        )
    elif error_rate > 0.1:
        suggestions.append(
            f"🟡 标注错误率 {error_rate:.1%} 中等 - 建议：\n"
            f"   - 针对高频错误类型进行专项优化\n"
            f"   - 增加质量抽检频率"
        )
    else:
        suggestions.append(
            f"🟢 标注错误率 {error_rate:.1%} 较低 - 建议：\n"
            f"   - 保持当前标注流程\n"
            f"   - 重点关注剩余错误的根因"
        )
    
    return suggestions


def main():
    parser = argparse.ArgumentParser(description="分析标注错误模式")
    parser.add_argument("--input", required=True, help="验证结果 JSONL 文件路径")
    parser.add_argument("--report", required=True, help="输出报告文件路径 (JSON)")
    parser.add_argument("--text-report", help="可选：输出文本报告路径")
    
    args = parser.parse_args()
    
    # 读取验证结果
    results = []
    with open(args.input, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    
    # 分析错误
    report = analyze_errors(results)
    
    # 写入 JSON 报告
    with open(args.report, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 可选：写入文本报告
    if args.text_report:
        with open(args.text_report, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("标注错误分析报告\n")
            f.write("=" * 60 + "\n\n")
            
            summary = report["summary"]
            f.write(f"📊 总体统计\n")
            f.write(f"   总样本数：{summary['total_samples']}\n")
            f.write(f"   错误样本：{summary['error_samples']}\n")
            f.write(f"   错误率：{summary['error_rate']:.1%}\n")
            f.write(f"   总错误数：{summary['total_errors']}\n\n")
            
            f.write(f"📋 错误类型分布\n")
            for error_type, count in report["error_type_distribution"].items():
                f.write(f"   {error_type}: {count}\n")
            f.write("\n")
            
            f.write(f"🏷️ 要素类型错误分布\n")
            for entity_type, count in report["entity_type_error_distribution"].items():
                f.write(f"   {entity_type}: {count}\n")
            f.write("\n")
            
            f.write(f"💡 改进建议\n")
            for i, suggestion in enumerate(report["suggestions"], 1):
                f.write(f"{i}. {suggestion}\n\n")
        
        print(f"文本报告：{args.text_report}")
    
    print(f"\n分析完成！")
    print(f"错误率：{report['summary']['error_rate']:.1%}")
    print(f"JSON 报告：{args.report}")


if __name__ == "__main__":
    main()

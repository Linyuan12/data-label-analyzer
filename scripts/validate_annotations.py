#!/usr/bin/env python3
"""
验证 NL2SQL 标注结果，检测幻觉标注，支持 Excel 输入输出

Usage:
    方式 1: 修改变量后直接运行
        input_file = "./数据分析 0311"
        output_file = "./数据分析 0311_验证结果"
    
    方式 2: 命令行参数
        python validate_annotations.py --input data.xlsx --output results.xlsx

检测类型：
1. 幻觉标注：标注的要素值在问题中不存在
2. 抽取错误：标注的值与问题不匹配

输出列：
- 标注：0=正确，1=有误
- 说明：错误原因
- 正确标注：修正后的标注（仅保留问题中实际存在的值）
"""

import json
import argparse
import re
import os
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher

# ==================== 配置区域 ====================
# 直接修改变量即可，无需命令行参数
input_file = "./数据重审.xlsx"
output_file = "./数据重审_分析修正结果.xlsx"

# 字段名配置
query_field = "问题"           # 问题字段名
label_field = "原抽取结果"      # 标注字段名

# 是否导出 Excel
export_excel = True        # True=导出 Excel, False=不导出

# Excel 配置
excel_sheet_name = "标注验证结果"  # Excel 工作表名称
# ================================================


def normalize_text(text: str) -> str:
    """标准化文本（去除多余空白、统一标点）"""
    text = ' '.join(text.split())
    text = text.lower()
    return text.strip()


def parse_label_string(label_str: str) -> Any:
    """
    解析标注字符串为 Python 对象
    
    支持格式：
    - JSON: {"时间": "2025 年"}
    - Python dict: {'时间': '2025 年'}
    - 空字符串：返回空字典
    """
    if not label_str or not isinstance(label_str, str):
        return {}
    
    label_str = label_str.strip()
    if not label_str:
        return {}
    
    # 尝试 JSON 解析
    try:
        return json.loads(label_str)
    except:
        pass
    
    # 尝试将单引号替换为双引号后解析
    try:
        label_str_fixed = label_str.replace("'", '"')
        return json.loads(label_str_fixed)
    except:
        pass
    
    # 如果都无法解析，返回原字符串
    return label_str


def extract_values_from_label(label: Any) -> List[Tuple[str, str]]:
    """
    从标注中提取所有需要验证的要素值
    
    只检查实际从问题中抽取的值，不检查标注框架的键名
    
    Args:
        label: 标注对象，可能是 dict、字符串或嵌套结构
    
    Returns:
        [(要素类型，值), ...] 列表
    """
    values = []
    
    # 标注框架的键名（这些是预定义的维度名称，不需要验证）
    # "维度" 里的值是维度名称（如"交货半年"），是标注体系的一部分，不是从问题中抽取的
    skip_list_keys = {"维度"}
    
    if isinstance(label, dict):
        for key, value in label.items():
            if isinstance(value, dict):
                # 嵌套结构，如 {"时间": {"交货半年": "2025 年上半年"}}
                # 只检查最深层的值
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        # 检查值，而不是键名
                        values.append((f"{key}.{sub_key}", sub_value))
                    elif isinstance(sub_value, list):
                        for item in sub_value:
                            if isinstance(item, str):
                                values.append((f"{key}.{sub_key}", item))
            elif isinstance(value, list):
                # 列表值，如 {"指标": ["销售合同金额含税", "销售额不含税"]}
                # 如果键名是"维度"，里面的值是维度名称，不检查
                if key not in skip_list_keys:
                    for item in value:
                        if isinstance(item, str):
                            values.append((key, item))
            elif isinstance(value, str):
                # 简单键值对，检查值
                values.append((key, value))
    elif isinstance(label, str):
        # 如果是字符串，尝试解析
        parsed = parse_label_string(label)
        if isinstance(parsed, dict):
            values.extend(extract_values_from_label(parsed))
    elif isinstance(label, list):
        for item in label:
            values.extend(extract_values_from_label(item))
    
    return values


def check_value_in_question(value: str, question: str) -> Tuple[bool, float, str]:
    """
    检查标注值是否在问题中存在
    
    Returns:
        (exists, confidence, matched_text)
    """
    value_norm = normalize_text(value)
    question_norm = normalize_text(question)
    
    if not value_norm:
        return False, 0.0, ""
    
    # 精确匹配
    if value_norm in question_norm:
        return True, 1.0, value
    
    # 部分匹配（去除括号、标点等）
    value_clean = re.sub(r'[\(\)（）,\uff0c]', '', value_norm)
    question_clean = re.sub(r'[\(\)（）,\uff0c]', '', question_norm)
    
    if value_clean and value_clean in question_clean:
        return True, 0.95, value_clean
    
    # 模糊匹配
    value_len = len(value_norm)
    if value_len > 0:
        best_ratio = 0.0
        best_match = ""
        for i in range(max(0, len(question_norm) - value_len * 2)):
            window = question_norm[i:i + value_len * 2]
            ratio = SequenceMatcher(None, value_norm, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = window
        
        if best_ratio >= 0.8:
            return True, best_ratio, best_match
    
    return False, 0.0, ""


def extract_correct_values(question: str, label_values: List[Tuple[str, str]]) -> Dict[str, Any]:
    """
    从问题中提取正确的标注值
    
    Args:
        question: 用户问题
        label_values: [(要素类型，标注值), ...]
    
    Returns:
        修正后的标注字典（只保留问题中实际存在的值）
    """
    correct_label = {}
    
    for entity_type, value in label_values:
        exists, confidence, matched = check_value_in_question(value, question)
        
        if exists and confidence >= 0.95:
            # 处理嵌套类型（如"时间。交货半年"）
            if '.' in entity_type:
                main_key, sub_key = entity_type.split('.', 1)
                if main_key not in correct_label:
                    correct_label[main_key] = {}
                if isinstance(correct_label[main_key], dict):
                    correct_label[main_key][sub_key] = value
            else:
                # 简单键值对
                if entity_type in correct_label:
                    # 已存在则转为列表
                    if isinstance(correct_label[entity_type], list):
                        correct_label[entity_type].append(value)
                    else:
                        correct_label[entity_type] = [correct_label[entity_type], value]
                else:
                    correct_label[entity_type] = value
    
    return correct_label


def validate_nl2sql_annotation(sample: Dict[str, Any], 
                                query_field: str = "问题",
                                label_field: str = "原抽取结果") -> Dict[str, Any]:
    """
    验证 NL2SQL 标注
    
    Args:
        sample: 原始样本
        query_field: 问题字段名
        label_field: 标注字段名
    
    Returns:
        验证结果
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "hallucinated_values": [],
        "corrected_label": {}
    }
    
    query = sample.get(query_field, "")
    label_str = sample.get(label_field, "")
    
    # 解析标注字符串
    label = parse_label_string(label_str)
    
    if not query:
        result["valid"] = False
        result["errors"].append({"type": "missing_query", "message": "问题字段为空"})
        return result
    
    # 提取标注中的所有值
    label_values = extract_values_from_label(label)
    
    # 逐个检查每个值是否在问题中存在
    for entity_type, value in label_values:
        exists, confidence, matched = check_value_in_question(value, query)
        
        if not exists:
            result["valid"] = False
            result["errors"].append({
                "type": "hallucination",
                "entity_type": entity_type,
                "value": value,
                "message": f"幻觉标注：'{entity_type}' 的值 '{value}' 在问题中不存在"
            })
            result["hallucinated_values"].append({
                "entity_type": entity_type,
                "value": value
            })
        elif confidence < 1.0:
            result["warnings"].append({
                "type": "partial_match",
                "entity_type": entity_type,
                "value": value,
                "confidence": confidence,
                "message": f"部分匹配：'{entity_type}' 的值 '{value}' 与问题匹配度 {confidence:.2f}"
            })
    
    # 生成修正后的标注
    result["corrected_label"] = extract_correct_values(query, label_values)
    
    return result


def read_excel_data(file_path: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """读取 Excel 文件"""
    import pandas as pd
    
    df = pd.read_excel(file_path, engine='openpyxl')
    
    # 转换为字典列表
    data = df.to_dict('records')
    
    # 获取列名
    columns = df.columns.tolist()
    
    return data, columns


def write_excel_data(data: List[Dict[str, Any]], output_path: str, 
                     original_columns: List[str], sheet_name: str = "标注验证结果"):
    """写入 Excel 文件"""
    import pandas as pd
    
    df = pd.DataFrame(data)
    
    # 调整列顺序：原始列 + 标注 + 说明 + 正确标注
    new_columns = original_columns + ['标注', '说明', '正确标注']
    available_columns = [c for c in new_columns if c in df.columns]
    df = df[available_columns]
    
    # 写入 Excel
    df.to_excel(output_path, index=False, engine='openpyxl', sheet_name=sheet_name)


def main():
    try:
        import pandas as pd
    except ImportError:
        print("❌ 错误：未安装 pandas 或 openpyxl")
        print("   安装命令：pip install pandas openpyxl")
        return
    
    # 检查是否使用命令行参数，否则使用变量
    import sys
    if len(sys.argv) > 1:
        # 使用命令行参数
        parser = argparse.ArgumentParser(description="验证 NL2SQL 标注结果（Excel 版）")
        parser.add_argument("--input", required=True, help="输入 Excel 文件路径")
        parser.add_argument("--output", required=True, help="输出 Excel 文件路径")
        parser.add_argument("--query-field", default="问题", help="问题字段名")
        parser.add_argument("--label-field", default="原抽取结果", help="标注字段名")
        parser.add_argument("--sheet-name", default="标注验证结果", help="Excel 工作表名称")
        
        args = parser.parse_args()
        input_path = args.input
        output_path = args.output
        query_f = args.query_field
        label_f = args.label_field
        sheet_name = args.sheet_name
    else:
        # 使用变量配置
        input_path = input_file
        output_path = output_file
        query_f = query_field
        label_f = label_field
        sheet_name = excel_sheet_name
    
    # 自动添加.xlsx 后缀（如果没有）
    if not input_path.endswith('.xlsx'):
        input_path += '.xlsx'
    if not output_path.endswith('.xlsx'):
        output_path += '.xlsx'
    
    valid_count = 0
    error_count = 0
    
    results = []
    
    print(f"📁 输入文件：{input_path}")
    print(f"📁 输出文件：{output_path}")
    print(f"📊 工作表名：{sheet_name}")
    print(f"{'='*60}")
    
    # 读取 Excel
    try:
        data, original_columns = read_excel_data(input_path)
        print(f"✅ 读取成功：{len(data)} 行，{len(original_columns)} 列")
        print(f"   列名：{', '.join(original_columns)}")
    except Exception as e:
        print(f"❌ 读取 Excel 失败：{e}")
        return
    
    # 验证每一行
    for row_idx, row in enumerate(data, 1):
        sample = dict(row)
        
        result = validate_nl2sql_annotation(
            sample,
            query_field=query_f,
            label_field=label_f
        )
        
        # 构建输出行（保留原始字段 + 新增标注列）
        output_row = dict(row)
        
        if result["valid"]:
            output_row["标注"] = 0
            output_row["说明"] = ""
            output_row["正确标注"] = json.dumps(result["corrected_label"], ensure_ascii=False)
            valid_count += 1
        else:
            output_row["标注"] = 1
            # 生成说明文字
            error_messages = [err["message"] for err in result["errors"]]
            output_row["说明"] = "；".join(error_messages)
            # 输出修正后的标注
            output_row["正确标注"] = json.dumps(result["corrected_label"], ensure_ascii=False)
            error_count += 1
        
        results.append(output_row)
    
    # 写入 Excel
    try:
        write_excel_data(results, output_path, original_columns, sheet_name=sheet_name)
        print(f"✅ Excel 写入成功")
    except Exception as e:
        print(f"❌ 写入 Excel 失败：{e}")
        return
    
    # 打印统计
    total = len(results)
    accuracy = valid_count / total * 100 if total > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"✅ NL2SQL 标注验证完成")
    print(f"{'='*60}")
    print(f"📊 总样本数：{total}")
    print(f"✅ 正确标注：{valid_count} ({accuracy:.1f}%)")
    print(f"❌ 错误标注：{error_count} ({100-accuracy:.1f}%)")
    print(f"\n💾 输出文件：{output_path}")
    print(f"📝 格式：原始数据 + 【标注】+【说明】+【正确标注】四列")
    
    if error_count > 0:
        print(f"\n⚠️  前 5 个错误样本:")
        error_rows = [r for r in results if r.get("标注") == 1][:5]
        for i, row in enumerate(error_rows, 1):
            query = str(row.get(query_f, ""))[:50]
            explanation = row.get("说明", "")[:60]
            correct = row.get("正确标注", "")[:60]
            print(f"  {i}. 问题：{query}...")
            print(f"     说明：{explanation}...")
            print(f"     正确标注：{correct}...")


if __name__ == "__main__":
    main()

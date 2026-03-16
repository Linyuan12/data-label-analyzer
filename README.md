# 数据标注分析器 (Data Label Analyzer)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**NL2SQL 标注质量验证工具** - 自动检测幻觉标注，智能修正标注结果

---

## 🎯 核心功能

- ✅ **幻觉检测**：识别标注中在问题中不存在的要素值
- ✅ **自动修正**：生成仅包含正确抽取值的标注
- ✅ **Excel 支持**：直接读写 Excel 文件，保留原始格式
- ✅ **批量验证**：一次性验证数千条标注数据
- ✅ **详细报告**：输出错误原因和统计信息

### 示例对比

| 问题 | 原标注 | 状态 | 修正后 |
|------|--------|------|--------|
| 查询工程用钢部现货 2025 年上半年的销售金额 | `{"部门": "工程用钢部", "订货用户": "本田贸易"}` | ❌ 幻觉 | `{"部门": "工程用钢部"}` |
| 查询张三的订单 | `{"客户": "张三"}` | ✅ 正确 | `{"客户": "张三"}` |

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/Linyuan12/data-label-analyzer.git
cd data-label-analyzer
pip install pandas openpyxl
```

### 方式 1：修改变量（推荐）

1. 打开 `scripts/validate_annotations.py`
2. 修改顶部配置：

```python
# ==================== 配置区域 ====================
input_file = "/path/to/your/data.xlsx"      # 输入文件
output_file = "/path/to/results.xlsx"       # 输出文件

query_field = "问题"           # 问题字段名
label_field = "原抽取结果"      # 标注字段名
excel_sheet_name = "标注验证结果"
# ================================================
```

3. 运行：
```bash
python scripts/validate_annotations.py
```

### 方式 2：命令行参数

```bash
python scripts/validate_annotations.py \
  --input data.xlsx \
  --output results.xlsx \
  --query-field 问题 \
  --label-field 原抽取结果
```

---

## 📊 输出说明

### 输出格式

自动新增 **3 列**：

| 列名 | 类型 | 说明 |
|------|------|------|
| `标注` | 0/1 | 0=正确，1=有误（含幻觉标注） |
| `说明` | 文本 | 错误原因（正确时为空） |
| `正确标注` | JSON | 修正后的标注（仅保留问题中实际存在的值） |

### 示例输出

```
📊 总样本数：2000
✅ 正确标注：1343 (67.2%)
❌ 错误标注：657 (32.8%)

💾 输出文件：results.xlsx
📝 格式：原始数据 + 【标注】+【说明】+【正确标注】
```

---

## 💡 典型工作流

```
1. 准备数据 → 2. 批量验证 → 3. 筛选错误 → 4. 使用【正确标注】修正
     ↑                                                      ↓
     └──────────────────── 重新验证 ←───────────────────────┘
```

### Excel 操作技巧

1. **筛选错误样本**
   - 打开结果文件
   - 筛选 `标注` 列 = 1
   
2. **批量修正**
   - 复制 `正确标注` 列
   - 粘贴覆盖 `原抽取结果` 列
   
3. **统计准确率**
   - 使用数据透视表或筛选功能
   - 查看脚本输出的统计信息

---

## 🔧 高级用法

### 自定义字段名

```python
# 如果你的 Excel 列名不同
query_field = "question"      # 问题字段
label_field = "annotation"    # 标注字段
```

### 处理嵌套标注

支持复杂结构：
```json
{
  "时间": {"交货半年": "2025 年上半年"},
  "指标": ["销售合同金额含税", "销售额不含税"],
  "限制条件": {"部门": "工程用钢部"}
}
```

### 批量处理多个文件

```bash
for file in data/*.xlsx; do
  python scripts/validate_annotations.py --input "$file" --output "results/${file%.xlsx}_results.xlsx"
done
```

---

## 📁 项目结构

```
data-label-analyzer/
├── scripts/
│   ├── validate_annotations.py    # 核心验证脚本
│   ├── analyze_errors.py          # 错误分析工具
│   └── find_problematic_samples.py # 问题样本筛选
├── references/
│   ├── improvement_strategies.md  # 优化策略
│   └── metrics.md                 # 评估指标
├── sample_data.jsonl              # 示例数据
├── sample_validation.jsonl        # 示例验证结果
├── README.md                      # 本文档
├── SKILL.md                       # 技能详细说明
└── 使用示例.md                     # 中文使用指南
```

---

## ❓ 常见问题

### Q: 准确率多少算合格？

- **训练数据**：建议 >98%
- **测试数据**：建议 >99%
- **快速迭代**：至少 >95%

### Q: 如何处理部分匹配？

脚本会标记匹配度 <100% 但 ≥80% 的值为"部分匹配"，建议人工确认。

### Q: 支持 JSONL 格式吗？

当前版本支持 Excel (.xlsx)。JSONL 支持请参考 `SKILL.md`。

### Q: 标注解析失败？

支持两种格式：
- JSON: `{"时间": "2025 年"}`
- Python dict: `{'时间': '2025 年'}`

### Q: 如何贡献代码？

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- 基于 OpenClaw 技能系统开发
- 感谢所有贡献者和用户反馈

---

**📮 问题反馈**：[GitHub Issues](https://github.com/Linyuan12/data-label-analyzer/issues)

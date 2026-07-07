# 重构方案 (REFACTOR_PLAN.md)

> 生成时间: 2026-07-07
> 目标: 低风险整理，不破坏现有功能

---

## 重构原则

1. **不破坏现有功能** - 只做整理，不改逻辑
2. **不删除文件** - 只移动到 archive/，保留可追溯性
3. **最小改动** - 优先通过目录重组实现，不需要大规模重写
4. **可验证** - 每次改动后运行测试确认

---

## 目标目录结构

```
datasheet-extractor/
├── src/                          # 核心代码
│   ├── extract_raw.py             # PDF 提取 raw text/tables (来自 core/parser.py)
│   ├── normalize_rows.py          # 表格行 → candidate parameter
│   ├── map_parameters.py          # candidate → 标准 schema
│   ├── confidence.py             # 置信度判断
│   ├── export_excel.py           # Excel 生成
│   ├── main.py                   # 总入口
│   └── _private/                 # 内部使用
│       ├── prompts.py
│       ├── text_block_extractor.py
│       └── normalizer.py
├── config/                       # 配置文件
│   ├── schema.yaml               # 标准参数字段
│   ├── synonyms.yaml             # 参数同义词
│   ├── units.yaml                # 单位规则
│   └── manufacturers.yaml         # 厂商别名
├── ai/                           # AI 相关（实验性）
│   ├── generic_extractor.py       # 重命名自 core/ai/
│   ├── merge.py                  # 参数合并
│   └── prompts.py
├── experiments/                   # 实验代码（保留）
├── outputs/                       # 输出目录
│   ├── latest/                   # 最新 Excel
│   ├── archive/                  # 历史版本
│   └── ai_extract/               # AI 中间结果
├── tests/                         # 测试
├── docs/                         # 文档
└── README.md
```

---

## 第一阶段：低风险整理（不改变任何代码逻辑）

### 1.1 创建目录结构

```bash
mkdir -p src/_private
mkdir -p config
mkdir -p outputs/latest
mkdir -p outputs/archive
mkdir -p tests
```

### 1.2 移动文件（不改变内容）

| 原位置 | 新位置 | 说明 |
|--------|--------|------|
| core/ai/prompts.py | src/_private/prompts.py | 内部使用 |
| core/ai/text_block_extractor.py | src/_private/text_block_extractor.py | 内部使用 |
| core/ai/normalizer.py | src/_private/normalizer.py | 内部使用 |
| core/ai/merge_ai_parameters.py | ai/merge.py | AI 合并 |
| core/ai/generic_table_extractor.py | ai/generic_extractor.py | AI 提取（需修复导入） |
| experiments/build_ai_excel_test.py | src/export_excel.py | Excel 生成 |
| experiments/evaluate_ai_extraction.py | tests/evaluate_ai_extraction.py | 移到测试 |

### 1.3 创建配置文件

创建 `config/schema.yaml`:

```yaml
# 标准参数字段定义
parameters:
  - name: RDS(on)
    symbol: RDS(on)
    category: static
    unit: mΩ
    has_temperature: true
    conditions:
      - VGS=18V
      - VGS=15V
      - ID=300A

  - name: VGS(th)
    symbol: VGS(th)
    category: static
    unit: V
    has_temperature: true

  - name: Ciss
    symbol: Ciss
    category: dynamic
    unit: nF

  # ... 完整列表
```

创建 `config/units.yaml`:

```yaml
# 单位白名单
units:
  - kV, mV, μV, V
  - kA, mA, μA, nA, A
  - mΩ, kΩ, MΩ, Ω
  - nF, pF, μF, F
  - nC, pC
  - mJ, μJ, J
  - ns, μs, ms, s
  - nH, μH, mH
  - °C, °C/W
  - g, kg, mm, μm
```

创建 `config/synonyms.yaml`:

```yaml
# Symbol 别名（来自 normalizer.py SYMBOL_ALIASES）
aliases:
  ciss: Ciss
  input capacitance: Ciss
  coss: Coss
  output capacitance: Coss
  crss: Crss
  reverse transfer capacitance: Crss
  rds on: RDS(on)
  rds(on): RDS(on)
  trr: trr
  reverse recovery time: trr
  # ... 完整列表
```

---

## 第二阶段：修复导入问题

### 2.1 修复 ai/generic_extractor.py 的导入

**问题**: 原导入 `from core.module_extractor import (...)` 的模块不存在

**方案**: 创建 `src/extract_raw.py` 作为 pdfplumber 提取的简单封装

```python
# src/extract_raw.py
import pdfplumber
from typing import Dict, List

def extract_with_pdfplumber(pdf_path: str) -> Dict:
    """从 PDF 提取原始文本和表格"""
    # 实现...

def call_deepseek_llm(prompt: str, api_key: str) -> Dict:
    """调用 DeepSeek API"""
    # 实现...
```

### 2.2 更新 ai/generic_extractor.py 的导入

```python
# ai/generic_extractor.py
from src.extract_raw import (
    extract_with_pdfplumber,
    call_deepseek_llm,
)
```

---

## 第三阶段：创建主入口

### 3.1 创建 src/main.py

```python
# src/main.py
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Datasheet Extractor")
    parser.add_argument("--input", required=True, help="Input PDF or directory")
    parser.add_argument("--output", required=True, help="Output Excel")
    parser.add_argument("--mode", choices=["full", "lite", "ai"], default="lite")
    args = parser.parse_args()
    
    if args.mode == "ai":
        from ai.merge import merge_parameters
        # AI 增强模式
    else:
        # 完整/精简模式

if __name__ == "__main__":
    main()
```

---

## 第四阶段：Excel 输出标准化

### 4.1 确保 3 个必需 Sheet 存在

当前 `build_ai_excel_test.py` 已经生成 8 个 sheets：
1. Comparison Matrix
2. Quick View
3. All Parameters
4. Needs Review
5. Raw Tables
6. Summary
7. AI Parameters
8. AI Evaluation

**需要确认的 3 个必需 Sheet**:

| Sheet | 必需字段 | 当前状态 |
|--------|----------|----------|
| Comparison | Parameter, Unit, [每个芯片的值], Status | ✅ 存在 |
| Need_Review | Part Number, Parameter, Extracted Value, Unit, Reason, Source Page, Source Text | ⚠️ 部分字段缺失 |
| Raw_Extracted | PDF, Page, Table, Raw Parameter, Symbol, Value, Unit, Condition, Raw Text | ⚠️ 需补充 |

### 4.2 补充缺失字段

在 `build_ai_excel_test.py` 中补充：

**Need_Review Sheet** 增加字段：
- `Part Number` - 当前只有 `field`（symbol）
- `Reason` - 当前有 `issue` 但格式需统一

**Raw_Extracted Sheet** - 需要新增：
- 当前 `Raw Tables` sheet 只有原始文本
- 需要结构化字段

---

## 第五阶段：置信度规则简化

### 5.1 当前规则（过于复杂）

`normalizer.py` 中的 `determine_status()` 有复杂逻辑。

### 5.2 简化后的规则

```python
def determine_status(param: dict) -> str:
    """
    confirmed:
      - 只有一个候选值
      - 参数名或 symbol 高度匹配（SYMBOL_ALIASES）
      - 单位正确（在 UNIT_WHITELIST 中）
      - source_page 和 source_text 存在且非空
    
    needs_review:
      - 多个候选值
      - 单位缺失或不在白名单
      - condition 缺失
      - 条件依赖参数（强条件依赖）但 condition 为空
      - 规则提取和 LLM 判断不一致
    
    missing:
      - 没有找到候选值
    """
    
    # 1. 检查是否有值
    value = param.get("typ") or param.get("value") or param.get("min")
    if not value:
        return "missing"
    
    # 2. 检查单位
    unit = param.get("unit", "")
    if not _is_valid_unit(unit):
        return "needs_review"
    
    # 3. 检查 symbol 是否已知
    symbol = param.get("symbol", "")
    if not _is_known_symbol(symbol):
        return "needs_alias_review"
    
    # 4. 检查 source_text
    source_text = param.get("source_text", "")
    if not source_text or source_text.strip() in ("-", "—", "N/A"):
        return "needs_review"
    
    # 5. 强条件依赖参数检查
    needs_condition = {"Ciss", "Coss", "Crss", "QG", "QGS", "QGD", 
                       "Eon", "Eoff", "RDS(on)", "Rth JC", "trr", "QRR"}
    if symbol in needs_condition:
        condition = param.get("condition", "")
        if not condition or condition.strip() in ("-", "—"):
            return "needs_review"
    
    return "confirmed"
```

---

## 实施顺序

### 第一步（低风险）
1. 创建目录结构（不移动文件）
2. 生成配置文件（config/*.yaml）
3. 更新文档

### 第二步（低风险）
1. 移动文件到新目录（保持内容不变）
2. 更新导入路径
3. 运行测试确认功能正常

### 第三步（中风险）
1. 创建 src/extract_raw.py（封装 pdfplumber）
2. 修复 ai/generic_extractor.py 的导入
3. 创建 src/main.py

### 第四步（低风险）
1. 补充 Excel sheet 缺失字段
2. 简化置信度规则
3. 运行完整测试

---

## 待确认事项

1. **核心提取流程文件在哪里？** - run_datasheet_tool.py, extract_datasheet.py, core/parser.py 是否存在于其他位置？
2. **输入 PDF 在哪里？** - datasheets_module/ 为空，是否有其他地方存储？
3. **v1.0 Excel 如何生成？** - 当前只有输出文件，没有生成输入文件的脚本

---

## 风险评估

| 改动 | 风险 | 影响 |
|------|------|------|
| 目录重组 | 低 | 文件移动，导入路径需更新 |
| 配置文件拆分 | 中 | 硬编码值移到 YAML，需同步更新逻辑 |
| 导入路径修复 | 中 | 需找到 core/module_extractor.py 的替代实现 |
| 置信度规则简化 | 高 | 可能改变参数状态判断，影响输出 |
| Excel 字段补充 | 低 | 只增加字段，不改变现有数据 |

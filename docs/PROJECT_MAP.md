# 项目文件地图 (PROJECT_MAP.md)

> 生成时间: 2026-07-07
> 扫描范围: /tmp/datasheet-extractor 2/

---

## ⚠️ 关键发现：核心文件缺失

**根据 README.md 应该有但实际不存在的文件：**

| 文件 | README 中的用途 | 状态 |
|------|----------------|------|
| `run_datasheet_tool.py` | CLI 简单入口 | ❌ 不存在 |
| `extract_datasheet.py` | MOSFET 主入口 | ❌ 不存在 |
| `core/parser.py` | MOSFET 解析器 | ❌ 不存在 |
| `core/module_extractor.py` | Module 提取逻辑 | ❌ 不存在 |
| `core/module_aliases.py` | 轻量别名映射 | ❌ 不存在 |
| `core/comparison/module_matrix_builder.py` | Comparison Matrix 构建器 | ❌ 不存在 |
| `core/comparison/module_excel_builder.py` | Module Excel 构建器 | ❌ 不存在 |
| `experiments/lite.py` | Lite 模式入口 | ❌ 不存在 |
| `datasheets_module/*.pdf` | 输入 PDF 文件 | ❌ 目录为空 |

**实际存在的文件只有 AI 实验代码（约 3785 行 Python）：**

```
datasheet-extractor/
├── core/ai/                  # ✅ 存在 (5 文件, 2336 行)
│   ├── prompts.py            # AI 提示词模板
│   ├── text_block_extractor.py  # 机械参数文本提取
│   ├── generic_table_extractor.py  # AI 表格提取（但依赖不存在的模块）
│   ├── normalizer.py         # AI 参数正则化
│   └── merge_ai_parameters.py  # AI 参数合并到 v1.0 Matrix
├── experiments/              # ✅ 存在 (3 文件, 1449 行)
│   ├── build_ai_excel_test.py  # AI Excel 生成脚本
│   ├── evaluate_ai_extraction.py  # AI 提取评估
│   └── ai_extract_wolfspeed_test.py  # Wolfspeed 测试
├── output/                   # 输出文件
│   ├── datasheet_extractor_lite.xlsx  # v1.0-lite 输出 (17KB)
│   └── datasheet_extractor_lite_ai.xlsx  # v1.1 AI 增强版 (92KB)
├── README.md                 # ✅ 存在
└── .git/                    # ✅ 已初始化
```

---

## 核心文件详解

### 1. core/ai/prompts.py (207 行)

**作用**: 定义 AI 提示词模板

**主要函数**:
- `build_page_extraction_prompt()` - 构建单页参数提取提示词
- `build_summary_prompt()` - 构建汇总后处理提示词

**内容**:
- 提取表格参数（Min/Typ/Max, Unit, Conditions）
- 支持机械/绝缘参数（Clearance, Creepage, Weight, Visol, Mounting Torque, Lstray）
- 输出 JSON schema（category, section, symbol, parameter, min/typ/max, unit, condition, source_page, source_text, raw_row, table_context, status, confidence）

**状态**: ✅ 独立完整，无外部依赖

---

### 2. core/ai/text_block_extractor.py (285 行)

**作用**: 当 pdfplumber 丢失表头时，用文本方式提取机械/绝缘参数

**主要函数**:
- `extract_relevant_text_blocks()` - 从页文本提取相关文本块
- `format_text_blocks_for_prompt()` - 格式化为 LLM 提示词
- `HEADING_PATTERNS` - 机械参数标题模式列表

**覆盖的参数类型**:
- Clearance Distance / Creepage Distance（Terminal to Terminal / Terminal to Baseplate）
- Isolation Voltage / Visol
- Weight
- Mounting Torque
- Stray Inductance / Lstray
- Mechanical Characteristics
- Storage/Operating Temperature

**状态**: ✅ 独立完整，无外部依赖

---

### 3. core/ai/normalizer.py (609 行)

**作用**: AI 提取结果的字段修复和标准化

**主要功能**:
- `fix_missing_fields()` - 修复缺失的 unit/symbol/condition
- `determine_status()` - 判断 confirmed / needs_review / needs_alias_review
- `normalize_ai_parameters()` - 批量标准化
- 单位白名单（UNIT_WHITELIST）
- Symbol 别名映射（SYMBOL_ALIASES）
- 机械参数推断规则（MECHANICAL_INFER）

**优先级策略**:
1. 保留已有有效值
2. 管道格式解析（`|symbol|value|unit|condition|`）
3. 数字+单位模式提取

**状态**: ✅ 独立完整，无外部依赖

---

### 4. core/ai/generic_table_extractor.py (471 行)

**作用**: 使用 LLM 从 PDF 页面提取参数

**主要函数**:
- `extract_page_with_ai()` - 单页 AI 提取
- `extract_all_pages_with_ai()` - 全页提取
- `normalize_ai_params()` - 标准化 AI 参数
- `merge_extractions()` - 合并原始提取和 AI 提取

**⚠️ 严重问题**: 导入不存在的模块

```python
from core.module_extractor import (
    extract_with_pdfplumber,
    call_deepseek_llm,
    DEEPSEEK_API_KEY,
)
```

`core/module_extractor.py` 不存在！此文件无法独立运行。

---

### 5. core/ai/merge_ai_parameters.py (764 行)

**作用**: 将 AI 参数合并到 v1.0-lite All Parameters

**主要函数**:
- `make_condition_aware_key()` - 生成条件感知 key（区分 T-T / T-B）
- `find_best_matching_row()` - 查找最佳匹配的 Matrix 行
- `merge_parameters()` - 执行合并（3 个 PASS）

**PASS 1**: AI confirmed 值填充 v1.0 空槽
**PASS 2**: AI needs_alias_review → All Parameters 新行
**PASS 3**: 高优先级参数（trr/QRR/Lstray）冲突检测

**状态**: ✅ 独立完整（无外部依赖），但需要外部提供 all_params_rows 和 ai_params

---

### 6. experiments/build_ai_excel_test.py (766 行)

**作用**: 生成 AI 增强版 Excel

**主要函数**:
- `_condition_key()` - 从 symbol 提取 T-T/T-B 条件
- `overlay_ai_on_matrix()` - 将 AI 参数叠加到 Matrix
- `write_all_params_enhanced()` - 写入增强版 All Parameters
- `write_ai_parameters_sheet()` - 写入 AI Parameters sheet
- `write_ai_evaluation_sheet()` - 写入 AI Evaluation sheet

**输出 Sheet**:
1. Comparison Matrix - 主输出
2. Quick View - 15 核心字段
3. All Parameters - 完整参数列表
4. Needs Review - 待审核项
5. Raw Tables - 原始表格
6. Summary - 统计摘要
7. AI Parameters - AI 提取详情（source_text 可追溯）
8. AI Evaluation - QA 结果

**命令**:
```bash
python3 experiments/build_ai_excel_test.py \
  --base-excel output/datasheet_extractor_lite.xlsx \
  --ai-json output/ai_extract/CAB530M12BM3_ai_parameters_normalized.json \
  --output output/datasheet_extractor_lite_ai.xlsx
```

**状态**: ✅ 可运行（需要正确的输入文件）

---

### 7. experiments/evaluate_ai_extraction.py (246 行)

**作用**: 评估 AI 提取结果

**内容**:
- 预定义的评估用例（EVALUATION_CASES）
- 参数值匹配检查
- source_text 覆盖率检查
- Normalizer 统计

**状态**: ✅ 独立完整，无外部依赖

---

### 8. experiments/ai_extract_wolfspeed_test.py (437 行)

**作用**: Wolfspeed CAB530 专项 AI 提取测试

**内容**:
- 硬编码的 Wolfspeed 型号信息
- 调用 `extract_all_pages_with_ai()`
- 输出评估结果

**状态**: ⚠️ 依赖 `generic_table_extractor`（后者依赖不存在的模块）

---

## PDF 读取流程（应该的样子）

根据 README，完整的 PDF 读取流程应该是：

```
PDF 文件 (datasheets_module/*.pdf)
    ↓
run_datasheet_tool.py (CLI 入口)
    ↓
extract_datasheet.py (MOSFET 主流程)
    ↓
core/parser.py (PDF 解析)
    ↓
core/module_extractor.py (Module 提取)
    ↓
core/comparison/module_matrix_builder.py (Matrix 构建)
    ↓
core/comparison/module_excel_builder.py (Excel 生成)
    ↓
output/datasheet_extractor_lite.xlsx
```

**实际现状**: 以上流程的所有核心文件都不存在！

---

## 表格提取（应该的样子）

根据代码注释，表格提取应该是：

```
pdfplumber 提取原始表格
    ↓
core/ai/text_block_extractor.py (机械参数文本 fallback)
    ↓
core/ai/prompts.py (构建 LLM 提示词)
    ↓
LLM API (DeepSeek)
    ↓
core/ai/generic_table_extractor.py (解析 LLM 输出)
    ↓
core/ai/normalizer.py (标准化字段)
    ↓
core/ai/merge_ai_parameters.py (合并到 v1.0)
    ↓
experiments/build_ai_excel_test.py (生成 Excel)
```

**实际现状**: `generic_table_extractor.py` 依赖不存在的 `core.module_extractor`。

---

## 废弃/临时文件清单

| 文件 | 说明 | 建议 |
|------|------|------|
| `output/ai_extract/debug/*.md` | LLM 输入调试文件 | 归档到 archive/debug/ |
| `output/ai_extract/*.json` | AI 提取缓存 | 保留（可复现结果）|
| `.llm_cache/` | LLM 缓存 | 保留 |
| `.pdfplumber_cache/` | PDF 解析缓存 | 保留 |
| `core/comparison/__pycache__/` | 空目录 | 可删除 |

---

## 未调用函数检测

通过静态分析，未发现明显未被调用的函数。但 `generic_table_extractor.py` 有未满足的导入依赖。

---

## 总结

| 类别 | 数量 |
|------|------|
| 核心 Python 文件 | 8 |
| 总代码行数 | ~3785 |
| 可独立运行的文件 | 5 (normalizer, prompts, text_block_extractor, merge_ai_parameters, evaluate_ai_extraction) |
| 有外部依赖无法运行的文件 | 1 (generic_table_extractor.py) |
| 完全缺失的核心文件 | 8+ (extract_datasheet.py, parser.py, etc.) |
| 缺失的输入 PDF | datasheets_module/ 为空 |

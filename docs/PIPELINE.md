# 当前流程图 (PIPELINE.md)

> 生成时间: 2026-07-07
> ⚠️ 本文档描述"应该"的流程，但核心文件实际已缺失

---

## 完整预期流程

```
PDF 输入
    ↓
┌─────────────────────────────────────┐
│  1. 原始文本/表格提取                │
│     core/parser.py                  │
│     pdfplumber 提取原始文本和表格     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  2. 参数候选值识别                    │
│     core/module_extractor.py         │
│     core/ai/text_block_extractor.py  │
│     (机械参数 fallback)              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  3. AI 参数提取（实验性）            │
│     core/ai/prompts.py              │
│     → LLM API (DeepSeek)           │
│     core/ai/generic_table_extractor.py│
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  4. 参数标准化                       │
│     core/ai/normalizer.py           │
│     - 修复缺失字段                  │
│     - Symbol 别名映射               │
│     - 单位验证                      │
│     - 置信度判断                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  5. 标准字段映射                    │
│     (应该有 map_parameters.py)       │
│     - 候选值 → 标准 schema          │
│     - Alias 处理                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  6. 置信度/needs_review 判断        │
│     confidence.py (应该有)          │
│     - confirmed                     │
│     - needs_review                  │
│     - needs_alias_review             │
│     - missing                       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  7. Excel 输出                      │
│     export_excel.py (应该有)        │
│     或 module_excel_builder.py      │
└─────────────────────────────────────┘
```

---

## 实际存在的流程（AI 部分）

根据 git 仓库中存在的文件，实际流程如下：

```
输入: 
  - v1.0-lite Excel (datasheet_extractor_lite.xlsx)
  - AI 提取的 JSON (CAB530M12BM3_ai_parameters_normalized.json)
    ↓
┌─────────────────────────────────────┐
│  AI 参数合并                        │
│  core/ai/merge_ai_parameters.py     │
│                                     │
│  PASS 1: AI confirmed → 填充空槽   │
│  PASS 2: needs_alias_review → 新行 │
│  PASS 3: 高优先级冲突检测          │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  AI Excel 生成                      │
│  experiments/build_ai_excel_test.py │
│                                     │
│  - overlay_ai_on_matrix()           │
│  - write_all_params_enhanced()      │
│  - write_ai_parameters_sheet()     │
│  - write_ai_evaluation_sheet()     │
└─────────────────────────────────────┘
    ↓
输出: datasheet_extractor_lite_ai.xlsx
```

---

## 混乱点分析

### 混乱点 1: 核心提取流程完全缺失

**问题**: `run_datasheet_tool.py`, `extract_datasheet.py`, `core/parser.py`, `core/module_extractor.py` 全部不存在。

**现状**: git 仓库只有 AI 实验代码，没有主流程。

**影响**: 无法从头运行完整提取，只能在已有 v1.0 Excel 基础上做 AI 增强。

---

### 混乱点 2: generic_table_extractor.py 依赖不存在的模块

**问题**: `core/ai/generic_table_extractor.py` 导入：

```python
from core.module_extractor import (
    extract_with_pdfplumber,
    call_deepseek_llm,
    DEEPSEEK_API_KEY,
)
```

**现状**: `core/module_extractor.py` 不存在。

**影响**: AI 表格提取功能无法独立运行。

---

### 混乱点 3: 缺少 config/ 目录

**问题**: 没有 `config/schema.yaml`, `config/synonyms.yaml`, `config/units.yaml`。

**现状**: 
- 硬编码在 `core/ai/normalizer.py` 里
- UNIT_WHITELIST
- SYMBOL_ALIASES
- _MECHANICAL_INFER

**影响**: 修改规则需要改代码，难以维护。

---

### 混乱点 4: experiments/ 命名不规范

**问题**: `experiments/` 目录包含实际使用的脚本（build_ai_excel_test.py）。

**现状**: 
- `build_ai_excel_test.py` 是生产脚本，但放在 experiments/
- `ai_extract_wolfspeed_test.py` 是测试脚本
- `evaluate_ai_extraction.py` 是评估脚本

**影响**: 难以区分哪些是实验、哪些是正式流程。

---

### 混乱点 5: 输入 PDF 为空

**问题**: `datasheets_module/` 目录为空。

**现状**: 无法运行完整的 PDF → Excel 流程。

**影响**: 只能基于已有 v1.0 Excel 做 AI 增强。

---

## 当前最小可运行命令

```bash
# 1. AI Excel 生成（需要已有 v1.0 Excel 和 AI JSON）
cd /tmp/datasheet-extractor\ 2
python3 experiments/build_ai_excel_test.py \
  --base-excel output/datasheet_extractor_lite.xlsx \
  --ai-json output/ai_extract/CAB530M12BM3_ai_parameters_normalized.json \
  --output output/datasheet_extractor_lite_ai.xlsx

# 2. AI 评估
python3 experiments/evaluate_ai_extraction.py \
  --json output/ai_extract/CAB530M12BM3_ai_parameters_normalized.json \
  --case wolfspeed_cab530_pages_1_3
```

---

## 目标流程 vs 当前流程

| 阶段 | 目标文件 | 实际状态 |
|------|----------|----------|
| 1. PDF 提取 | core/parser.py | ❌ 缺失 |
| 2. 候选值识别 | core/module_extractor.py | ❌ 缺失 |
| 3. AI 提取 | core/ai/generic_table_extractor.py | ⚠️ 有依赖问题 |
| 4. 参数标准化 | core/ai/normalizer.py | ✅ 存在 |
| 5. 字段映射 | config/schema.yaml | ❌ 硬编码 |
| 6. 置信度判断 | confidence.py | ❌ 缺失 |
| 7. Excel 输出 | export_excel.py | ⚠️ 在 build_ai_excel_test.py |

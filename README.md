# Datasheet Extractor Tool

> **⚠️ This is a lightweight datasheet comparison tool, not an industrial-grade datasheet intelligence system.**

Extract structured parameters from SiC MOSFET and Power Module datasheet PDFs into horizontal Excel comparison format.

---

## 安装方法

```bash
# 依赖
pip install pdfplumber openpyxl python-dotenv

# API Key（如需 LLM 提取）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
```

---

## 运行命令

```bash
# 方式 1：简单入口（推荐）
python3 run_datasheet_tool.py --input datasheets_module --output output

# 方式 2：Lite 模式（使用预生成数据）
PYTHONPATH="$(pwd):$PYTHONPATH" python3 experiments/lite.py
```

---

## 输入输出

**输入：** `datasheets_module/*.pdf` — 一个或多个 datasheet PDF 文件

**输出：** `output/datasheet_extractor_lite.xlsx` — 横向对比 Excel

---

## Sheet 说明

| # | Sheet | 说明 |
|---|-------|------|
| 1 | **Comparison Matrix** | 主输出：不同型号横向对比，每型号含 Value / Condition / Source Page，有值填值，无值留空 |
| 2 | **Quick View** | 15 个核心字段：Part Number, Manufacturer, Module Type, Voltage Rating, Current Rating, RDS(on), VGS(th), Eon, Eoff, QG, Ciss, Coss, Rth, Isolation Voltage, Weight |
| 3 | **All Parameters** | 完整参数列表（含 source_text），不要因为不在 schema 里就丢弃 |
| 4 | **Needs Review** | 收集 missing / needs_review / needs_manual_review / needs_alias_review 项 |
| 5 | **Raw Tables** | pdfplumber 原始表格文本，用于人工核对 |
| 6 | **Summary** | 统计摘要 |

---

## 工具原则

```
- extract explicitly listed values
- preserve unknown parameters
- leave missing values blank
- do not infer unlisted parameters
- keep source text for review
```

**不保证：**
- 所有 condition 100% 正确理解
- 图纸尺寸自动提取
- 扫描 PDF 支持
- 新厂商无需人工检查

---

## 已验证型号

| 型号 | 厂商 | 备注 |
|------|------|------|
| ASC300N1200ME3-X | AST Technology | 1200V Gen3-X SiC Module |
| ASC600N1700ME3 | AST Technology | 1700V Gen3 SiC Module |

---

## 已知限制

- **Dimensions**: 如 PDF 只有机械图纸，无表格文字，则不保证提取
- **Scanned PDFs**: 图片扫描 PDF 不保证支持
- **Condition 值**: 不保证 100% 完美理解；不同厂商 condition 格式差异可能需要人工检查
- **新厂商**: alias_review 需要人工核对（Comparison Matrix Notes 标 `needs_alias_review`）
- **Erec**: 未列出则标 needs_manual_review，不从 Qrr 估算

---

## v1.1 AI Audit Mode (实验性)

> ⚠️ **本模式为实验性功能，用于参数溯源和冲突发现，不自动覆盖 v1.0 Matrix 值。**

### 定位

`output/datasheet_extractor_lite_ai.xlsx` 是 AI Enhanced 版本：

- **AI 用于参数补充**：AI 从 datasheet 表格提取参数值
- **AI 用于 source_text 溯源**：每条 AI 参数保留 `source_text`，便于人工核对
- **AI 用于冲突发现**：当 AI 值与 v1.0 Matrix 值不一致时，标记为冲突（红色高亮）
- **不静默覆盖**：v1.0 Matrix 已有的值不会被 AI 自动覆盖

### 规则

| 规则 | 说明 |
|------|------|
| v1.0 confirmed 值 | 不被 AI 自动覆盖 |
| AI 冲突值 | 红色高亮 + Condition 列注明冲突信息 |
| AI 溯源 | AI Parameters sheet 保留完整 source_text |
| matrix_sanity_review | trr / QRR / Lstray 等高优先级参数冲突进入 Needs Review |

### 输出文件

- `output/datasheet_extractor_lite_ai.xlsx` — AI Enhanced Excel（含 8 个 sheets）
- `output/ai_extract/CAB530M12BM3_ai_parameters_normalized.json` — AI 提取的 normalized 参数

### 生成命令

```bash
python3 experiments/build_ai_excel_test.py \
  --base-excel output/datasheet_extractor_lite.xlsx \
  --ai-json output/ai_extract/CAB530M12BM3_ai_parameters_normalized.json \
  --output output/datasheet_extractor_lite_ai.xlsx
```

### 当前 QA 状态

| 检查项 | 状态 |
|--------|------|
| v1.0-lite Excel 未被覆盖 | ✅ |
| MOSFET 主流程未修改 | ✅ |
| AI 不静默覆盖 v1.0 confirmed 值 | ✅ |
| trr / QRR 进入 matrix_sanity_review | ✅ |
| Clearance / Creepage 冲突已标记 | ✅ |
| Matrix conflict cells | 7 |
| Needs Review (AI 新增) | 18 |
| High priority review | 3 (trr, QRR, Lstray) |

---

## 严禁事项

- ❌ 不要修改 `extract_datasheet.py`（MOSFET 主流程）
- ❌ 不要修改 `core/parser.py`（MOSFET 解析器）
- ❌ 不要修改 `output/chip_comparison.xlsx`（MOSFET 输出）
- ❌ 不要接入 Docling
- ❌ 不要新增数据库
- ❌ 不要新增 Web UI
- ❌ 不要继续扩大 schema
- ❌ 不要手动修改最终 Excel
- ❌ 不要提交 `.env` / API key / cache 文件

---

## 文件结构

```
datasheet-extractor/
├── run_datasheet_tool.py          # 简单入口（推荐）
├── extract_datasheet.py           # MOSFET 入口（勿改）
├── core/
│   ├── parser.py                  # MOSFET 解析器（勿改）
│   ├── module_extractor.py       # Module 提取逻辑
│   ├── module_aliases.py         # 轻量别名映射
│   └── comparison/
│       ├── module_matrix_builder.py  # Comparison Matrix 构建器
│       └── module_excel_builder.py # Module Excel 构建器
├── experiments/
│   └── lite.py                   # Lite 模式入口
├── datasheets_module/            # 放 PDF 文件
└── output/
    └── datasheet_extractor_lite.xlsx  # 输出文件
```

---

## 环境变量

```bash
DEEPSEEK_API_KEY=your_api_key_here
```

`.env` 已加入 `.gitignore`，不会提交。

# 提取小工具 (Datasheet Extractor)

> 轻量级 datasheet 参数提取工具 - 从 PDF datasheet 自动提取参数生成 Excel 对比表

## 项目目标

输入一个或多个 datasheet PDF，自动提取指定参数，生成一张干净、正确、人易读的 Excel 对比表。

## 项目阶段

**当前阶段：Step 5.6 - Debug Pipeline 验证阶段**

此阶段目标是验证规则匹配和值解析逻辑，输出为 debug JSON 和 audit Markdown 文件。

### 当前生成的输出文件

| 文件 | 内容 |
|------|------|
| `output/debug_extracted_pages.json` | PDF 页面文本和表格原始数据 |
| `output/raw_candidates_debug.json` | 候选行匹配 debug 数据 |
| `output/candidate_audit.md` | 候选行匹配 audit 报告 |
| `output/raw_params_debug.json` | 解析后参数 debug 数据 |
| `output/value_parse_audit.md` | 值解析 audit 报告 |

### 后续阶段目标

- **Step 6+**: Excel 输出 (final_comparison.xlsx)
- **Future**: LLM 增强、Final Selector、值选择逻辑

当前**不生成** Excel 文件。Excel 输出是后续阶段目标。

## 快速开始

### 安装

```bash
# 克隆项目
cd datasheet-extractor-rebuild

# 安装依赖
pip install -r requirements.txt

# 配置 (可选，用于 LLM 增强，当前阶段不使用)
cp .env.example .env
```

### 运行 (Debug Pipeline)

```bash
# 验证配置文件
python3 main.py --validate-config

# 测试单位转换
python3 main.py --test-units

# 完整 debug pipeline
python3 main.py --pdf tests/sample_datasheets/ASC300N1200ME3.pdf --output output/final_comparison.xlsx
```

注意：当前即使指定 `--output output/final_comparison.xlsx` 也不会生成 Excel，只会生成 debug JSON/MD 文件。

## 项目结构

```
datasheet-extractor-rebuild/
├── main.py                    # CLI 入口
├── requirements.txt           # 依赖
├── .env.example              # 环境变量示例
├── config/
│   └── target_fields.yaml    # 目标字段配置 (30 个字段)
├── pipeline/
│   ├── extractor.py          # PDF 提取层 (pdfplumber)
│   ├── parser.py             # 候选行匹配层
│   ├── models.py             # 数据模型
│   ├── value_parser.py       # 值解析层
│   ├── llm_agent.py          # [stub] LLM 增强层
│   └── post_processor.py     # [stub] 最终值选择层
├── utils/
│   ├── pdf_utils.py          # PDF 底层工具
│   ├── table_normalizer.py   # 表格清洗
│   ├── config_loader.py      # 配置加载
│   ├── unit_converter.py     # 单位换算
│   ├── condition_parser.py   # [stub] 条件解析
│   └── excel_writer.py       # [stub] Excel 输出
├── output/                   # 输出目录 (debug 文件)
├── tests/
│   └── sample_datasheets/    # 测试用 PDF
└── README.md
```

## 模块职责 (已实现)

| 模块 | 职责 |
|------|------|
| `main.py` | CLI 参数解析，入口调度 |
| `extractor.py` | 读取 PDF，提取 page_text 和 raw_tables |
| `parser.py` | 根据 target_fields.yaml 规则做初步匹配 |
| `models.py` | 数据模型定义 |
| `value_parser.py` | 值解析、range/slash-list 处理、单位合理性检查 |
| `pdf_utils.py` | pdfplumber/pypdf 封装 |
| `table_normalizer.py` | 清洗空行空列，保留结构 |
| `config_loader.py` | target_fields.yaml 加载和验证 |
| `unit_converter.py` | 单位换算 (当前禁用) |

## 配置字段

`config/target_fields.yaml` 定义了 **30 个**目标参数，包括：

- 基本信息：Manufacturer, Part Number, Module Type
- 额定值：Voltage Rating, Current Rating
- RDS(on)：@25°C, @150°C
- 阈值电压：VGS(th)
- 电容：Ciss, Coss, Crss
- 栅极电荷：QG, QGS, QGD
- 开关能量：Eon, Eoff
- 反向恢复：trr, QRR, IRRM, Err
- 热阻：Rth JC, Rth JH, Junction Temperature
- 杂散电感：Lstray
- 机械参数：Weight, Visol
- 爬电/间隙：Clearance T-T/T-B, Creepage T-T/T-B

## 技术栈

- Python 3.10+
- pdfplumber, pypdf (PDF 读取)
- PyYAML (配置)
- python-dotenv (环境变量)
- rapidfuzz (模糊匹配)

## 不做什么 (当前阶段禁止)

- ❌ **不生成 Excel** (后续阶段目标)
- ❌ 不做 Web UI / Docker
- ❌ 不做 OCR
- ❌ 不做 LangChain / LlamaIndex
- ❌ 不做单位换算 (当前禁用)
- ❌ 不做 Final Selector
- ❌ 不调用 LLM
- ❌ 不写厂商专用规则
- ❌ 不把任何值标 confirmed
- ❌ 不估算、不编造数据
- ❌ 不混合不同条件的数据

## 许可证

MIT

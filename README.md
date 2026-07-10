# 提取小工具 (Datasheet Extractor)

> 轻量级 datasheet 参数提取工具 - 从 PDF datasheet 自动提取参数生成 Excel 对比表

## 项目目标

输入一个或多个 datasheet PDF，自动提取指定参数，生成一张干净、正确、人易读的 Excel 对比表。

## 项目定位

这不是工业级 datasheet intelligence 系统，也不是复杂 AI agent 系统。

这是一个**轻量 CLI 小工具**，优先保证：
1. ✅ 能跑
2. ✅ 结构清楚
3. ✅ 输出 Excel 可读
4. ✅ 数据尽量正确
5. ✅ 不确定的数据进入 Review Needed
6. ✅ 不乱填、不估算、不幻觉

## 快速开始

### 安装

```bash
# 克隆项目
cd datasheet-extractor-rebuild

# 安装依赖
pip install -r requirements.txt

# 配置 (可选，用于 LLM 增强)
cp .env.example .env
# 编辑 .env 填入 API key
```

### 运行

```bash
# 基本用法 (规则模式)
python3 main.py --input datasheets/ --output output/final_comparison.xlsx

# 单个 PDF
python3 main.py --pdf datasheets/sample.pdf --output output/final_comparison.xlsx

# 启用 LLM 增强 (需要 .env 配置)
python3 main.py --input datasheets/ --output output/final_comparison.xlsx --llm
```

## 输出 Excel 结构

| Sheet | 内容 |
|-------|------|
| Final Comparison | 确定的参数值，格式：Parameter \| Unit \| Part A \| Part B \| ... |
| Review Needed | 需要人工审核的参数 |
| Raw Extracted Params | 所有提取的参数（含来源） |
| Source Evidence | 原始文本用于核对 |

## 项目结构

```
datasheet-extractor-rebuild/
├── main.py                    # CLI 入口
├── requirements.txt           # 依赖
├── .env.example              # 环境变量示例
├── config/
│   └── target_fields.yaml    # 目标字段配置
├── pipeline/
│   ├── extractor.py          # PDF 提取层
│   ├── parser.py             # 规则解析层
│   ├── llm_agent.py         # LLM 增强层 (可选)
│   └── post_processor.py     # 最终值选择层
├── utils/
│   ├── pdf_utils.py          # PDF 底层工具
│   ├── table_normalizer.py   # 表格清洗
│   ├── condition_parser.py   # 条件解析
│   └── excel_writer.py       # Excel 输出
├── output/                   # 输出目录
├── tests/                    # 测试
└── recovered/                # 旧项目残余说明
```

## 模块职责

| 模块 | 职责 |
|------|------|
| `main.py` | CLI 参数解析，入口调度 |
| `extractor.py` | 读取 PDF，提取 page_text 和 raw_tables |
| `parser.py` | 根据 target_fields.yaml 规则做初步匹配 |
| `llm_agent.py` | 可选 LLM 增强，处理复杂表格和条件 |
| `post_processor.py` | **最关键**：值选择、冲突检测、单位检查 |
| `pdf_utils.py` | pdfplumber/pypdf 封装 |
| `table_normalizer.py` | 清洗空行空列，保留结构 |
| `condition_parser.py` | 解析温度/电压/电流/T-T/T-B 等条件 |
| `excel_writer.py` | 输出 4 个 sheet |

## 配置字段

`config/target_fields.yaml` 定义了 31 个目标参数，包括：

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
- pandas, openpyxl (Excel 输出)
- PyYAML (配置)
- python-dotenv (环境变量)
- rapidfuzz (模糊匹配)
- requests/httpx (LLM API 调用)

## 不做什么

- ❌ 不做 Web UI / Docker
- ❌ 不做 OCR
- ❌ 不做 LangChain / LlamaIndex
- ❌ 不做厂商专用适配
- ❌ 不估算、不编造数据
- ❌ 不混合不同条件的数据

## 许可证

MIT

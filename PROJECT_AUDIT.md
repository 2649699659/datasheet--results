# PROJECT_AUDIT.md - Datasheet Extractor Architecture Analysis

> **Date**: 2026-07-15
> **Auditor**: Agent (Architecture Review)
> **Project**: datasheet-extractor-rebuild
> **Language**: Chinese/English
> **Status**: PHASE 1 - Analysis Only (No Code Changes)

---

## 1. 项目结构分析

### 1.1 目录和文件作用

```
datasheet-extractor-rebuild/
├── main.py                          # CLI 入口，流程编排（712 行）
│
├── config/
│   └── target_fields.yaml           # 30 个目标字段定义（9579 字节）
│
├── pipeline/                        # 核心处理流水线
│   ├── extractor.py                 # PDF 页面文本 + 表格提取（337 行）
│   ├── parser.py                   # 候选行匹配（1076 行）⚠️ 最大模块
│   ├── value_parser.py              # 值解析（1882 行）⚠️ 最大模块
│   ├── final_selector.py            # 最终候选选择（1217 行）
│   ├── models.py                   # 数据模型定义（357 行）
│   ├── llm_agent.py                # [stub] LLM 增强（15 行）
│   └── post_processor.py            # [stub] 后处理（26 行）
│
├── extractors/                     # [Step 8 新增] 可插拔后端系统
│   ├── base.py                     # ExtractedTable/Page/Document 数据模型（34 行）
│   ├── pdfplumber_backend.py        # pdfplumber 后端（110 行）
│   ├── camelot_backend.py           # Camelot v2 后端（251 行）
│   └── converters.py                # 格式转换 + 调度器（94 行）
│
├── utils/
│   ├── excel_writer.py             # Excel 输出生成器（855 行）
│   ├── config_loader.py             # YAML 配置加载（255 行）
│   ├── table_normalizer.py          # 表格清洗（205 行）
│   ├── unit_converter.py            # 单位换算（285 行）
│   ├── pdf_utils.py                 # PDF 底层工具（144 行）
│   └── condition_parser.py          # [stub] 条件解析（21 行）
│
├── experiments/
│   └── backend_compare.py          # 后端对比脚本
│
├── tests/
│   └── sample_datasheets/           # 测试 PDF
│
└── output/                         # 调试输出和最终结果
```

**代码行数统计（总计 7896 行 Python）：**

| 模块 | 文件 | 行数 | 占比 | 状态 |
|------|------|------|------|------|
| 值解析 | value_parser.py | 1882 | 23.8% | ⚠️ 过载 |
| 候选选择 | final_selector.py | 1217 | 15.4% | ⚠️ 过大 |
| 候选匹配 | parser.py | 1076 | 13.6% | ⚠️ 过大 |
| Excel 生成 | excel_writer.py | 855 | 10.8% | ⚠️ 过大 |
| 入口编排 | main.py | 712 | 9.0% | 适中 |
| 数据模型 | models.py | 357 | 4.5% | 可接受 |
| PDF 提取 | extractor.py | 337 | 4.3% | 可接受 |
| 表格清洗 | table_normalizer.py | 205 | 2.6% | 可接受 |
| 单位换算 | unit_converter.py | 285 | 3.6% | 可接受 |
| 配置加载 | config_loader.py | 255 | 3.2% | 可接受 |
| Camelot 后端 | camelot_backend.py | 251 | 3.2% | 可接受 |
| 其他 | (多个小文件) | ~459 | 5.8% | - |

### 1.2 当前数据流

```
输入: PDF 文件
  │
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: PDF 提取 (extractor.py / extractors/)                       │
│   - 提取页面文本 + 原始表格                                           │
│   - camelot vs pdfplumber 后端抽象                                   │
│   输出: ExtractedDocument → pipeline_format                          │
└─────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 2: 表格处理 (process_page_tables)                              │
│   - normalize_table: 清洗空行空列                                     │
│   - 判断 valid / empty_after_normalization                           │
└─────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3: 候选行匹配 (parser.py)                                       │
│   - alias 匹配: exact / normalized_symbol / fuzzy                    │
│   - 硬编码 false_positive 检测                                       │
│   - 硬编码 rating_guard (current_rating/voltage_rating 专用规则)    │
│   - 输出: List[RawExtractedParam] candidates                         │
└─────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 5: 值解析 (value_parser.py)                                     │
│   - 解析 min/typ/max/range/slash_list                               │
│   - 单位提取 + ALLOWED_UNITS 硬编码                                   │
│   - HIGH_RISK_FIELDS 特殊处理                                        │
│   - 硬编码 dimension_constraints (rds_on, vgs_th 等)                 │
│   输出: List[RawExtractedParam] with parsed values                  │
└─────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 6: 最终选择 (final_selector.py)                                 │
│   - 评分算法: max 100 分                                             │
│   - DANGEROUS_BLOCKERS / SOFT_WARNINGS 硬编码                        │
│   - HIGH_RISK_FIELDS 特殊规则                                        │
│   - 输出: selection_result (document-based)                          │
└─────────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Step 7: Excel 生成 (excel_writer.py)                                │
│   - 硬编码 _CONDITION_PATTERNS 正则                                  │
│   - 硬编码 _GENERIC_KEY_SUPPRESSES 逻辑                              │
│   - 4 sheets: Final Comparison / Review Needed / Blocked / Source   │
└─────────────────────────────────────────────────────────────────────┘
  │
  ▼
输出: final_comparison.xlsx
```

### 1.3 模块依赖关系

```
main.py (编排层)
  │
  ├──> extractors/
  │     ├── extract_with_backend() [调度器]
  │     ├── camelot_backend.py
  │     └── pdfplumber_backend.py
  │
  ├──> pipeline/extractor.py
  │     └── process_page_tables()
  │
  ├──> pipeline/parser.py
  │     └── parse_table_candidates()
  │           (依赖: target_fields.yaml, rapidfuzz)
  │
  ├──> pipeline/value_parser.py
  │     └── parse_candidate_values()
  │           (依赖: ALLOWED_UNITS, UNIT_PATTERNS, HIGH_RISK_FIELDS)
  │
  ├──> pipeline/final_selector.py
  │     └── select_final_candidates()
  │           (依赖: DANGEROUS_BLOCKERS, SOFT_WARNINGS, HIGH_RISK_FIELDS)
  │
  ├──> utils/excel_writer.py
  │     └── write_excel_report()
  │           (依赖: _CONDITION_PATTERNS, _GENERIC_KEY_SUPPRESSES)
  │
  └──> utils/config_loader.py
        └── load_target_fields()

config/target_fields.yaml
  (被 parser.py, value_parser.py, final_selector.py 共同依赖)
```

---

## 2. 架构判断

### 结论：**传统 Pipeline 架构（NOT Agent）**

### 判断依据

| 特征 | 当前项目 | Agent 架构 | 说明 |
|------|----------|------------|------|
| 处理模式 | 顺序线性 | 循环/反馈 | 数据流是单向的，无迭代 |
| 决策点 | 硬编码 if/else | LLM 推理 | 无 LLM 做判断 |
| 规则存储 | 代码中硬编码 | 配置文件/Skill | 30 个字段的匹配/验证规则散落在各处 |
| 错误恢复 | 无 | 自我纠正 | 无回退/重试机制 |
| 上下文 | 无状态传递 | 有记忆 | 字段之间无信息共享 |
| 扩展方式 | 修改代码 | 增加 Skill | 需要改 parser.py/value_parser.py |
| 多来源处理 | 规则覆盖 | LLM 判断 | 同一参数多来源时靠硬编码优先级 |

### 当前项目符合 Pipeline 的特征

1. **顺序执行**: Step 1 → 2 → 3 → 5 → 6 → 7，线性无分支
2. **无反馈回路**: 候选行匹配结果直接传给值解析，不验证/回退
3. **规则驱动**: 所有决策都是 if/elif/else 硬编码
4. **固定 schema**: 30 个字段固定，增加字段需改代码
5. **黑箱规则**: 为什么 current_rating 选了某行、为什么 eon 落了 review，无法解释

---

## 3. 核心问题分析

### 3.1 应该保留的代码（✅）

| 模块/文件 | 理由 |
|-----------|------|
| `extractors/` 整体 | Camelot + pdfplumber 双后端抽象良好，可插拔设计合理 |
| `pipeline/models.py` | RawExtractedParam dataclass 设计清晰，to_dict/from_dict 完善 |
| `pipeline/extractor.py` | 页面/表格数据结构设计合理 |
| `utils/table_normalizer.py` | 表格清洗逻辑干净，职责单一 |
| `utils/config_loader.py` | YAML 加载验证逻辑可复用 |
| `config/target_fields.yaml` | 30 个字段定义是核心资产，应该保留 |

### 3.2 应该删除/简化的代码（❌）

| 模块/文件 | 问题 | 建议 |
|-----------|------|------|
| `parser.py` 中的 `should_reject_rating_candidate()` | 300+ 行硬编码规则，处理 current_rating/voltage_rating 特殊逻辑 | 迁移到配置文件 |
| `parser.py` 中的 `is_false_positive()` | 100+ 行 Visol/Rth/JC/JH 硬编码判断 | 迁移到配置文件 |
| `value_parser.py` 中的 `ALLOWED_UNITS` | 1882 行文件中最大的字典硬编码 | 迁移到 target_fields.yaml |
| `value_parser.py` 中的 `HIGH_RISK_FIELDS` | 字段名硬编码集合 | 迁移到 target_fields.yaml |
| `final_selector.py` 中的 `DANGEROUS_BLOCKERS` | 硬编码 blocker 集合 | 迁移到 target_fields.yaml |
| `final_selector.py` 中的 `SOFT_WARNINGS` | 硬编码扣分规则 | 迁移到 target_fields.yaml |
| `final_selector.py` 中的 `HIGH_RISK_FIELDS` | 与 value_parser.py 重复 | 合并到一处 |
| `excel_writer.py` 中的 `_GENERIC_KEY_SUPPRESSES` | 硬编码通用键抑制逻辑 | 迁移到配置文件 |
| `parser.py` 中的 `get_review_reason()` | 200+ 行硬编码 review reason 生成 | LLM 替代或配置文件 |
| `parser.py` 中的 `get_rating_accept_reason()` | 150+ 行 current_rating/voltage_rating 专用 | LLM 替代或删除 |

### 3.3 不应该硬编码的逻辑

| 不应该硬编码 | 应该迁移到 |
|-------------|-----------|
| 字段别名 (aliases) | ✅ 已在 target_fields.yaml |
| 字段允许单位 (ALLOWED_UNITS) | ❌ 需从 target_fields.yaml 扩展 |
| 字段风险等级 (HIGH_RISK_FIELDS) | ❌ 需在 target_fields.yaml 中标记 |
| Dangerous blockers 列表 | ❌ 需在 target_fields.yaml 中标记 per-field |
| Soft warnings 扣分值 | ❌ 需在 target_fields.yaml 中标记 per-field |
| rating_guard 规则 | ❌ 需独立的 rating_rules.yaml |
| false_positive 检测规则 | ❌ 需独立的 vendor_adapters.yaml 或 LLM |
| 条件提取正则模式 | ❌ 需在 target_fields.yaml 的 condition_keywords |
| V→VGS 升级逻辑 | ❌ 需在 target_fields.yaml 的 condition_keywords |
| 通用键抑制关系 | ❌ 需在 target_fields.yaml 的 condition_keywords |
| 阈值验证规则 (vgs_th min<typ<max) | ❌ 需在 target_fields.yaml 的 validation_rules |

### 3.4 最大问题总结

**问题 1: 规则爆炸（Rule Explosion）**
- parser.py: 300+ 行处理 current_rating/voltage_rating
- value_parser.py: 500+ 行处理单位/范围/slash-list
- final_selector.py: 400+ 行处理 field-specific 选择逻辑
- excel_writer.py: 300+ 行处理条件提取

**问题 2: 字段间耦合**
- current_rating 和 voltage_rating 的规则散落在 parser.py, value_parser.py, final_selector.py 三处
- clearance/creepage 的 T-T/T-B 匹配逻辑在 parser.py 和 excel_writer.py 两处

**问题 3: 无法处理多来源冲突**
- 当同一个参数有多个有效候选时，依赖硬编码的评分规则选择
- 无法让用户参与决策或解释为什么选 A 不选 B

**问题 4: vendor-specific 适配困难**
- 不同厂商的表格格式略有不同，靠不断添加 if/else 应对
- 无法优雅地处理新的表格格式变体

---

## 4. Agent 化架构设计

### 4.1 目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Agent Orchestrator                          │
│  (Agent Planner - LLM-powered)                                    │
│  负责理解任务、规划步骤、协调 Skill、判断完成标准                   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ PDF Analysis  │   │ Table Extract │   │ Param         │
│ Skill         │   │ Skill         │   │ Understanding │
│               │   │               │   │ Skill         │
│ - 识别 PDF 类型 │   │ - Camelot     │   │ - 理解参数语义 │
│ - 检测文本/扫描 │   │ - pdfplumber  │   │ - 验证数值合理 │
│ - 估算难度     │   │ - 表格质量评分  │   │ - 单位一致性   │
└───────────────┘   └───────────────┘   └───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Validation    │   │ Conflict      │   │ Excel         │
│ Skill         │   │ Resolution     │   │ Reporting     │
│               │   │ Skill         │   │ Skill         │
│ - 字段级验证   │   │ - 多候选排序   │   │ - 格式化输出  │
│ - 跨字段一致性 │   │ - LLM 判断    │   │ - 条件展示    │
│ - 缺失检测    │   │ - 用户确认    │   │ - 多 PDF 对比  │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 4.2 Skill 分解（复用优先）

| Skill | 职责 | 复用现有 | 输入 | 输出 |
|-------|------|----------|------|------|
| **pdf_analysis_skill** | 判断 PDF 类型、难度、文本/扫描 | extractor.py 部分逻辑 | PDF 文件 | PDFAnalysisReport |
| **table_extraction_skill** | Camelot/pdfplumber 提取+质量评分 | extractors/ 整体 | PDFAnalysisReport | List[ExtractedTable] |
| **param_matching_skill** | alias 匹配、行分类 | parser.py 核心逻辑 | ExtractedTable + target_fields | List[CandidateRow] |
| **value_parsing_skill** | 数值/范围/slash-list、单位提取 | value_parser.py 核心逻辑 | CandidateRow | ParsedValue |
| **param_validation_skill** | 字段级验证、单位合理性、阈值检查 | value_parser.py + final_selector.py | ParsedValue | ValidationResult |
| **conflict_resolution_skill** | 多候选排序、LLM 判断 | final_selector.py 核心逻辑 | List[ParsedValue] | SelectedValue |
| **excel_reporting_skill** | Excel 生成、条件格式化 | excel_writer.py 整体 | SelectedValue | Excel 文件 |

### 4.3 Agent 与 Pipeline 的关键区别

| 维度 | 当前 Pipeline | Agent 架构 |
|------|-------------|------------|
| 决策 | 硬编码评分 | LLM 判断 |
| 多候选 | 评分排序 | LLM 推理 + 用户确认 |
| 新字段 | 改代码 | 改 YAML + Skill |
| 错误恢复 | 无 | 回退 + 重试 |
| 跨字段推理 | 无 | Agent 协调器可做 |
| 解释性 | 黑箱 | LLM 生成理由 |
| Vendor 适配 | if/else 爆炸 | LLM 理解表格语义 |

### 4.4 LLM 的角色（不是读取所有内容）

**LLM 不负责：**
- ❌ 读取整个 PDF 的所有文本
- ❌ 解析所有表格的所有行
- ❌ 生成所有字段的候选

**LLM 负责：**
- ✅ **理解**：当规则无法判断时，理解参数语义（如 "VGS(th) 和 VGS(th) Gate Threshold Voltage 有什么区别？"）
- ✅ **判断**：多候选冲突时，判断哪个更可信
- ✅ **验证**：检查提取结果的合理性（如 "VGS(th) = 4V 对于 SiC MOSFET 是否合理？"）
- ✅ **规划**：决定下一步做什么（先提取表格还是先分析页面结构？）
- ✅ **解释**：生成人工可读的决策理由

### 4.5 数据结构设计（保持复用）

```python
# 复用的数据结构
ExtractedDocument     # 来自 extractors/base.py
ExtractedTable        # 来自 extractors/base.py
RawExtractedParam     # 来自 pipeline/models.py ✅ 保留

# 新增的 Skill 输出结构
PDFAnalysisReport     # PDF 类型、难度、文本/扫描判断
TableQualityScore     # Camelot 表格质量评分
ValidationResult      # 字段级验证结果
ConflictResolution    # 多候选判断结果 + 理由
AgentTaskPlan         # Agent 规划的任务步骤
```

---

## 5. 迁移路线图

### Phase 1: 项目整理（不改变架构）

**目标**: 摸清家底，消除重复，整理配置文件

**任务**:
- [ ] 整理 `config/target_fields.yaml`：添加 `allowed_units`, `high_risk`, `dangerous_blockers`, `soft_warnings` 字段
- [ ] 将 `parser.py` 中的 `should_reject_rating_candidate()` 规则迁移到 YAML
- [ ] 将 `parser.py` 中的 `is_false_positive()` 规则迁移到 YAML
- [ ] 将 `value_parser.py` 中的 `ALLOWED_UNITS` 迁移到 YAML
- [ ] 将 `value_parser.py` 中的 `HIGH_RISK_FIELDS` 迁移到 YAML
- [ ] 将 `final_selector.py` 中的 `DANGEROUS_BLOCKERS` / `SOFT_WARNINGS` 迁移到 YAML
- [ ] 将 `excel_writer.py` 中的 `_GENERIC_KEY_SUPPRESSES` 迁移到 YAML
- [ ] 合并 `value_parser.py` 和 `final_selector.py` 中重复的 `HIGH_RISK_FIELDS`
- [ ] 删除 `parser.py` 中的 `get_rating_accept_reason()`（300+ 行，可删除）
- [ ] 整理输出 audit 文件，规范化格式

**验收标准**:
- `target_fields.yaml` 是唯一的规则来源（除了提取逻辑本身）
- `parser.py` < 600 行
- `value_parser.py` < 1000 行
- `final_selector.py` < 800 行
- `excel_writer.py` < 600 行

**产出**: `PROJECT_AUDIT_PHASE1.md` - 整理后的架构文档

---

### Phase 2: 模块 Skill 化

**目标**: 将大模块拆分为独立 Skill，保持 Pipeline 架构

**任务**:
- [ ] 创建 `skills/pdf_analysis_skill/` - PDF 类型分析
- [ ] 创建 `skills/table_extraction_skill/` - 表格提取（封装 Camelot/pdfplumber）
- [ ] 创建 `skills/param_matching_skill/` - 候选行匹配
- [ ] 创建 `skills/value_parsing_skill/` - 值解析
- [ ] 创建 `skills/param_validation_skill/` - 参数验证
- [ ] 创建 `skills/conflict_resolution_skill/` - 冲突解决
- [ ] 创建 `skills/excel_reporting_skill/` - Excel 报告生成
- [ ] 创建 `skills/orchestrator/` - Skill 调度器（简单的基于规则的调度）
- [ ] 更新 `main.py` 为 Skill 调度器调用
- [ ] 每个 Skill 有独立的 `SKILL.md` 和测试

**验收标准**:
- 每个 Skill 可独立测试
- `main.py` 只是调度器，不包含业务逻辑
- 增加新字段只需要改 YAML，不需要改 Skill 代码

**产出**: `SKILL.md` 文件集合 + Skill 测试套件

---

### Phase 3: 加入 Agent Planner

**目标**: 在 Skill 层之上加入 LLM 驱动的规划器

**任务**:
- [ ] 创建 `agent/planner.py` - LLM 驱动的任务规划
- [ ] 实现 `TaskPlanner` 类：接收用户任务 → LLM 规划步骤 → 执行 Skill
- [ ] 添加 `agent/memory.py` - 跨任务记忆（同类 PDF 曾经如何处理）
- [ ] 实现 Skill 调用的反馈循环：Skill 结果 → Planner 判断 → 下一步
- [ ] 添加简单的自我纠正：当 Skill 返回 low confidence 时，LLM 决定重试或降级

**关键设计**:
```
Planner 输入: "从 ASC300N1200ME3.pdf 提取 SiC MOSFET 参数"
Planner 输出: TaskPlan([
    Step("pdf_analysis", skill="pdf_analysis_skill", input=pdf_path),
    Step("table_extraction", skill="table_extraction_skill", depends_on=[0]),
    Step("param_matching", skill="param_matching_skill", depends_on=[1]),
    Step("value_parsing", skill="value_parsing_skill", depends_on=[2]),
    Step("conflict_resolution", skill="conflict_resolution_skill", depends_on=[3]),
    Step("excel_reporting", skill="excel_reporting_skill", depends_on=[4]),
])
```

**验收标准**:
- Agent Planner 可处理单 PDF 提取任务
- LLM 决定 Skill 执行顺序和参数
- 自我纠正机制生效（低 confidence 时重试）

**产出**: `agent/` 模块 + Planner 测试

---

### Phase 4: 加入 LLM Reasoning Layer

**目标**: LLM 参与关键决策，不是读取所有内容

**任务**:
- [ ] 实现 `conflict_resolution_skill` 中的 LLM 判断：当多个候选无法用规则区分时，LLM 判断
- [ ] 实现 `param_validation_skill` 中的 LLM 验证：超出规则范围时，LLM 验证合理性
- [ ] 实现 `param_matching_skill` 的 LLM 辅助：vendor-specific 表格格式由 LLM 理解
- [ ] 添加 `reasoning_trace` 输出：每个决策附带 LLM 推理理由
- [ ] 实现用户确认机制：当 LLM 不确定时，暂停等待用户确认

**LLM 不做**:
- ❌ 读取整个 PDF
- ❌ 解析所有表格行
- ❌ 生成所有候选项

**LLM 只做**:
- ✅ 理解语义：这是什么参数？表格结构是什么？
- ✅ 判断选择：这个候选比那个更好吗？为什么？
- ✅ 验证合理性：这个值对于这个器件类型合理吗？
- ✅ 生成解释：为什么选了这个候选而不是另一个？

**验收标准**:
- 冲突解决时 LLM 有明确的推理过程输出
- 用户可审查和覆盖 LLM 的决定
- reasoning_trace 可导出为人工可读报告

**产出**: LLM reasoning layer + 用户确认 UI（如果需要）

---

### Phase 5: 测试和准确率提升

**目标**: 构建测试集，量化准确率，持续迭代

**任务**:
- [ ] 建立测试 PDF 数据集：按厂家/类型/难度分类
- [ ] 实现自动化准确率测试：提取结果 vs 人工标注 ground truth
- [ ] 测量每种字段类型的准确率：final_candidate vs review_needed vs blocked
- [ ] A/B 测试 Skill 组合：Rule-based vs LLM-assisted
- [ ] 建立回归测试：每次变更后自动运行测试集
- [ ] 准确率目标：final_candidate precision > 90%，review_needed recall > 80%

**测试 PDF 数据集结构**:
```
tests/
├── ground_truth/           # 人工标注结果
│   ├── ASC300N1200ME3.json
│   ├── Wolfspeed_C3M0065065D.json
│   └── ...
├── sample_datasheets/      # 原始 PDF
│   └── ...
└── regression_tests/        # 自动化测试脚本
    └── test_extraction_accuracy.py
```

**验收标准**:
- 每次 PR 必须通过回归测试
- final_candidate precision >= 90%
- 有明确的准确率报告输出

---

## 6. 关键风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Phase 1 整理阶段过于庞大 | 项目无法完成整理就开始重构 | 限制范围，只整理规则，不改提取逻辑 |
| LLM 成本过高 | 每次提取都要调用 LLM | LLM 只在冲突时调用，不读取全量内容 |
| Skill 拆分后协调复杂 | 反而比原来更复杂 | Phase 3 前保持简单调度器，不加 LLM |
| 多 vendor 适配仍然复杂 | 规则无法覆盖所有情况 | Phase 4 LLM reasoning 处理规则外情况 |
| 测试集建立成本高 | 没有 ground truth 无法衡量改进 | 使用已有的 audit 文件作为部分 ground truth |

---

## 7. 立即可执行的下一步（不改变代码）

1. **阅读 `config/target_fields.yaml`** - 理解 30 个字段的完整定义
2. **阅读 `output/selector_audit.md`** - 理解当前选择结果的问题
3. **阅读 `output/candidate_audit.md`** - 理解候选行匹配的问题
4. **建立 Phase 1 的 YAML 重构计划** - 把硬编码规则迁移到 YAML

---

*本报告仅作为架构分析参考，不涉及任何代码修改。*

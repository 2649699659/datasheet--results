# AST Datasheet Extraction Workflow v1

**Version**: 1.0  
**Date**: 2026-07-16  
**Purpose**: OpenClaw-native scripted workflow for AST SiC MOSFET module datasheet parameter extraction

---

## 工作流名称

AST Datasheet Extraction Workflow v1

---

## 目标

用户放入一个 AST SiC MOSFET module datasheet PDF，OpenClaw 按固定步骤运行现有 pipeline，收集 AI review 上下文，调用 parameter review prompt，最后生成可用于后续 repair 的 ai_parameter_review.json。

**当前 v1 只做 review，不做自动 repair。**

---

## 前置条件

- Python 3.10+
- 已安装依赖: `pip install -r requirements.txt`
- 工作目录: 项目根目录

---

## OpenClaw 执行规则

> ⚠️ 严格遵守以下规则：

1. **不要跳步** - 必须按 Step 1-5 顺序执行
2. **不要直接编辑 Excel** - 不要修改 output/final_comparison.xlsx
3. **不要凭空生成参数** - 所有值必须来自 source_text
4. **不要调用 LLM API** - 本阶段只生成 context，不做 AI 审查
5. **所有判断必须引用 source_text/page/field_id** - 不能无依据判断
6. **如果 AI 不确定，必须输出 review_needed** - 宁可保守
7. **如果发现明显错误，输出 suggested_action，但不要直接执行**

---

## 工作流步骤

### Step 1: 运行 Legacy Pipeline

**命令模板**:

```bash
python3 main.py --pdf <PDF_PATH> --output output/final_comparison.xlsx
```

**参数说明**:
- `<PDF_PATH>`: 用户提供的 datasheet PDF 文件路径
- output 目录会自动创建

**预期输出文件**:
- `output/debug_extracted_pages.json`
- `output/raw_candidates_debug.json`
- `output/candidate_audit.md`
- `output/raw_params_debug.json`
- `output/value_parse_audit.md`
- `output/selected_params_debug.json`
- `output/selector_audit.md`
- `output/final_comparison.xlsx`

---

### Step 2: 检查必要输出是否存在

**必须存在的文件**:
- `output/raw_candidates_debug.json`
- `output/raw_params_debug.json`
- `output/selected_params_debug.json`
- `output/final_comparison.xlsx`

**如果缺失**:
- 停止工作流
- 报告缺失的文件
- 不继续执行后续步骤

**检查命令**:
```bash
for f in output/raw_candidates_debug.json output/raw_params_debug.json output/selected_params_debug.json output/final_comparison.xlsx; do
  if [ ! -f "$f" ]; then
    echo "ERROR: Missing required file: $f"
    exit 1
  fi
done
echo "All required files present"
```

---

### Step 3: 生成 AI Review Context

**命令模板**:

```bash
python3 agent_tools/collect_context_for_ai.py \
  --selection output/selected_params_debug.json \
  --params output/raw_params_debug.json \
  --candidates output/raw_candidates_debug.json \
  --fields config/target_fields.yaml \
  --output output/ai_review_context.json
```

**输入文件**:
- `output/selected_params_debug.json` - Final Selector 输出
- `output/raw_params_debug.json` - 解析后的参数
- `output/raw_candidates_debug.json` - 候选行数据
- `config/target_fields.yaml` - 字段定义配置

**输出文件**:
- `output/ai_review_context.json` - AI 审查所需的压缩上下文

**脚本功能**:
- 压缩过大的 debug JSON
- 每个 field 只保留 selected_param + review_candidates 前 5 个 + blocked_candidates 前 3 个
- source_text 截断到 600 字符
- 保留 source_page、source_hash、field_id、unit、condition、review_reason

---

### Step 4: AI Parameter Review

**本阶段由 OpenClaw Agent 手动执行**

使用 `prompts/parameter_review.md` 作为 system prompt，审查 `output/ai_review_context.json`。

**操作指引**:

1. 读取 `prompts/parameter_review.md` 作为审查标准
2. 读取 `output/ai_review_context.json` 作为输入数据
3. 按照 prompt 中的 10 个审查重点逐一检查
4. 生成严格 JSON 格式的审查结果
5. 保存为 `output/ai_parameter_review.json`

**注意**: 本工作流 v1 不自动调用 LLM，需要人工触发 AI 审查步骤。

---

### Step 5: 本轮停止

**本轮输出**:

| 文件 | 说明 |
|------|------|
| `output/final_comparison.xlsx` | Legacy pipeline 生成的 Excel 对比表 |
| `output/ai_review_context.json` | AI 审查所需的压缩上下文 |
| `output/ai_parameter_review.json` | AI 审查结果 (JSON) |

**本轮不输出**:
- ❌ 不自动 repair selection
- ❌ 不自动修改 Excel
- ❌ 不调用 LLM API

---

## 本轮输出清单

1. ✅ `output/final_comparison.xlsx` - Legacy pipeline 生成
2. ✅ `output/ai_review_context.json` - collect_context_for_ai.py 生成
3. ✅ `output/ai_parameter_review.json` - AI 审查结果 (人工触发)
4. ⏳ 简短执行报告 - 工作流完成后输出

---

## 执行报告模板

工作流完成后，输出以下格式的报告：

```markdown
# AST Datasheet Extraction Workflow v1 - 执行报告

**PDF**: <file_name>
**执行时间**: <timestamp>
**结果**: <success|partial|failure>

## 步骤执行状态

| Step | 状态 | 说明 |
|------|------|------|
| Step 1: Legacy Pipeline | ✅/❌ | <info> |
| Step 2: 检查输出 | ✅/❌ | <info> |
| Step 3: 生成 Context | ✅/❌ | <info> |
| Step 4: AI Review | ⏳/✅/❌ | <info> |
| Step 5: 停止 | ✅ | 本轮不 repair |

## 输出文件

- `output/final_comparison.xlsx` - <size> bytes
- `output/ai_review_context.json` - <size> bytes
- `output/ai_parameter_review.json` - <size> bytes (如已生成)

## 下一步

- Review `output/ai_parameter_review.json`
- 根据 suggested_action 进行 repair
- 或人工确认后进入下一轮
```

---

## 错误处理

### 缺少 PDF 文件
```
ERROR: PDF file not found: <PDF_PATH>
Action: 请提供有效的 PDF 文件路径
```

### Legacy Pipeline 失败
```
ERROR: Legacy pipeline failed with exit code <code>
Action: 检查 PDF 文件是否有效，或查看 error log
```

### 缺少必要输出文件
```
ERROR: Missing required file: <file_path>
Action: Step 2 检查失败，停止工作流
```

### collect_context_for_ai.py 失败
```
ERROR: collect_context_for_ai.py failed with exit code <code>
Action: 检查输入 JSON 文件是否完整，或查看 error log
```

---

## OpenClaw 执行约束

> 🔒 以下约束必须严格遵守：

1. **不要跳步** - 必须按 Step 1-5 顺序执行
2. **不要直接编辑 Excel** - 不要修改 `output/final_comparison.xlsx`
3. **不要凭空生成参数** - 所有值必须来自 `source_text`
4. **不要调用 LLM API** - 本阶段只生成 context
5. **不要修改 selection** - 不要修改 `output/selected_params_debug.json`
6. **不要进入下一阶段** - 本周只完成 v1 review skeleton

---

*End of AST Datasheet Extraction Workflow v1*

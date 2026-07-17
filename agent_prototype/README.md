# Agent Prototype README

## Agent 1 — Table Classifier v0.1

**目标**: 验证 LLM 能否替代硬编码 parser 规则

**测试范围**: 5 个简单参数
- voltage_rating (VDS)
- current_rating (ID)
- rds_on_25c
- vgs_th
- trr

**数据来源**: 
- `output/backend_compare/camelot_tables.json` - Camelot 原始提取
- 或 `output/raw_candidates_debug.json` - pipeline 中间结果

**Prototype 文件**:
```
agent_prototype/
├── prompts/
│   └── agent1_table_classifier_v1.md   # 分类 prompt
├── data/
│   └── test_rows.json                  # 测试数据
├── test_classifier.py                  # 测试脚本
└── results/
    └── prototype_results.json           # 测试结果
```

**验证标准**:
- LLM 分类结果 vs Current Pipeline 结果
- 一致率 > 80% 则 prototype 通过
- < 80% 则分析差异，优化 prompt

---

## Agent 2 — Parameter Validation & Disambiguation v0.1

**目标**: 验证 LLM 能否验证和修正 pipeline 选中的候选值

**测试范围**: 11 个关键字段（ASC300N1200ME3）
- qg, qgd, qgs, ciss, coss, crss, junction_temperature, rds_on_150c, isol, part_number, module_type

**核心能力验证**:
- Symbol exact match (QG vs QGD vs QGS)
- Unit reasonableness (nF vs pF)
- Temperature condition validation (TC=25°C vs TC=150°C)
- Value plausibility (1839°C vs 175°C)
- Source text inspection (Package Type vs Part Number)

**结果**: 11/11 关键期望全部通过 ✅

**文件**:
```
agent_prototype/
├── prompts/agent2_validator.md          # Agent 2 prompt
├── data/agent2_test_input_asc300.json  # 测试输入
├── results/agent2_final_params_asc300.json  # LLM 输出
├── results/agent2_audit_asc300.md      # 审核报告
└── test_classifier.py                  # 测试脚本
```

---

## Agent 3 — Cross-Parameter Consistency Checker v1

**目标**: 验证跨参数一致性关系是否合理

**测试范围**: 10 个一致性规则

| # | 规则 | 严重性 | ASC300 结果 |
|---|------|--------|-------------|
| 1 | RDS(on) 温度特性（正温度系数） | critical | ⏭️ SKIP (rds_on_150c blocked) |
| 2 | 栅极电荷层级（QG > QGS + QGD） | critical | ✅ PASS |
| 3 | 电容层级（Ciss >> Coss > Crss） | critical | ✅ PASS |
| 4 | 反向恢复一致性（Qrr ≈ 0.5×trr×IRRM） | high | ✅ PASS |
| 5 | 开关能量可比性（Eon/Eoff < 3.3x） | high | ✅ PASS |
| 6 | Tj_max 范围（150-200°C） | high | ✅ PASS |
| 7 | VGS(th) 范围（1.5-5.5V） | medium | ✅ PASS |
| 8 | 隔离电压 vs 额定电压 | medium | ✅ PASS |
| 9 | RDS(on) 绝对值合理性 | medium | ✅ PASS |
| 10 | QG 绝对值合理性 | medium | ✅ PASS |

**结果**: 9/10 通过，1 个跳过（预期行为）

**文件**:
```
agent_prototype/
├── prompts/agent3_cross_check_v1.md    # Agent 3 prompt
├── schemas/agent3_consistency.schema.json  # 输出 schema
├── data/agent3_test_input_asc300.json  # 测试输入
├── test_cross_check.py                 # 测试脚本（自动化）
└── results/agent3_consistency_*.json  # 测试结果
```

**运行方式**:
```bash
python3 agent_prototype/test_cross_check.py
# 或指定输入文件
python3 agent_prototype/test_cross_check.py agent_prototype/data/agent3_test_input_asc300.json
```

**与 Agent 2 的区别**:
- Agent 2: 单参数内部验证（值、单位、symbol、condition）
- Agent 3: 参数之间的关系验证（物理关系、量级关系）

---

## 流水线

```
Pipeline → Agent 1 → Agent 2 → Agent 3 → Excel
            ↓          ↓         ↓
        Table       Param     Cross-param
       classify   validate   consistency
```

---

## 下一步

1. **Agent 4** (future): Multi-PDF comparison consistency
2. **Excel Writer Integration**: Use Agent 2/3 output for final Excel generation
3. **Multi-PDF test**: Validate generalization to other datasheets (ROHM, SwissSEM, InventChip)

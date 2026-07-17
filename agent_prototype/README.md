# Agent 1 Prototype - Table Classifier v0.1

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
    └── prototype_results.json          # 测试结果
```

**工作流**:
```
Camelot Tables → test_rows.json → LLM (agent1 prompt) → JSON 结果 → 对比 current pipeline
```

**验证标准**:
- LLM 分类结果 vs Current Pipeline 结果
- 一致率 > 80% 则 prototype 通过
- < 80% 则分析差异，优化 prompt

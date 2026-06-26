# Datasheet Results Repository

This repository stores automatically generated chip comparison results from the [datasheet-extractor](https://github.com/2649699659/datasheet--results) project.

## 📁 目录结构

```
datasheet-results/
├── latest/                      # 最新提取结果
│   └── chip_comparison.xlsx     # 最新的对比 Excel
├── archive/                     # 历史归档
│   └── chip_comparison_YYYY-MM-DD_HHMM.xlsx
├── README.md                    # 本文件
└── .gitignore
```

## 🔄 自动更新

每次运行 `extract_datasheet.py` 后，执行：

```bash
bash scripts/push_results_to_github.sh
```

脚本会自动：
1. 检查 `output/chip_comparison.xlsx` 是否存在
2. 复制最新结果到 `latest/`
3. 归档一份带时间戳的版本到 `archive/`
4. Git add + commit + push

## ⚙️ 初始配置

### 1. 配置 GitHub Remote

```bash
cd datasheet-results
git remote add origin git@github.com:2649699659/datasheet--results.git
git branch -M main
git push -u origin main
```

### 2. 配置 Git 用户（如需要）

```bash
git config user.email "chopper@openclaw.ai"
git config user.name "Chopper-Auto"
```

### 3. 配置 SSH Key

确保 SSH key 已配置并添加到 GitHub：

```bash
# 检查 SSH key
ls -la ~/.ssh/

# 测试连接
ssh -T git@github.com
```

## 📊 数据来源

提取的芯片数据来自以下厂商的 SiC MOSFET datasheet：
- YASC (Anhui YOFC)
- SwissSEM
- InventChip
- ROHM

## 🔒 安全说明

本仓库 **不包含**：
- API keys / .env 文件
- LLM 缓存
- 源代码

只包含提取后的结果文件（Excel）。

## 📝 更新日志

- 2026-06-26: 初始化仓库

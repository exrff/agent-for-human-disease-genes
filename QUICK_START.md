# 快速开始指南

## 5 分钟上手

### 步骤 1: 启动环境

```bash
# 双击运行（Windows）
start.bat

# 或手动激活
conda activate thesis_env
```

### 步骤 2: 设置 API Key

```bash
# 创建 .env 文件
echo "DASHSCOPE_API_KEY=your_key_here" > .env
```

### 步骤 3: 运行分析

```bash
# 自动选择并分析一个数据集
python run_auto_analysis.py --mode single
```

就这么简单！智能体会：
1. ✅ 自动选择最有价值的数据集
2. ✅ 自动从 GEO 下载数据（如果需要）
3. ✅ 自动分析并生成报告

## 常用命令

```bash
# 批量分析所有数据集
python run_auto_analysis.py --mode batch

# 测试数据下载
python test_geo_downloader.py --test single --gse GSE2034

# 不使用 LLM（更快）
python run_auto_analysis.py --mode single --no-llm
```

## 查看结果

```bash
# 分析报告
results/agent_analysis/GSE2034/GSE2034_report.md

# 图表
results/agent_analysis/GSE2034/figures/

# 日志
logs/auto_analysis_*.log
```

## 故障排查

### 问题: API Key 未设置
```bash
# 检查
type .env

# 设置
echo "DASHSCOPE_API_KEY=sk-your-key" > .env
```

### 问题: 数据下载失败
```bash
# 手动测试下载
python test_geo_downloader.py --test single --gse GSE2034

# 检查网络连接
ping ftp.ncbi.nlm.nih.gov
```

### 问题: 依赖缺失
```bash
pip install -r requirements.txt
```

## 下一步

- 查看完整文档: `README.md`
- 查看清理总结: `CLEANUP_SUMMARY.md`
- 查看归档文档: `archive/old_docs/`

## 技术支持

如有问题，请检查：
1. `logs/` 目录中的日志文件
2. `archive/old_docs/` 中的详细文档
3. 确保网络连接正常（需要访问 GEO 数据库）

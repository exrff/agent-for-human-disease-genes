# GPL 平台文件解决方案

## 问题

平台文件下载经常失败，原因：
1. 文件名格式不统一（GPL16699.txt vs GPL16699-15607.txt）
2. 每次分析都要重新下载
3. 网络不稳定导致下载失败

## 解决方案

### 方案：建立本地 GPL 数据库

**核心思路**：
- 一次性批量下载所有常用 GPL 平台文件
- 建立本地 GPL 数据库
- 分析时优先从本地获取，无需重复下载

## 实现

### 1. GPL 管理器

**文件**: `src/data_extraction/gpl_manager.py`

**功能**:
- 批量下载 17 个常用 GPL 平台
- 建立本地索引（gpl_index.json）
- 提供快速查找接口

**支持的平台**:
```python
# Affymetrix (5 个)
GPL96, GPL97, GPL570, GPL571, GPL1352

# Illumina (5 个)
GPL6883, GPL6884, GPL6947, GPL10558, GPL13667

# Agilent (3 个)
GPL6480, GPL4133, GPL14550, GPL16699

# 其他 (2 个)
GPL6102, GPL10322
```

### 2. 集成到下载器

**文件**: `src/data_extraction/geo_downloader.py`

**工作流**:
```
下载数据集
    ↓
提取平台 ID
    ↓
查找平台文件
    ├─ 本地 GPL 数据库 ✓ (优先)
    └─ 在线下载 (备选)
    ↓
复制到数据集目录
    ↓
继续分析
```

### 3. 便捷下载脚本

**文件**: `download_gpl_platforms.py`

**用法**:
```bash
# 下载所有常用平台
python download_gpl_platforms.py --action download

# 列出已下载的平台
python download_gpl_platforms.py --action list

# 检查特定平台
python download_gpl_platforms.py --action check --platform GPL96
```

## 使用指南

### 步骤 1: 一次性下载 GPL 平台

```bash
# 激活环境
conda activate thesis_env

# 下载所有常用平台（约 10-20 分钟）
python download_gpl_platforms.py --action download
```

输出示例:
```
准备下载所有常用 GPL 平台文件...

这将下载以下平台:
  ✗ GPL96: Affymetrix Human Genome U133A Array
  ✗ GPL570: Affymetrix Human Genome U133 Plus 2.0 Array
  ✗ GPL16699: Agilent-039494 SurePrint G3 Human GE v2 8x60K Microarray
  ...

是否继续？(y/n): y

[1/17] GPL96
  下载成功: GPL96.annot.gz

[2/17] GPL570
  下载成功: GPL570.annot.gz

...

下载完成
成功: 15/17
本地平台数: 15
```

### 步骤 2: 正常运行分析

```bash
# 运行分析（会自动使用本地 GPL 文件）
python run_auto_analysis.py --mode single
```

日志示例:
```
步骤 3: 下载平台注释文件...
  ✓ 从本地 GPL 数据库获取: GPL16699
✅ 平台文件: GPL16699-15607.txt
```

## 目录结构

```
data/
├── gpl_platforms/              # GPL 本地数据库
│   ├── gpl_index.json          # 索引文件
│   ├── GPL96.annot.gz
│   ├── GPL570.annot.gz
│   ├── GPL16699-15607.txt
│   └── ...
│
└── validation_datasets/        # 数据集
    └── GSE122063/
        ├── GSE122063_series_matrix.txt.gz
        └── GPL16699-15607.txt  # 从本地复制
```

## 优势

### 1. 下载成功率高
- ✅ 一次性下载，有充足时间处理失败
- ✅ 可以手动重试失败的平台
- ✅ 不影响后续分析流程

### 2. 分析速度快
- ✅ 无需每次下载平台文件
- ✅ 本地复制速度快（秒级）
- ✅ 不依赖网络状态

### 3. 离线可用
- ✅ 下载后可离线分析
- ✅ 适合网络不稳定环境
- ✅ 节省带宽

### 4. 易于管理
- ✅ 集中管理所有平台文件
- ✅ 索引文件记录详细信息
- ✅ 可以随时查看和更新

## 索引文件示例

`data/gpl_platforms/gpl_index.json`:
```json
{
  "GPL96": {
    "file_path": "data/gpl_platforms/GPL96.annot.gz",
    "filename": "GPL96.annot.gz",
    "download_time": "2024-03-13 16:30:15",
    "file_size": 15728640,
    "description": "Affymetrix Human Genome U133A Array"
  },
  "GPL16699": {
    "file_path": "data/gpl_platforms/GPL16699-15607.txt",
    "filename": "GPL16699-15607.txt",
    "download_time": "2024-03-13 16:35:22",
    "file_size": 45678901,
    "description": "Agilent-039494 SurePrint G3 Human GE v2 8x60K Microarray"
  }
}
```

## 故障排查

### 问题 1: 某些平台下载失败

**解决**:
```bash
# 查看哪些平台失败了
python download_gpl_platforms.py --action list

# 手动重试单个平台
python -c "from src.data_extraction.gpl_manager import GPLManager; GPLManager().download_platform('GPL16699', force=True)"
```

### 问题 2: 需要添加新平台

**解决**:
编辑 `src/data_extraction/gpl_manager.py`，在 `COMMON_PLATFORMS` 中添加：
```python
COMMON_PLATFORMS = {
    ...
    'GPL新平台': '平台描述',
}
```

然后重新下载：
```bash
python download_gpl_platforms.py --action download
```

### 问题 3: 索引文件损坏

**解决**:
```bash
# 删除索引文件
rm data/gpl_platforms/gpl_index.json

# 重新下载（会自动重建索引）
python download_gpl_platforms.py --action download
```

## 命令速查

```bash
# 下载所有平台
python download_gpl_platforms.py --action download

# 列出已下载的平台
python download_gpl_platforms.py --action list

# 检查特定平台
python download_gpl_platforms.py --action check --platform GPL96

# 在 Python 中使用
from src.data_extraction.gpl_manager import get_platform_file
file_path = get_platform_file('GPL96')
```

## 总结

✅ **问题解决**: 平台文件下载不再是瓶颈

✅ **一次下载，永久使用**: 建立本地 GPL 数据库

✅ **自动回退**: 本地没有时自动在线下载

✅ **提高效率**: 分析速度显著提升

现在可以放心运行批量分析了！

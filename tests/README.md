# 调试测试脚本

在项目根目录激活环境后运行。

**当前测试脚本**
- `_test_llm.py`
  作用：测试当前 `llm_client` 的连通性
- `_test_plots.py`
  作用：测试 `geo_parsing`、`scoring_core` 和 `plot_generator` 的联动
- `_test_validator.py`
  作用：测试 `geo_validator` 的 GEO 数据集验证
- `_test_analysis_mode.py`
  作用：测试第一期 `analysis_mode` 判定、模式统计骨架和 `plot_plan`
- `test_geo_downloader.py`
  作用：测试 GEO 下载器

**常用命令**
```bash
python tests/_test_llm.py
python tests/_test_plots.py
python tests/_test_validator.py
python tests/_test_analysis_mode.py
python tests/test_geo_downloader.py
```

**说明**
- 这些脚本偏向“本地联调检查”，不是完整的 pytest 单元测试套件
- `_test_plots.py` 已切到新结构，不再依赖 `disease_analysis_agent.py` 中的大量私有实现

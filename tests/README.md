# 调试测试脚本

在项目根目录激活环境后运行（需先执行 `start.bat`）：

| 文件 | 用途 |
|------|------|
| `_test_llm.py` | 测试 DashScope LLM 连通性 |
| `_test_plots.py` | 测试 plot_generator 图表生成 |
| `_test_validator.py` | 测试 geo_validator GEO 数据集验证 |
| `test_geo_downloader.py` | 测试 GEO 下载器 |

```bash
python tests/_test_llm.py
python tests/_test_plots.py
```

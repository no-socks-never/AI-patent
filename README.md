# 中国人工智能专利转让网络分析

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![R](https://img.shields.io/badge/R-4.0+-blue.svg)](https://www.r-project.org/)
[![License](https://img.shields.io/badge/License-Academic-green.svg)](LICENSE)

## 📋 项目简介

本项目系统分析中国人工智能专利转让网络（2001-2024年），通过社会网络分析方法研究专利在不同主体之间的流动模式、网络结构特征、影响因素及创新产出关系。

**数据规模**: 358,733条专利转让记录，115,552个参与主体  
**分析工具**: Python (NetworkX, scikit-learn, XGBoost) + R (ergm)  
**研究问题**: 4个核心研究问题（RQ1-RQ4）

---

## 🎯 研究问题

### RQ1: 网络演化特征分析
**问题**: 专利转让网络如何随时间演化？  
**方法**: 构建2001-2024年度网络，计算密度、聚类系数、模块度等拓扑指标  
**数据**: 全量数据

### RQ2: 主体类型与角色差异
**问题**: 不同类型主体在网络中的角色有何差异？  
**方法**: 计算度中心性、中介中心性、特征向量中心性，比较企业、高校、科研机构、个人的网络位置  
**数据**: 全量数据

### RQ3: 网络形成影响因素
**问题**: 地理邻近性和技术相似度如何影响专利转让？  
**方法**: 使用ERGM（指数随机图模型）分析网络形成机制，分时段建模（2001-2010、2011-2017、2018-2024）  
**数据**: 筛选后数据（度>=2的节点）

### RQ4: 网络位置与创新产出
**问题**: 网络位置如何影响主体的专利转让活跃度？  
**方法**: 负二项回归、随机森林、XGBoost预测模型  
**数据**: 筛选后数据（度>=2的节点）

---

## 📁 项目结构

```
中国专利转让/
├── coding/                          # 分析代码目录
│   ├── data_loader.py              # Python数据加载工具（支持全量/筛选后数据）⭐
│   ├── font_config.py              # 跨平台字体配置
│   ├── filter_nodes_by_degree.py   # 节点筛选工具（生成筛选后数据）
│   │
│   ├── RQ1/                        # 研究问题1: 网络演化
│   │   └── network_metrics.py
│   │
│   ├── RQ2/                        # 研究问题2: 主体角色
│   │   └── type_role.py
│   │
│   ├── RQ3/                        # 研究问题3: 影响因素
│   │   ├── data_loader.R           # R数据加载工具（支持全量/筛选后数据）⭐
│   │   ├── r_font_config.R        # R字体配置
│   │   ├── tongji.py               # 数据统计（全量数据）
│   │   ├── jishu_improved_filtered.R    # 技术相似度分析（筛选后数据）
│   │   └── dili_improved_filtered.R     # 地理邻近性分析（筛选后数据）
│   │
│   └── RQ4/                        # 研究问题4: 创新产出
│       ├── zhongxin_improved.py   # 改进版（筛选后数据）
│       └── zhongxin.py            # 旧版本（全量数据）
│
├── data_cleaned/                   # 清洗后的全量数据
│   └── 人工智能专利转让数据_XXXX.xlsx (2001-2024)
│
├── data_cache/                     # 数据缓存目录 ⭐
│   ├── raw_data_merged.pkl        # Python缓存（全量数据）
│   ├── raw_data_merged.rds        # R缓存（全量数据）
│   ├── filtered_data_degree_ge2.pkl  # Python缓存（筛选后数据）
│   └── filtered_data_degree_ge2.rds  # R缓存（筛选后数据）
│
├── result/                         # 分析结果目录
│   ├── node_filtering/            # 节点筛选结果
│   │   └── data/
│   │       ├── filtered_data_degree_ge2.csv  # 筛选后的数据（240,776条）
│   │       ├── node_degrees_full.csv
│   │       └── node_degrees_filtered_ge2.csv
│   │
│   ├── RQ1_network_metrics/       # 网络演化结果
│   ├── RQ2_entity_roles/          # 主体角色结果
│   ├── RQ3_formation_factors/      # 影响因素结果
│   │   ├── technology_improved_filtered/  # 技术相似度（筛选后数据）
│   │   └── geography_improved_filtered/    # 地理邻近性（筛选后数据）
│   └── RQ4_centrality_prediction_filtered/ # 网络位置预测（筛选后数据）
│
└── 中国专利转让全量数据/          # 原始数据备份
```

---

## 🚀 快速开始

### 环境要求

#### Python环境 (推荐 Python 3.8+)

```bash
pip install pandas numpy networkx matplotlib seaborn scikit-learn xgboost openpyxl tqdm python-louvain
```

#### R环境 (推荐 R 4.0+)

```r
install.packages(c("readxl", "dplyr", "ergm", "network", "readr", "showtext"))
```

### 数据准备

#### 1. 全量数据
将Excel数据文件放置在 `data_cleaned/` 目录下。

#### 2. 筛选后数据（可选，用于RQ3和RQ4）
首次运行需要生成筛选后的数据：

```bash
cd coding
python filter_nodes_by_degree.py
```

这将生成：
- `result/node_filtering/data/filtered_data_degree_ge2.csv` (240,776条记录)
- 筛选条件：度 >= 2（入度 + 出度 >= 2）

---

## 📊 运行分析

### RQ1: 网络演化特征分析（全量数据）

```bash
cd coding/RQ1
python network_metrics.py
```

**输出**:
- `result/RQ1_network_metrics/data/network_metrics.csv` - 24年网络拓扑指标
- `result/RQ1_network_metrics/data/year_XXXX_network.gexf` - 年度网络文件（可导入Gephi）
- `result/RQ1_network_metrics/figures/*.png` - 趋势分析图

---

### RQ2: 主体类型与角色差异（全量数据）

```bash
cd coding/RQ2
python type_role.py
```

**输出**:
- `result/RQ2_entity_roles/data/type_role_stats.csv` - 主体类型统计对比
- `result/RQ2_entity_roles/data/entity_role_metrics.csv` - 个体层面网络指标
- `result/RQ2_entity_roles/figures/*.png` - 可视化图表

---

### RQ3: 网络形成影响因素（筛选后数据）

#### 技术相似度分析

```bash
cd coding/RQ3
Rscript jishu_improved_filtered.R
```

#### 地理邻近性分析

```bash
cd coding/RQ3
Rscript dili_improved_filtered.R
```

**输出**:
- `result/RQ3_formation_factors/technology_improved_filtered/` - 技术相似度ERGM结果
- `result/RQ3_formation_factors/geography_improved_filtered/` - 地理邻近性ERGM结果
- 包含分时段系数对比、模型摘要、可视化图表

#### 数据统计（全量数据）

```bash
cd coding/RQ3
python tongji.py
```

---

### RQ4: 网络位置与创新产出（筛选后数据）

```bash
cd coding/RQ4
python zhongxin_improved.py
```

**注意**: 默认使用筛选后数据（`USE_FILTERED_DATA = True`）。如需使用全量数据，修改文件开头的配置。

**输出**:
- `result/RQ4_centrality_prediction_filtered/data/` - 模型结果和特征重要性
- `result/RQ4_centrality_prediction_filtered/figures/` - 可视化图表

---

## 🔧 数据加载工具

### Python数据加载

```python
from data_loader import load_all_excel_files, load_filtered_data

# 加载全量数据（支持缓存）
df = load_all_excel_files(data_dir="./data_cleaned", use_cache=True)

# 加载筛选后数据（支持缓存）
df = load_filtered_data(use_cache=True)
```

### R数据加载

```r
source("data_loader.R")

# 加载全量数据
df <- load_all_excel_files(data_dir = "./data_cleaned")

# 加载筛选后数据
df <- load_filtered_data(use_cache = TRUE)
```

**缓存机制**: 
- 首次运行自动缓存数据（`.pkl`或`.rds`格式）
- 后续运行自动检测数据更新，未更新则使用缓存
- 大幅提升运行速度（约10倍）

---

## 📈 主要发现

### 网络演化
- 网络规模快速扩张：节点从103个（2001）增至22,727个（2024），增长220倍
- 密度持续下降：从0.00533降至0.000027，说明转让关系分散
- 高模块度（0.77-0.99）：存在明显的社群结构，专利转让呈"圈子化"

### 主体角色
- **高校**: 专利输出中心（出度中心性是企业的10倍以上）
- **企业**: 市场主导者（数量占84.3%）
- **科研单位**: 技术供应商
- **个人**: 边缘参与者

### 影响因素
- **地理邻近性**: 始终显著为正（系数+0.53~+1.19），同省份转让概率更高
- **技术相似度**: 早期显著为正，随市场成熟逐渐减弱甚至反转
- **互惠性**: 大部分时期显著（系数+2.70~+4.16），存在双向转让倾向

### 网络位置价值
- k-core（核心度）是最强预测因子（重要性52.9%）
- eigenvector（影响力）次之（重要性38.1%）
- 模型R²=0.47，网络位置对创新产出有显著影响

---

## 🎨 项目特点

✅ **跨平台兼容**: 支持 Windows/macOS/Linux  
✅ **自动化字体配置**: 无需手动设置中文字体  
✅ **智能数据缓存**: Python+R双语言缓存机制，大幅提升运行效率  
✅ **灵活数据选择**: 支持全量数据和筛选后数据，根据分析需求选择  
✅ **模块化设计**: 每个研究问题独立运行，代码清晰易维护  
✅ **详细注释**: 代码包含详细注释，易于理解和修改  
✅ **规范化输出**: 统一result文件夹结构，数据与图表分离

---

## 📚 技术栈

### Python
- **网络分析**: NetworkX
- **数据处理**: pandas, numpy
- **机器学习**: scikit-learn, XGBoost
- **可视化**: matplotlib, seaborn
- **数据读取**: openpyxl

### R
- **网络分析**: network, ergm
- **数据处理**: dplyr, readr
- **数据读取**: readxl

---

## 📝 数据说明

### 数据来源
- **来源**: 国家知识产权局（CNIPA）公开专利转让记录
- **时间范围**: 2001-2024年
- **技术范围**: AI相关IPC分类（G06N, G06F, G06T, G10L等）

### 数据文件
- **全量数据**: `data_cleaned/` 目录下的Excel文件（24个文件）
- **筛选后数据**: `result/node_filtering/data/filtered_data_degree_ge2.csv`
  - 筛选条件：度 >= 2（入度 + 出度 >= 2）
  - 节点数：22,506个（从257,363减少91.26%）
  - 记录数：240,776条（从695,259减少65.37%）

### 数据使用策略
| RQ | 数据来源 | 说明 |
|---|---------|------|
| RQ1 | 全量数据 | 需要完整网络信息分析演化趋势 |
| RQ2 | 全量数据 | 需要全面分析所有主体类型 |
| RQ3 | 筛选后数据 | 减少计算开销，保留核心结构 |
| RQ4 | 筛选后数据 | 减少计算开销，提高模型效率 |

---

## 🛠️ 常见问题

### Q1: 如何生成筛选后的数据？

**A**: 运行节点筛选工具：
```bash
cd coding
python filter_nodes_by_degree.py
```

### Q2: 筛选后数据在哪里？

**A**: `result/node_filtering/data/filtered_data_degree_ge2.csv`

### Q3: RQ3和RQ4必须使用筛选后数据吗？

**A**: 
- RQ3的改进版脚本（`*_filtered.R`）使用筛选后数据
- RQ4的改进版（`zhongxin_improved.py`）默认使用筛选后数据，可通过修改`USE_FILTERED_DATA`切换

### Q4: ERGM模型运行时间过长？

**A**: 
- 已使用筛选后数据减少计算开销
- 模型已设置合理的MCMC参数
- 如仍失败，可查看模型摘要文件了解部分结果

### Q5: 如何切换数据源？

**A**: 
- **Python**: 修改`load_all_excel_files()`和`load_filtered_data()`的调用
- **R**: 修改`load_all_excel_files()`和`load_filtered_data()`的调用
- **RQ4**: 修改`USE_FILTERED_DATA`变量

---

## 📄 文件说明

### 核心代码文件

| 文件 | 说明 |
|------|------|
| `coding/data_loader.py` | Python数据加载工具（支持全量/筛选后数据） |
| `coding/filter_nodes_by_degree.py` | 节点筛选工具（生成筛选后数据） |
| `coding/font_config.py` | 跨平台字体配置 |
| `coding/RQ3/data_loader.R` | R数据加载工具（支持全量/筛选后数据） |

### 分析脚本

| RQ | 脚本 | 数据 | 说明 |
|---|------|------|------|
| RQ1 | `network_metrics.py` | 全量 | 网络演化分析 |
| RQ2 | `type_role.py` | 全量 | 主体角色分析 |
| RQ3 | `jishu_improved_filtered.R` | 筛选后 | 技术相似度ERGM |
| RQ3 | `dili_improved_filtered.R` | 筛选后 | 地理邻近性ERGM |
| RQ3 | `tongji.py` | 全量 | 数据统计报告 |
| RQ4 | `zhongxin_improved.py` | 筛选后 | 网络位置预测（改进版） |

---

## 📊 结果文件结构

```
result/
├── node_filtering/                    # 节点筛选结果
│   └── data/
│       ├── filtered_data_degree_ge2.csv
│       ├── node_degrees_full.csv
│       └── filtering_report.txt
│
├── RQ1_network_metrics/              # 网络演化
│   ├── data/network_metrics.csv
│   └── figures/*.png
│
├── RQ2_entity_roles/                 # 主体角色
│   ├── data/type_role_stats.csv
│   └── figures/*.png
│
├── RQ3_formation_factors/            # 影响因素
│   ├── technology_improved_filtered/
│   │   ├── data/coefficients_comparison_by_period.csv
│   │   └── plots/coefficients_over_time.png
│   └── geography_improved_filtered/
│       ├── data/coefficients_comparison_by_period.csv
│       └── plots/coefficients_over_time.png
│
└── RQ4_centrality_prediction_filtered/  # 网络位置预测
    ├── data/model_comparison.csv
    └── figures/model_comparison.png
```

---

## 🔬 研究方法

### 网络分析
- **网络构建**: 基于专利转让关系构建有向加权网络
- **拓扑指标**: 密度、聚类系数、路径长度、模块度
- **中心性指标**: 度中心性、中介中心性、特征向量中心性、k-core

### 统计模型
- **ERGM**: 指数随机图模型，分析网络形成机制
- **机器学习**: 随机森林、XGBoost预测模型
- **回归分析**: 负二项回归（计数数据）

### 数据处理
- **数据清洗**: 去重、缺失值处理、字段标准化
- **特征工程**: IPC分类号解析、地理位置匹配、主体类型识别
- **数据缓存**: Python+R双语言缓存机制

---

## 📖 相关文档

- `中国AI专利转让.md` - 详细研究结果报告
- `研究总结报告.md` - 完整研究总结
- `coding/数据使用说明.md` - 数据使用策略说明

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📄 许可证

本项目仅用于学术研究和学习交流。

---

## 📧 联系方式

如有问题或建议，请提交Issue。

---

**最后更新**: 2024年12月  
**数据版本**: V1.0（2001-2024年完整数据）  
**分析工具版本**: Python 3.8+, R 4.0+

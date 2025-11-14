# 中国专利转让网络分析项目

## 项目简介

本项目分析中国人工智能专利转让网络,研究专利在不同主体之间的流动模式、网络结构特征以及影响因素。

## 目录结构

```
中国专利转让/
├── data/                           # 原始数据目录
│   ├── 人工智能专利转让数据_2001.xlsx
│   ├── 人工智能专利转让数据_2002.xlsx
│   └── ...                        # 2001-2024年数据
│
├── AI-patent/                     # 分析代码目录
│   ├── font_config.py            # 跨平台字体配置模块 ⭐
│   ├── RQ1/                       # 研究问题1: 网络演化
│   │   └── network_metrics.py
│   │
│   ├── RQ2/                       # 研究问题2: 主体角色
│   │   └── type_role.py
│   │
│   ├── RQ3/                       # 研究问题3: 影响因素
│   │   ├── tongji.py             # 数据统计
│   │   ├── r_font_config.R       # R语言字体配置 ⭐
│   │   ├── dili_normal.R         # 地理因素分析
│   │   ├── dili_up.R
│   │   ├── jishu.R               # 技术相似度分析
│   │   └── jishu_up.R
│   │
│   └── RQ4/                       # 研究问题4: 创新产出
│       ├── zhongxin.py           # 中心性分析
│       └── dp_1.py               # 简化分析
│
├── result/                        # 分析结果目录
│   ├── RQ1/                       # 网络指标结果
│   ├── RQ2/                       # 主体角色结果
│   ├── RQ3/                       # 影响因素结果
│   └── RQ4/                       # 创新产出结果
│
└── 中国专利转让全量数据/          # 备用全量数据
```

## 快速开始

### 环境要求

#### Python环境 (推荐 Python 3.8+)

```bash
pip install pandas numpy networkx matplotlib seaborn scikit-learn openpyxl tqdm python-louvain
```

#### R环境 (推荐 R 4.0+)

```r
install.packages(c("readxl", "dplyr", "ergm", "network", "graphics", "showtext"))
```

### 跨平台兼容性 ⭐

#### Python脚本

所有Python脚本已自动配置跨平台中文字体,无需手动设置。

#### R脚本

如需在R中使用中文,请在脚本开头添加:

```r
source("r_font_config.R")
setup_chinese_fonts()
```

### 运行分析

#### 研究问题1: 网络演化分析

```bash
cd AI-patent/RQ1
python network_metrics.py
```

输出结果:
- `result/RQ1/statistics/network_metrics.csv` - 网络指标数据
- `result/RQ1/gexf/` - 年度网络文件(可导入Gephi)
- `result/RQ1/trends/` - 趋势图表

#### 研究问题2: 主体类型角色分析

```bash
cd AI-patent/RQ2
python type_role.py
```

输出结果:
- `result/RQ2/entity_role_metrics.csv` - 主体角色指标
- `result/RQ2/type_role_stats.csv` - 类型统计
- `result/RQ2/visualizations/` - 可视化图表

#### 研究问题3: 影响因素分析

**数据统计:**

```bash
cd AI-patent/RQ3
python tongji.py
```

**地理因素分析 (R语言):**

```bash
cd AI-patent/RQ3
Rscript dili_normal.R
```

**技术相似度分析 (R语言):**

```bash
cd AI-patent/RQ3
Rscript jishu.R
```

输出结果:
- `result/RQ3/数据统计结果.xlsx` - 统计汇总
- `result/RQ3_geo_fixed/` - 地理因素结果
- `result/RQ3_tech/` - 技术相似度结果

#### 研究问题4: 网络位置与创新产出

```bash
cd AI-patent/RQ4
python zhongxin.py
```

输出结果:
- `result/RQ4/node_centrality.csv` - 节点中心性
- `result/RQ4/regression_coefficients.csv` - 回归系数
- `result/RQ4/figures/` - 可视化图表

## 研究问题说明
| 模块 | 方法 / 模型 | 分析目标 |
|------|--------------|-----------|
| **结构分析** | 网络密度、聚类系数、平均路径、模块度 | 描述整体网络演化趋势 |
| **角色分析** | 度中心性、中介中心性、特征向量中心性、K-core | 识别不同主体的功能地位 |
| **机制分析** | Logistic回归 | 检验技术相似性与地理邻近性的作用 |
| **绩效分析** | 面板回归模型 | 探索结构位置对创新产出的影响 |
| **演化分析** | 时间序列聚类 / SAOM | 识别网络演化阶段与模式 |
### RQ1: 网络演化特征

- **目标**: 分析专利转让网络的时间演化规律
- **方法**: 构建年度网络,计算密度、聚类系数、路径长度等指标
- **关键发现**: 网络规模扩大,密度变化,社群结构演化

### RQ2: 主体类型与角色

- **目标**: 识别不同类型主体在转让网络中的角色差异
- **方法**: 计算度中心性、中介中心性、特征向量中心性
- **关键发现**: 企业、高校、科研机构的角色定位与差异

### RQ3: 转让影响因素

- **目标**: 探究地理邻近性和技术相似度对专利转让的影响
- **方法**: 使用ERGM(指数随机图模型)分析网络形成机制
- **关键发现**: 地理因素和技术相似度的作用强度

### RQ4: 网络位置与创新产出

- **目标**: 分析网络位置对主体创新产出的影响
- **方法**: 泊松回归,以中心性指标预测专利转让活跃度
- **关键发现**: 中心性指标与创新产出的关系

## 数据说明

### 数据来源
| 项目 | 内容 | 说明 |
|------|------|------|
| 数据来源 | 国家知识产权局（CNIPA） | 公开专利转让记录 |
| 时间范围 | 2000–2024 | 年度更新 |
| 技术范围 | AI相关IPC分类（G06N, G06F, G06T, G10L 等） | 覆盖人工智能主要技术分支 |
| 节点定义 | 专利转让主体（企业、高校、科研机构、个人） | 转让人或受让人 |
| 边定义 | 转让关系（有向边：转让人 → 受让人） | 带权网络 |
| 节点属性 | 主体类型、地区、省份、专利数量 | 用于角色与机制分析 |
| 衍生变量 | 技术相似性、地理邻近性、创新产出 | 从专利文本及结构中计算 |


### 数据处理

所有脚本已自动处理数据加载、清洗、去重、缺失值处理等步骤。

## 常见问题

### Q1: Windows系统运行Python脚本时中文显示为方框?

**A**: 本项目已支持跨平台字体自动配置。如仍有问题,请确保系统已安装微软雅黑或黑体(Windows内置)。

### Q2: macOS系统R语言中文显示异常?

**A**: 在R脚本开头添加:
```r
source("r_font_config.R")
setup_chinese_fonts()
```

### Q3: 数据文件路径错误?

**A**: 确保:
1. 工作目录在项目根目录或对应的RQ文件夹
2. `data/` 目录与脚本的相对位置正确
3. Excel文件未被其他程序占用

### Q4: ERGM模型运行时间过长或失败?

**A**: RQ3的ERGM模型对计算资源要求较高:
- 确保R已安装`ergm`包及其依赖
- 模型已设置较小的MCMC参数以加快运行
- 如仍失败,可参考脚本中的统计结果

### Q5: 如何在新电脑上运行项目?

**A**: 
1. 克隆/下载整个项目文件夹
2. 安装Python和R环境及依赖包
3. 确保`data/`目录包含Excel数据文件
4. 直接运行各RQ目录下的脚本

## 技术栈

- **Python**: pandas, networkx, matplotlib, seaborn, scikit-learn
- **R**: dplyr, ergm, network, readxl
- **可视化**: matplotlib, seaborn, Gephi(可选)

## 项目特点

✅ **跨平台兼容**: 支持 Windows/macOS/Linux  
✅ **自动化字体配置**: 无需手动设置中文字体  
✅ **相对路径**: 无需修改硬编码路径  
✅ **模块化设计**: 每个研究问题独立运行  
✅ **详细注释**: 代码清晰,易于理解和修改  


## 许可证

本项目仅用于学术研究和学习交流。


---

**注意**: 运行前请确保已安装所有依赖包,并将数据文件放置在正确的目录中。


# 🧠 README  
## 基于多层社会网络的中国人工智能专利转让结构特征及演化机制研究  
**Multilayer Network Analysis of China's Artificial Intelligence Patent Transfer: Structural Features and Evolution Mechanisms (2005–2024)**

---

### 📘 1. 研究简介 / Project Overview

本研究基于**2000–2024年中国人工智能（AI）专利转让数据**，运用**社会网络分析（SNA）**方法，系统探讨AI领域技术流动的结构特征、主体角色及演化机制。  
研究聚焦以下四个问题（RQs）：

1. **RQ1：** 中国AI专利转让网络的整体结构特征及演化趋势如何？  
2. **RQ2：** 不同类型主体（企业、高校、科研机构）在网络中扮演了怎样的结构角色？  
3. **RQ3：** 技术相似性与地理邻近性如何影响专利转让关系的形成？  
4. **RQ4：** 网络位置（中心性等）是否促进主体的创新产出？  

> 本项目完全基于现有的专利转让数据，无需外部补充数据（如宏观经济或企业财报）。

---

### 🧩 2. 数据说明 / Data Description

| 项目 | 内容 | 说明 |
|------|------|------|
| 数据来源 | 国家知识产权局（CNIPA） | 公开专利转让记录 |
| 时间范围 | 2000–2024 | 年度更新 |
| 技术范围 | AI相关IPC分类（G06N, G06F, G06T, G10L 等） | 覆盖人工智能主要技术分支 |
| 节点定义 | 专利转让主体（企业、高校、科研机构、个人） | 转让人或受让人 |
| 边定义 | 转让关系（有向边：转让人 → 受让人） | 带权网络 |
| 节点属性 | 主体类型、地区、省份、专利数量 | 用于角色与机制分析 |
| 衍生变量 | 技术相似性、地理邻近性、创新产出 | 从专利文本及结构中计算 |

---

### 🧮 3. 研究方法 / Methods

| 模块 | 方法 / 模型 | 分析目标 |
|------|--------------|-----------|
| **结构分析** | 网络密度、聚类系数、平均路径、模块度 | 描述整体网络演化趋势 |
| **角色分析** | 度中心性、中介中心性、特征向量中心性、K-core | 识别不同主体的功能地位 |
| **机制分析** | Logistic回归 | 检验技术相似性与地理邻近性的作用 |
| **绩效分析** | 面板回归模型 | 探索结构位置对创新产出的影响 |
| **演化分析** | 时间序列聚类 / SAOM | 识别网络演化阶段与模式 |

**主要软件环境：**
- Python（NetworkX, Pandas, Numpy, Statsmodels）
- Gephi（网络可视化）

---

### 🔍 4. 文件结构 / Repository Structure

```
AI_Patent_Transfer_Network/
│
├── data/
│   ├── raw_patent_data.csv
│   ├── cleaned_network_edges.csv
│   ├── node_attributes.csv
│   ├── tech_similarity_matrix.csv
│   └── innovation_output.csv
│
├── code/
│   ├── 01_data_cleaning.ipynb
│   ├── 02_network_construction.ipynb
│   ├── 03_ergm_analysis.R
│   ├── 04_panel_regression.ipynb
│   ├── 05_visualization.ipynb
│   └── utils/
│
├── results/
│   ├── figures/
│   ├── tables/
│   └── reports/
│
├── README.md
└── requirements.txt
```

---

### 📈 5. 分析流程 / Analytical Workflow

```
数据收集与清洗
      ↓
网络构建（节点、边、属性）
      ↓
整体结构分析（RQ1）
      ↓
主体角色分析（RQ2）
      ↓
技术/地理机制分析（RQ3）
      ↓
结构–绩效关系建模（RQ4）
      ↓
演化阶段识别与模式总结
```

---

### 🧠 6. 主要发现（预期） / Expected Findings

- AI专利转让网络逐步由稀疏向集中演化，知识扩散效率提升；  
- 技术相似性显著正向影响转让关系形成，地理邻近性作用逐渐减弱；  
- 企业是网络核心主体，高校承担桥梁角色；  
- 网络中心度越高的节点，其未来创新产出越多；  
- 网络演化呈现“集聚化—多极化—生态化”阶段特征。

---

### 🧩 7. 创新点 / Contributions

1. **理论创新**：从社会网络视角揭示AI技术扩散机制，连接“结构—机制—绩效”链条。  
2. **方法创新**：结合logic与动态SNA，实现机制建模与演化分析。  
3. **数据创新**：构建中国AI专利转让长时序多层网络数据集（2000–2024）。  
4. **政策价值**：为区域创新协同与技术转化政策提供结构性证据。

---

### ⚙️ 8. 环境与依赖 / Environment

**Python Version:** 3.10+  
**R Version:** 4.3+  

主要依赖：
```txt
networkx
pandas
numpy
matplotlib
plotly
statsmodels
```

安装命令：
```bash
pip install -r requirements.txt
```

---

### 📚 9. 引用格式 / Citation

> Tang, T. (2025). *Multilayer Network Analysis of China's Artificial Intelligence Patent Transfer: Structural Features and Evolution Mechanisms (2005–2024).*  
> Unpublished research project.

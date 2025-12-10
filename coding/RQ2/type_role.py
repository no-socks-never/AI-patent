import os
# 设置matplotlib配置目录（解决权限问题）
os.environ['MPLCONFIGDIR'] = os.path.join(os.getcwd(), '.matplotlib_cache')
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

import pandas as pd
import networkx as nx
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import warnings

# 检测CPU核心数用于并行计算
CPU_COUNT = os.cpu_count() or 4

# 导入跨平台字体配置和数据加载工具
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from font_config import setup_chinese_fonts, get_font_dict
from data_loader import load_all_excel_files

# --------------------------
# 配置参数
# --------------------------
data_dir = "./data_cleaned"  # 数据目录
result_root = "./result/RQ2_entity_roles"  # 结果目录
os.makedirs(result_root, exist_ok=True)  # 创建结果目录
os.makedirs(os.path.join(result_root, "data"), exist_ok=True)
os.makedirs(os.path.join(result_root, "figures"), exist_ok=True)

# 自动配置中文字体（支持 Windows/macOS/Linux）
setup_chinese_fonts()
font_dicts = get_font_dict()
title_font = font_dicts['title_font']
label_font = font_dicts['label_font']


# --------------------------
# 步骤1：数据加载与预处理
# --------------------------
def load_and_clean_data():
    """加载原始数据并提取转让关系和主体类型"""
    # 使用统一的数据加载工具（支持缓存）
    cols_needed = [
        "专利名称", "申请号", "转让次数", "转让生效年份",
        "转让人", "转让人类型", "受让人", "受让人类型"
    ]
    
    # 从缓存加载或重新读取
    df = load_all_excel_files(data_dir=data_dir, columns=cols_needed)
    
    # 筛选有效转让记录
    valid_df = df[
        (df["转让次数"] >= 1) &  # 至少1次转让
        (df["转让人"].notna()) &  # 转让人不为空
        (df["受让人"].notna()) &  # 受让人不为空
        (df["转让生效年份"].notna())  # 年份有效
    ].copy()
    
    # 清洗主体名称（去除空格和特殊字符）
    valid_df["转让人"] = valid_df["转让人"].str.strip().replace(r'[^\w\s]', '', regex=True)
    valid_df["受让人"] = valid_df["受让人"].str.strip().replace(r'[^\w\s]', '', regex=True)
    
    # 处理主体类型缺失值（默认为"其他"）
    valid_df["转让人类型"] = valid_df["转让人类型"].fillna("其他")
    valid_df["受让人类型"] = valid_df["受让人类型"].fillna("其他")
    
    print(f"原始数据记录数：{len(df)}")
    print(f"有效转让记录数：{len(valid_df)}")
    print(f"主体类型分布：\n{pd.concat([valid_df['转让人类型'], valid_df['受让人类型']]).value_counts()}")
    
    return valid_df


# --------------------------
# 步骤2：构建主体-主体转让网络
# --------------------------
def build_transfer_network(cleaned_df):
    """构建有向加权网络（节点：主体，边：转让关系，权重：转让次数）"""
    # 聚合相同转让人-受让人的转让次数（加权）
    edge_data = cleaned_df.groupby(["转让人", "受让人"]).size().reset_index(name="weight")
    
    # 构建有向图
    G = nx.DiGraph()
    
    # 添加节点及属性（主体类型）
    # 收集所有主体并映射类型（优先用转让人类型，若不存在则用受让人类型）
    all_entities = pd.unique(cleaned_df[["转让人", "受让人"]].values.ravel("K"))
    entity_types = {}
    
    # 提取转让人类型
    for _, row in cleaned_df[["转让人", "转让人类型"]].drop_duplicates().iterrows():
        entity_types[row["转让人"]] = row["转让人类型"]
    # 补充受让人类型（若转让人中未出现）
    for _, row in cleaned_df[["受让人", "受让人类型"]].drop_duplicates().iterrows():
        if row["受让人"] not in entity_types:
            entity_types[row["受让人"]] = row["受让人类型"]
    
    # 添加节点
    for entity in all_entities:
        G.add_node(entity, type=entity_types[entity])
    
    # 添加边（带权重）
    for _, row in edge_data.iterrows():
        G.add_edge(row["转让人"], row["受让人"], weight=row["weight"])
    
    print(f"\n网络构建完成：{G.number_of_nodes()}个节点，{G.number_of_edges()}条边")
    return G, entity_types


# --------------------------
# 步骤3：计算主体结构角色指标（中心性分析）
# --------------------------
def calculate_role_metrics(G):
    """计算节点中心性指标（衡量网络角色）"""
    print("\n开始计算网络角色指标...")
    metrics = {}
    
    # 1. 度中心性（入度：被转让活跃度；出度：主动转让活跃度）
    in_degree = nx.in_degree_centrality(G)
    out_degree = nx.out_degree_centrality(G)
    
    # 2. 中介中心性（控制资源流动的能力）
    # 对于大型网络使用采样近似以加速
    n_nodes = G.number_of_nodes()
    if n_nodes > 10000:
        # 大型网络：使用采样近似（采样1%的节点，但至少2000个）
        k_samples = max(2000, int(n_nodes * 0.01))
        print(f"  计算betweenness中心性（大型网络，使用采样近似，k={k_samples}，约{100*k_samples/n_nodes:.1f}%）...")
        betweenness = nx.betweenness_centrality(G, weight="weight", k=k_samples)
    else:
        # 中小型网络：完整计算
        print("  计算betweenness中心性（完整计算）...")
        betweenness = nx.betweenness_centrality(G, weight="weight")
    
    # 3. 特征向量中心性（与高影响力主体的连接强度）
    try:
        eigenvector = nx.eigenvector_centrality(G, weight="weight", max_iter=500)
    except:
        eigenvector = {node: 0 for node in G.nodes()}  # 计算失败时置0
        print("警告：特征向量中心性计算收敛失败，结果置0")
    
    # 合并指标
    for node in G.nodes():
        metrics[node] = {
            "type": G.nodes[node]["type"],
            "in_degree": in_degree[node],
            "out_degree": out_degree[node],
            "betweenness": betweenness[node],
            "eigenvector": eigenvector[node]
        }
    
    # 转为DataFrame
    metrics_df = pd.DataFrame.from_dict(metrics, orient="index").reset_index()
    metrics_df.columns = ["entity", "type", "in_degree", "out_degree", "betweenness", "eigenvector"]
    return metrics_df


# --------------------------
# 步骤4：按主体类型分析角色差异
# --------------------------
def analyze_type_differences(metrics_df):
    """按主体类型分组统计指标差异"""
    # 分组计算均值和标准差
    type_stats = metrics_df.groupby("type").agg({
        "in_degree": ["mean", "std", "count"],
        "out_degree": ["mean", "std", "count"],
        "betweenness": ["mean", "std", "count"],
        "eigenvector": ["mean", "std", "count"]
    })
    
    # 重命名列
    type_stats.columns = ["_".join(col).strip() for col in type_stats.columns.values]
    return type_stats


# --------------------------
# 步骤5：可视化分析结果
# --------------------------
def visualize_results(metrics_df, type_stats):
    """可视化优化：显示坐标轴数值+青绿色系+前10类型"""
    vis_dir = os.path.join(result_root, "figures")
    os.makedirs(vis_dir, exist_ok=True)
    
    # 筛选前10主体类型
    type_counts = metrics_df["type"].value_counts()
    top10_types = type_counts.index[:10].tolist()
    top10_df = metrics_df[metrics_df["type"].isin(top10_types)].copy()
    top10_df["type"] = pd.Categorical(top10_df["type"], categories=top10_types, ordered=True)
    top10_stats = type_stats.loc[top10_types].copy()
    
    # 定义青绿色系配色（从浅到深）
    cmap = plt.cm.YlGn  # 黄绿渐变（接近示例色系）
    # 或使用纯青绿渐变：cmap = plt.cm.GnBu
    bar_colors = [cmap(i/10) for i in range(10)]  # 前10类型的颜色
    line_colors = [cmap(0.2), cmap(0.4), cmap(0.6), cmap(0.8)]  # 4个指标的颜色


    # 1. Entity Type Distribution (Top 10)
    plt.figure(figsize=(10, 6))
    ax = type_counts[:10].plot(kind="bar", color=bar_colors)
    plt.title("Entity Type Distribution (Top 10)", fontdict=title_font)
    plt.xlabel("Entity Type", fontdict=label_font)
    plt.ylabel("Count", fontdict=label_font)
    plt.xticks(rotation=45)
    ax.set_xticklabels(ax.get_xticklabels(), ha="right")
    
    # Display values on y-axis
    for p in ax.patches:
        ax.annotate(f"{int(p.get_height())}",
                    (p.get_x() + p.get_width()/2., p.get_height()),
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(vis_dir, "1_entity_type_distribution.png"), dpi=300)
    plt.close()


    # 2. Centrality Metrics Boxplot (Top 10 Types)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    metrics = [
        ("in_degree", "In-Degree Centrality (Transfer Receiver Activity)"),
        ("out_degree", "Out-Degree Centrality (Transfer Sender Activity)"),
        ("betweenness", "Betweenness Centrality (Resource Control)"),
        ("eigenvector", "Eigenvector Centrality (Network Influence)")
    ]
    
    for i, (metric, title) in enumerate(metrics):
        row, col = i // 2, i % 2
        sns.boxplot(
            x="type", 
            y=metric, 
            data=top10_df, 
            ax=axes[row, col],
            palette=bar_colors  # 应用青绿色系
        )
        axes[row, col].set_title(title, fontdict=title_font)
        axes[row, col].set_xlabel("Entity Type", fontdict=label_font)
        axes[row, col].set_ylabel("Metric Value", fontdict=label_font)
        axes[row, col].tick_params(axis="x", rotation=45, labelsize=10)
        axes[row, col].set_xticklabels(axes[row, col].get_xticklabels(), ha="right")
        
        # 显示y轴具体数值（保留4位小数）
        axes[row, col].yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, _: f"{x:.4f}"
        ))
    
    plt.tight_layout()
    plt.savefig(os.path.join(vis_dir, "2_centrality_boxplot.png"), dpi=300)
    plt.close()


    # 3. Average Centrality Bar Chart (Top 10 Types)
    plt.figure(figsize=(16, 10))
    ax = top10_stats[[
        "in_degree_mean", "out_degree_mean", 
        "betweenness_mean", "eigenvector_mean"
    ]].plot(
        kind="bar", 
        yerr=top10_stats[[
            "in_degree_std", "out_degree_std", 
            "betweenness_std", "eigenvector_std"
        ]],
        capsize=5,
        color=line_colors,
        ax=plt.gca()
    )
    plt.title("Average Centrality by Entity Type (Top 10)", fontdict=title_font)
    plt.xlabel("Entity Type", fontdict=label_font)
    plt.ylabel("Average Value", fontdict=label_font)
    plt.xticks(rotation=45, fontsize=10)
    ax.set_xticklabels(ax.get_xticklabels(), ha="right")
    
    # 显示y轴具体数值（保留6位小数，适应小数值）
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, _: f"{x:.6f}"
    ))
    
    # 为每个柱子添加数值标签
    for container in ax.containers:
        ax.bar_label(container, fmt="%.6f", fontsize=8, padding=3)
    
    plt.legend(
        title="Metrics", 
        labels=["In-Degree", "Out-Degree", "Betweenness", "Eigenvector"],
        bbox_to_anchor=(1.05, 1), 
        loc="upper left"
    )
    plt.tight_layout()
    plt.savefig(os.path.join(vis_dir, "3_centrality_bar_chart.png"), dpi=300)
    plt.close()
    
    print(f"\nVisualization results saved to: {vis_dir}")

# --------------------------
# 主函数：执行完整流程
# --------------------------
def main():
    # 步骤1：数据加载与清洗
    print("=== 步骤1/5：数据加载与清洗 ===")
    cleaned_df = load_and_clean_data()
    # 保存清洗后的数据
    data_dir_out = os.path.join(result_root, "data")
    cleaned_df.to_csv(os.path.join(data_dir_out, "cleaned_transfer_data.csv"), index=False, encoding="utf-8-sig")
    
    # 步骤2：构建网络
    print("\n=== 步骤2/5：构建转让网络 ===")
    G, entity_types = build_transfer_network(cleaned_df)
    # 保存网络为GEXF（可导入Gephi可视化）
    gexf_path = os.path.join(data_dir_out, "transfer_network.gexf")
    nx.write_gexf(G, gexf_path, encoding="utf-8")
    print(f"网络已保存为GEXF：{gexf_path}")
    
    # 步骤3：计算角色指标
    print("\n=== 步骤3/5：计算角色指标 ===")
    metrics_df = calculate_role_metrics(G)
    metrics_df.to_csv(os.path.join(data_dir_out, "entity_role_metrics.csv"), index=False, encoding="utf-8-sig")
    
    # 步骤4：按类型分析
    print("\n=== 步骤4/5：按主体类型分析 ===")
    type_stats = analyze_type_differences(metrics_df)
    type_stats.to_csv(os.path.join(data_dir_out, "type_role_stats.csv"), encoding="utf-8-sig")
    print("\n主体类型统计结果：")
    print(type_stats)
    
    # 步骤5：可视化
    print("\n=== 步骤5/5：结果可视化 ===")
    visualize_results(metrics_df, type_stats)
    
    print("\n=== RQ2分析完成 ===")
    print(f"所有结果已保存至：{result_root}")


if __name__ == "__main__":
    # 检查依赖
    try:
        import networkx
        import seaborn
    except ImportError as e:
        print(f"缺少依赖：{e}，请执行安装命令：")
        print("pip install pandas openpyxl networkx matplotlib seaborn tqdm")
    else:
        main()
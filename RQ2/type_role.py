import pandas as pd
import networkx as nx
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from matplotlib.font_manager import FontProperties

# --------------------------
# 配置参数
# --------------------------
data_dir = "./data"  # 数据目录
result_root = "./result/RQ2"  # 结果目录
os.makedirs(result_root, exist_ok=True)  # 创建结果目录

# 中文显示设置
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False
title_font = {"fontsize": 14, "fontweight": "bold"}
label_font = {"fontsize": 12}


# --------------------------
# 步骤1：数据加载与预处理
# --------------------------
def load_and_clean_data():
    """加载原始数据并提取转让关系和主体类型"""
    # 读取Excel文件
    excel_path = os.path.join(data_dir, "AI_patent_data2001-2024.xlsx")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"数据文件不存在：{excel_path}")
    
    # 读取数据（只保留需要的列）
    cols_needed = [
        "专利名称", "申请号", "转让次数", "转让生效年份",
        "转让人", "转让人类型", "受让人", "受让人类型"
    ]
    df = pd.read_excel(excel_path, usecols=cols_needed, engine="openpyxl")
    
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
    betweenness = nx.betweenness_centrality(G, weight="weight", k=1000)  # k限制计算量
    
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
    vis_dir = os.path.join(result_root, "visualizations")
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


    # 1. 主体类型数量分布（前10）
    plt.figure(figsize=(10, 6))
    ax = type_counts[:10].plot(kind="bar", color=bar_colors)
    plt.title("主体类型数量分布（前10）", fontdict=title_font)
    plt.xlabel("主体类型", fontdict=label_font)
    plt.ylabel("数量", fontdict=label_font)
    plt.xticks(rotation=45)
    ax.set_xticklabels(ax.get_xticklabels(), ha="right")  # 标签右对齐
    
    # 显示坐标轴具体数值（y轴）
    for p in ax.patches:
        ax.annotate(f"{int(p.get_height())}",  # 显示数量
                    (p.get_x() + p.get_width()/2., p.get_height()),
                    ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(vis_dir, "1_主体类型数量分布.png"), dpi=300)
    plt.close()


    # 2. 中心性指标箱线图（前10类型）
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    metrics = [
        ("in_degree", "入度中心性（被转让活跃度）"),
        ("out_degree", "出度中心性（主动转让活跃度）"),
        ("betweenness", "中介中心性（资源控制能力）"),
        ("eigenvector", "特征向量中心性（网络影响力）")
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
        axes[row, col].set_xlabel("主体类型", fontdict=label_font)
        axes[row, col].set_ylabel("指标值", fontdict=label_font)
        axes[row, col].tick_params(axis="x", rotation=45, labelsize=10)
        axes[row, col].set_xticklabels(axes[row, col].get_xticklabels(), ha="right")
        
        # 显示y轴具体数值（保留4位小数）
        axes[row, col].yaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, _: f"{x:.4f}"
        ))
    
    plt.tight_layout()
    plt.savefig(os.path.join(vis_dir, "2_中心性指标箱线图.png"), dpi=300)
    plt.close()


    # 3. 中心性均值柱状图（前10类型）
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
        color=line_colors,  # 应用青绿色系（4个指标对应4种深浅）
        ax=plt.gca()
    )
    plt.title("不同类型主体的中心性均值（前10类型）", fontdict=title_font)
    plt.xlabel("主体类型", fontdict=label_font)
    plt.ylabel("均值", fontdict=label_font)
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
        title="指标", 
        labels=["入度中心性", "出度中心性", "中介中心性", "特征向量中心性"],
        bbox_to_anchor=(1.05, 1), 
        loc="upper left"
    )
    plt.tight_layout()
    plt.savefig(os.path.join(vis_dir, "3_中心性均值柱状图.png"), dpi=300)
    plt.close()
    
    print(f"\n可视化结果已保存至：{vis_dir}")

# --------------------------
# 主函数：执行完整流程
# --------------------------
def main():
    # 步骤1：数据加载与清洗
    print("=== 步骤1/5：数据加载与清洗 ===")
    cleaned_df = load_and_clean_data()
    # 保存清洗后的数据
    cleaned_df.to_csv(os.path.join(result_root, "cleaned_transfer_data.csv"), index=False, encoding="utf-8-sig")
    
    # 步骤2：构建网络
    print("\n=== 步骤2/5：构建转让网络 ===")
    G, entity_types = build_transfer_network(cleaned_df)
    # 保存网络为GEXF（可导入Gephi可视化）
    gexf_path = os.path.join(result_root, "transfer_network.gexf")
    nx.write_gexf(G, gexf_path, encoding="utf-8")
    print(f"网络已保存为GEXF：{gexf_path}")
    
    # 步骤3：计算角色指标
    print("\n=== 步骤3/5：计算角色指标 ===")
    metrics_df = calculate_role_metrics(G)
    metrics_df.to_csv(os.path.join(result_root, "entity_role_metrics.csv"), index=False, encoding="utf-8-sig")
    
    # 步骤4：按类型分析
    print("\n=== 步骤4/5：按主体类型分析 ===")
    type_stats = analyze_type_differences(metrics_df)
    type_stats.to_csv(os.path.join(result_root, "type_role_stats.csv"), encoding="utf-8-sig")
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
import pandas as pd
import numpy as np
import networkx as nx
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
import seaborn as sns
import os
import warnings
warnings.filterwarnings('ignore')

# --------------------------
# 1. 全局设置（彻底解决中文+编码问题）
# --------------------------
os.chdir("D:/AI_patent")  # 你的工作目录

# 中文显示适配
plt.rcParams['font.sans-serif'] = ['SimHei']  # 黑体
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号

# 创建结果目录
result_root = "./result/RQ4"
os.makedirs(result_root, exist_ok=True)
fig_dir = os.path.join(result_root, "figures")
os.makedirs(fig_dir, exist_ok=True)

# --------------------------
# 2. 数据加载与精简
# --------------------------
def load_and_preprocess_data():
    # 读取Excel数据
    excel_path = "./data/AI_patent_data2001-2024.xlsx"
    df = pd.read_excel(excel_path)
    print(f"原始数据：{len(df)} 条记录")
    
    # 提取边数据（去重+去自环）
    edges_df = df[["转让人", "受让人"]].dropna()
    edges_df["转让人"] = edges_df["转让人"].astype(str).str.strip()
    edges_df["受让人"] = edges_df["受让人"].astype(str).str.strip()
    edges_df = edges_df[edges_df["转让人"] != edges_df["受让人"]].drop_duplicates()
    print(f"有效转让关系：{len(edges_df)} 条")
    
    # 提取节点数据（创新产出+精简分类变量）
    all_entities = pd.unique(edges_df[["转让人", "受让人"]].values.ravel("K"))
    nodes_df = pd.DataFrame({"主体ID": all_entities})
    
    # 创新产出（转让次数代理）
    transfer_counts = pd.concat([
        edges_df["转让人"].value_counts(),
        edges_df["受让人"].value_counts()
    ], axis=1).sum(axis=1).reset_index()
    transfer_counts.columns = ["主体ID", "专利数量"]
    nodes_df = pd.merge(nodes_df, transfer_counts, on="主体ID", how="left")
    nodes_df["专利数量"] = nodes_df["专利数量"].fillna(0).astype(int)
    
    # 精简省份（只保留省级行政区）
    def extract_province(address):
        if pd.isna(address) or address == "未知":
            return "未知"
        address = str(address)
        provinces = ["北京", "上海", "广东", "江苏", "浙江", "山东", "四川", "湖北", "湖南", 
                     "河南", "河北", "辽宁", "陕西", "安徽", "福建", "黑龙江", "江西", 
                     "广西", "吉林", "山西", "内蒙古", "贵州", "云南", "新疆", "甘肃", 
                     "青海", "海南", "宁夏", "西藏", "天津", "重庆"]
        for p in provinces:
            if p in address:
                return p
        return "其他"
    
    # 精简主体类型
    def simplify_entity_type(entity_name):
        if pd.isna(entity_name):
            return "其他"
        entity_name = str(entity_name)
        if any(key in entity_name for key in ["公司", "企业", "集团", "有限"]):
            return "企业"
        elif any(key in entity_name for key in ["大学", "学院", "科研", "研究院"]):
            return "高校/科研"
        else:
            return "其他"
    
    # 提取并精简属性
    assigner_info = df[["转让人", "申请人地区"]].dropna().rename(
        columns={"转让人": "主体ID", "申请人地区": "省份"}
    )
    receiver_info = df[["受让人", "受让人地址"]].dropna().rename(
        columns={"受让人": "主体ID", "受让人地址": "省份"}
    )
    entity_info = pd.concat([assigner_info, receiver_info]).drop_duplicates("主体ID")
    entity_info["省份"] = entity_info["省份"].apply(extract_province)
    entity_info["主体类型"] = entity_info["主体ID"].apply(simplify_entity_type)
    
    # 合并节点属性
    nodes_df = pd.merge(nodes_df, entity_info[["主体ID", "主体类型", "省份"]], on="主体ID", how="left")
    nodes_df[["主体类型", "省份"]] = nodes_df[["主体类型", "省份"]].fillna("其他")
    
    print(f"节点数据：{len(nodes_df)} 个主体")
    return edges_df, nodes_df

edges_df, nodes_df = load_and_preprocess_data()

# --------------------------
# 3. 网络构建与中心性计算
# --------------------------
def build_network_and_calculate_centrality(edges_df):
    G = nx.DiGraph()
    edge_weights = edges_df.groupby(["转让人", "受让人"]).size().reset_index(name="weight")
    G.add_weighted_edges_from([(r["转让人"], r["受让人"], r["weight"]) for _, r in edge_weights.iterrows()])
    print(f"网络规模：{G.number_of_nodes()} 节点，{G.number_of_edges()} 边")
    
    # 中心性计算
    centrality = {}
    centrality["degree"] = nx.degree_centrality(G)
    centrality["in_degree"] = nx.in_degree_centrality(G)
    centrality["out_degree"] = nx.out_degree_centrality(G)
    centrality["betweenness"] = nx.betweenness_centrality(G, weight="weight", k=100)
    
    # 特征向量中心性（异常处理）
    try:
        centrality["eigenvector"] = nx.eigenvector_centrality(G, weight="weight", max_iter=500, tol=1e-4)
    except:
        centrality["eigenvector"] = {n: 0 for n in G.nodes()}
    
    # K-core核心度
    G_undir = G.to_undirected()
    centrality["k_core"] = nx.core_number(G_undir)
    
    # 转换为DataFrame
    centrality_df = pd.DataFrame(centrality).reset_index()
    centrality_df.columns = ["主体ID"] + list(centrality.keys())
    return centrality_df

centrality_df = build_network_and_calculate_centrality(edges_df)
# 保存时指定编码为utf-8
centrality_df.to_csv(os.path.join(result_root, "node_centrality.csv"), index=False, encoding="utf-8-sig")
print("中心性指标已保存")

# --------------------------
# 4. 回归分析（解决编码错误）
# --------------------------
# 合并数据
analysis_df = pd.merge(
    nodes_df[["主体ID", "专利数量", "主体类型", "省份"]],
    centrality_df,
    on="主体ID",
    how="inner"
)
print(f"分析数据：{len(analysis_df)} 个主体")

# 生成哑变量
analysis_df = pd.get_dummies(analysis_df, columns=["主体类型", "省份"], drop_first=True)
print(f"哑变量后维度：{analysis_df.shape}")

# 探索性分析
def exploratory_analysis(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    corr_matrix = df[numeric_cols].corr()
    centrality_cols = ["degree", "in_degree", "out_degree", "betweenness", "eigenvector", "k_core"]
    plot_corr = corr_matrix.loc[["专利数量"], centrality_cols]
    
    plt.figure(figsize=(10, 4))
    sns.heatmap(plot_corr, annot=True, cmap="coolwarm", fmt=".3f")
    plt.title("网络位置与创新产出相关性")
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "correlation_heatmap.png"), dpi=300)
    plt.close()

exploratory_analysis(analysis_df)

# 回归模型（修复文件写入编码）
def regression_analysis(df):
    y = df["专利数量"]
    X = df.drop(columns=["主体ID", "专利数量"])
    
    # 去除冗余变量
    X = X.loc[:, X.var() > 0]
    print(f"最终回归变量数：{X.shape[1]}")
    
    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 泊松回归
    poisson_model = PoissonRegressor(alpha=0.1, max_iter=1000)
    poisson_model.fit(X_scaled, y)
    poisson_pred = poisson_model.predict(X_scaled)
    poisson_r2 = r2_score(y, poisson_pred)
    
    # 提取系数
    coefficients = pd.DataFrame({
        "变量": X.columns,
        "泊松回归系数": poisson_model.coef_
    }).sort_values(by="泊松回归系数", key=abs, ascending=False)
    
    # 保存结果（指定utf-8编码，解决GBK错误）
    coefficients.to_csv(os.path.join(result_root, "regression_coefficients.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(result_root, "model_performance.txt"), "w", encoding="utf-8") as f:
        f.write(f"泊松回归伪R²: {poisson_r2:.4f}\n")
    
    print("核心变量系数（前10）：")
    print(coefficients.head(10))
    return coefficients

reg_coef = regression_analysis(analysis_df)

# --------------------------
# 5. 结果可视化
# --------------------------
def visualize_results(coefficients):
    centrality_vars = ["degree", "in_degree", "out_degree", "betweenness", "eigenvector", "k_core"]
    centrality_coef = coefficients[coefficients["变量"].isin(centrality_vars)]
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x="变量", y="泊松回归系数", data=centrality_coef, palette="coolwarm")
    plt.axhline(y=0, color="black", linestyle="--")
    plt.title("网络位置对创新产出的影响系数")
    plt.xlabel("网络位置指标")
    plt.ylabel("泊松回归系数")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "centrality_coefficients.png"), dpi=300)
    plt.close()

visualize_results(reg_coef)

print("\n✅ RQ4分析完成！所有结果已保存至", result_root)
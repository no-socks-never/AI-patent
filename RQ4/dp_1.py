# RQ4简化版本 - 强制中文显示版本
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
import os

def quick_rq4_analysis_force_chinese():
    """强制中文显示的RQ4分析"""
    print("=== RQ4简化分析（强制中文显示） ===")
    
    # 设置路径
    result_root = "./result/RQ4_simple"
    os.makedirs(result_root, exist_ok=True)
    
    # 方法1：直接设置字体路径（如果知道系统中文字体位置）
    try:
        # Windows 常见中文字体
        zh_fonts = ['SimHei', 'Microsoft YaHei', 'KaiTi', 'SimSun']
        for font in zh_fonts:
            try:
                mpl.rcParams['font.family'] = font
                mpl.rcParams['axes.unicode_minus'] = False
                print(f"使用字体: {font}")
                break
            except:
                continue
    except:
        pass
    
    # 1. 加载数据
    edges_path = "./result/RQ3/cleaned_edges.csv"
    df = pd.read_csv(edges_path)
    
    # 2. 构建简单网络
    G = nx.DiGraph()
    for _, row in df.head(10000).iterrows():
        G.add_edge(row['转让人'], row['受让人'])
    
    print(f"网络: {G.number_of_nodes()}节点, {G.number_of_edges()}边")
    
    # 3. 计算核心指标
    nodes_data = []
    for node in G.nodes():
        degree = G.degree(node)
        try:
            pagerank = nx.pagerank(G)[node]
        except:
            pagerank = 0
        
        assigner_count = len([e for e in G.out_edges(node)])
        assignee_count = len([e for e in G.in_edges(node)])
        total_activity = assigner_count + assignee_count
        
        nodes_data.append({
            'node': node,
            'degree': degree,
            'pagerank': pagerank,
            'assigner_count': assigner_count,
            'assignee_count': assignee_count,
            'total_activity': total_activity
        })
    
    analysis_df = pd.DataFrame(nodes_data)
    
    # 4. 简单回归分析
    X = analysis_df[['degree', 'pagerank']]
    y = analysis_df['total_activity']
    
    rf = RandomForestRegressor(n_estimators=50, random_state=42)
    rf.fit(X, y)
    
    importance_df = pd.DataFrame({
        'feature': ['度数中心性', 'PageRank'],  # 直接用中文
        'importance': rf.feature_importances_
    })
    
    # 5. 可视化 - 使用更直接的中文设置方法
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # 第一个图：散点图
    ax1.scatter(analysis_df['degree'], analysis_df['total_activity'], alpha=0.6)
    ax1.set_xlabel('节点度数', fontname='SimHei')
    ax1.set_ylabel('总专利活动', fontname='SimHei')
    ax1.set_title('度数中心性 vs 创新产出', fontname='SimHei', fontsize=14)
    
    # 第二个图：柱状图（直接使用matplotlib，避免seaborn字体问题）
    features = importance_df['feature'].tolist()
    importances = importance_df['importance'].tolist()
    
    bars = ax2.bar(features, importances, color=['skyblue', 'lightcoral'])
    ax2.set_xlabel('特征', fontname='SimHei')
    ax2.set_ylabel('重要性', fontname='SimHei')
    ax2.set_title('特征重要性', fontname='SimHei', fontsize=14)
    
    # 在柱子上添加数值标签
    for bar, importance in zip(bars, importances):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{importance:.3f}',
                ha='center', va='bottom', fontname='SimHei')
    
    plt.tight_layout()
    plt.savefig(os.path.join(result_root, 'quick_analysis.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 保存结果
    analysis_df.to_csv(os.path.join(result_root, 'quick_analysis.csv'), index=False)
    importance_df.to_csv(os.path.join(result_root, 'feature_importance.csv'), index=False)
    
    print("简化分析完成!")
    print(f"结果保存至: {result_root}")

if __name__ == "__main__":
    quick_rq4_analysis_force_chinese()
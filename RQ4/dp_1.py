# RQ4简化版本 - 强制中文显示版本
import os
# 设置matplotlib配置目录（解决权限问题）
os.environ['MPLCONFIGDIR'] = os.path.join(os.getcwd(), '.matplotlib_cache')
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
import warnings

# 导入跨平台字体配置
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from font_config import setup_chinese_fonts, get_font_dict

def quick_rq4_analysis_force_chinese():
    """跨平台兼容的RQ4简化分析"""
    print("=== RQ4简化分析（跨平台兼容版） ===")
    
    # 设置路径
    result_root = "./result/RQ4_simple"
    os.makedirs(result_root, exist_ok=True)
    
    # 自动配置中文字体（支持 Windows/macOS/Linux）
    setup_chinese_fonts()
    
    # 1. 加载数据
    # 如果RQ3的结果存在，使用它；否则从data目录读取原始数据
    edges_path = "./result/RQ3/cleaned_edges.csv"
    if os.path.exists(edges_path):
        df = pd.read_csv(edges_path)
        print(f"从RQ3结果加载数据：{len(df)}条记录")
    else:
        print("RQ3结果不存在，从data目录读取原始数据...")
        data_dir = "./data"
        excel_files = [f for f in os.listdir(data_dir) if f.endswith('.xlsx') and not f.startswith('~$')]
        if not excel_files:
            raise FileNotFoundError(f"数据目录不存在Excel文件：{data_dir}")
        
        print(f"发现{len(excel_files)}个Excel文件，开始合并...")
        dfs = []
        for file in sorted(excel_files):
            file_path = os.path.join(data_dir, file)
            try:
                temp_df = pd.read_excel(file_path, engine='openpyxl')
                dfs.append(temp_df)
                print(f"  已读取：{file}，记录数：{len(temp_df)}")
            except Exception as e:
                print(f"  警告：文件{file}读取失败：{str(e)}")
                continue
        
        if not dfs:
            raise ValueError("没有成功读取任何Excel文件")
        
        raw_df = pd.concat(dfs, ignore_index=True)
        print(f"成功合并所有文件，总记录数：{len(raw_df)}")
        
        # 提取转让关系
        df = raw_df[["转让人", "受让人"]].dropna()
        df = df[(df["转让人"].notna()) & (df["受让人"].notna())]
        print(f"提取转让关系：{len(df)}条记录")
    
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
        'feature': ['Degree Centrality', 'PageRank'],
        'importance': rf.feature_importances_
    })
    
    # 5. Visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    # First plot: Scatter plot
    ax1.scatter(analysis_df['degree'], analysis_df['total_activity'], alpha=0.6)
    ax1.set_xlabel('Node Degree')
    ax1.set_ylabel('Total Patent Activity')
    ax1.set_title('Degree Centrality vs Innovation Output', fontsize=14)
    
    # Second plot: Bar chart
    features = importance_df['feature'].tolist()
    importances = importance_df['importance'].tolist()
    
    bars = ax2.bar(features, importances, color=['skyblue', 'lightcoral'])
    ax2.set_xlabel('Feature')
    ax2.set_ylabel('Importance')
    ax2.set_title('Feature Importance', fontsize=14)
    
    # 在柱子上添加数值标签
    for bar, importance in zip(bars, importances):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{importance:.3f}',
                ha='center', va='bottom')
    
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
import os
# 设置matplotlib配置目录（解决权限问题）
os.environ['MPLCONFIGDIR'] = os.path.join(os.getcwd(), '.matplotlib_cache')
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

import pandas as pd
import networkx as nx
from tqdm import tqdm
import numpy as np
import seaborn as sns
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import warnings

# 导入跨平台字体配置和数据加载工具
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from font_config import setup_chinese_fonts, get_font_dict
from data_loader import load_all_excel_files

# 自动配置中文字体（支持 Windows/macOS/Linux）
setup_chinese_fonts()
plt.rcParams['font.size'] = 10

# 1. 数据加载与预处理
def load_and_preprocess_data(data_dir):
    print(f"当前工作目录：{os.getcwd()}")
    print(f"数据读取路径：{os.path.abspath(data_dir)}")
    
    # 使用统一的数据加载工具（支持缓存）
    df = load_all_excel_files(data_dir=data_dir, use_cache=True)
    print(f"成功加载数据，总记录数：{len(df)}")
    
    required_columns = ['转让次数', '转让人', '受让人', '转让生效日', '转让生效年份']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"数据缺少必要字段：{missing_cols}")
    
    valid_transfer = df[(df['转让次数'] >= 1) & 
                       (df['转让人'].notna()) & 
                       (df['受让人'].notna())].copy()
    
    valid_transfer['转让生效日'] = pd.to_datetime(valid_transfer['转让生效日'], 
                                               format='%Y-%m-%d', 
                                               errors='coerce')
    valid_transfer['转让年份'] = valid_transfer['转让生效年份'].fillna(
        valid_transfer['转让生效日'].dt.year
    ).astype(int, errors='ignore')
    
    valid_transfer = valid_transfer[(valid_transfer['转让年份'] >= 2000) & 
                                   (valid_transfer['转让年份'] <= 2024)]
    
    print(f"有效转让记录数：{len(valid_transfer)}")
    if len(valid_transfer) == 0:
        print("警告：未筛选出有效转让记录，请检查数据质量")
    else:
        year_dist = sorted(valid_transfer['转让年份'].unique())
        print(f"年份分布：{year_dist}（共{len(year_dist)}个年份）")
    
    return valid_transfer

# 2. 构建年度有向加权网络
def build_annual_networks(df):
    df = df[df['转让年份'].notna()]
    if len(df) == 0:
        raise ValueError("无有效年份数据，无法构建网络")
    
    years = sorted(df['转让年份'].unique())
    annual_networks = {}
    
    for year in tqdm(years, desc="构建年度网络"):
        year_data = df[df['转让年份'] == year]
        edges = year_data.groupby(['转让人', '受让人']).size().reset_index(name='weight')
        
        G = nx.DiGraph()
        nodes = pd.unique(edges[['转让人', '受让人']].values.ravel('K'))
        G.add_nodes_from(nodes)
        for _, row in edges.iterrows():
            G.add_edge(row['转让人'], row['受让人'], weight=row['weight'])
        
        annual_networks[year] = G
        print(f"✅ {year}年网络：{G.number_of_nodes()}个节点，{G.number_of_edges()}条边")
    
    return annual_networks

# 3. 网络指标计算（移除连通分量计算）
def calculate_network_metrics(annual_networks):
    if not annual_networks:
        raise ValueError("无网络数据，无法计算指标")
    
    metrics_list = []
    
    for year, G in tqdm(annual_networks.items(), desc="计算网络指标"):
        n_nodes = G.number_of_nodes()
        n_edges = G.number_of_edges()
        
        # 网络密度
        density = nx.density(G) if n_nodes >= 2 else 0
        
        # 平均聚类系数
        try:
            clustering = nx.average_clustering(G.to_undirected()) if n_nodes >= 2 else 0
        except:
            clustering = 0
        
        # 平均路径长度（简化处理，不依赖连通分量）
        avg_path = 0
        
        # 模块度计算
        try:
            from community import community_louvain
            modularity = community_louvain.modularity(
                community_louvain.best_partition(G.to_undirected()), 
                G.to_undirected()
            ) if n_nodes >= 2 else 0
        except ImportError:
            print("⚠️ 未安装community库，模块度计算跳过（执行：pip install python-louvain）")
            modularity = None
        except:
            modularity = 0
        
        # 保存指标（不含连通分量相关字段）
        metrics_list.append({
            'year': year,
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'density': round(density, 6),
            'avg_clustering': round(clustering, 6),
            'avg_path_length': round(avg_path, 6),
            'modularity': round(modularity, 6) if modularity is not None else None
        })
    
    metrics_df = pd.DataFrame(metrics_list)
    return metrics_df

# 4. 导出GEXF文件
def export_gexf(annual_networks, output_dir='./result/RQ1/gexf'):
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📤 GEXF文件保存路径：{os.path.abspath(output_dir)}")
    
    for year, G in tqdm(annual_networks.items(), desc="导出GEXF文件"):
        gexf_path = os.path.join(output_dir, f'year_{year}_network.gexf')
        nx.write_gexf(G, gexf_path, encoding='utf-8')
        print(f"✅ {year}年GEXF文件已保存：{os.path.basename(gexf_path)}")

# 5. 可视化函数（修复字体参数错误）
def visualize_trends(metrics_df, output_dir='./result/RQ1/trends'):
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📈 指标趋势图保存路径：{os.path.abspath(output_dir)}")
    
    # 定义字体配置（Mac系统适配）
    title_font = {'fontsize': 14, 'fontweight': 'bold'}
    label_font = {'fontsize': 12}
    legend_font = {'size': 11}
    
    sns.set_style("whitegrid")
    sns.set_palette("tab10")
    fig_params = {'figsize': (10, 6), 'dpi': 300}
    
    # 1. Network Size
    plt.figure(**fig_params)
    sns.lineplot(data=metrics_df, x='year', y='n_nodes', marker='o', linewidth=2.5, label='Nodes')
    sns.lineplot(data=metrics_df, x='year', y='n_edges', marker='s', linewidth=2.5, label='Edges')
    plt.title('Patent Transfer Network Size Evolution', fontdict=title_font, pad=15)
    plt.xlabel('Year', fontdict=label_font)
    plt.ylabel('Count', fontdict=label_font)
    plt.legend(prop=legend_font)
    plt.xticks(metrics_df['year'], rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'network_size_trend.png'), facecolor='white')
    plt.close()
    
    # 2. Network Density
    plt.figure(**fig_params)
    sns.lineplot(data=metrics_df, x='year', y='density', marker='^', linewidth=2.5, color='#2ecc71')
    plt.title('Patent Transfer Network Density Evolution', fontdict=title_font, pad=15)
    plt.xlabel('Year', fontdict=label_font)
    plt.ylabel('Density', fontdict=label_font)
    plt.xticks(metrics_df['year'], rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'network_density_trend.png'), facecolor='white')
    plt.close()
    
    # 3. Average Clustering Coefficient
    plt.figure(**fig_params)
    sns.lineplot(data=metrics_df, x='year', y='avg_clustering', marker='d', linewidth=2.5, color='#e74c3c')
    plt.title('Average Clustering Coefficient Evolution', fontdict=title_font, pad=15)
    plt.xlabel('Year', fontdict=label_font)
    plt.ylabel('Clustering Coefficient', fontdict=label_font)
    plt.xticks(metrics_df['year'], rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'network_clustering_trend.png'), facecolor='white')
    plt.close()
    
    # 4. Average Path Length
    plt.figure(**fig_params)
    sns.lineplot(data=metrics_df, x='year', y='avg_path_length', marker='*', linewidth=2.5, color='#9b59b6')
    plt.title('Average Path Length Evolution', fontdict=title_font, pad=15)
    plt.xlabel('Year', fontdict=label_font)
    plt.ylabel('Path Length', fontdict=label_font)
    plt.xticks(metrics_df['year'], rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'network_path_length_trend.png'), facecolor='white')
    plt.close()
    
    # 5. Modularity
    if 'modularity' in metrics_df.columns and not metrics_df['modularity'].isna().all():
        plt.figure(**fig_params)
        sns.lineplot(data=metrics_df, x='year', y='modularity', marker='p', linewidth=2.5, color='#f39c12')
        plt.title('Network Modularity Evolution', fontdict=title_font, pad=15)
        plt.xlabel('Year', fontdict=label_font)
        plt.ylabel('Modularity', fontdict=label_font)
        plt.xticks(metrics_df['year'], rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'network_modularity_trend.png'), facecolor='white')
        plt.close()
    
    print("✅ All trend charts saved")

# 主函数
def main():
    try:
        data_dir = "./data_cleaned"
        result_root = "./result/RQ1_network_metrics"
        os.makedirs(result_root, exist_ok=True)
        os.makedirs(os.path.join(result_root, "data"), exist_ok=True)
        os.makedirs(os.path.join(result_root, "figures"), exist_ok=True)
        
        data_dir_out = os.path.join(result_root, "data")
        fig_dir = os.path.join(result_root, "figures")
        os.makedirs(data_dir_out, exist_ok=True)
        os.makedirs(fig_dir, exist_ok=True)
        
        print("\n=== 步骤1/5：加载并预处理数据 ===")
        df = load_and_preprocess_data(data_dir)
        if len(df) == 0:
            print("⚠️ 无有效数据，程序提前退出")
            return
        
        print("\n=== 步骤2/5：构建年度专利转让网络 ===")
        annual_networks = build_annual_networks(df)
        if not annual_networks:
            print("⚠️ 未构建任何年度网络，程序提前退出")
            return
        
        print("\n=== 步骤3/5：计算网络指标 ===")
        metrics_df = calculate_network_metrics(annual_networks)  # 不再返回连通分量统计
        
        metrics_path = os.path.join(data_dir_out, "network_metrics.csv")
        metrics_df.to_csv(metrics_path, index=False, encoding="utf-8-sig")
        print(f"✅ 网络指标已保存：{os.path.abspath(metrics_path)}")
        
        print("\n=== 步骤4/5：导出GEXF文件 ===")
        export_gexf(annual_networks, output_dir=data_dir_out)
        
        print("\n=== 步骤5/5：绘制指标趋势图 ===")
        visualize_trends(metrics_df, output_dir=fig_dir)
        
        print("\n=== 分析完成 ===")
        print(f"结果目录：{os.path.abspath(result_root)}")
        
    except Exception as e:
        print(f"\n❌ 程序执行出错：{str(e)}")
        return

if __name__ == "__main__":
    print("依赖安装：pip install networkx pandas matplotlib seaborn python-louvain tqdm openpyxl")
    main()
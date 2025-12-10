"""
节点筛选工具：基于度（degree）筛选网络节点
目标：从度>=1改为度>=2，减少计算开销
"""

import os
import sys
import pandas as pd
import networkx as nx
from pathlib import Path
import numpy as np
from datetime import datetime

# 设置matplotlib配置目录
os.environ['MPLCONFIGDIR'] = os.path.join(os.getcwd(), '.matplotlib_cache')
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

# 导入数据加载工具
sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_all_excel_files

# 自动检测项目根目录（包含data_cleaned的目录）
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # coding的父目录
os.chdir(project_root)  # 切换到项目根目录

# 设置输出目录
OUTPUT_DIR = "./result/node_filtering"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "data"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "figures"), exist_ok=True)

print("=" * 70)
print("节点筛选工具：基于度（degree）筛选")
print("=" * 70)
print(f"当前工作目录：{os.getcwd()}")
print(f"筛选条件：度 >= 2（入度 + 出度 >= 2）")
print(f"输出目录：{OUTPUT_DIR}")
print("=" * 70 + "\n")

# =============================================================================
# 步骤1：加载原始数据
# =============================================================================
print("[步骤1/5] 加载原始数据...")
data_dir = "./data_cleaned"
df_raw = load_all_excel_files(data_dir=data_dir, use_cache=True)
print(f"  ✅ 原始数据：{len(df_raw):,} 条记录")
print(f"  列名：{list(df_raw.columns)[:10]}...\n")

# 检查必要字段
required_cols = ['转让人', '受让人']
missing_cols = [col for col in required_cols if col not in df_raw.columns]
if missing_cols:
    raise ValueError(f"数据缺少必要字段：{missing_cols}")

# 检查是否有类型字段
has_type_cols = '转让人类型' in df_raw.columns and '受让人类型' in df_raw.columns
if has_type_cols:
    print(f"  ✅ 发现类型字段：转让人类型、受让人类型")
else:
    print(f"  ⚠️  未找到类型字段，将跳过类型提取")

# 数据清洗：去除缺失值和自环
df_clean = df_raw[
    (df_raw['转让人'].notna()) & 
    (df_raw['受让人'].notna()) &
    (df_raw['转让人'] != df_raw['受让人'])
].copy()

df_clean['转让人'] = df_clean['转让人'].astype(str).str.strip()
df_clean['受让人'] = df_clean['受让人'].astype(str).str.strip()

print(f"  ✅ 清洗后数据：{len(df_clean):,} 条记录")
print(f"  唯一转让人数：{df_clean['转让人'].nunique():,}")
print(f"  唯一受让人数：{df_clean['受让人'].nunique():,}\n")

# =============================================================================
# 步骤2：构建完整网络并计算节点度
# =============================================================================
print("[步骤2/5] 构建完整网络并计算节点度...")

# 构建有向网络（聚合重复边）
G_full = nx.DiGraph()

# 统计边权重（同一对转让人-受让人可能有多次转让）
edge_weights = df_clean.groupby(['转让人', '受让人']).size().reset_index(name='weight')

# 添加边
for _, row in edge_weights.iterrows():
    G_full.add_edge(row['转让人'], row['受让人'], weight=row['weight'])

print(f"  ✅ 完整网络规模：")
print(f"    节点数：{G_full.number_of_nodes():,}")
print(f"    边数：{G_full.number_of_edges():,}")

# 计算每个节点的度（入度 + 出度）
node_degrees = {}
for node in G_full.nodes():
    in_degree = G_full.in_degree(node)
    out_degree = G_full.out_degree(node)
    total_degree = in_degree + out_degree
    node_degrees[node] = {
        'in_degree': in_degree,
        'out_degree': out_degree,
        'total_degree': total_degree
    }

# 转换为DataFrame
degrees_df = pd.DataFrame.from_dict(node_degrees, orient='index').reset_index()
degrees_df.columns = ['节点ID', '入度', '出度', '总度']
degrees_df = degrees_df.sort_values('总度', ascending=False).reset_index(drop=True)

# 提取节点类型信息（如果存在类型字段）
if has_type_cols:
    print("  提取节点类型信息...")
    
    # 提取转让人类型（去重，保留第一个）
    assigner_types = df_clean[['转让人', '转让人类型']].dropna(subset=['转让人', '转让人类型'])
    assigner_types = assigner_types.drop_duplicates(subset=['转让人'], keep='first')
    assigner_types = assigner_types.rename(columns={'转让人': '节点ID', '转让人类型': '类型_转让人'})
    
    # 提取受让人类型（去重，保留第一个）
    receiver_types = df_clean[['受让人', '受让人类型']].dropna(subset=['受让人', '受让人类型'])
    receiver_types = receiver_types.drop_duplicates(subset=['受让人'], keep='first')
    receiver_types = receiver_types.rename(columns={'受让人': '节点ID', '受让人类型': '类型_受让人'})
    
    # 合并类型信息（outer join，确保所有节点都有类型）
    entity_types = assigner_types.merge(
        receiver_types, 
        on='节点ID', 
        how='outer'
    )
    
    # 确定最终类型：优先使用转让人类型，如果不存在则使用受让人类型
    def determine_type(row):
        assigner_type = row.get('类型_转让人')
        receiver_type = row.get('类型_受让人')
        
        if pd.notna(assigner_type) and str(assigner_type).strip() != '':
            return str(assigner_type).strip()
        elif pd.notna(receiver_type) and str(receiver_type).strip() != '':
            return str(receiver_type).strip()
        else:
            return '未知'
    
    entity_types['申请人类型'] = entity_types.apply(determine_type, axis=1)
    entity_types = entity_types[['节点ID', '申请人类型']]
    
    # 合并到度统计DataFrame
    degrees_df = degrees_df.merge(entity_types, on='节点ID', how='left')
    degrees_df['申请人类型'] = degrees_df['申请人类型'].fillna('未知')
    
    # 统计类型分布
    type_dist = degrees_df['申请人类型'].value_counts()
    print(f"    节点类型分布：")
    for entity_type, count in type_dist.head(10).items():
        print(f"      {entity_type}: {count:,} 个节点 ({count/len(degrees_df)*100:.2f}%)")
else:
    # 如果没有类型字段，添加空列
    degrees_df['申请人类型'] = '未知'

print(f"\n  节点度统计：")
print(f"    总度最小值：{degrees_df['总度'].min()}")
print(f"    总度最大值：{degrees_df['总度'].max()}")
print(f"    总度平均值：{degrees_df['总度'].mean():.2f}")
print(f"    总度中位数：{degrees_df['总度'].median():.2f}")

# 统计不同度值的节点数量
degree_dist = degrees_df['总度'].value_counts().sort_index()
print(f"\n  度分布（前10个最常见的度值）：")
for degree, count in degree_dist.head(10).items():
    print(f"    度={degree}: {count:,} 个节点")

# 保存完整度统计（包含类型信息）
degrees_file = os.path.join(OUTPUT_DIR, "data", "node_degrees_full.csv")
# 确保列顺序：节点ID, 入度, 出度, 总度, 申请人类型
column_order = ['节点ID', '入度', '出度', '总度', '申请人类型']
degrees_df = degrees_df[column_order]
degrees_df.to_csv(degrees_file, index=False, encoding='utf-8-sig')
print(f"\n  ✅ 完整度统计已保存：{degrees_file}（包含申请人类型）\n")

# =============================================================================
# 步骤3：筛选度>=2的节点
# =============================================================================
print("[步骤3/5] 筛选度 >= 2 的节点...")

# 筛选度>=2的节点（用于数据筛选）
nodes_degree_ge2 = degrees_df[degrees_df['总度'] >= 2]['节点ID'].tolist()
n_nodes_before = len(degrees_df)
n_nodes_degree_ge2 = len(nodes_degree_ge2)  # 筛选前度>=2的节点数

print(f"  筛选前节点数（所有节点）：{n_nodes_before:,}")
print(f"  筛选条件：度 >= 2 的节点数：{n_nodes_degree_ge2:,}")
print(f"  筛选比例：{n_nodes_degree_ge2/n_nodes_before*100:.2f}%")
print(f"  说明：这些节点将用于数据筛选，最终网络中的实际节点数将在步骤4中确定")

# 筛选度>=2的节点（用于后续数据筛选）
# 注意：这些节点中，部分可能不会出现在最终网络中（因为它们只连接到度=1的节点）
degrees_filtered_pre = degrees_df[degrees_df['总度'] >= 2].copy()
print(f"\n  筛选前度>=2的节点数：{len(degrees_filtered_pre):,}")
print(f"    说明：这些节点将用于数据筛选，但最终网络中的实际节点数可能更少")

# =============================================================================
# 步骤4：筛选数据（只保留度>=2节点之间的边）
# =============================================================================
print("[步骤4/5] 筛选数据（只保留度>=2节点之间的边）...")

# 筛选数据：只保留转让人和受让人都在筛选节点集合中的记录
df_filtered = df_clean[
    (df_clean['转让人'].isin(nodes_degree_ge2)) & 
    (df_clean['受让人'].isin(nodes_degree_ge2))
].copy()

n_edges_before = len(df_clean)
n_edges_after = len(df_filtered)

print(f"  筛选前边数（记录数）：{n_edges_before:,}")
print(f"  筛选后边数（记录数）：{n_edges_after:,}")
print(f"  筛选比例：{n_edges_after/n_edges_before*100:.2f}%")
print(f"  减少边数：{n_edges_before - n_edges_after:,} ({100*(1-n_edges_after/n_edges_before):.2f}%)")

# 构建筛选后的网络
G_filtered = nx.DiGraph()
edge_weights_filtered = df_filtered.groupby(['转让人', '受让人']).size().reset_index(name='weight')
for _, row in edge_weights_filtered.iterrows():
    G_filtered.add_edge(row['转让人'], row['受让人'], weight=row['weight'])

print(f"\n  筛选后网络规模：")
print(f"    节点数：{G_filtered.number_of_nodes():,}")
print(f"    边数：{G_filtered.number_of_edges():,}")

# 重新计算筛选后网络中实际节点的度统计
print(f"\n  重新计算筛选后网络中实际节点的度统计...")
node_degrees_filtered_actual = {}
for node in G_filtered.nodes():
    in_degree = G_filtered.in_degree(node)
    out_degree = G_filtered.out_degree(node)
    total_degree = in_degree + out_degree
    node_degrees_filtered_actual[node] = {
        'in_degree': in_degree,
        'out_degree': out_degree,
        'total_degree': total_degree
    }

# 转换为DataFrame
degrees_filtered_actual = pd.DataFrame.from_dict(node_degrees_filtered_actual, orient='index').reset_index()
degrees_filtered_actual.columns = ['节点ID', '入度', '出度', '总度']
degrees_filtered_actual = degrees_filtered_actual.sort_values('总度', ascending=False).reset_index(drop=True)

# 合并类型信息（从之前的degrees_df中获取）
if has_type_cols:
    # 从完整度统计中提取类型信息
    type_info = degrees_df[['节点ID', '申请人类型']].copy()
    degrees_filtered_actual = degrees_filtered_actual.merge(type_info, on='节点ID', how='left')
    degrees_filtered_actual['申请人类型'] = degrees_filtered_actual['申请人类型'].fillna('未知')
else:
    degrees_filtered_actual['申请人类型'] = '未知'

# 更新筛选后的度统计（使用实际网络中的节点）
degrees_filtered = degrees_filtered_actual.copy()

print(f"    实际网络节点数：{len(degrees_filtered):,}")
print(f"    度统计：")
print(f"      最小值：{degrees_filtered['总度'].min()}")
print(f"      最大值：{degrees_filtered['总度'].max()}")
print(f"      平均值：{degrees_filtered['总度'].mean():.2f}")
print(f"      中位数：{degrees_filtered['总度'].median():.2f}")

# 统计筛选后实际网络中节点的类型分布
if has_type_cols:
    type_dist_filtered_actual = degrees_filtered['申请人类型'].value_counts()
    print(f"\n    实际网络节点类型分布：")
    for entity_type, count in type_dist_filtered_actual.head(10).items():
        print(f"      {entity_type}: {count:,} 个节点 ({count/len(degrees_filtered)*100:.2f}%)")

# 保存筛选后的度统计（基于实际网络）
degrees_filtered_file = os.path.join(OUTPUT_DIR, "data", "node_degrees_filtered_ge2.csv")
degrees_filtered = degrees_filtered[column_order]
degrees_filtered.to_csv(degrees_filtered_file, index=False, encoding='utf-8-sig')
print(f"\n  ✅ 筛选后度统计已保存：{degrees_filtered_file}（基于实际网络中的{len(degrees_filtered):,}个节点）\n")

# 保存筛选后的数据
filtered_data_file = os.path.join(OUTPUT_DIR, "data", "filtered_data_degree_ge2.csv")
df_filtered.to_csv(filtered_data_file, index=False, encoding='utf-8-sig')
print(f"  ✅ 筛选后数据已保存：{filtered_data_file}")
print(f"    文件大小：{os.path.getsize(filtered_data_file) / 1024 / 1024:.2f} MB\n")

# =============================================================================
# 步骤5：描述统计和报告生成
# =============================================================================
print("[步骤5/5] 生成描述统计和报告...")

# 5.1 基本统计
stats = {
    '筛选条件': '度 >= 2（入度 + 出度 >= 2）',
    '原始数据记录数': len(df_raw),
    '清洗后记录数': len(df_clean),
    '筛选后记录数': len(df_filtered),
    '原始节点数': n_nodes_before,
    '筛选条件_度>=2节点数': n_nodes_degree_ge2,
    '筛选后网络实际节点数': G_filtered.number_of_nodes(),
    '节点减少数量': n_nodes_before - G_filtered.number_of_nodes(),
    '节点减少比例(%)': f"{(1-G_filtered.number_of_nodes()/n_nodes_before)*100:.2f}",
    '原始边数（记录数）': n_edges_before,
    '筛选后边数（记录数）': n_edges_after,
    '边减少数量': n_edges_before - n_edges_after,
    '边减少比例(%)': f"{(1-n_edges_after/n_edges_before)*100:.2f}",
    '筛选后网络边数（去重后）': G_filtered.number_of_edges(),
}

# 5.2 度分布统计
degree_stats = {
    '筛选前_度最小值': degrees_df['总度'].min(),
    '筛选前_度最大值': degrees_df['总度'].max(),
    '筛选前_度平均值': f"{degrees_df['总度'].mean():.2f}",
    '筛选前_度中位数': degrees_df['总度'].median(),
    '筛选后_度最小值': degrees_filtered['总度'].min(),
    '筛选后_度最大值': degrees_filtered['总度'].max(),
    '筛选后_度平均值': f"{degrees_filtered['总度'].mean():.2f}",
    '筛选后_度中位数': degrees_filtered['总度'].median(),
}

# 5.3 如果有年份字段，统计时间分布
if '转让生效年份' in df_filtered.columns:
    year_dist = df_filtered['转让生效年份'].value_counts().sort_index()
    stats['年份范围'] = f"{year_dist.index.min()}-{year_dist.index.max()}"
    stats['年份数量'] = len(year_dist)
    
    # 保存年度分布
    year_dist_file = os.path.join(OUTPUT_DIR, "data", "year_distribution_filtered.csv")
    year_dist.to_frame('记录数').to_csv(year_dist_file, encoding='utf-8-sig')
    print(f"  ✅ 年度分布已保存：{year_dist_file}")

# 5.4 保存统计报告
stats_df = pd.DataFrame([{**stats, **degree_stats}])
stats_file = os.path.join(OUTPUT_DIR, "data", "filtering_statistics.csv")
stats_df.to_csv(stats_file, index=False, encoding='utf-8-sig')
print(f"  ✅ 统计报告已保存：{stats_file}")

# 5.5 生成文本报告
report_file = os.path.join(OUTPUT_DIR, "data", "filtering_report.txt")
with open(report_file, 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("节点筛选报告：基于度（degree）筛选\n")
    f.write("=" * 70 + "\n")
    f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    f.write("【筛选条件】\n")
    f.write(f"  筛选标准：度 >= 2（入度 + 出度 >= 2）\n")
    f.write(f"  说明：只保留在网络中至少连接2次（作为转让人或受让人）的节点\n\n")
    
    f.write("【数据规模变化】\n")
    f.write(f"  原始数据记录数：{stats['原始数据记录数']:,}\n")
    f.write(f"  清洗后记录数：{stats['清洗后记录数']:,}\n")
    f.write(f"  筛选后记录数：{stats['筛选后记录数']:,}\n")
    f.write(f"  记录减少：{stats['边减少数量']:,} ({stats['边减少比例(%)']}%)\n\n")
    
    f.write("【节点规模变化】\n")
    f.write(f"  原始节点数：{stats['原始节点数']:,}\n")
    f.write(f"  筛选条件（度>=2）节点数：{stats['筛选条件_度>=2节点数']:,}\n")
    f.write(f"  筛选后网络实际节点数：{stats['筛选后网络实际节点数']:,}\n")
    f.write(f"  说明：筛选后网络中的实际节点数（{stats['筛选后网络实际节点数']:,}）小于筛选条件节点数（{stats['筛选条件_度>=2节点数']:,}），\n")
    f.write(f"        因为部分度>=2的节点只连接到被移除的度=1节点，导致它们在新网络中消失\n")
    f.write(f"  节点减少：{stats['节点减少数量']:,} ({stats['节点减少比例(%)']}%)\n\n")
    
    f.write("【网络规模变化】\n")
    f.write(f"  原始网络边数（记录数）：{stats['原始边数（记录数）']:,}\n")
    f.write(f"  筛选后网络边数（记录数）：{stats['筛选后边数（记录数）']:,}\n")
    f.write(f"  筛选后网络节点数：{stats['筛选后网络实际节点数']:,}\n")
    f.write(f"  筛选后网络边数（去重后）：{stats['筛选后网络边数（去重后）']:,}\n\n")
    
    f.write("【度分布统计】\n")
    f.write("  筛选前：\n")
    f.write(f"    最小值：{degree_stats['筛选前_度最小值']}\n")
    f.write(f"    最大值：{degree_stats['筛选前_度最大值']}\n")
    f.write(f"    平均值：{degree_stats['筛选前_度平均值']}\n")
    f.write(f"    中位数：{degree_stats['筛选前_度中位数']}\n")
    f.write("  筛选后：\n")
    f.write(f"    最小值：{degree_stats['筛选后_度最小值']}\n")
    f.write(f"    最大值：{degree_stats['筛选后_度最大值']}\n")
    f.write(f"    平均值：{degree_stats['筛选后_度平均值']}\n")
    f.write(f"    中位数：{degree_stats['筛选后_度中位数']}\n\n")
    
    f.write("【输出文件】\n")
    f.write(f"  1. 完整度统计：node_degrees_full.csv\n")
    f.write(f"  2. 筛选后度统计：node_degrees_filtered_ge2.csv\n")
    f.write(f"  3. 筛选后数据：filtered_data_degree_ge2.csv\n")
    f.write(f"  4. 统计报告：filtering_statistics.csv\n")
    if '转让生效年份' in df_filtered.columns:
        f.write(f"  5. 年度分布：year_distribution_filtered.csv\n")
    f.write("\n")
    
    f.write("=" * 70 + "\n")
    f.write("说明：筛选后的数据可用于后续的ERGM分析，减少计算开销\n")
    f.write("=" * 70 + "\n")

print(f"  ✅ 文本报告已保存：{report_file}\n")

# =============================================================================
# 完成
# =============================================================================
print("=" * 70)
print("✅ 节点筛选完成！")
print("=" * 70)
print(f"\n结果目录：{OUTPUT_DIR}")
print(f"  - data/filtered_data_degree_ge2.csv：筛选后的数据（可用于后续分析）")
print(f"  - data/node_degrees_full.csv：完整度统计")
print(f"  - data/node_degrees_filtered_ge2.csv：筛选后度统计")
print(f"  - data/filtering_statistics.csv：统计摘要")
print(f"  - data/filtering_report.txt：详细报告")
print("\n筛选效果：")
print(f"  - 节点数从 {n_nodes_before:,} 减少到 {G_filtered.number_of_nodes():,}（减少 {stats['节点减少比例(%)']}%）")
print(f"  - 边数从 {n_edges_before:,} 减少到 {n_edges_after:,}（减少 {stats['边减少比例(%)']}%）")
print(f"\n注意：筛选后网络中的实际节点数（{G_filtered.number_of_nodes():,}）")
print(f"      小于筛选条件节点数（{n_nodes_degree_ge2:,}），因为部分度>=2的节点")
print(f"      只连接到被移除的度=1节点，导致它们在新网络中消失")
print("=" * 70)

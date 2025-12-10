import os
# 设置matplotlib配置目录（解决权限问题）
os.environ['MPLCONFIGDIR'] = os.path.join(os.getcwd(), '.matplotlib_cache')
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

# 导入跨平台字体配置和数据加载工具
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from font_config import setup_chinese_fonts, get_font_dict
from data_loader import load_all_excel_files

# --------------------------
# 配置参数（固定路径）
# --------------------------
data_dir = "./data_cleaned"
result_root = "./result/RQ3_formation_factors/statistics"
os.makedirs(result_root, exist_ok=True)
os.makedirs(os.path.join(result_root, "data"), exist_ok=True)
os.makedirs(os.path.join(result_root, "figures"), exist_ok=True)

# 自动配置中文字体（支持 Windows/macOS/Linux）
setup_chinese_fonts()
font_dicts = get_font_dict()
title_font = font_dicts['title_font']
label_font = font_dicts['label_font']

# --------------------------
# 核心：数据统计汇总
# --------------------------
def data_summary():
    # 1. 加载数据
    print("=== 步骤1：加载数据 ===")
    
    # 使用统一的数据加载工具（支持缓存）
    df = load_all_excel_files(data_dir=data_dir, use_cache=True)
    print(f"原始数据总行数：{len(df)}")
    print(f"原始数据总列数：{len(df.columns)}")
    print(f"\n所有列名：\n{list(df.columns)}")

    # 2. 基础数据质量统计
    print("\n=== 步骤2：基础数据质量 ===")
    # 缺失值统计（前10个缺失最多的列）
    missing_stats = df.isnull().sum().sort_values(ascending=False).head(10)
    print("缺失值最多的10列：")
    for col, cnt in missing_stats.items():
        if cnt > 0:
            print(f"  {col}: {cnt}个（占比{cnt/len(df)*100:.2f}%）")
    
    # 3. 核心字段分布统计
    print("\n=== 步骤3：核心字段分布 ===")
    core_fields = {
        "转让次数": "转让次数",
        "转让生效年份": "转让生效年份",
        "转让人类型": "转让人类型",
        "受让人类型": "受让人类型",
        "申请人地区": "申请人地区",
        "受让人地址": "受让人省份",  # 从地址提取省份
        "专利类型": "专利类型",
        "专利有效性": "专利有效性"
    }
    
    # 统计每个核心字段
    stats_result = {}
    for col, alias in core_fields.items():
        if col not in df.columns:
            print(f"  ❌ 未找到字段：{col}")
            continue
        
        print(f"\n  【{alias}】")
        # 去重后的数据量
        unique_cnt = df[col].nunique()
        print(f"  唯一值数量：{unique_cnt}")
        
        # 数值型字段（统计分布）
        if df[col].dtype in [np.int64, np.float64] and col != "转让人类型" and col != "受让人类型":
            valid_data = df[col].dropna()
            print(f"  有效值范围：{valid_data.min():.0f} ~ {valid_data.max():.0f}")
            print(f"  有效值均值：{valid_data.mean():.2f}")
            print(f"  有效值中位数：{valid_data.median():.0f}")
            # 保存统计结果
            stats_result[alias] = {
                "类型": "数值型",
                "唯一值数量": unique_cnt,
                "最小值": valid_data.min(),
                "最大值": valid_data.max(),
                "均值": valid_data.mean(),
                "中位数": valid_data.median()
            }
        
        # 字符型字段（统计前10个高频值）
        else:
            top10 = df[col].value_counts().head(10)
            print(f"  前10个高频值：")
            for val, cnt in top10.items():
                print(f"    {val}: {cnt}次（占比{cnt/len(df)*100:.2f}%）")
            # 保存统计结果
            stats_result[alias] = {
                "类型": "字符型",
                "唯一值数量": unique_cnt,
                "前10高频值": top10.to_dict()
            }

    # 4. 转让关系核心统计
    print("\n=== 步骤4：转让关系核心统计 ===")
    # 有效转让关系（转让人、受让人非空）
    valid_transfer = df[
        (df["转让人"].notna()) & 
        (df["受让人"].notna())
    ].copy()
    print(f"有效转让关系（转让人+受让人非空）：{len(valid_transfer)}条（占比{len(valid_transfer)/len(df)*100:.2f}%）")
    
    # 转让主体统计
    all_entities = pd.unique(valid_transfer[["转让人", "受让人"]].values.ravel("K"))
    print(f"参与转让的独立主体总数：{len(all_entities)}个")
    
    # 年度转让分布
    if "转让生效年份" in df.columns:
        year_dist = df["转让生效年份"].dropna().astype(int).value_counts().sort_index()
        print(f"\n年度转让次数分布（前5年和后5年）：")
        print("  早期5年：")
        for year, cnt in year_dist.head(5).items():
            print(f"    {year}年：{cnt}次")
        print("  近期5年：")
        for year, cnt in year_dist.tail(5).items():
            print(f"    {year}年：{cnt}次")
    
    # 主体类型分布（转让人+受让人合并）
    if "转让人类型" in df.columns and "受让人类型" in df.columns:
        all_types = pd.concat([df["转让人类型"], df["受让人类型"]]).dropna()
        type_dist = all_types.value_counts()
        print(f"\n所有主体类型分布：")
        for typ, cnt in type_dist.items():
            print(f"  {typ}: {cnt}次（占比{cnt/len(all_types)*100:.2f}%）")

    # 5. 保存统计结果到文件
    print("\n=== 步骤5：保存统计结果 ===")
    # 保存文本格式的统计报告
    report_path = os.path.join(result_root, "数据统计报告.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"数据统计报告（生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}）\n")
        f.write(f"原始数据总行数：{len(df)}\n")
        f.write(f"原始数据总列数：{len(df.columns)}\n")
        f.write(f"\n核心字段统计：\n")
        for alias, stats in stats_result.items():
            f.write(f"\n【{alias}】\n")
            for k, v in stats.items():
                f.write(f"  {k}: {v}\n")
    
    # 保存统计表格（Excel）
    excel_path = os.path.join(result_root, "数据统计结果.xlsx")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        # 缺失值统计
        missing_stats.to_frame("缺失值数量").to_excel(writer, sheet_name="缺失值统计")
        # 年度分布
        if "转让生效年份" in df.columns:
            year_dist.to_frame("转让次数").to_excel(writer, sheet_name="年度转让分布")
        # 主体类型分布
        if "转让人类型" in df.columns and "受让人类型" in df.columns:
            type_dist.to_frame("出现次数").to_excel(writer, sheet_name="主体类型分布")
    
    print(f"\n✅ 统计报告已保存至：{report_path}")
    print(f"✅ 统计表格已保存至：{excel_path}")

    # 6. 快速可视化（核心分布图表）
    print("\n=== 步骤6：生成核心分布图表 ===")
    vis_dir = os.path.join(result_root, "统计图表")
    os.makedirs(vis_dir, exist_ok=True)
    
    # (1) Annual Transfer Trend
    if "转让生效年份" in df.columns:
        year_counts = df["转让生效年份"].dropna().astype(int).value_counts().sort_index()
        plt.figure(figsize=(12, 6))
        year_counts.plot(kind="line", marker="o", color="#2ecc71")
        plt.title("Annual Patent Transfer Trend", fontdict=title_font)
        plt.xlabel("Year", fontdict=label_font)
        plt.ylabel("Transfer Count", fontdict=label_font)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(vis_dir, "annual_transfer_trend.png"), dpi=300)
        plt.close()
        print("  ✅ Annual transfer trend chart saved")
    
    # (2) Entity Type Distribution Pie Chart
    if "转让人类型" in df.columns and "受让人类型" in df.columns:
        all_types = pd.concat([df["转让人类型"], df["受让人类型"]]).dropna()
        type_counts = all_types.value_counts().head(8)
        plt.figure(figsize=(10, 8))
        plt.pie(type_counts.values, labels=type_counts.index, autopct="%1.1f%%", 
                colors=plt.cm.GnBu(np.linspace(0.3, 0.8, len(type_counts))))
        plt.title("Entity Type Distribution (Top 8)", fontdict=title_font)
        plt.axis("equal")
        plt.tight_layout()
        plt.savefig(os.path.join(vis_dir, "entity_type_distribution.png"), dpi=300)
        plt.close()
        print("  ✅ Entity type distribution pie chart saved")
    
    # (3) Transfer Count Distribution Histogram
    if "转让次数" in df.columns:
        transfer_counts = df["转让次数"].dropna()
        plt.figure(figsize=(10, 6))
        sns.histplot(transfer_counts[transfer_counts <= 10], bins=10, color="#3498db")
        plt.title("Patent Transfer Count Distribution (≤10)", fontdict=title_font)
        plt.xlabel("Transfer Count", fontdict=label_font)
        plt.ylabel("Number of Patents", fontdict=label_font)
        plt.tight_layout()
        plt.savefig(os.path.join(vis_dir, "transfer_count_distribution.png"), dpi=300)
        plt.close()
        print("  ✅ Transfer count distribution chart saved")

    print("\n=== 数据统计完成 ===")
    print(f"所有结果已保存至：{result_root}")

# --------------------------
# 执行统计
# --------------------------
if __name__ == "__main__":
    try:
        data_summary()
    except Exception as e:
        print(f"\n❌ 统计失败：{str(e)}")
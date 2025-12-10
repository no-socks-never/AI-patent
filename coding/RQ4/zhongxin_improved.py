"""
RQ4: 网络位置与创新产出 - 改进版模型
"""
import os
import warnings
warnings.filterwarnings('ignore')

os.environ['MPLCONFIGDIR'] = os.path.join(os.getcwd(), '.matplotlib_cache')
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

import pandas as pd
import numpy as np
import networkx as nx
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, make_scorer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 检测CPU核心数用于并行计算
CPU_COUNT = os.cpu_count() or 4

# 导入统计模型
try:
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# 导入跨平台字体配置和数据加载工具
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from font_config import setup_chinese_fonts, get_font_dict
from data_loader import load_all_excel_files, load_filtered_data

# --------------------------
# 1. 全局设置（跨平台兼容）
# --------------------------
# 是否使用筛选后的数据
USE_FILTERED_DATA = True  # 设置为True使用筛选后的数据（度>=2的节点）

setup_chinese_fonts()
fonts = get_font_dict()

# 根据是否使用筛选后的数据设置结果目录
if USE_FILTERED_DATA:
    result_root = "./result/RQ4_centrality_prediction_filtered"
else:
    result_root = "./result/RQ4_centrality_prediction"
os.makedirs(result_root, exist_ok=True)
data_dir = os.path.join(result_root, "data")
fig_dir = os.path.join(result_root, "figures")
os.makedirs(data_dir, exist_ok=True)
os.makedirs(fig_dir, exist_ok=True)

# 是否使用筛选后的数据
USE_FILTERED_DATA = True  # 设置为True使用筛选后的数据（度>=2的节点）

print("="*60)
if USE_FILTERED_DATA:
    print("RQ4: 网络位置与创新产出分析（使用筛选后数据，度>=2的节点）")
else:
    print("RQ4: 网络位置与创新产出分析")
print("="*60)

# --------------------------
# 2. 数据加载与精简
# --------------------------
def load_and_preprocess_data(use_filtered_data=False):
    """
    加载数据
    
    参数:
        use_filtered_data: 如果为True，使用筛选后的数据（度>=2的节点）
    """
    if use_filtered_data:
        print(f"\n[1/5] 数据加载（使用筛选后的数据）")
        try:
            # 使用统一的数据加载工具加载筛选后的数据
            df = load_filtered_data(use_cache=True)
            print(f"  总记录数：{len(df):,}（筛选后数据，度>=2的节点）")
        except FileNotFoundError as e:
            print(f"  ⚠️  {e}")
            print(f"  ⚠️  改用原始数据")
            use_filtered_data = False
    
    if not use_filtered_data:
        data_dir = "./data_cleaned"
        print(f"\n[1/5] 数据加载")
        # 使用统一的数据加载工具（支持缓存）
        df = load_all_excel_files(data_dir=data_dir, use_cache=True)
        print(f"  总记录数：{len(df):,}")
    
    edges_df = df[["转让人", "受让人"]].dropna()
    edges_df["转让人"] = edges_df["转让人"].astype(str).str.strip()
    edges_df["受让人"] = edges_df["受让人"].astype(str).str.strip()
    edges_df = edges_df[edges_df["转让人"] != edges_df["受让人"]].drop_duplicates()
    
    all_entities = pd.unique(edges_df[["转让人", "受让人"]].values.ravel("K"))
    nodes_df = pd.DataFrame({"主体ID": all_entities})
    
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
    
    nodes_df = pd.merge(nodes_df, entity_info[["主体ID", "主体类型", "省份"]], on="主体ID", how="left")
    nodes_df[["主体类型", "省份"]] = nodes_df[["主体类型", "省份"]].fillna("其他")
    
    print(f"  节点数：{len(nodes_df):,}, 边数：{len(edges_df):,}")
    print(f"  因变量均值：{nodes_df['专利数量'].mean():.2f}, 标准差：{nodes_df['专利数量'].std():.2f}")
    
    return edges_df, nodes_df

edges_df, nodes_df = load_and_preprocess_data(use_filtered_data=USE_FILTERED_DATA)

# --------------------------
# 3. 网络构建与中心性计算
# --------------------------
def build_network_and_calculate_centrality(edges_df):
    print("\n[2/5] 网络构建与中心性计算")
    G = nx.DiGraph()
    edge_weights = edges_df.groupby(["转让人", "受让人"]).size().reset_index(name="weight")
    G.add_weighted_edges_from([(r["转让人"], r["受让人"], r["weight"]) for _, r in edge_weights.iterrows()])
    
    centrality = {}
    centrality["degree"] = nx.degree_centrality(G)
    centrality["in_degree"] = nx.in_degree_centrality(G)
    centrality["out_degree"] = nx.out_degree_centrality(G)
    
    # betweenness计算：使用全量计算（不再使用采样近似）
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    print(f"  计算betweenness中心性（全量计算，节点数={n_nodes:,}，边数={n_edges:,}）...")
    print(f"  注意：全量计算可能较慢，请耐心等待...")
    centrality["betweenness"] = nx.betweenness_centrality(G, weight="weight")
    print(f"  ✅ betweenness中心性计算完成")
    
    try:
        centrality["eigenvector"] = nx.eigenvector_centrality(G, weight="weight", max_iter=500, tol=1e-4)
    except:
        centrality["eigenvector"] = {n: 0 for n in G.nodes()}
    
    G_undir = G.to_undirected()
    centrality["k_core"] = nx.core_number(G_undir)
    
    centrality_df = pd.DataFrame(centrality).reset_index()
    centrality_df.columns = ["主体ID"] + list(centrality.keys())
    print(f"  完成中心性计算")
    return centrality_df

centrality_df = build_network_and_calculate_centrality(edges_df)
centrality_df.to_csv(os.path.join(data_dir, "node_centrality.csv"), index=False, encoding="utf-8-sig")

# --------------------------
# 4. 数据准备（移除泄漏变量）
# --------------------------
print("\n[3/5] 数据准备")
analysis_df = pd.merge(
    nodes_df[["主体ID", "专利数量", "主体类型", "省份"]],
    centrality_df,
    on="主体ID",
    how="inner"
)

# 移除度中心性相关变量（数据泄漏）
leakage_vars = ['degree', 'in_degree', 'out_degree']
analysis_df = analysis_df.drop(columns=leakage_vars, errors='ignore')
print(f"  已移除泄漏变量：{', '.join(leakage_vars)}")

# One-hot编码控制变量
analysis_df = pd.get_dummies(analysis_df, columns=["主体类型", "省份"], drop_first=True)

y = analysis_df["专利数量"]
X = analysis_df.drop(columns=["主体ID", "专利数量"])
X = X.loc[:, X.var() > 0]

# 定义变量类型（用于解释）
network_vars = [col for col in X.columns if col in ['betweenness', 'eigenvector', 'k_core']]
control_entity_vars = [col for col in X.columns if col.startswith('主体类型_')]
control_province_vars = [col for col in X.columns if col.startswith('省份_')]
control_vars = control_entity_vars + control_province_vars

print(f"  核心网络变量（{len(network_vars)}个）：{', '.join(network_vars)}")
print(f"  控制变量：主体类型（{len(control_entity_vars)}个）、省份（{len(control_province_vars)}个）")
print(f"  总特征数：{X.shape[1]}")

# 数据预处理
y_99 = y.quantile(0.99)
y_clipped = y.clip(upper=y_99)

X_train, X_test, y_train, y_test = train_test_split(X, y_clipped, test_size=0.2, random_state=42)

scaler = RobustScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
X_train_scaled = np.clip(X_train_scaled, -5, 5)
X_test_scaled = np.clip(X_test_scaled, -5, 5)

# --------------------------
# 5. 模型训练（含交叉验证）
# --------------------------
results = []
print("\n[4/5] 模型训练（5折交叉验证）")

# 交叉验证设置
kf = KFold(n_splits=5, shuffle=True, random_state=1)
r2_scorer = make_scorer(r2_score)

# 模型1: 负二项回归
if STATSMODELS_AVAILABLE:
    print("  [1/3] 负二项回归...")
    try:
        X_train_const = sm.add_constant(X_train_scaled)
        X_test_const = sm.add_constant(X_test_scaled)
        
        # 使用更稳健的设置
        nb_model = sm.NegativeBinomial(y_train, X_train_const, loglike_method='nb2')
        
        # 尝试多种优化方法（先尝试计算完整统计量，失败则跳过Hessian）
        nb_results = None
        for method in ['bfgs', 'nm', 'powell']:
            try:
                nb_results = nb_model.fit(
                    disp=False, 
                    maxiter=500, 
                    method=method,
                    warn_convergence=False
                )
                break
            except:
                continue
        
        # 如果上述方法都失败，尝试跳过Hessian
        if nb_results is None:
            for method in ['bfgs', 'nm', 'powell']:
                try:
                    nb_results = nb_model.fit(
                        disp=False, 
                        maxiter=500, 
                        method=method,
                        warn_convergence=False,
                        skip_hessian=True
                    )
                    break
                except:
                    continue
        
        nb_pred_train = np.clip(nb_results.predict(X_train_const), 0, y_99)
        nb_pred_test = np.clip(nb_results.predict(X_test_const), 0, y_99)
        
        nb_r2_train = r2_score(y_train, nb_pred_train)
        nb_r2_test = r2_score(y_test, nb_pred_test)
        
        results.append({
            '模型': '负二项回归',
            'R²_训练集': nb_r2_train,
            'R²_测试集': nb_r2_test,
            'MAE': mean_absolute_error(y_test, nb_pred_test),
            'RMSE': np.sqrt(mean_squared_error(y_test, nb_pred_test)),
            '过拟合': nb_r2_train - nb_r2_test
        })
        
        # 保存系数、P值、置信区间等统计信息
        has_pvalues = hasattr(nb_results, 'pvalues') and nb_results.pvalues is not None and not np.isnan(nb_results.pvalues).all()
        has_bse = hasattr(nb_results, 'bse') and nb_results.bse is not None and not np.isnan(nb_results.bse).all()
        
        nb_coef_data = {
            '变量': ['const'] + list(X.columns),
            '系数': nb_results.params
        }
        
        if has_bse:
            nb_coef_data['标准误'] = nb_results.bse
            nb_coef_data['z值'] = nb_results.tvalues if hasattr(nb_results, 'tvalues') else np.nan
        
        if has_pvalues:
            nb_coef_data['P值'] = nb_results.pvalues
            nb_coef_data['显著性'] = ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' 
                                    for p in nb_results.pvalues]
            # 如果有置信区间，添加
            if hasattr(nb_results, 'conf_int'):
                try:
                    conf_int = nb_results.conf_int()
                    nb_coef_data['95%CI下限'] = conf_int[0]
                    nb_coef_data['95%CI上限'] = conf_int[1]
                except:
                    pass
        else:
            nb_coef_data['说明'] = '⚠️ Hessian矩阵求逆失败，无法计算P值'
        
        nb_coef = pd.DataFrame(nb_coef_data)
        
        # 按系数绝对值排序
        nb_coef = nb_coef.sort_values(by='系数', key=abs, ascending=False)
        nb_coef.to_csv(os.path.join(data_dir, "nb_coefficients.csv"), index=False, encoding="utf-8-sig")
        
        nb_success = True
        print(f"    R²={nb_r2_test:.4f}")
    except Exception as e:
        print(f"    失败（跳过）")
        nb_success = False
else:
    nb_success = False


# 模型2: 随机森林（放松正则化，加交叉验证）
print("  [2/3] 随机森林...")
try:
    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15, 
        min_samples_split=20,
        min_samples_leaf=10,
        max_features='sqrt',
        random_state=1,
        n_jobs=CPU_COUNT
    )
    
    # 交叉验证
    cv_scores = cross_val_score(rf_model, X_train, y_train, cv=kf, scoring=r2_scorer, n_jobs=CPU_COUNT)
    
    rf_model.fit(X_train, y_train)
    rf_pred_train = np.clip(rf_model.predict(X_train), 0, y_99)
    rf_pred_test = np.clip(rf_model.predict(X_test), 0, y_99)
    
    rf_r2_train = r2_score(y_train, rf_pred_train)
    rf_r2_test = r2_score(y_test, rf_pred_test)
    
    results.append({
        '模型': '随机森林',
        'R²_训练集': rf_r2_train,
        'R²_测试集': rf_r2_test,
        'R²_交叉验证': cv_scores.mean(),
        'MAE': mean_absolute_error(y_test, rf_pred_test),
        'RMSE': np.sqrt(mean_squared_error(y_test, rf_pred_test)),
        '过拟合': rf_r2_train - rf_r2_test
    })
    
    # 特征重要性分析（标注变量类型）
    feature_importance = pd.DataFrame({
        '变量': X.columns,
        '重要性': rf_model.feature_importances_
    })
    
    # 添加变量类型列
    def get_var_type(var_name):
        if var_name in network_vars:
            return '核心网络变量'
        elif var_name.startswith('主体类型_'):
            return '控制变量（主体类型）'
        elif var_name.startswith('省份_'):
            return '控制变量（省份）'
        else:
            return '其他'
    
    feature_importance['变量类型'] = feature_importance['变量'].apply(get_var_type)
    feature_importance = feature_importance.sort_values(by='重要性', ascending=False)
    feature_importance.to_csv(os.path.join(data_dir, "rf_importance.csv"), index=False, encoding="utf-8-sig")
    
    # 输出核心网络变量的重要性排名
    network_importance = feature_importance[feature_importance['变量类型'] == '核心网络变量'].copy()
    network_importance.to_csv(os.path.join(data_dir, "rf_importance_network_only.csv"), index=False, encoding="utf-8-sig")
    
    rf_success = True
    print(f"    R²={rf_r2_test:.4f}, CV={cv_scores.mean():.4f}")
except Exception as e:
    print(f"    失败")
    rf_success = False

# 模型3: XGBoost（放松正则化，加交叉验证）
if XGBOOST_AVAILABLE:
    print("  [3/3] XGBoost...")
    try:
        xgb_model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,  
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.5,
            random_state=1,
            n_jobs=CPU_COUNT,
            objective='count:poisson',
            tree_method='hist'
        )
        
        # 交叉验证
        cv_scores = cross_val_score(xgb_model, X_train, y_train, cv=kf, scoring=r2_scorer, n_jobs=CPU_COUNT)
        
        xgb_model.fit(X_train, y_train, verbose=False)
        xgb_pred_train = np.clip(xgb_model.predict(X_train), 0, y_99)
        xgb_pred_test = np.clip(xgb_model.predict(X_test), 0, y_99)
        
        xgb_r2_train = r2_score(y_train, xgb_pred_train)
        xgb_r2_test = r2_score(y_test, xgb_pred_test)
        
        results.append({
            '模型': 'XGBoost',
            'R²_训练集': xgb_r2_train,
            'R²_测试集': xgb_r2_test,
            'R²_交叉验证': cv_scores.mean(),
            'MAE': mean_absolute_error(y_test, xgb_pred_test),
            'RMSE': np.sqrt(mean_squared_error(y_test, xgb_pred_test)),
            '过拟合': xgb_r2_train - xgb_r2_test
        })
        
        # 特征重要性分析（标注变量类型）
        xgb_importance = pd.DataFrame({
            '变量': X.columns,
            '重要性': xgb_model.feature_importances_
        })
        
        # 添加变量类型列
        xgb_importance['变量类型'] = xgb_importance['变量'].apply(get_var_type)
        xgb_importance = xgb_importance.sort_values(by='重要性', ascending=False)
        xgb_importance.to_csv(os.path.join(data_dir, "xgb_importance.csv"), index=False, encoding="utf-8-sig")
        
        # 输出核心网络变量的重要性排名
        network_importance_xgb = xgb_importance[xgb_importance['变量类型'] == '核心网络变量'].copy()
        network_importance_xgb.to_csv(os.path.join(data_dir, "xgb_importance_network_only.csv"), index=False, encoding="utf-8-sig")
        
        xgb_success = True
        print(f"    R²={xgb_r2_test:.4f}, CV={cv_scores.mean():.4f}")
    except Exception as e:
        print(f"    失败")
        xgb_success = False
else:
    xgb_success = False

# --------------------------
# 6. 结果输出
# --------------------------
print("\n[5/5] 结果汇总")
results_df = pd.DataFrame(results)
results_df = results_df.sort_values(by='R²_测试集', ascending=False)

print("\n模型性能对比:")
print(results_df[['模型', 'R²_测试集', 'MAE', '过拟合']].to_string(index=False))

results_df.to_csv(os.path.join(data_dir, "model_comparison.csv"), index=False, encoding="utf-8-sig")

# 保存详细报告
with open(os.path.join(data_dir, "model_performance_report.txt"), "w", encoding="utf-8") as f:
    f.write("=" * 60 + "\n")
    f.write("RQ4: 网络位置与创新产出 - 改进模型结果\n")
    f.write("（已移除数据泄漏变量）\n")
    f.write("=" * 60 + "\n\n")
    
    f.write("⚠️ 数据泄漏处理:\n")
    f.write("  - 因变量: 专利数量（转让次数+受让次数）\n")
    f.write("  - 已移除: degree, in_degree, out_degree（直接泄漏）\n")
    f.write("  - 保留变量: betweenness, eigenvector, k_core\n")
    f.write("  - 控制变量: 主体类型, 省份\n")
    f.write(f"  - 交叉验证: 5折\n\n")
    
    f.write("📊 统计说明:\n")
    f.write("  - 负二项回归: 报告系数、P值、置信区间（统计显著性检验）\n")
    f.write("  - 随机森林/XGBoost: 报告特征重要性（预测贡献度，无P值）\n")
    f.write("  - 显著性标记: *** p<0.001, ** p<0.01, * p<0.05\n\n")
    
    f.write(f"样本量: {len(analysis_df):,}, 特征数: {X.shape[1]}\n\n")
    
    f.write("模型性能:\n")
    f.write(results_df.to_string(index=False))
    
    # 添加负二项回归的显著性结果
    if nb_success:
        f.write("\n\n" + "=" * 60 + "\n")
        f.write("负二项回归 - 回归系数\n")
        f.write("=" * 60 + "\n")
        nb_coef_file = os.path.join(result_root, "nb_coefficients.csv")
        if os.path.exists(nb_coef_file):
            nb_coef_display = pd.read_csv(nb_coef_file)
            # 只显示Top 15变量
            f.write("\nTop 15 最重要变量（按系数绝对值）:\n")
            f.write(nb_coef_display.head(15).to_string(index=False))
            
            # 检查是否有P值
            if 'P值' in nb_coef_display.columns and not nb_coef_display['P值'].isna().all():
                f.write("\n\n显著性统计:\n")
                sig_count = (nb_coef_display['显著性'] != '').sum()
                f.write(f"  - 显著变量数: {sig_count}/{len(nb_coef_display)}\n")
                if '显著性' in nb_coef_display.columns:
                    f.write(f"  - p<0.001 (***): {(nb_coef_display['显著性'] == '***').sum()}\n")
                    f.write(f"  - p<0.01 (**): {(nb_coef_display['显著性'] == '**').sum()}\n")
                    f.write(f"  - p<0.05 (*): {(nb_coef_display['显著性'] == '*').sum()}\n")
            elif '说明' in nb_coef_display.columns:
                f.write("\n\n⚠️ 统计检验局限:\n")
                f.write("  - Hessian矩阵求逆失败，无法计算标准误和P值\n")
                f.write("  - 可能原因: 高维数据、变量共线性、样本量相对特征数较小\n")
                f.write("  - 建议: 参考机器学习模型（RF/XGBoost）的特征重要性作为补充证据\n")
                f.write("  - 系数方向仍有参考价值（正/负影响）\n")
    f.write("\n\n")
    
    best = results_df.iloc[0]
    f.write(f"最佳模型: {best['模型']}\n")
    f.write(f"  R²={best['R²_测试集']:.4f}, MAE={best['MAE']:.3f}, 过拟合={best['过拟合']:.4f}\n")

# --------------------------
# 7. 可视化
# --------------------------
# 简化可视化：只生成模型对比图
fig, ax = plt.subplots(figsize=(10, 6))
results_plot = results_df.sort_values(by='R²_测试集')
ax.barh(results_plot['模型'], results_plot['R²_测试集'], color='steelblue')
ax.set_xlabel('R² Score', **fonts['label_font'])
ax.set_title('模型性能对比（测试集R²）', **fonts['title_font'])
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(fig_dir, "model_comparison.png"), dpi=300, bbox_inches='tight')
plt.close()

print("\n" + "="*60)
print("✅ 分析完成")
print("="*60)
print(f"\n结果目录: {result_root}")
print(f"  - model_comparison.csv")
print(f"  - model_performance_report.txt")
print(f"  - figures/model_comparison.png")



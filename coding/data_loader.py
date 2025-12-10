"""
统一数据加载工具模块
避免每次运行都重复读取和合并Excel文件
"""
import os
import pandas as pd
import pickle
from pathlib import Path
from typing import Optional, List, Tuple
import warnings

# 数据缓存目录
CACHE_DIR = "./data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# 缓存文件路径
RAW_DATA_CACHE = os.path.join(CACHE_DIR, "raw_data_merged.pkl")
RAW_DATA_CACHE_META = os.path.join(CACHE_DIR, "raw_data_merged_meta.txt")


def load_all_excel_files(data_dir: str = "./data_cleaned", 
                         use_cache: bool = True,
                         force_reload: bool = False,
                         columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    加载并合并所有Excel文件
    
    参数:
        data_dir: 数据目录路径
        use_cache: 是否使用缓存（如果缓存存在且数据未更新）
        force_reload: 强制重新加载（忽略缓存）
        columns: 指定要读取的列（None表示读取所有列）
    
    返回:
        合并后的DataFrame
    """
    # 检查缓存
    if use_cache and not force_reload and os.path.exists(RAW_DATA_CACHE):
        # 检查数据文件是否有更新
        cache_time = os.path.getmtime(RAW_DATA_CACHE)
        excel_files = [f for f in os.listdir(data_dir) 
                       if f.endswith('.xlsx') and not f.startswith('~$')]
        
        # 检查是否有Excel文件比缓存更新
        data_updated = False
        for file in excel_files:
            file_path = os.path.join(data_dir, file)
            if os.path.getmtime(file_path) > cache_time:
                data_updated = True
                break
        
        if not data_updated:
            print(f"📦 从缓存加载数据（{RAW_DATA_CACHE}）...")
            try:
                with open(RAW_DATA_CACHE, 'rb') as f:
                    df = pickle.load(f)
                print(f"  ✅ 成功加载缓存数据，记录数：{len(df):,}")
                return df
            except Exception as e:
                print(f"  ⚠️  缓存加载失败，将重新读取：{e}")
    
    # 读取并合并所有Excel文件
    print(f"📂 读取数据目录：{data_dir}")
    excel_files = [f for f in os.listdir(data_dir) 
                   if f.endswith('.xlsx') and not f.startswith('~$')]
    
    if not excel_files:
        raise FileNotFoundError(f"数据目录不存在Excel文件：{data_dir}")
    
    print(f"发现{len(excel_files)}个Excel文件，开始合并...")
    
    dfs = []
    for file in sorted(excel_files):
        file_path = os.path.join(data_dir, file)
        try:
            if columns:
                # 先检查列是否存在
                temp_df_header = pd.read_excel(file_path, engine='openpyxl', nrows=0)
                available_cols = [col for col in columns if col in temp_df_header.columns]
                if available_cols:
                    temp_df = pd.read_excel(file_path, usecols=available_cols, engine='openpyxl')
                else:
                    print(f"  ⚠️  跳过 {file}（没有需要的列）")
                    continue
            else:
                temp_df = pd.read_excel(file_path, engine='openpyxl')
            
            dfs.append(temp_df)
            print(f"  ✅ {file}：{len(temp_df):,} 条记录")
        except Exception as e:
            print(f"  ❌ {file} 读取失败：{str(e)}")
            continue
    
    if not dfs:
        raise ValueError("没有成功读取任何Excel文件")
    
    # 合并所有数据
    print("正在合并数据...")
    df = pd.concat(dfs, ignore_index=True)
    print(f"✅ 合并完成，总记录数：{len(df):,}")
    
    # 保存缓存
    if use_cache:
        try:
            with open(RAW_DATA_CACHE, 'wb') as f:
                pickle.dump(df, f)
            
            # 保存元数据
            with open(RAW_DATA_CACHE_META, 'w', encoding='utf-8') as f:
                f.write(f"数据合并时间：{pd.Timestamp.now()}\n")
                f.write(f"总记录数：{len(df):,}\n")
                f.write(f"列数：{len(df.columns)}\n")
                f.write(f"列名：{', '.join(df.columns.tolist())}\n")
            
            print(f"💾 数据已缓存至：{RAW_DATA_CACHE}")
        except Exception as e:
            print(f"  ⚠️  缓存保存失败：{e}")
    
    return df


def get_cached_data_info() -> Optional[dict]:
    """获取缓存数据的信息"""
    if os.path.exists(RAW_DATA_CACHE_META):
        try:
            with open(RAW_DATA_CACHE_META, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            info = {}
            for line in lines:
                if '：' in line:
                    key, value = line.strip().split('：', 1)
                    info[key] = value
            return info
        except:
            return None
    return None


def clear_cache():
    """清除数据缓存"""
    if os.path.exists(RAW_DATA_CACHE):
        os.remove(RAW_DATA_CACHE)
        print("✅ 已清除数据缓存")
    if os.path.exists(RAW_DATA_CACHE_META):
        os.remove(RAW_DATA_CACHE_META)
        print("✅ 已清除缓存元数据")


def load_filtered_data(filtered_data_path: Optional[str] = None,
                       use_cache: bool = True) -> pd.DataFrame:
    """
    加载筛选后的数据（度>=2的节点）
    
    参数:
        filtered_data_path: 筛选后数据的路径，如果为None则自动查找
        use_cache: 是否使用缓存（如果CSV文件未更新）
    
    返回:
        筛选后的DataFrame
    """
    # 自动查找筛选后的数据文件
    if filtered_data_path is None:
        possible_paths = [
            "./result/node_filtering/data/filtered_data_degree_ge2.csv",
            "../result/node_filtering/data/filtered_data_degree_ge2.csv",
            "../../result/node_filtering/data/filtered_data_degree_ge2.csv"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                filtered_data_path = path
                break
        
        if filtered_data_path is None:
            raise FileNotFoundError(
                "找不到筛选后的数据文件。请先运行 filter_nodes_by_degree.py 生成筛选后的数据。\n"
                "尝试的路径：\n" + "\n".join(f"  - {p}" for p in possible_paths)
            )
    
    if not os.path.exists(filtered_data_path):
        raise FileNotFoundError(f"筛选后的数据文件不存在：{filtered_data_path}")
    
    # 检查缓存（如果CSV文件未更新，使用缓存的pickle文件）
    cache_file = os.path.join(CACHE_DIR, "filtered_data_degree_ge2.pkl")
    if use_cache and os.path.exists(cache_file):
        csv_time = os.path.getmtime(filtered_data_path)
        cache_time = os.path.getmtime(cache_file)
        
        if cache_time > csv_time:
            print(f"📦 从缓存加载筛选后的数据（{cache_file}）...")
            try:
                with open(cache_file, 'rb') as f:
                    df = pickle.load(f)
                print(f"  ✅ 成功加载缓存数据，记录数：{len(df):,}")
                return df
            except Exception as e:
                print(f"  ⚠️  缓存加载失败，将重新读取CSV：{e}")
    
    # 读取CSV文件
    print(f"📂 读取筛选后的数据：{filtered_data_path}")
    try:
        df = pd.read_csv(filtered_data_path, encoding='utf-8-sig', low_memory=False)
        print(f"  ✅ 成功加载筛选后的数据，记录数：{len(df):,}")
        
        # 保存缓存
        if use_cache:
            try:
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(cache_file, 'wb') as f:
                    pickle.dump(df, f)
                print(f"  💾 数据已缓存至：{cache_file}")
            except Exception as e:
                print(f"  ⚠️  缓存保存失败：{e}")
        
        return df
    except Exception as e:
        raise IOError(f"读取筛选后的数据失败：{e}")


if __name__ == "__main__":
    # 测试数据加载
    print("=" * 60)
    print("数据加载工具测试")
    print("=" * 60)
    
    # 检查缓存信息
    cache_info = get_cached_data_info()
    if cache_info:
        print("\n📦 当前缓存信息：")
        for key, value in cache_info.items():
            print(f"  {key}：{value}")
    
    # 加载数据
    print("\n" + "=" * 60)
    df = load_all_excel_files(force_reload=False)
    print(f"\n数据形状：{df.shape}")
    print(f"列名：{list(df.columns)[:10]}..." if len(df.columns) > 10 else f"列名：{list(df.columns)}")


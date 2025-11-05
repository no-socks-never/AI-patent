import pandas as pd
import re
import os
from pathlib import Path
import datetime

# 1. 配置参数
folder_path = r"D:\图情软件\中国专利转让数据1998-2025"  # 目标文件夹路径
output_folder = r"D:\图情软件\人工智能专利转让年度数据"  # 输出文件夹路径
supported_formats = [".xlsx", ".xls", ".csv"]  # 支持的文件格式

# 创建输出文件夹（如果不存在）
os.makedirs(output_folder, exist_ok=True)

# 2. 定义AI专利筛选规则
ai_ipc = ["G06F", "G06N", "G06Q", "G06V", "H04L", "G06K", "G06T"]  # AI相关IPC分类
ai_keywords = [
    "人工智能", "机器学习", "深度学习", "神经网络", "自然语言处理",
    "计算机视觉", "语音识别", "智能推荐", "强化学习", "GAN", "生成对抗网络",
    "大语言模型", "LLM", "知识图谱", "图像识别", "文本挖掘"
]

def is_ai_transfer_patent(row):
    # AI专利判定：IPC匹配 或 关键词匹配
    ipc_match = any(ipc in str(row.get("IPC主分类号", "")) for ipc in ai_ipc)
    text_content = str(row.get("摘要文本", "")) + str(row.get("专利名称", ""))
    text_match = any(re.search(keyword, text_content, re.IGNORECASE) for keyword in ai_keywords)
    
    # 转让记录判定：转让次数≥1 或 历史法律状态含转让信息
    transfer_match = (
        (row.get("转让次数", 0) >= 1) or
        (re.search("专利申请权、专利权的转移", str(row.get("历史法律状态", "")), re.IGNORECASE))
    )
    return (ipc_match or text_match) and transfer_match

def extract_year_from_filename(filename):
    """从文件名中提取年份"""
    year_match = re.search(r'(\d{4})', filename)
    if year_match:
        return year_match.group(1)
    # 如果文件名中没有年份，使用当前年份
    return str(datetime.datetime.now().year)

# 3. 遍历文件夹并筛选数据
folder = Path(folder_path)
total_records = 0  # 统计总记录数

for file in folder.iterdir():
    if file.suffix in supported_formats and not file.name.startswith("~$"):  # 排除临时文件
        print(f"\n正在处理文件：{file.name}")
        try:
            # 读取不同格式文件
            if file.suffix in [".xlsx", ".xls"]:
                # 根据文件后缀选择合适的引擎
                engine = "openpyxl" if file.suffix == ".xlsx" else "xlrd"
                df = pd.read_excel(file, engine=engine)
            elif file.suffix == ".csv":
                # 尝试不同编码读取CSV
                try:
                    df = pd.read_csv(file, encoding="utf-8-sig")
                except UnicodeDecodeError:
                    df = pd.read_csv(file, encoding="gbk")
            
            # 筛选当前文件中的AI转让专利
            ai_df = df[df.apply(is_ai_transfer_patent, axis=1)].copy()
            
            if not ai_df.empty:
                # 新增来源文件列，便于追溯
                ai_df["来源文件"] = file.name
                # 提取年份作为输出文件的一部分
                year = extract_year_from_filename(file.name)
                # 构建输出文件名
                output_file = os.path.join(output_folder, f"人工智能专利转让数据_{year}.xlsx")
                
                # 检查文件是否已存在，如果存在则追加数据
                if os.path.exists(output_file):
                    existing_df = pd.read_excel(output_file, engine="openpyxl")
                    # 合并数据并按申请号去重
                    combined_df = pd.concat([existing_df, ai_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=["申请号"], keep="first")
                    combined_df.to_excel(output_file, index=False, engine="openpyxl")
                    print(f"已追加至文件，当前文件共{len(combined_df)}条数据")
                else:
                    # 新文件直接保存
                    ai_df.to_excel(output_file, index=False, engine="openpyxl")
                    print(f"已创建新文件，包含{len(ai_df)}条数据")
                
                # 更新总记录数
                new_records = len(ai_df)
                total_records += new_records
                print(f"该文件筛选出{new_records}条新数据")
            else:
                print(f"该文件无符合条件的数据")
                
        except Exception as e:
            print(f"处理文件{file.name}失败：{str(e)}")

print(f"\n处理完成！共筛选出{total_records}条人工智能专利转让数据")
print(f"所有数据已按年份保存至：{output_folder}")

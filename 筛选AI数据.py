import pandas as pd
import re
import os
from pathlib import Path
import datetime

# 注意：本脚本中使用的 IPC 分类号列表来自于用户提供的AI专利分类体系（2025-11-07），
# 根据"IPC主分类号"字段进行筛选。带*的分类号表示该层级及以下所有分类号。
# 若需修改或扩展，请编辑 raw_ipc_patterns 字符串。

# 1. 配置参数
folder_path = r"/Users/1m/Desktop/大三上/社会网络分析/中国专利转让/中国专利转让全量数据"  # 目标文件夹路径
output_folder = r"/Users/1m/Desktop/大三上/社会网络分析/中国专利转让/data"  # 输出文件夹路径
supported_formats = [".xlsx", ".xls", ".csv"]  # 支持的文件格式

# 创建输出文件夹（如果不存在）
os.makedirs(output_folder, exist_ok=True)

# 2. 定义AI专利筛选规则
# 根据用户提供的 IPC 分类号列表进行筛选
# 带星号(*)表示匹配该分类号及其所有子类，如 G06F3* 匹配 G06F3, G06F3/01, G06F3/048 等
# 不带星号表示精确匹配该分类号前缀
raw_ipc_patterns = """
G06F3* G06F8* G06F9* G06F11* G06F12* G06F13* G06F15* G06F16*
G06F17* G06F21* G06F30* G06F40* G06K7* G06K9* G06K17* G06K19*
G06N* G06T1* G06T3* G06T5* G06T7* G06T11* G06T15* G06V* G16B* G16C*
G16H* H01L21* H01L23* H01L25* H01L27* H05K1* H05K3* G05B19* G06F7*
H03K19* G06F* H01L21* H01L23* H01L25* H01L27* H03K* H05K1* H05K3*
G06N3* G11C13* G06F30/27 G06N20* G06N99* G06Q* G10L* G06K* G06T*
H04L12* G05B13* B82Y10* G02F2* G06E1* G06N10* G16C10* H01L29* H01L33*
H04B10/70 A61B5* B23P6* B23P9* B23P23* B25J9* B60W30* B64C* B64D*
B64G1* G01C* G01S* G05B* G05D* G08G* H02J* H04B* H04N* H04W*
B23Q15* B23Q16* B23Q23* B25J11* G06N5* G06V30* G06F40/40 G06F40/42
G06F40/44 G06F40/45 G06F40/47 G06F40/49 G06F40/51 G06F40/53 G06F40/55
G06F40/56 G06F40/58 G06F40/30 G06F40/35 G06V20/40 G06V30/262 G01C21/36
G10L13* G10L15* G10L17* G10L25* G10L19* G01S13* G06F21/32 G06N7*
G06V10* G06V20/59 G06V40* G16B20* G16B25* G16B30* G16B35* G16B40*
G06V40/12 G06V40/13 G07C9/00 G07C9/25 G07C9/37 H04L9/40 G06V40/16
G06V40/18 G06V40/19 C07K* C12Q* G01N33* G06V40/20 A63F13* G02B27/01
G06F3/01 G06Q30* H04N13* H04N21/472 H04N21/478 G06F9/44 G06F9/451
G06F3/02 G06F3/033 G06F3/0338 G06F3/0346 G06F3/0354 G06F3/0362
G06F3/038 G06F3/041 G06F3/042 G06F3/043 G06F3/044 G06F3/045 G06F3/046
G06F3/047 G06F3/048 G06F3/0481 G06F3/04812 G06F3/04815 G06F3/04817
G06F3/0482 G06F3/0483 G06F3/0484 G06F3/04842 G06F3/04845 G06F3/04847
G06F3/0485 G06F3/04855 G06F3/0486 G06F3/0487 G06F3/0488 G06F3/04883
G06F3/04886 G06F3/0489 G06F3/04892 G06F3/04895 A63F13/215 A63F13/424
A63F13/54 B60W50/08 B60W50/10 B60W50/12 B60W50/14 G06F3/16 A63B71*
B60W50/16 G09B5* H04N21* G06V20/20 B23P* B60W40/08 B60W40/09
G06T13* G06T17* G06T19*
"""

# 将原始模式转换为正则表达式列表
def compile_ipc_patterns(pattern_string):
    """
    解析IPC分类号模式字符串，生成正则表达式列表
    带*的模式：匹配该分类号及其所有子类
    不带*的模式：匹配该分类号前缀
    """
    regexes = []
    seen = set()  # 用于去重
    
    # 分割并清理模式
    patterns = pattern_string.strip().split()
    
    for p in patterns:
        p = p.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        
        # 处理带星号的模式
        if p.endswith('*'):
            # 移除星号，匹配该前缀及其所有子类
            base = p[:-1]
            # 匹配 base 开头的所有分类号
            regexes.append(re.compile(r"^" + re.escape(base), re.IGNORECASE))
        else:
            # 不带星号，精确匹配该前缀
            regexes.append(re.compile(r"^" + re.escape(p), re.IGNORECASE))
    
    return regexes

# 编译后的 IPC 正则列表
ai_ipc_regex = compile_ipc_patterns(raw_ipc_patterns)

def is_ai_transfer_patent(row):
    # AI专利判定：仅通过 IPC 匹配
    ipc_field = str(row.get("IPC主分类号", ""))
    # 标准化字段，去除多余空格并按分隔符分割（IPC 可能由逗号/分号分隔多个分类号）
    ipc_candidates = re.split(r"[,;\s]+", ipc_field.strip()) if ipc_field else []
    ipc_match = False
    for cand in ipc_candidates:
        cand = cand.strip()
        if not cand:
            continue
        # 逐个正则匹配
        for rx in ai_ipc_regex:
            if rx.search(cand):
                ipc_match = True
                break
        if ipc_match:
            break

    # 转让记录判定：转让次数≥1 或 历史法律状态含转让信息
    transfer_match = (
        (row.get("转让次数", 0) >= 1) or
        (re.search("专利申请权、专利权的转移", str(row.get("历史法律状态", "")), re.IGNORECASE))
    )
    return ipc_match and transfer_match

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

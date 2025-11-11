"""
跨平台字体配置模块
自动检测操作系统并设置合适的中文字体
"""
import platform
import matplotlib.pyplot as plt
import warnings
from matplotlib import font_manager


def setup_chinese_fonts():
    """
    根据操作系统自动配置中文字体
    
    支持系统:
    - macOS: 使用 Arial Unicode MS 或 PingFang SC
    - Windows: 使用 Microsoft YaHei 或 SimHei
    - Linux: 使用 WenQuanYi 或 Droid Sans Fallback
    """
    system = platform.system()
    
    # 禁用字体fallback警告
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib.font_manager')
    
    # 根据操作系统设置字体优先级列表
    if system == 'Darwin':  # macOS
        font_list = [
            'Arial Unicode MS',      # macOS 默认中文字体
            'PingFang SC',           # macOS 中文字体
            'Heiti SC',              # macOS 黑体
            'STHeiti',               # 华文黑体
        ]
    elif system == 'Windows':  # Windows
        font_list = [
            'Microsoft YaHei',       # 微软雅黑
            'SimHei',                # 黑体
            'KaiTi',                 # 楷体
            'SimSun',                # 宋体
        ]
    else:  # Linux 和其他系统
        font_list = [
            'WenQuanYi Micro Hei',   # 文泉驿微米黑
            'WenQuanYi Zen Hei',     # 文泉驿正黑
            'Droid Sans Fallback',   # Android字体
            'DejaVu Sans',           # 备选字体
        ]
    
    # 配置 matplotlib
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = font_list
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    # 打印当前使用的字体
    print(f"检测到操作系统: {system}")
    print(f"字体优先级列表: {', '.join(font_list)}")
    
    # 尝试确认实际使用的字体
    try:
        from matplotlib.font_manager import findfont, FontProperties
        actual_font = findfont(FontProperties(family=font_list))
        print(f"实际使用字体路径: {actual_font}")
    except:
        pass
    
    return font_list


def get_font_dict():
    """
    获取标准化的字体字典,用于图表标题和标签
    
    Returns:
        dict: 包含 title_font 和 label_font 的字典
    """
    return {
        'title_font': {'fontsize': 14, 'fontweight': 'bold'},
        'label_font': {'fontsize': 12},
        'legend_font': {'size': 11}
    }


if __name__ == "__main__":
    # 测试字体配置
    import matplotlib.pyplot as plt
    
    setup_chinese_fonts()
    fonts = get_font_dict()
    
    # 创建测试图表
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([1, 2, 3], [1, 4, 9], 'o-')
    ax.set_title('中文标题测试 - Chinese Title Test', **fonts['title_font'])
    ax.set_xlabel('横坐标 X-axis', **fonts['label_font'])
    ax.set_ylabel('纵坐标 Y-axis', **fonts['label_font'])
    ax.legend(['数据 Data'], prop=fonts['legend_font'])
    plt.tight_layout()
    
    print("\n✅ 字体配置测试完成")
    print("如果保存的图片中文显示正常，说明字体配置成功")
    
    # 保存测试图片
    plt.savefig('font_test.png', dpi=150)
    print("测试图片已保存: font_test.png")


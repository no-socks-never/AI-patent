# ============================
# R语言跨平台中文字体配置
# ============================

setup_chinese_fonts <- function() {
  # 检测操作系统
  os_type <- Sys.info()["sysname"]
  
  cat("检测到操作系统:", os_type, "\n")
  
  # 根据操作系统设置字体
  if (os_type == "Darwin") {
    # macOS 系统
    font_family <- "Arial Unicode MS"
    cat("使用字体: Arial Unicode MS (macOS)\n")
  } else if (os_type == "Windows") {
    # Windows 系统
    font_family <- "SimHei"  # 黑体
    cat("使用字体: SimHei (Windows)\n")
    
    # 如果黑体不可用，尝试微软雅黑
    tryCatch({
      par(family = font_family)
    }, error = function(e) {
      font_family <<- "Microsoft YaHei"
      cat("切换到: Microsoft YaHei\n")
    })
  } else {
    # Linux 系统
    font_family <- "WenQuanYi Micro Hei"  # 文泉驿微米黑
    cat("使用字体: WenQuanYi Micro Hei (Linux)\n")
    
    # 如果不可用，使用默认
    tryCatch({
      par(family = font_family)
    }, error = function(e) {
      font_family <<- "sans"
      cat("切换到默认字体\n")
    })
  }
  
  # 设置全局字体参数
  par(family = font_family)
  
  return(font_family)
}

# 使用方法示例:
if (FALSE) {
  # 在脚本开头调用
  source("r_font_config.R")
  setup_chinese_fonts()
  
  # 然后正常绘图,中文会自动显示
  plot(1:10, main = "测试标题")
}

# ============================
# 备选方案: 使用 showtext 包
# ============================
setup_chinese_fonts_showtext <- function() {
  # showtext包支持更好的跨平台中文显示
  if (!require("showtext", quietly = TRUE)) {
    cat("安装 showtext 包...\n")
    install.packages("showtext", repos = "https://cloud.r-project.org/")
    library(showtext)
  }
  
  library(sysfonts)
  library(showtext)
  
  os_type <- Sys.info()["sysname"]
  
  # 添加系统字体
  if (os_type == "Darwin") {
    # macOS
    font_add("chinese", "Arial Unicode MS.ttf")
  } else if (os_type == "Windows") {
    # Windows
    font_add("chinese", "simhei.ttf")  # 黑体
  } else {
    # Linux
    font_add("chinese", "wqy-microhei.ttc")  # 文泉驿微米黑
  }
  
  # 启用showtext
  showtext_auto()
  
  cat("showtext 已启用,使用 family='chinese' 绘制中文\n")
}

# 使用方法示例:
if (FALSE) {
  source("r_font_config.R")
  setup_chinese_fonts_showtext()
  
  # 绘图时指定 family='chinese'
  plot(1:10, main = "测试标题", family = "chinese")
}


# ============================
# R语言统一数据加载工具
# 避免每次运行都重复读取和合并Excel文件
# ============================

# 自动设置工作目录到项目根目录（包含data_cleaned的目录）
# 如果当前目录没有data_cleaned，尝试向上查找
if (!file.exists("./data_cleaned")) {
  # 尝试向上查找
  if (file.exists("../data_cleaned")) {
    setwd("..")
  } else if (file.exists("../../data_cleaned")) {
    setwd("../..")
  }
}

# 数据缓存目录（相对于当前工作目录）
cache_dir <- "./data_cache"
dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)

# 缓存文件路径
raw_data_cache <- file.path(cache_dir, "raw_data_merged.rds")
raw_data_cache_meta <- file.path(cache_dir, "raw_data_merged_meta.txt")

#' 加载并合并所有Excel文件
#'
#' @param data_dir 数据目录路径，默认为"./data_cleaned"
#' @param use_cache 是否使用缓存（如果缓存存在且数据未更新），默认为TRUE
#' @param force_reload 强制重新加载（忽略缓存），默认为FALSE
#' @param columns 指定要读取的列（NULL表示读取所有列）
#'
#' @return 合并后的data.frame
load_all_excel_files <- function(data_dir = "./data_cleaned",
                                 use_cache = TRUE,
                                 force_reload = FALSE,
                                 columns = NULL) {
  
  # 检查缓存
  if (use_cache && !force_reload && file.exists(raw_data_cache)) {
    # 检查数据文件是否有更新
    cache_time <- file.mtime(raw_data_cache)
    excel_files <- list.files(data_dir, pattern = "\\.xlsx$", full.names = TRUE)
    excel_files <- excel_files[!grepl("~\\$", excel_files)]  # 排除临时文件
    
    # 检查是否有Excel文件比缓存更新
    data_updated <- FALSE
    for (file in excel_files) {
      if (file.mtime(file) > cache_time) {
        data_updated <- TRUE
        break
      }
    }
    
    if (!data_updated) {
      cat("📦 从缓存加载数据（", raw_data_cache, "）...\n", sep = "")
      tryCatch({
        df <- readRDS(raw_data_cache)
        cat("  ✅ 成功加载缓存数据，记录数：", format(nrow(df), big.mark = ","), "\n", sep = "")
        
        # 【关键】如果指定了columns，检查缓存是否包含所需列
        if (!is.null(columns)) {
          missing_cols <- columns[!columns %in% colnames(df)]
          if (length(missing_cols) > 0) {
            cat("  ⚠️  缓存缺少所需列：", paste(missing_cols, collapse=", "), "\n", sep = "")
            cat("  🔄 自动重新加载完整数据...\n")
            # 不返回，继续执行下面的重新加载逻辑
          } else {
            # 缓存包含所有需要的列，可以安全使用
            return(df)
          }
        } else {
          # 不指定列，直接返回缓存
          return(df)
        }
      }, error = function(e) {
        cat("  ⚠️  缓存加载失败，将重新读取：", e$message, "\n", sep = "")
      })
    } else {
      cat("  🔄 数据文件已更新，重新加载...\n")
    }
  }
  
  # 读取并合并所有Excel文件
  cat("📂 读取数据目录：", data_dir, "\n", sep = "")
  excel_files <- list.files(data_dir, pattern = "\\.xlsx$", full.names = TRUE)
  excel_files <- excel_files[!grepl("~\\$", excel_files)]  # 排除临时文件
  
  if (length(excel_files) == 0) {
    stop("数据目录不存在Excel文件: ", data_dir)
  }
  
  cat("发现", length(excel_files), "个Excel文件，开始合并...\n", sep = "")
  
  # 读取所有文件（忽略columns参数，总是加载所有列以便缓存）
  df_list <- lapply(excel_files, function(file) {
    cat("  ✅ ", basename(file), "：", sep = "")
    tryCatch({
      temp_df <- readxl::read_excel(file, col_names = TRUE)
      cat(format(nrow(temp_df), big.mark = ","), " 条记录\n", sep = "")
      return(temp_df)
    }, error = function(e) {
      cat("读取失败：", e$message, "\n", sep = "")
      return(NULL)
    })
  })
  
  # 移除NULL值
  df_list <- df_list[!sapply(df_list, is.null)]
  
  if (length(df_list) == 0) {
    stop("没有成功读取任何Excel文件")
  }
  
  # 合并所有数据
  cat("正在合并数据...\n")
  df <- dplyr::bind_rows(df_list)
  cat("✅ 合并完成，总记录数：", format(nrow(df), big.mark = ","), "\n", sep = "")
  
  # 保存缓存
  if (use_cache) {
    tryCatch({
      saveRDS(df, raw_data_cache)
      
      # 保存元数据
      meta_info <- paste(
        paste("数据合并时间：", Sys.time(), sep = ""),
        paste("总记录数：", format(nrow(df), big.mark = ","), sep = ""),
        paste("列数：", ncol(df), sep = ""),
        paste("列名：", paste(colnames(df), collapse = ", "), sep = ""),
        sep = "\n"
      )
      writeLines(meta_info, raw_data_cache_meta)
      
      cat("💾 数据已缓存至：", raw_data_cache, "\n", sep = "")
    }, error = function(e) {
      cat("  ⚠️  缓存保存失败：", e$message, "\n", sep = "")
    })
  }
  
  return(df)
}

#' 获取缓存数据的信息
#'
#' @return 包含缓存信息的列表，如果缓存不存在则返回NULL
get_cached_data_info <- function() {
  if (file.exists(raw_data_cache_meta)) {
    tryCatch({
      meta_lines <- readLines(raw_data_cache_meta)
      info <- list()
      for (line in meta_lines) {
        if (grepl("：", line)) {
          parts <- strsplit(line, "：", fixed = TRUE)[[1]]
          if (length(parts) == 2) {
            info[[parts[1]]] <- parts[2]
          }
        }
      }
      return(info)
    }, error = function(e) {
      return(NULL)
    })
  }
  return(NULL)
}

#' 清除数据缓存
clear_cache <- function() {
  if (file.exists(raw_data_cache)) {
    file.remove(raw_data_cache)
    cat("✅ 已清除数据缓存\n")
  }
  if (file.exists(raw_data_cache_meta)) {
    file.remove(raw_data_cache_meta)
    cat("✅ 已清除缓存元数据\n")
  }
}

#' 加载筛选后的数据（度>=2的节点）
#'
#' @param filtered_data_path 筛选后数据的路径，如果为NULL则自动查找
#' @param use_cache 是否使用缓存（如果CSV文件未更新）
#'
#' @return 筛选后的data.frame
load_filtered_data <- function(filtered_data_path = NULL, use_cache = TRUE) {
  # 自动查找筛选后的数据文件
  if (is.null(filtered_data_path)) {
    possible_paths <- c(
      "./result/node_filtering/data/filtered_data_degree_ge2.csv",
      "../result/node_filtering/data/filtered_data_degree_ge2.csv",
      "../../result/node_filtering/data/filtered_data_degree_ge2.csv",
      "../../../result/node_filtering/data/filtered_data_degree_ge2.csv"
    )
    for (path in possible_paths) {
      if (file.exists(path)) {
        filtered_data_path <- path
        break
      }
    }
    
    if (is.null(filtered_data_path)) {
      stop("找不到筛选后的数据文件。请先运行 filter_nodes_by_degree.py 生成筛选后的数据。")
    }
  }
  
  if (!file.exists(filtered_data_path)) {
    stop("筛选后的数据文件不存在：", filtered_data_path)
  }
  
  # 检查缓存（如果CSV文件未更新，使用缓存的RDS文件）
  cache_file <- file.path(cache_dir, "filtered_data_degree_ge2.rds")
  if (use_cache && file.exists(cache_file)) {
    csv_time <- file.mtime(filtered_data_path)
    cache_time <- file.mtime(cache_file)
    
    if (cache_time > csv_time) {
      cat("📦 从缓存加载筛选后的数据（", cache_file, "）...\n", sep = "")
      tryCatch({
        df <- readRDS(cache_file)
        cat("  ✅ 成功加载缓存数据，记录数：", format(nrow(df), big.mark = ","), "\n", sep = "")
        return(df)
      }, error = function(e) {
        cat("  ⚠️  缓存加载失败，将重新读取CSV：", e$message, "\n", sep = "")
      })
    }
  }
  
  # 读取CSV文件
  cat("📂 读取筛选后的数据：", filtered_data_path, "\n", sep = "")
  
  # 检查readr包是否已安装
  if (!requireNamespace("readr", quietly = TRUE)) {
    stop("需要安装readr包来读取CSV文件：install.packages('readr')")
  }
  
  tryCatch({
    df <- readr::read_csv(filtered_data_path, 
                          locale = readr::locale(encoding = "UTF-8"), 
                          show_col_types = FALSE)
    cat("  ✅ 成功加载筛选后的数据，记录数：", format(nrow(df), big.mark = ","), "\n", sep = "")
    
    # 保存缓存
    if (use_cache) {
      tryCatch({
        saveRDS(df, cache_file)
        cat("  💾 数据已缓存至：", cache_file, "\n", sep = "")
      }, error = function(e) {
        cat("  ⚠️  缓存保存失败：", e$message, "\n", sep = "")
      })
    }
    
    return(df)
  }, error = function(e) {
    stop("读取筛选后的数据失败：", e$message)
  })
}

# 显示加载成功信息
cat("✅ 数据加载工具已加载\n")
cat("📖 使用说明：\n")
cat("  - load_all_excel_files() - 加载所有Excel文件\n")
cat("  - load_filtered_data() - 加载筛选后的数据（度>=2的节点）\n")
cat("  - get_cached_data_info() - 查看缓存信息\n")
cat("  - clear_cache() - 清除缓存\n")
cat("📝 示例：\n")
cat("  df <- load_all_excel_files(data_dir = '../data_cleaned')\n")
cat("  df_filtered <- load_filtered_data()\n\n")


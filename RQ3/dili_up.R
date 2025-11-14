# ============================
# 地理因素深入分析：比例计算与区域差异
# ============================

# Mac系统使用默认的R库路径
# 使用相对路径，不需要setwd

# 结果目录（独立于之前的结果）
result_root <- "./result/RQ3_geo_detailed"
dir.create(result_root, recursive = TRUE, showWarnings = FALSE)
plot_dir <- file.path(result_root, "plots")
dir.create(plot_dir, recursive = TRUE, showWarnings = FALSE)

# --------------------------
# Step 1: 加载包（修复版本冲突）
# --------------------------
cat("=== Step 1/6: 加载包 ===\n")

# 强制更新关键依赖包以解决版本冲突
cat("检查并更新关键依赖包...\n")
update.packages(oldPkgs = c("rlang", "cli", "lifecycle"), ask = FALSE, repos = "https://cloud.r-project.org/")

install_if_missing <- function(pkg) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org/")
    library(pkg, character.only = TRUE)
  }
}
required_packages <- c("readxl", "dplyr", "network", "ergm", "graphics", "grDevices")
for (pkg in required_packages) install_if_missing(pkg)
`%||%` <- function(x, y) if (!is.null(x)) x else y

# --------------------------
# Step 2: 数据预处理（保留地址完整样本）
# --------------------------
cat("\n=== Step 2/6: 数据预处理 ===\n")
load_data <- function() {
  # 读取并合并所有年份的Excel文件（Mac系统）
  data_dir <- "./data"
  excel_files <- list.files(data_dir, pattern = "\\.xlsx$", full.names = TRUE)
  excel_files <- excel_files[!grepl("~\\$", excel_files)]  # 排除临时文件
  
  if (length(excel_files) == 0) stop("数据目录不存在Excel文件: ", data_dir)
  
  cat("发现", length(excel_files), "个Excel文件，开始合并...\n")
  
  # 读取所有文件并标准化列名
  df_list <- lapply(excel_files, function(file) {
    cat("  读取:", basename(file), "\n")
    temp_df <- readxl::read_excel(file)
    
    cat("    列数:", ncol(temp_df), "| 前5列:", 
        paste(head(colnames(temp_df), 5), collapse=", "), "\n")
    
    needed_columns <- c("转让人", "受让人", "申请人地区", "受让人地址")
    
    if (all(needed_columns %in% colnames(temp_df))) {
      result <- temp_df[, needed_columns]
    } else if (ncol(temp_df) >= 5) {
      result <- temp_df[, c(1, 2, 4, 5)]
      colnames(result) <- needed_columns
    } else {
      cat("    ⚠️  警告：文件列数不足，跳过\n")
      return(NULL)
    }
    
    return(result)
  })
  
  # 移除NULL值
  df_list <- df_list[!sapply(df_list, is.null)]
  
  # 使用bind_rows合并
  df <- dplyr::bind_rows(df_list)
  cat("成功合并", length(df_list), "个文件，总记录数:", nrow(df), "\n")
  
  needed_columns <- c("转让人", "受让人", "申请人地区", "受让人地址")
  if (!all(needed_columns %in% colnames(df))) {
    stop("合并后的数据缺少必需的列")
  }
  
  df <- df[, needed_columns]
  
  # 严格保留地址完整的样本（无缺失）
  valid_df <- df %>%
    filter(
      !is.na(转让人), !is.na(受让人),
      !is.na(申请人地区), !is.na(受让人地址),  # 地址非空
      转让人 != "", 受让人 != "", 转让人 != 受让人,
      申请人地区 != "", 受让人地址 != ""
    ) %>%
    mutate(
      转让人 = trimws(转让人),
      受让人 = trimws(受让人),
      申请人地区 = trimws(申请人地区),
      受让人地址 = trimws(受让人地址)
    ) %>%
    distinct(转让人, 受让人, .keep_all = TRUE)  # 去重
  
  # 提取省份（优化逻辑）
  extract_province <- function(address) {
    if (is.na(address) || address == "") return("Unknown")
    # 处理直辖市和省份前缀
    addr_prefix <- substr(address, 1, 2)
    if (addr_prefix %in% c("北京", "上海", "天津", "重庆")) return(addr_prefix)
    if (substr(addr_prefix, 2, 2) == "省") return(substr(addr_prefix, 1, 1))  # 如"广东"→"广"
    return(addr_prefix)
  }
  valid_df$转让人省份 <- sapply(valid_df$申请人地区, extract_province)
  valid_df$受让人省份 <- sapply(valid_df$受让人地址, extract_province)
  
  # 再次过滤省份识别失败的样本
  valid_df <- valid_df %>%
    filter(转让人省份 != "Unknown", 受让人省份 != "Unknown")
  
  cat("保留", nrow(valid_df), "条地址完整的样本（无缺失）\n")
  write.csv(valid_df, file.path(result_root, "geo_detailed_data.csv"), row.names = FALSE, fileEncoding = "UTF-8")
  return(valid_df)
}
df <- load_data()

# --------------------------
# Step 3: 计算排除缺失后的同省份转让比例
# --------------------------
cat("\n=== Step 3/6: 同省份转让比例计算 ===\n")
# 计算同省份/异省份的数量与比例
province_compare <- df %>%
  mutate(同省份 = 转让人省份 == 受让人省份) %>%
  count(同省份) %>%
  mutate(比例 = n / sum(n) * 100)  # 百分比

# 打印结果
cat("排除地址缺失样本后的转让分布：\n")
print(province_compare)

# Visualize proportions
png(file.path(plot_dir, "same_province_ratio.png"), width = 600, height = 500)
barplot(
  province_compare$比例,
  names.arg = ifelse(province_compare$同省份, "Same Province", "Different Province"),
  col = c("lightblue", "lightcoral"),
  ylab = "Ratio (%)",
  main = "Transfer Ratio After Excluding Missing Addresses",
  ylim = c(0, 100)
)
text(
  x = 1:nrow(province_compare),
  y = province_compare$比例 + 5,
  labels = paste0(round(province_compare$比例, 1), "%"),
  cex = 1.2
)
dev.off()
cat("Same province ratio chart saved to:", plot_dir, "\n")

# --------------------------
# Step 4: 东部vs中西部区域划分
# --------------------------
cat("\n=== Step 4/6: 区域划分 ===\n")
# 中国东部省份列表（根据常见地理划分）
east_provinces <- c("北京", "天津", "河北", "山东", "江苏", "上海", "浙江", "福建", "广东", "海南")
# 中西部省份列表（简化版）
midwest_provinces <- c("山西", "河南", "安徽", "江西", "湖北", "湖南", "内蒙古", "广西", "重庆", 
                       "四川", "贵州", "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆")

# 为转让人/受让人的省份匹配区域
df <- df %>%
  mutate(
    转让人区域 = case_when(
      转让人省份 %in% east_provinces ~ "东部",
      转让人省份 %in% midwest_provinces ~ "中西部",
      TRUE ~ "其他"
    ),
    受让人区域 = case_when(
      受让人省份 %in% east_provinces ~ "东部",
      受让人省份 %in% midwest_provinces ~ "中西部",
      TRUE ~ "其他"
    )
  ) %>%
  filter(转让人区域 != "其他", 受让人区域 != "其他")  # 仅保留东部和中西部

cat("区域划分后样本量:", nrow(df), "条（仅保留东部和中西部）\n")

# --------------------------
# Step 5: 区域差异分析（同省份比例的区域对比）
# --------------------------
cat("\n=== Step 5/6: 区域差异分析 ===\n")
# 按转让人区域分组，计算每组的同省份比例
region_analysis <- df %>%
  mutate(同省份 = 转让人省份 == 受让人省份) %>%
  group_by(转让人区域) %>%
  summarise(
    样本量 = n(),
    同省份数量 = sum(同省份),
    同省份比例 = 同省份数量 / 样本量 * 100
  ) %>%
  arrange(desc(同省份比例))

# 打印区域差异结果
cat("东部vs中西部的同省份转让比例：\n")
print(region_analysis)

# Visualize regional differences
png(file.path(plot_dir, "region_comparison.png"), width = 700, height = 600)
barplot(
  region_analysis$同省份比例,
  names.arg = region_analysis$转让人区域,
  col = c("lightgreen", "orange"),
  ylab = "Same Province Transfer Ratio (%)",
  main = "Same Province Transfer Ratio: East vs Midwest",
  ylim = c(0, max(region_analysis$同省份比例) + 10)
)
text(
  x = 1:nrow(region_analysis),
  y = region_analysis$同省份比例 + 5,
  labels = paste0(round(region_analysis$同省份比例, 1), "%"),
  cex = 1.2
)
dev.off()
cat("Regional difference comparison chart saved to:", plot_dir, "\n")

# --------------------------
# Step 6: 区域分组ERGM模型（可选，验证统计显著性）
# --------------------------
cat("\n=== Step 6/6: 区域分组模型验证 ===\n")
# 仅对样本量足够的区域拟合模型（如样本量≥50）
fit_region_model <- function(subset_df, region_name) {
  if (nrow(subset_df) < 50) {
    cat(region_name, "样本量不足50，跳过模型拟合\n")
    return(NULL)
  }
  
  # 构建子网络
  all_entities <- unique(c(subset_df$转让人, subset_df$受让人))
  entity_id <- setNames(1:length(all_entities), all_entities)
  edges <- data.frame(
    from = entity_id[subset_df$转让人],
    to = entity_id[subset_df$受让人]
  ) %>% na.omit()
  net <- network::network(edges, directed = TRUE)
  network::set.vertex.attribute(net, "vertex.names", all_entities)
  
  # 计算地理proximity矩阵
  n_nodes <- network::network.size(net)
  geo_prox_mat <- matrix(0, n_nodes, n_nodes)
  edges_mat <- as.matrix(net, matrix.type = "edgelist")
  province_df <- subset_df %>%
    select(转让人, 转让人省份) %>% rename(name = 转让人, province = 转让人省份) %>%
    bind_rows(subset_df %>% select(受让人, 受让人省份) %>% rename(name = 受让人, province = 受让人省份)) %>%
    distinct(name, .keep_all = TRUE)
  node_provinces <- province_df$province[match(all_entities, province_df$name)]
  for (i in 1:nrow(edges_mat)) {
    from <- edges_mat[i, 1]; to <- edges_mat[i, 2]
    geo_prox_mat[from, to] <- ifelse(node_provinces[from] == node_provinces[to], 1, 0)
  }
  network::set.network.attribute(net, "geo_prox", geo_prox_mat)
  
  # 拟合模型
  cat("拟合", region_name, "子模型...\n")
  model <- ergm::ergm(
    net ~ edges + edgecov("geo_prox"),
    control = ergm::control.ergm(
      MCMC.burnin = 2000,
      MCMC.interval = 200,
      MCMC.samplesize = 300,
      seed = 123
    )
  )
  return(list(region = region_name, model = model))
}

# 按区域分组拟合模型
east_df <- df %>% filter(转让人区域 == "东部")
midwest_df <- df %>% filter(转让人区域 == "中西部")

east_model <- fit_region_model(east_df, "东部")
midwest_model <- fit_region_model(midwest_df, "中西部")

# 保存区域模型结果
if (!is.null(east_model)) {
  sink(file.path(result_root, "east_model_summary.txt"))
  cat("=== 东部区域模型结果 ===\n")
  summary(east_model$model)
  sink()
}
if (!is.null(midwest_model)) {
  sink(file.path(result_root, "midwest_model_summary.txt"))
  cat("=== 中西部区域模型结果 ===\n")
  summary(midwest_model$model)
  sink()
}

cat("\n分析结束，所有结果保存至:", result_root, "\n")
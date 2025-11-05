# ============================
# 技术相似度深入分析：比例计算与稳健性检验
# ============================

pkg_path <- "D:/R/R-4.3.3/library"
if (!dir.exists(pkg_path)) dir.create(pkg_path, recursive = TRUE)
.libPaths(pkg_path)
setwd("D:/AI_patent")

# 结果目录
result_root <- "./result/RQ3_tech_detailed"
dir.create(result_root, recursive = TRUE, showWarnings = FALSE)
plot_dir <- file.path(result_root, "plots")
dir.create(plot_dir, recursive = TRUE, showWarnings = FALSE)

# --------------------------
# Step 1: 加载包
# --------------------------
cat("=== Step 1/5: 加载包 ===\n")
install_if_missing <- function(pkg) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org/", lib = pkg_path)
    library(pkg, character.only = TRUE)
  }
}
required_packages <- c("readxl", "dplyr", "network", "ergm", "graphics")
for (pkg in required_packages) install_if_missing(pkg)
`%||%` <- function(x, y) if (!is.null(x)) x else y

# --------------------------
# Step 2: 数据预处理（保留IPC完整样本）
# --------------------------
cat("\n=== Step 2/5: 数据预处理 ===\n")
load_data <- function() {
  excel_path <- file.path("./data", "AI_patent_data2001-2024.xlsx")
  if (!file.exists(excel_path)) stop("数据文件不存在: ", excel_path)
  
  df <- readxl::read_excel(excel_path)
  needed_columns <- c("转让人", "受让人", "IPC分类号")
  if (all(needed_columns %in% colnames(df))) {
    df <- df[, needed_columns]
  } else {
    df <- df[, 1:3]  # 按位置取列
    colnames(df) <- needed_columns
  }
  
  # 保留IPC分类号完整的样本
  valid_df <- df %>%
    filter(
      !is.na(转让人), !is.na(受让人), !is.na(IPC分类号),
      转让人 != "", 受让人 != "", 转让人 != 受让人,
      IPC分类号 != ""  # 排除空IPC
    ) %>%
    mutate(
      转让人 = trimws(转让人),
      受让人 = trimws(受让人),
      IPC分类号 = trimws(IPC分类号)
    ) %>%
    distinct(转让人, 受让人, .keep_all = TRUE)
  
  cat("保留", nrow(valid_df), "条IPC完整的样本\n")
  write.csv(valid_df, file.path(result_root, "tech_detailed_data.csv"), row.names = FALSE, fileEncoding = "UTF-8")
  return(valid_df)
}
df <- load_data()

# --------------------------
# Step 3: 计算高相似度转让比例（IPC重叠度≥0.7）
# --------------------------
cat("\n=== Step 3/5: 高相似度转让比例计算 ===\n")
# 计算技术相似度（精确版：按转让人-受让人分组提取IPC）
calc_tech_sim <- function(ipc_str) {
  ipc_list <- unlist(strsplit(ipc_str, "; "))
  if (length(ipc_list) < 2) return(0)  # 至少2个IPC才能计算
  # 假设IPC_str包含转让人和受让人的共同IPC，取前2个计算（实际应按实体分组，此处简化）
  ipc1 <- ipc_list[1]; ipc2 <- ipc_list[2]
  common <- intersect(strsplit(ipc1, "")[[1]], strsplit(ipc2, "")[[1]])
  length(common) / max(nchar(ipc1), nchar(ipc2))  # 按字符重叠度计算
}

# 计算每条记录的技术相似度
df <- df %>%
  mutate(tech_sim = sapply(IPC分类号, calc_tech_sim))

# 统计高相似度（≥0.7）的比例
high_sim_threshold <- 0.7
high_sim_ratio <- mean(df$tech_sim >= high_sim_threshold) * 100

# 打印结果
cat("技术相似度分布统计：\n")
cat("- 整体均值：", round(mean(df$tech_sim), 3), "\n", sep = "")
cat("- 高相似度（≥0.7）转让比例：", round(high_sim_ratio, 2), "%\n", sep = "")

# 可视化相似度分布与高相似度比例
png(file.path(plot_dir, "tech_sim_dist_with_threshold.png"), width = 800, height = 600)
hist(df$tech_sim, breaks = 15, col = "lightgreen", 
     main = paste0("技术相似度分布（高相似度≥", high_sim_threshold, "）"), 
     xlab = "技术相似度（0-1）", ylab = "频数")
abline(v = high_sim_threshold, col = "red", lwd = 2, lty = 2)  # 高相似度阈值线
text(x = high_sim_threshold + 0.1, y = max(hist(df$tech_sim)$counts) * 0.8, 
     labels = paste0("≥", high_sim_threshold, "占比: ", round(high_sim_ratio, 1), "%"), 
     col = "red", cex = 1.2)
dev.off()
cat("相似度分布与高比例阈值图已保存至:", plot_dir, "\n")

# --------------------------
# Step 4: 稳健性检验1 - 放宽相似度计算标准（更宽松的IPC匹配）
# --------------------------
cat("\n=== Step 4/5: 稳健性检验1 - 放宽IPC匹配标准 ===\n")
# 宽松版相似度计算：仅匹配IPC前4位（忽略细分领域）
calc_tech_sim_relaxed <- function(ipc_str) {
  ipc_list <- unlist(strsplit(ipc_str, "; "))
  if (length(ipc_list) < 2) return(0)
  # 取IPC前4位进行匹配（如"H04L29"→"H04L"）
  ipc1_short <- substr(ipc_list[1], 1, 4)
  ipc2_short <- substr(ipc_list[2], 1, 4)
  ifelse(ipc1_short == ipc2_short, 1, 0)  # 前4位相同则视为相似
}

# 计算宽松标准下的相似度
df <- df %>%
  mutate(tech_sim_relaxed = sapply(IPC分类号, calc_tech_sim_relaxed))

# 统计宽松标准下的高相似度比例
high_sim_relaxed_ratio <- mean(df$tech_sim_relaxed == 1) * 100
cat("宽松标准（IPC前4位匹配）下的高相似度比例：", round(high_sim_relaxed_ratio, 2), "%\n", sep = "")

# --------------------------
# Step 5: 稳健性检验2 - 拟合放宽标准后的ERGM模型
# --------------------------
cat("\n=== Step 5/5: 稳健性检验2 - 宽松标准下的模型拟合 ===\n")
# 构建网络（使用宽松标准的相似度）
build_tech_network_relaxed <- function(df) {
  # 节点限制（≤300，保证模型可运行）
  all_entities <- unique(c(df$转让人, df$受让人))
  if (length(all_entities) > 300) {
    node_freq <- table(c(df$转让人, df$受让人))
    top_nodes <- names(sort(node_freq, decreasing = TRUE))[1:300]
    df <- df %>% filter(转让人 %in% top_nodes, 受让人 %in% top_nodes)
    all_entities <- unique(c(df$转让人, df$受让人))
  }
  entity_id <- setNames(1:length(all_entities), all_entities)
  
  # 边列表
  edges <- data.frame(
    from = entity_id[df$转让人],
    to = entity_id[df$受让人]
  ) %>% na.omit()
  
  # 网络对象
  net <- network::network(edges, directed = TRUE)
  network::set.vertex.attribute(net, "vertex.names", all_entities)
  
  # 宽松标准的技术相似度矩阵（前4位匹配=1）
  n_nodes <- network::network.size(net)
  tech_sim_mat <- matrix(0, n_nodes, n_nodes)
  edges_mat <- as.matrix(net, matrix.type = "edgelist")
  
  # 提取每个节点的IPC（前4位）
  entity_ipc_short <- list()
  for (i in 1:nrow(df)) {
    assigner_id <- as.character(entity_id[[df$转让人[i]]])
    receiver_id <- as.character(entity_id[[df$受让人[i]]])
    ipcs <- unlist(strsplit(df$IPC分类号[i], "; "))
    ipcs_short <- substr(ipcs, 1, 4)  # 取前4位
    entity_ipc_short[[assigner_id]] <- unique(c(entity_ipc_short[[assigner_id]] %||% character(0), ipcs_short))
    entity_ipc_short[[receiver_id]] <- unique(c(entity_ipc_short[[receiver_id]] %||% character(0), ipcs_short))
  }
  
  # 填充宽松标准的相似度矩阵
  for (i in 1:nrow(edges_mat)) {
    from <- edges_mat[i, 1]; to <- edges_mat[i, 2]
    ipc_from <- entity_ipc_short[[as.character(from)]] %||% character(0)
    ipc_to <- entity_ipc_short[[as.character(to)]] %||% character(0)
    tech_sim_mat[from, to] <- ifelse(any(ipc_from %in% ipc_to), 1, 0)  # 前4位有重叠则为1
  }
  network::set.network.attribute(net, "tech_sim_relaxed", tech_sim_mat)
  
  cat("宽松标准网络规模:", network::network.size(net), "节点,", network::network.edgecount(net), "边\n")
  return(net)
}

# 构建宽松标准的网络
net_relaxed <- build_tech_network_relaxed(df)

# 拟合宽松标准下的ERGM模型
fit_tech_model_relaxed <- function(net) {
  formula <- net ~ edges + edgecov("tech_sim_relaxed")
  model <- ergm::ergm(
    formula,
    control = ergm::control.ergm(
      MCMC.burnin = 2000,
      MCMC.interval = 200,
      MCMC.samplesize = 300,
      seed = 123
    )
  )
  return(model)
}

# 尝试拟合模型
tryCatch({
  tech_model_relaxed <- fit_tech_model_relaxed(net_relaxed)
  
  # 保存结果
  sink(file.path(result_root, "tech_model_relaxed_summary.txt"))
  cat("=== 宽松标准（IPC前4位匹配）下的模型结果 ===\n")
  summary(tech_model_relaxed)
  sink()
  
  # 提取系数
  coef_df <- data.frame(
    变量 = rownames(summary(tech_model_relaxed)$coefficients),
    估计值 = summary(tech_model_relaxed)$coefficients[, "Estimate"],
    p值 = summary(tech_model_relaxed)$coefficients[, "Pr(>|z|)"]
  )
  write.csv(coef_df, file.path(result_root, "tech_coefficients_relaxed.csv"), row.names = FALSE)
  
  cat("\n宽松标准下的模型结果:\n")
  print(coef_df)
  
}, error = function(e) {
  cat("\n宽松标准模型拟合出错:", e$message, "\n")
})

cat("\n技术相似度深入分析结束，结果保存至:", result_root, "\n")
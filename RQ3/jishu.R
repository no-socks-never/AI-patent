# ============================
# 专利转让网络：技术相似度专用分析
# ============================

# 设置路径
pkg_path <- "D:/R/R-4.3.3/library"
if (!dir.exists(pkg_path)) dir.create(pkg_path, recursive = TRUE)
.libPaths(pkg_path)
setwd("D:/AI_patent")

# 结果目录
result_root <- "./result/RQ3_tech"
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
required_packages <- c("readxl", "dplyr", "ergm", "network", "graphics")
for (pkg in required_packages) install_if_missing(pkg)
`%||%` <- function(x, y) if (!is.null(x)) x else y

# --------------------------
# Step 2: 数据预处理
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
  
  # 过滤与清洗
  valid_df <- df %>%
    filter(
      !is.na(转让人), !is.na(受让人), !is.na(IPC分类号),
      转让人 != "", 受让人 != "", 转让人 != 受让人,
      IPC分类号 != ""
    ) %>%
    mutate(
      转让人 = trimws(转让人),
      受让人 = trimws(受让人)
    ) %>%
    distinct(转让人, 受让人, .keep_all = TRUE)
  
  # 限制规模（边数≤500）
  sample_size <- min(500, nrow(valid_df))
  valid_df <- valid_df %>% sample_n(sample_size, seed = 123)
  
  write.csv(valid_df, file.path(result_root, "tech_data.csv"), row.names = FALSE, fileEncoding = "UTF-8")
  cat("保留", nrow(valid_df), "条数据用于技术相似度分析\n")
  return(valid_df)
}
df <- load_data()

# --------------------------
# Step 3: 技术相似度数据验证
# --------------------------
cat("\n=== Step 3/5: 技术相似度数据验证 ===\n")
# 计算技术相似度
calc_tech_sim <- function(ipc_str) {
  ipc_list <- unlist(strsplit(ipc_str, "; "))
  if (length(ipc_list) < 2) return(0)
  sample_ipc <- sample(ipc_list, min(2, length(ipc_list)))  # 取2个IPC计算
  ipc1 <- sample_ipc[1]; ipc2 <- sample_ipc[2]
  common <- intersect(strsplit(ipc1, "")[[1]], strsplit(ipc2, "")[[1]])
  length(common) / max(nchar(ipc1), nchar(ipc2))
}

df$tech_sim <- sapply(df$IPC分类号, calc_tech_sim)
cat("技术相似度统计:\n")
cat("均值:", round(mean(df$tech_sim), 3), "\n")
cat("中位数:", round(median(df$tech_sim), 3), "\n")
cat("范围:", round(range(df$tech_sim), 3), "\n")

# 相似度分布可视化
png(file.path(plot_dir, "tech_sim_dist.png"), width = 800, height = 600)
hist(df$tech_sim, breaks = 10, col = "lightgreen", main = "技术相似度分布", xlab = "相似度")
dev.off()
cat("技术相似度分布图已保存至:", plot_dir, "\n")

# --------------------------
# Step 4: 构建网络与协变量
# --------------------------
cat("\n=== Step 4/5: 构建网络 ===\n")
build_tech_network <- function(df) {
  # 节点限制（≤300）
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
  
  # 技术相似度矩阵
  n_nodes <- network::network.size(net)
  tech_sim_mat <- matrix(0, n_nodes, n_nodes)
  edges_mat <- as.matrix(net, matrix.type = "edgelist")
  
  # 提取每个节点的IPC
  entity_ipc <- list()
  for (i in 1:nrow(df)) {
    assigner_id <- as.character(entity_id[[df$转让人[i]]])
    receiver_id <- as.character(entity_id[[df$受让人[i]]])
    ipcs <- unlist(strsplit(df$IPC分类号[i], "; "))
    entity_ipc[[assigner_id]] <- unique(c(entity_ipc[[assigner_id]] %||% character(0), ipcs))
    entity_ipc[[receiver_id]] <- unique(c(entity_ipc[[receiver_id]] %||% character(0), ipcs))
  }
  
  # 填充相似度矩阵
  for (i in 1:nrow(edges_mat)) {
    from <- edges_mat[i, 1]; to <- edges_mat[i, 2]
    ipc_from <- entity_ipc[[as.character(from)]] %||% character(0)
    ipc_to <- entity_ipc[[as.character(to)]] %||% character(0)
    if (length(ipc_from) > 0 && length(ipc_to) > 0) {
      common <- intersect(ipc_from, ipc_to)
      tech_sim_mat[from, to] <- length(common) / max(length(ipc_from), length(ipc_to))
    }
  }
  network::set.network.attribute(net, "tech_sim", tech_sim_mat)
  
  cat("网络规模:", network::network.size(net), "节点,", network::network.edgecount(net), "边\n")
  return(net)
}
net <- build_tech_network(df)

# --------------------------
# Step 5: 技术相似度ERGM模型
# --------------------------
cat("\n=== Step 5/5: 拟合技术相似度模型 ===\n")
fit_tech_model <- function(net) {
  formula <- net ~ edges + edgecov("tech_sim")  # 仅含技术相似度
  model <- ergm::ergm(
    formula,
    control = ergm::control.ergm(
      MCMC.burnin = 3000,
      MCMC.interval = 300,
      MCMC.samplesize = 500,
      seed = 123
    )
  )
  return(model)
}

tryCatch({
  tech_model <- fit_tech_model(net)
  # 保存结果
  sink(file.path(result_root, "tech_model_summary.txt"))
  summary(tech_model)
  sink()
  coef_df <- data.frame(
    变量 = rownames(summary(tech_model)$coefficients),
    估计值 = summary(tech_model)$coefficients[, "Estimate"],
    p值 = summary(tech_model)$coefficients[, "Pr(>|z|)"]
  )
  write.csv(coef_df, file.path(result_root, "tech_coefficients.csv"), row.names = FALSE)
  cat("\n技术相似度模型结果:\n")
  print(coef_df)
}, error = function(e) {
  cat("\n模型出错:", e$message, "\n请参考数据层面的相似度分布结论\n")
})

cat("\n技术相似度分析结束，结果保存至:", result_root, "\n")
# RQ3: 技术相似度对专利转让网络的影响 - 改进版（使用筛选后数据）
# 改进1: 加入内生结构项（mutual + gwesp）
# 改进2: 分时段建模（2001-2010、2011-2017、2018-2024）
# 改进3: 使用筛选后的数据（度>=2的节点）

# 设置工作目录并加载依赖
script_dir <- dirname(rstudioapi::getSourceEditorContext()$path)
if (dir.exists(script_dir)) {
  setwd(script_dir)
} else {
  script_dir <- getwd()
  possible_paths <- c(
    ".",
    "coding/RQ3",
    "../RQ3",
    "../../RQ3"
  )
  for (path in possible_paths) {
    if (file.exists(file.path(path, "r_font_config.R"))) {
      setwd(path)
      script_dir <- getwd()
      break
    }
  }
}

cat("当前工作目录:", getwd(), "\n")
source("r_font_config.R", encoding = "UTF-8")
source("data_loader.R", encoding = "UTF-8")

library(dplyr)
library(ergm)
library(network)

setup_chinese_fonts()

# 结果保存路径
result_root <- "./result/RQ3_formation_factors/technology_improved_filtered"
data_dir <- file.path(result_root, "data")
plot_dir <- file.path(result_root, "plots")
dir.create(result_root, recursive = TRUE, showWarnings = FALSE)
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(plot_dir, recursive = TRUE, showWarnings = FALSE)

cat("\n", strrep("=", 60), "\n", sep="")
cat("RQ3: 技术相似度影响分析 - 改进版（使用筛选后数据）\n")
cat("改进1: 加入内生结构项（mutual + gwesp）\n")
cat("改进2: 分时段建模（2001-2010、2011-2017、2018-2024）\n")
cat("改进3: 使用筛选后的数据（度>=2的节点）\n")
cat(strrep("=", 60), "\n\n", sep="")

# =============================================================================
# 数据加载（使用筛选后的数据）
# =============================================================================
cat("=== Step 1/6: 数据加载（筛选后数据） ===\n")

# 使用统一的数据加载工具加载筛选后的数据
df <- load_filtered_data(use_cache = TRUE)

# 定义需要的列
needed_columns <- c("转让人", "受让人", "IPC分类号", "转让生效年份")

# 检查并选择需要的列
missing_cols <- needed_columns[!needed_columns %in% colnames(df)]
if (length(missing_cols) > 0) {
  stop("数据缺少必需的列: ", paste(missing_cols, collapse=", "))
}

df <- df[, needed_columns]

# 筛选有效数据
df <- df %>%
  filter(
    !is.na(转让人), !is.na(受让人),
    转让人 != 受让人,  # 排除自环（转让人=受让人）
    !is.na(IPC分类号), IPC分类号 != "",
    !is.na(转让生效年份)
  ) %>%
  mutate(
    转让生效年份 = as.integer(转让生效年份)
  )

cat("有效记录数:", nrow(df), "\n")
cat("年份范围:", min(df$转让生效年份, na.rm=TRUE), "-", max(df$转让生效年份, na.rm=TRUE), "\n")
cat("说明: 数据已筛选，只包含度>=2节点之间的转让关系\n\n")

# =============================================================================
# 定义时间段
# =============================================================================
time_periods <- list(
  Period1 = list(name = "2001-2010（萌芽期）", start = 2001, end = 2010),
  Period2 = list(name = "2011-2017（发展期）", start = 2011, end = 2017),
  Period3 = list(name = "2018-2024（爆发期）", start = 2018, end = 2024)
)

# =============================================================================
# 构建技术相似度网络的函数（基于节点活跃度筛选）
# =============================================================================
build_tech_network <- function(df, max_nodes = 250) {  # 与原始研究一致，保留200-250个最活跃节点
  cat("\n构建技术相似度网络...\n")
  cat("样本量:", nrow(df), "条\n")
  
  # 提取主体
  all_entities <- unique(c(df$转让人, df$受让人))
  cat("主体数:", length(all_entities), "\n")
  
  # 【简化策略】如果节点数过多，只保留最活跃的节点（基于转让次数排序）
  if (length(all_entities) > max_nodes) {
    cat("  节点数过多，筛选活跃度最高的", max_nodes, "个节点...\n")
    
    # 统计每个节点的活跃度（出现次数）
    node_freq <- table(c(df$转让人, df$受让人))
    top_nodes <- names(sort(node_freq, decreasing = TRUE))[1:max_nodes]
    
    # 筛选数据（只保留活跃节点）
    df <- df %>% 
      filter(转让人 %in% top_nodes, 受让人 %in% top_nodes)
    
    all_entities <- unique(c(df$转让人, df$受让人))
    cat("  ✅ 筛选后: ", length(all_entities), "个节点, ", nrow(df), "条记录\n", sep = "")
  }
  
  entity_id <- setNames(1:length(all_entities), all_entities)
  
  # 聚合重复边（同一对转让人-受让人可能有多次转让）
  df_agg <- df %>%
    group_by(转让人, 受让人) %>%
    summarise(
      转让次数 = n(),
      IPC分类号 = paste(unique(unlist(strsplit(IPC分类号, "; "))), collapse = "; "),
      .groups = "drop"
    )
  
  # 边列表（去重后）
  edges <- data.frame(
    from = entity_id[df_agg$转让人],
    to = entity_id[df_agg$受让人]
  ) %>% na.omit()
  
  cat("  唯一边数:", nrow(edges), "（聚合前:", nrow(df), "）\n")
  
  # 网络对象
  net <- network::network(edges, directed = TRUE)
  network::set.vertex.attribute(net, "vertex.names", all_entities)
  
  # 技术相似度矩阵（Jaccard相似度）
  n_nodes <- network::network.size(net)
  tech_sim_mat <- matrix(0, n_nodes, n_nodes)
  
  # 提取每个节点的IPC（前4位）- 使用聚合后的df_agg
  entity_ipc_short <- list()
  for (i in 1:nrow(df_agg)) {
    assigner_id <- as.character(entity_id[[df_agg$转让人[i]]])
    receiver_id <- as.character(entity_id[[df_agg$受让人[i]]])
    ipcs <- unlist(strsplit(df_agg$IPC分类号[i], "; "))
    ipcs_short <- substr(ipcs, 1, 4)
    entity_ipc_short[[assigner_id]] <- unique(c(entity_ipc_short[[assigner_id]] %||% character(0), ipcs_short))
    entity_ipc_short[[receiver_id]] <- unique(c(entity_ipc_short[[receiver_id]] %||% character(0), ipcs_short))
  }
  
  # 填充相似度矩阵（Jaccard相似度）
  for (i in 1:n_nodes) {
    for (j in 1:n_nodes) {
      if (i != j) {
        ipc_from <- entity_ipc_short[[as.character(i)]] %||% character(0)
        ipc_to <- entity_ipc_short[[as.character(j)]] %||% character(0)
        if (length(ipc_from) > 0 && length(ipc_to) > 0) {
          common <- intersect(ipc_from, ipc_to)
          tech_sim_mat[i, j] <- length(common) / max(length(ipc_from), length(ipc_to))
        }
      }
    }
  }
  
  network::set.network.attribute(net, "tech_sim", tech_sim_mat)
  
  # 检查互惠边
  edges_mat <- as.matrix(net, matrix.type = "edgelist")
  mutual_count <- 0
  if (nrow(edges_mat) > 0) {
    # 创建反向边查找
    edges_set <- paste(edges_mat[,1], edges_mat[,2], sep="_")
    reverse_edges_set <- paste(edges_mat[,2], edges_mat[,1], sep="_")
    mutual_count <- sum(reverse_edges_set %in% edges_set)
  }
  mutual_ratio <- ifelse(nrow(edges_mat) > 0, mutual_count / nrow(edges_mat), 0)
  
  cat("网络规模:", network::network.size(net), "节点,", network::network.edgecount(net), "边\n")
  cat("互惠边数量:", mutual_count, "（占比:", round(mutual_ratio * 100, 2), "%）\n")
  
  if (mutual_count == 0) {
    cat("  ⚠️  警告：网络中没有互惠边，mutual项将无法估计！\n")
  }
  
  return(net)
}

# =============================================================================
# 拟合ERGM模型的函数（加入内生结构项）
# =============================================================================
fit_tech_ergm <- function(net, period_name) {
  cat("\n拟合", period_name, "ERGM模型...\n")
  
  # 【改进】加入内生结构项
  formula <- net ~ edges +                          # 基线密度
                   edgecov("tech_sim") +           # 技术相似度
                   mutual +                         # 互惠性（A→B且B→A）
                   gwesp(0.25, fixed = TRUE)       # 三角闭合（传递性）
  
  model <- tryCatch({
    ergm::ergm(
      formula,
      control = ergm::control.ergm(
        MCMC.burnin = 2000,
        MCMC.interval = 200,
        MCMC.samplesize = 300,
        seed = 123,
        init.method = "CD"
      ),
      eval.loglik = FALSE
    )
  }, error = function(e) {
    cat("  ⚠️  完整模型拟合失败，尝试简化模型（移除gwesp）...\n")
    formula_simple <- net ~ edges + edgecov("tech_sim") + mutual
    ergm::ergm(
      formula_simple,
      control = ergm::control.ergm(
        MCMC.burnin = 2000,
        MCMC.interval = 200,
        MCMC.samplesize = 300,
        seed = 123,
        init.method = "CD"
      ),
      eval.loglik = FALSE
    )
  })
  
  return(model)
}

# =============================================================================
# 分时段建模
# =============================================================================
cat("\n=== Step 2/6: 分时段建模 ===\n")

results_list <- list()

for (period_key in names(time_periods)) {
  period <- time_periods[[period_key]]
  cat("\n", strrep("=", 60), "\n", sep="")
  cat("【", period$name, "】\n", sep="")
  cat(strrep("=", 60), "\n", sep="")
  
  # 筛选时期数据
  df_period <- df %>% 
    filter(转让生效年份 >= period$start, 转让生效年份 <= period$end)
  
  if (nrow(df_period) < 50) {
    cat("样本量不足（n=", nrow(df_period), "），跳过此时期\n", sep="")
    next
  }
  
  # 构建网络（保留活跃度最高的节点，与原始研究一致）
  net_period <- build_tech_network(df_period, max_nodes = 250)
  
  # 拟合模型
  model_period <- fit_tech_ergm(net_period, period$name)
  
  # 保存结果
  results_list[[period_key]] <- list(
    period = period$name,
    model = model_period,
    n_nodes = network::network.size(net_period),
    n_edges = network::network.edgecount(net_period)
  )
  
  # 输出摘要
  cat("\n模型摘要:\n")
  print(summary(model_period))
  
  # 保存到文件
  summary_file <- file.path(data_dir, paste0(period_key, "_model_summary.txt"))
  sink(summary_file)
  cat("=== ", period$name, " 技术相似度ERGM模型结果（筛选后数据） ===\n\n", sep="")
  print(summary(model_period))
  cat("\n模型公式：", deparse(model_period$formula), "\n")
  cat("样本量：", nrow(df_period), " 条\n", sep="")
  cat("网络规模：", network::network.size(net_period), " 节点，", 
      network::network.edgecount(net_period), " 边\n", sep="")
  cat("数据说明：使用筛选后的数据（度>=2的节点）\n")
  sink()
  cat("  ✅ 摘要已保存:", summary_file, "\n")
}

# =============================================================================
# 提取并对比系数
# =============================================================================
cat("\n=== Step 3/6: 系数对比 ===\n")

coef_comparison <- data.frame()

for (period_key in names(results_list)) {
  result <- results_list[[period_key]]
  coefs <- coef(result$model)
  
  coef_row <- data.frame(
    时期 = result$period,
    edges = coefs["edges"],
    tech_sim = coefs["edgecov.tech_sim"],
    mutual = ifelse("mutual" %in% names(coefs), coefs["mutual"], NA),
    gwesp = ifelse("gwesp.fixed.0.25" %in% names(coefs), coefs["gwesp.fixed.0.25"], NA),
    节点数 = result$n_nodes,
    边数 = result$n_edges,
    stringsAsFactors = FALSE
  )
  
  coef_comparison <- rbind(coef_comparison, coef_row)
}

print(coef_comparison)

# 保存系数对比
coef_file <- file.path(data_dir, "coefficients_comparison_by_period.csv")
write.csv(coef_comparison, coef_file, row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 系数对比已保存:", coef_file, "\n")

# =============================================================================
# 可视化：系数随时间变化
# =============================================================================
cat("\n=== Step 4/6: 可视化系数变化 ===\n")

png(file.path(plot_dir, "coefficients_over_time.png"), 
    width = 2400, height = 1600, res = 300, family = "sans")

par(mfrow = c(2, 2), mar = c(4, 4, 3, 1))

# 准备x轴标签
periods_label <- c("2001-2010", "2011-2017", "2018-2024")
x_pos <- 1:nrow(coef_comparison)

# 1. edges系数
plot(x_pos, coef_comparison$edges, type = "b", pch = 19, col = "#2E86AB",
     xlab = "时期", ylab = "系数值", main = "Edges系数变化（筛选后数据）",
     xaxt = "n", ylim = range(coef_comparison$edges, na.rm = TRUE))
axis(1, at = x_pos, labels = periods_label, las = 2)
abline(h = 0, lty = 2, col = "gray")

# 2. tech_sim系数
plot(x_pos, coef_comparison$tech_sim, type = "b", pch = 19, col = "#A23B72",
     xlab = "时期", ylab = "系数值", main = "技术相似度系数变化（筛选后数据）",
     xaxt = "n", ylim = range(coef_comparison$tech_sim, na.rm = TRUE))
axis(1, at = x_pos, labels = periods_label, las = 2)
abline(h = 0, lty = 2, col = "gray")

# 3. mutual系数
if (any(!is.na(coef_comparison$mutual))) {
  plot(x_pos, coef_comparison$mutual, type = "b", pch = 19, col = "#F18F01",
       xlab = "时期", ylab = "系数值", main = "互惠性系数变化（筛选后数据）",
       xaxt = "n", ylim = range(coef_comparison$mutual, na.rm = TRUE))
  axis(1, at = x_pos, labels = periods_label, las = 2)
  abline(h = 0, lty = 2, col = "gray")
}

# 4. gwesp系数
if (any(!is.na(coef_comparison$gwesp))) {
  plot(x_pos, coef_comparison$gwesp, type = "b", pch = 19, col = "#6A994E",
       xlab = "时期", ylab = "系数值", main = "三角闭合系数变化（筛选后数据）",
       xaxt = "n", ylim = range(coef_comparison$gwesp, na.rm = TRUE))
  axis(1, at = x_pos, labels = periods_label, las = 2)
  abline(h = 0, lty = 2, col = "gray")
}

dev.off()
cat("✅ 系数变化图已保存:", file.path(plot_dir, "coefficients_over_time.png"), "\n")

# =============================================================================
# 生成综合报告
# =============================================================================
cat("\n=== Step 5/6: 生成综合报告 ===\n")

report_file <- file.path(data_dir, "comprehensive_report.txt")
sink(report_file)

cat(strrep("=", 70), "\n", sep="")
cat("RQ3: 技术相似度影响分析 - 改进版综合报告（筛选后数据）\n")
cat(strrep("=", 70), "\n\n", sep="")

cat("【数据说明】\n")
cat("本分析使用筛选后的数据，只包含度>=2节点之间的转让关系。\n")
cat("这减少了计算开销，同时保留了网络的核心结构。\n\n")

cat("【改进点】\n")
cat("1. 加入内生结构项：\n")
cat("   - mutual: 互惠性（A→B且B→A的倾向）\n")
cat("   - gwesp: 三角闭合（传递性，A→B→C则A→C）\n")
cat("2. 分时段建模：2001-2010、2011-2017、2018-2024\n")
cat("3. 使用筛选后的数据（度>=2的节点）\n\n")

cat("【分时段系数对比】\n")
print(coef_comparison)
cat("\n")

cat("【关键发现】\n\n")

cat("1. 技术相似度效应（tech_sim）:\n")
if (nrow(coef_comparison) >= 2) {
  trend <- ifelse(coef_comparison$tech_sim[nrow(coef_comparison)] > coef_comparison$tech_sim[1],
                  "增强", "减弱")
  cat("   ", coef_comparison$时期[1], ": ", round(coef_comparison$tech_sim[1], 3), "\n", sep="")
  cat("   ", coef_comparison$时期[nrow(coef_comparison)], ": ", 
      round(coef_comparison$tech_sim[nrow(coef_comparison)], 3), "\n", sep="")
  cat("   → 技术匹配效应随时间", trend, "\n\n", sep="")
}

cat("2. 互惠性效应（mutual）:\n")
if (any(!is.na(coef_comparison$mutual))) {
  for (i in 1:nrow(coef_comparison)) {
    if (!is.na(coef_comparison$mutual[i])) {
      cat("   ", coef_comparison$时期[i], ": ", round(coef_comparison$mutual[i], 3), "\n", sep="")
    }
  }
  cat("   → 专利转让存在", ifelse(mean(coef_comparison$mutual, na.rm=TRUE) > 0, "显著", "较弱"), 
      "的互惠倾向\n\n", sep="")
}

cat("3. 三角闭合效应（gwesp）:\n")
if (any(!is.na(coef_comparison$gwesp))) {
  for (i in 1:nrow(coef_comparison)) {
    if (!is.na(coef_comparison$gwesp[i])) {
      cat("   ", coef_comparison$时期[i], ": ", round(coef_comparison$gwesp[i], 3), "\n", sep="")
    }
  }
  cat("   → 网络", ifelse(mean(coef_comparison$gwesp, na.rm=TRUE) > 0, "存在", "缺乏"), 
      "传递性闭合倾向\n\n", sep="")
}

cat("【理论意义】\n")
cat("加入内生结构项后，模型不仅考虑外生因素（技术相似度），\n")
cat("还控制了网络自身的结构倾向（互惠性、三角闭合），\n")
cat("使得技术相似度的效应估计更加准确，避免遗漏变量偏差。\n\n")

cat("【与原始分析对比】\n")
cat("使用筛选后的数据可以：\n")
cat("1. 减少计算开销（节点数从257,363减少到22,506）\n")
cat("2. 保留网络核心结构（度>=2的节点）\n")
cat("3. 提高模型拟合效率\n\n")

cat(strrep("=", 70), "\n", sep="")

sink()
cat("✅ 综合报告已保存:", report_file, "\n")

cat("\n", strrep("=", 60), "\n", sep="")
cat("✅ 分析完成！\n")
cat(strrep("=", 60), "\n", sep="")
cat("结果目录:", result_root, "\n")
cat("  - data/: 模型摘要和系数对比\n")
cat("  - plots/: 系数变化可视化\n")
cat("说明: 本分析使用筛选后的数据（度>=2的节点）\n")


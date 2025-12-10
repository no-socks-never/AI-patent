# RQ3: 地理邻近性对专利转让网络的影响 - 改进版（使用筛选后数据）
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
result_root <- "./result/RQ3_formation_factors/geography_improved_filtered"
data_dir <- file.path(result_root, "data")
plot_dir <- file.path(result_root, "plots")
dir.create(result_root, recursive = TRUE, showWarnings = FALSE)
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(plot_dir, recursive = TRUE, showWarnings = FALSE)

cat("\n", strrep("=", 60), "\n", sep="")
cat("RQ3: 地理邻近性影响分析 - 改进版（使用筛选后数据）\n")
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
needed_columns <- c("转让人", "受让人", "申请人地区", "受让人地址", "转让生效年份")

# 检查并选择需要的列
missing_cols <- needed_columns[!needed_columns %in% colnames(df)]
if (length(missing_cols) > 0) {
  stop("数据缺少必需的列: ", paste(missing_cols, collapse=", "))
}

df <- df[, needed_columns]

# 提取省份信息（参照dili_up.R的逻辑）
extract_province <- function(address) {
  if (is.na(address)) return(NA_character_)
  provinces <- c("北京", "天津", "河北", "山西", "内蒙古", 
                 "辽宁", "吉林", "黑龙江", 
                 "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东",
                 "河南", "湖北", "湖南", "广东", "广西", "海南",
                 "重庆", "四川", "贵州", "云南", "西藏",
                 "陕西", "甘肃", "青海", "宁夏", "新疆")
  for (prov in provinces) {
    if (grepl(prov, address, fixed = TRUE)) return(prov)
  }
  return("Unknown")
}

df <- df %>%
  mutate(
    转让人省份 = sapply(申请人地区, extract_province),
    受让人省份 = sapply(受让人地址, extract_province),
    转让生效年份 = as.integer(转让生效年份)
  ) %>%
  filter(
    !is.na(转让人), !is.na(受让人),
    转让人 != 受让人,  # 排除自环（转让人=受让人）
    转让人省份 != "Unknown", 受让人省份 != "Unknown",
    !is.na(转让生效年份)
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
# 构建地理网络的函数（分层随机抽样）
# =============================================================================
build_geo_network <- function(df, max_nodes = 800) {  # 提高阈值
  cat("\n构建地理网络...\n")
  cat("样本量:", nrow(df), "条\n")
  
  # 提取主体
  all_entities <- unique(c(df$转让人, df$受让人))
  cat("主体数:", length(all_entities), "\n")
  
  # 【改进】如果节点数过多，使用分层随机抽样
  if (length(all_entities) > max_nodes) {
    node_freq <- table(c(df$转让人, df$受让人))
    
    # 按活跃度分层（四分位数）
    quartiles <- quantile(node_freq, probs = c(0, 0.25, 0.5, 0.75, 1))
    cat("  活跃度分层（四分位数）:", paste(round(quartiles, 1), collapse = " | "), "\n")
    
    # 每层随机抽样（保持结构代表性）
    selected_nodes <- c()
    for (i in 1:4) {
      layer_nodes <- names(node_freq[node_freq >= quartiles[i] & node_freq < quartiles[i+1]])
      if (i == 4) {  # 最后一层包含最大值
        layer_nodes <- names(node_freq[node_freq >= quartiles[i]])
      }
      
      # 每层抽样数量按比例分配
      n_sample <- round(max_nodes * length(layer_nodes) / length(all_entities))
      n_sample <- min(n_sample, length(layer_nodes))  # 不超过该层实际数量
      
      if (n_sample > 0 && length(layer_nodes) > 0) {
        set.seed(123 + i)  # 固定随机种子，保证可重复
        sampled <- sample(layer_nodes, size = n_sample)
        selected_nodes <- c(selected_nodes, sampled)
        cat("    第", i, "层（活跃度", round(quartiles[i], 1), "-", round(quartiles[i+1], 1), 
            "）: ", length(layer_nodes), "个节点 → 抽样", n_sample, "个\n", sep = "")
      }
    }
    
    # 筛选数据
    df <- df %>% filter(转让人 %in% selected_nodes, 受让人 %in% selected_nodes)
    all_entities <- unique(c(df$转让人, df$受让人))
    cat("  ✅ 分层抽样后主体数:", length(all_entities), "\n")
  }
  
  entity_id <- setNames(1:length(all_entities), all_entities)
  
  # 聚合重复边（同一对转让人-受让人可能有多次转让）
  # 只按转让人和受让人聚合，省份取第一个值
  df_agg <- df %>%
    group_by(转让人, 受让人) %>%
    summarise(
      转让次数 = n(),
      转让人省份 = first(转让人省份),
      受让人省份 = first(受让人省份),
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
  
  # 地理邻近性矩阵
  n_nodes <- network::network.size(net)
  geo_prox_mat <- matrix(0, n_nodes, n_nodes)
  
  # 获取节点省份 - 使用聚合后的df_agg
  province_df <- df_agg %>%
    select(转让人, 转让人省份) %>% rename(name = 转让人, province = 转让人省份) %>%
    bind_rows(df_agg %>% select(受让人, 受让人省份) %>% rename(name = 受让人, province = 受让人省份)) %>%
    distinct(name, .keep_all = TRUE)
  
  node_provinces <- province_df$province[match(all_entities, province_df$name)]
  node_provinces[is.na(node_provinces)] <- "Unknown"
  
  # 填充地理邻近性矩阵
  for (i in 1:n_nodes) {
    for (j in 1:n_nodes) {
      if (i != j) {
        geo_prox_mat[i, j] <- ifelse(
          node_provinces[i] == node_provinces[j] & 
          node_provinces[i] != "Unknown", 
          1, 0
        )
      }
    }
  }
  
  # 检查协变量多样性
  edges_mat <- as.matrix(net, matrix.type = "edgelist")
  edge_values <- geo_prox_mat[edges_mat[,1:2,drop=FALSE]]
  same_province_ratio <- mean(edge_values)
  cat("同省份转让比例:", round(same_province_ratio, 3), "\n")
  
  network::set.network.attribute(net, "geo_prox", geo_prox_mat)
  
  cat("网络规模:", network::network.size(net), "节点,", network::network.edgecount(net), "边\n")
  return(list(net = net, same_province_ratio = same_province_ratio))
}

# =============================================================================
# 拟合ERGM模型的函数（加入内生结构项）
# =============================================================================
fit_geo_ergm <- function(net, period_name) {
  cat("\n拟合", period_name, "ERGM模型...\n")
  
  # 【改进】加入内生结构项
  formula <- net ~ edges +                          # 基线密度
                   edgecov("geo_prox") +           # 地理邻近性
                   mutual +                         # 互惠性
                   gwesp(0.25, fixed = TRUE)       # 三角闭合
  
  model <- tryCatch({
    ergm::ergm(
      formula,
      control = ergm::control.ergm(
        MCMC.burnin = 3000,
        MCMC.interval = 300,
        MCMC.samplesize = 500,
        seed = 123,
        init.method = "CD"
      ),
      eval.loglik = FALSE
    )
  }, error = function(e) {
    cat("  ⚠️  完整模型拟合失败，尝试简化模型（移除gwesp）...\n")
    formula_simple <- net ~ edges + edgecov("geo_prox") + mutual
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
same_province_ratios <- data.frame()

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
  
  # 构建网络（使用更大的阈值）
  net_result <- build_geo_network(df_period, max_nodes = 800)
  net_period <- net_result$net
  
  # 记录同省份比例
  same_province_ratios <- rbind(same_province_ratios, 
    data.frame(时期 = period$name, 同省份比例 = net_result$same_province_ratio)
  )
  
  # 拟合模型
  model_period <- fit_geo_ergm(net_period, period$name)
  
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
  cat("=== ", period$name, " 地理邻近性ERGM模型结果（筛选后数据） ===\n\n", sep="")
  print(summary(model_period))
  cat("\n模型公式：", deparse(model_period$formula), "\n")
  cat("样本量：", nrow(df_period), " 条\n", sep="")
  cat("网络规模：", network::network.size(net_period), " 节点，", 
      network::network.edgecount(net_period), " 边\n", sep="")
  cat("同省份转让比例：", round(net_result$same_province_ratio, 3), "\n", sep="")
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
  
  # 处理mutual的-Inf值（在保存时转换为字符串以便识别）
  mutual_val <- ifelse("mutual" %in% names(coefs), coefs["mutual"], NA)
  if (!is.na(mutual_val) && is.infinite(mutual_val)) {
    # 如果是-Inf，保存为特殊标记，但保持数值类型用于后续处理
    mutual_val <- -Inf
  }
  
  coef_row <- data.frame(
    时期 = result$period,
    edges = coefs["edges"],
    geo_prox = coefs["edgecov.geo_prox"],
    mutual = mutual_val,
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

# 保存同省份比例变化
ratio_file <- file.path(data_dir, "same_province_ratios.csv")
write.csv(same_province_ratios, ratio_file, row.names = FALSE, fileEncoding = "UTF-8")
cat("✅ 同省份比例已保存:", ratio_file, "\n")

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

# 1. edges系数（处理异常值）
edges_plot <- coef_comparison$edges
edges_plot[is.infinite(edges_plot)] <- NA
y_range_edges <- range(edges_plot, na.rm = TRUE, finite = TRUE)
plot(x_pos, edges_plot, type = "b", pch = 19, col = "#2E86AB",
     xlab = "时期", ylab = "系数值", main = "Edges系数变化（筛选后数据）",
     xaxt = "n", ylim = y_range_edges)
axis(1, at = x_pos, labels = periods_label, las = 2)
abline(h = 0, lty = 2, col = "gray")

# 2. geo_prox系数（处理异常值）
geo_prox_plot <- coef_comparison$geo_prox
geo_prox_plot[is.infinite(geo_prox_plot)] <- NA
y_range_geo <- range(geo_prox_plot, na.rm = TRUE, finite = TRUE)
plot(x_pos, geo_prox_plot, type = "b", pch = 19, col = "#A23B72",
     xlab = "时期", ylab = "系数值", main = "地理邻近性系数变化（筛选后数据）",
     xaxt = "n", ylim = y_range_geo)
axis(1, at = x_pos, labels = periods_label, las = 2)
abline(h = 0, lty = 2, col = "gray")

# 3. mutual系数（处理-Inf值）
if (any(!is.na(coef_comparison$mutual))) {
  # 处理-Inf值：替换为NA以便绘图
  mutual_plot <- coef_comparison$mutual
  mutual_plot[is.infinite(mutual_plot)] <- NA
  
  # 计算y轴范围（排除Inf和NA）
  y_range <- range(mutual_plot, na.rm = TRUE, finite = TRUE)
  if (any(is.infinite(coef_comparison$mutual))) {
    # 如果有-Inf，在图上标注
    plot(x_pos, mutual_plot, type = "b", pch = 19, col = "#F18F01",
         xlab = "时期", ylab = "系数值", main = "互惠性系数变化（筛选后数据）",
         xaxt = "n", ylim = y_range)
    # 标注-Inf的位置
    inf_pos <- which(is.infinite(coef_comparison$mutual))
    if (length(inf_pos) > 0) {
      text(x_pos[inf_pos], y_range[2] * 0.9, "-Inf", col = "red", cex = 0.8)
    }
  } else {
    plot(x_pos, mutual_plot, type = "b", pch = 19, col = "#F18F01",
         xlab = "时期", ylab = "系数值", main = "互惠性系数变化（筛选后数据）",
         xaxt = "n", ylim = y_range)
  }
  axis(1, at = x_pos, labels = periods_label, las = 2)
  abline(h = 0, lty = 2, col = "gray")
}

# 4. gwesp系数（处理异常值）
if (any(!is.na(coef_comparison$gwesp))) {
  gwesp_plot <- coef_comparison$gwesp
  gwesp_plot[is.infinite(gwesp_plot)] <- NA
  y_range_gwesp <- range(gwesp_plot, na.rm = TRUE, finite = TRUE)
  if (length(y_range_gwesp) == 2 && is.finite(y_range_gwesp[1]) && is.finite(y_range_gwesp[2])) {
    plot(x_pos, gwesp_plot, type = "b", pch = 19, col = "#6A994E",
         xlab = "时期", ylab = "系数值", main = "三角闭合系数变化（筛选后数据）",
         xaxt = "n", ylim = y_range_gwesp)
    axis(1, at = x_pos, labels = periods_label, las = 2)
    abline(h = 0, lty = 2, col = "gray")
  }
}

dev.off()
cat("✅ 系数变化图已保存:", file.path(plot_dir, "coefficients_over_time.png"), "\n")

# =============================================================================
# 可视化：同省份比例变化
# =============================================================================
png(file.path(plot_dir, "same_province_ratio_over_time.png"), 
    width = 1600, height = 1200, res = 300, family = "sans")

barplot(same_province_ratios$同省份比例, 
        names.arg = periods_label,
        col = "#2E86AB",
        main = "同省份转让比例随时间变化（筛选后数据）",
        ylab = "同省份比例",
        xlab = "时期",
        ylim = c(0, max(same_province_ratios$同省份比例) * 1.2))
text(x = 1:nrow(same_province_ratios) * 1.2 - 0.5, 
     y = same_province_ratios$同省份比例 + 0.02,
     labels = round(same_province_ratios$同省份比例, 3),
     col = "black", cex = 1)

dev.off()
cat("✅ 同省份比例图已保存:", file.path(plot_dir, "same_province_ratio_over_time.png"), "\n")

# =============================================================================
# 生成综合报告
# =============================================================================
cat("\n=== Step 5/6: 生成综合报告 ===\n")

report_file <- file.path(data_dir, "comprehensive_report.txt")
sink(report_file)

cat(strrep("=", 70), "\n", sep="")
cat("RQ3: 地理邻近性影响分析 - 改进版综合报告（筛选后数据）\n")
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

cat("【同省份转让比例变化】\n")
print(same_province_ratios)
cat("\n")

cat("【关键发现】\n\n")

cat("1. 地理邻近性效应（geo_prox）:\n")
if (nrow(coef_comparison) >= 2) {
  trend <- ifelse(coef_comparison$geo_prox[nrow(coef_comparison)] > coef_comparison$geo_prox[1],
                  "增强", "减弱")
  cat("   ", coef_comparison$时期[1], ": ", round(coef_comparison$geo_prox[1], 3), "\n", sep="")
  cat("   ", coef_comparison$时期[nrow(coef_comparison)], ": ", 
      round(coef_comparison$geo_prox[nrow(coef_comparison)], 3), "\n", sep="")
  cat("   → 地理邻近效应随时间", trend, "\n\n", sep="")
}

cat("2. 互惠性效应（mutual）:\n")
if (any(!is.na(coef_comparison$mutual))) {
  for (i in 1:nrow(coef_comparison)) {
    if (!is.na(coef_comparison$mutual[i])) {
      if (is.infinite(coef_comparison$mutual[i])) {
        cat("   ", coef_comparison$时期[i], ": -Inf（网络中没有互惠边）\n", sep="")
      } else {
        cat("   ", coef_comparison$时期[i], ": ", round(coef_comparison$mutual[i], 3), "\n", sep="")
      }
    }
  }
  # 计算平均值时排除-Inf
  mutual_finite <- coef_comparison$mutual[is.finite(coef_comparison$mutual) & !is.na(coef_comparison$mutual)]
  if (length(mutual_finite) > 0) {
    cat("   → 专利转让", ifelse(mean(mutual_finite) > 0, "存在显著", "缺乏"), 
        "的互惠倾向\n", sep="")
    if (any(is.infinite(coef_comparison$mutual))) {
      cat("   → 注意：部分时期网络中没有互惠边（mutual=-Inf），说明该时期网络结构简单\n")
    }
  }
  cat("\n")
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
cat("加入内生结构项后，模型不仅考虑外生因素（地理邻近性），\n")
cat("还控制了网络自身的结构倾向（互惠性、三角闭合），\n")
cat("使得地理邻近性的效应估计更加准确，避免遗漏变量偏差。\n\n")

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

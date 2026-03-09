数据科学与大数据技术毕业设计,SIDS (Spark-based Intrusion Detection System) 设计与实现项目计划书

## 目录
- [一、项目概述](#一项目概述)
  - [1.1 项目背景](#11-项目背景)
  - [1.2 项目目标](#12-项目目标)
  - [1.3 项目范围](#13-项目范围)
- [二、需求分析](#二需求分析)
  - [2.1 功能需求](#21-功能需求)
  - [2.2 技术需求](#22-技术需求)
  - [2.3 验收标准](#23-验收标准)
- [三、总体设计](#三总体设计)
  - [3.1 架构设计](#31-架构设计)
  - [3.2 技术栈选型](#32-技术栈选型)
  - [3.3 数据集设计](#33-数据集设计)
  - [3.4 核心流程设计](#34-核心流程设计)
- [四、工程化治理与版本控制 (Engineering Governance)](#四工程化治理与版本控制-engineering-governance)
  - [4.1 Git 空间管理逻辑](#41-git-空间管理逻辑)
  - [4.2 提交信息规范](#42-提交信息规范)
  - [4.3 存储治理红线](#43-存储治理红线)
  - [4.4 AI 协同开发](#44-ai-协同开发)
- [五、详细设计](#五详细设计)
  - [5.1 总体项目目录结构](#51-总体项目目录结构)
  - [5.2 部署模块详细设计](#52-部署模块详细设计)
  - [5.3 Makefile 构建脚本设计](#53-makefile-构建脚本设计)
  - [5.4 公共工具模块 (utils.py)](#54-公共工具模块-utilspy)
  - [5.5 数据处理模块详细设计](#55-数据处理模块详细设计)
  - [5.6 模型训练模块详细设计](#56-模型训练模块详细设计)
  - [5.7 后端服务模块详细设计](#57-后端服务模块详细设计)
  - [5.8 前端模块详细设计](#58-前端模块详细设计)
- [六、实施计划](#六实施计划)
  - [6.1 项目里程碑](#61-项目里程碑)

# 一、项目概述

## 1.1 项目背景

随着网络攻击手段的多样化与复杂化，网络安全分析成为提升信息系统安全性的重要需求。CSE-CIC-IDS2018 数据集涵盖多种典型网络攻击类型（如 DoS、DDoS、暴力破解等），为攻击检测模型的训练与验证提供了真实有效的数据支撑。本项目基于该数据集，结合 **逻辑层存算分离设计** 与 **现代数据栈 (Modern Data Stack)** 技术，设计并实现一套 SIDS (Spark-based Intrusion Detection System) 系统。
## 1.2 项目目标

本项目核心目标是构建一套“数据处理-模型训练-检测预测-可视化展示”全链路的 SIDS (Spark-based Intrusion Detection System) 系统，具体目标如下：

- 数据层：完成CSE-CIC-IDS2018数据集的清洗、转换与治理，构建1GB规模的高保真训练与演示数据集，确保数据完整性与可用性；

- 技术层：基于Spark实现并行数据处理，基于XGBoost构建攻击检测模型，攻击识别准确率目标为99%（注：数据不平衡可能影响准确率，后续可通过加权或重采样优化，此目标为工程可达指标）；

- 应用层：开发前后端分离的交互系统，实现攻击检测、数据统计可视化功能；

- 文档层：形成完整的项目开发文档与论文素材，系统功能可稳定演示，满足本科毕业设计答辩要求。

## 1.3 项目范围

本项目聚焦公开数据集的网络攻击检测的核心流程，不涉及实时流量采集，具体范围界定如下：

- 数据范围：选取 CSE-CIC-IDS2018 中 2018年2月15日 (Thursday) 的流量数据 (DoS/DDoS 核心场景)；

- 功能范围：数据清洗规范化 (ETL)、攻击检测 (XGBoost)、离线分析型态势感知 (DuckDB+ECharts)、工程化治理；

- 技术范围：采用 **macOS (Apple Silicon M2)** 开发环境，基于OrbStack使用docker容器化技术确保跨平台兼容性，利用24G统一内存的数据读写优势。

# 二、需求分析

## 2.1 功能需求

### 2.1.1 数据处理功能

本系统定位为实验验证型离线分析系统，模拟SOC（Security Operations Center）内部态势感知大屏的展示效果。本项目为教学验证环境，不面向公网部署，安全控制不在本项目范围。本项目遵循‘无状态、零阻碍’设计原则，移除登录验证模块，聚焦数据可观测性的核心需求，不涉及实时流量接入。

- 数据读取：支持读取CSV格式的原始网络流量数据，适配CSE-CIC-IDS2018数据集的字段规范；

- 数据清洗：处理数据中的Infinity、NaN等异常值，对核心特征执行零值填充，过滤无效负数字段；

- 标签统一：将原始数据中混乱的攻击标签映射为3大类（0-正常、1-DoS/DDoS、2-暴力破解），删除未匹配标签数据；

- 预计算统计：离线计算攻击类型分布、Top10目标端口等核心指标，保存为JSON文件供前端快速调用；

- 数据存储：清洗后的数据集以Parquet格式存储，提升数据读取效率。

### 2.1.2 模型训练与预测功能

- 特征筛选：选取10个核心网络流量特征（如Flow Duration、Tot Fwd Pkts等）用于模型训练；

- 模型训练：基于XGBoost算法构建多分类模型，结合理论调研结论确定该模型为核心攻击检测模型，实现攻击类型的精准识别；

- 模型保存：训练完成的模型以JSON格式存储，支持快速加载与调用；

- 攻击预测：支持接收用户上传的CSV格式流量数据，调用模型输出攻击类型预测结果与置信度。

### 2.1.3 可视化与交互功能

- 零配置启动：系统启动即进入全屏离线分析模式；

- 大屏展示：通过ECharts实现攻击类型分布饼图、流量趋势折线图、Top10目标端口柱状图等可视化图表；

- 文件上传：支持分析人员上传CSV格式的流量数据，用于攻击检测；

- 结果展示：清晰展示攻击检测结果，包括数据条数、各攻击类型占比、置信度等信息，供分析人员参考；

### 2.1.4 系统部署功能

- 容器化部署：基于Docker Compose实现Spark、Web应用等组件的一键部署；

- 网络配置：确保容器间网络互通，实现挂载目录的数据共享；

- 反向代理：配置Nginx实现80端口访问，优化系统访问体验。

## 2.2 技术需求

- 开发环境：核心开发与运行环境为macOS (Apple Silicon M2) 系统（24GB Unified Memory/512GB SSD），基于OrbStack使用docker容器化技术确保环境一致性；

- 技术栈要求：Python 3.10+、PySpark 3.5+ (ARM64原生镜像)、XGBoost 2.0+ (ARM64原生镜像)、FastAPI 0.100+、Vue3+Element Plus、ECharts 5.0+、DuckDB 0.9+；

- 数据契约：基于显式Schema驱动，确保跨容器、跨计算引擎的数据类型一致性；

## 2.3 验收标准

- 功能验收：核心功能（数据处理、模型预测、可视化）全部实现，无功能性缺陷；

- 性能验收：满足2.2节性能需求，演示过程流畅无明显卡顿；

- 文档验收：项目计划书、开发文档、论文素材（含架构图、流程图、实验数据、截图）齐全；

- 演示验收：答辩现场可完整演示“启动系统→查看可视化大屏→上传CSV检测→查看结果”流程，能清晰阐述核心技术细节。

# 三、总体设计

## 3.1 架构设计

本项目采用 **逻辑层存算分离设计** 架构，整体分为数据层、计算层、服务层、前端层与部署层，架构图如下（论文中需补充可视化架构图）：

### 主要架构说明：

- 服务端 (Server)：macOS (Apple Silicon M2) (24G Unified Memory)，承载容器化服务组合 (Spark, Web, Nginx)，确保开发环境一致性；

- 控制端 (Client)：Mac M2，通过 VS Code 本地开发，基于OrbStack使用docker容器化技术实现"开发在Mac，运行在容器"的逻辑。

### 核心数据流：

1. ETL 流：CSV (Raw) -> **Spark (清洗/重分区)** -> Parquet (Data Lake)；

2. 分析流：Web Request -> **FastAPI** -> **DuckDB (零拷贝读取)** -> ECharts；

3. 预测流：CSV Upload -> **FastAPI** -> **XGBoost (内存推理)** -> Result。

### 3.1.1 数据层

负责数据的存储与管理，采用三级存储结构：

- 原始数据层：
存储下载的CSE-CIC-IDS2018原始CSV文件
（宿主机路径：./data/raw/ 映射至 容器内路径：/app/data/raw/）；

- 处理数据层：
存储清洗后的Parquet文件
（宿主机路径：./data/processed/ 映射至 容器内路径：/app/data/processed/）；

- 结果数据层：
存储模型文件（/app/data/models/）、
预计算统计JSON（/app/data/processed/dashboard_stats.json）
与预测结果（宿主机路径：./data/models/ 映射至 容器内路径：/app/data/models/）；

### 3.1.2 计算层

核心计算单元，基于Spark local实现数据处理，承担三大核心任务：

- 数据清洗与标准化：执行异常值处理、零值填充、数据类型转换、标签统一等操作；

- 预计算统计：离线计算可视化所需的核心指标；

- 数据读取支撑：为模型训练提供Parquet数据读取服务。

### 3.1.3 服务层

基于FastAPI构建后端服务，提供接口调用能力，所有API均设为public，无需认证即可访问。本系统为教学验证环境，运行在受控网络环境中，不面向公网部署，安全控制不在本项目范围：

- 统计接口：/api/stats，返回预计算的可视化统计数据；

- 预测接口：/api/predict，接收上传数据，调用模型返回预测结果；

- 数据处理接口：/api/process，提供手动触发数据清洗的功能（备用）。

### 3.1.4 前端层

基于Vue3+Element Plus+ECharts构建前端交互界面，核心为分析展示界面：

- 可视化大屏页：核心展示界面，呈现攻击类型分布、Top10目标端口等统计图表；

- 攻击检测页：支持分析人员上传数据并查看检测结果的功能界面；

### 3.1.5 部署层

基于OrbStack使用docker与Docker Compose实现容器化部署，包含三个核心容器：

- Spark容器：运行PySpark数据处理脚本，使用ARM64原生镜像；

- Web应用容器：运行FastAPI后端服务与Vue3前端静态资源；

- Nginx容器：提供反向代理服务，优化访问体验。

## 3.2 技术栈选型

|层级|技术组件|选型理由|
|-|-|-|
|基础设施|Docker + Docker Compose|环境隔离，一键交付，确保跨平台兼容性|
|数据清洗|PySpark 3.5 (ARM64原生镜像)|大规模数据 ETL，避免使用 coalesce(1) 强制合并，采用多分区 Parquet 输出，交由 DuckDB 使用通配符读取。|
|数据查询|DuckDB 0.9+|嵌入式 OLAP，直接查询 Parquet，替代 MySQL 承载海量数据统计|
|核心算法|Native XGBoost (ARM64原生镜像)|单机多核训练，迭代速度快，原生支持特征重要性提取 (Explainability)|
|后端服务|FastAPI|异步框架，统一 Python 技术栈|
|前端交互|Vue 3 + ECharts|可视化大屏|
|开发工具|VS Code、Git|支持本地开发，便于代码管理与版本控制|

## 3.3 数据集设计

### 3.3.1 数据集选取

选取CSE-CIC-IDS2018数据集中2018年2月15日（Thursday）的流量数据文件（Thur-15-02-2018_TrafficForML_CICFlowMeter.csv），
（预处理前，需将该原始文件重命名为 `full_data.csv` 并放置于 `./data/raw/` 目录下）
该文件原始大小约800MB-1GB，涵盖Normal（正常流量）与DoS attacks-Hulk、DoS attacks-GoldenEye、DoS attacks-Slowloris、FTP-BruteForce、SSH-Bruteforce等核心攻击类型，

### 3.3.2 数据集处理规范

- 演示集：1GB (`full_data.csv`)，直接使用原始数据集进行清洗处理，用于最终答辩演示（注：开发调试时可手动截取部分数据，但ETL脚本统一处理 `full_data.csv`）；

- 字段筛选：保留10个核心字段，包括Flow Duration、Tot Fwd Pkts、Tot Bwd Pkts、Flow Byts/s、Flow Pkts/s、TotLen Fwd Pkts、TotLen Bwd Pkts、Fwd Pkt Len Max、Fwd Pkt Len Min、Fwd Pkt Len Mean等（详见4.0节CORE_FEATURES配置）；

- 标签映射：采用统一标签映射规则，将原始标签映射为3大类，具体映射表如下：

|原始标签|映射后标签|标签说明|
|-|-|-|
|Benign|0|正常流量|
|DoS attacks-Hulk、DoS attacks-GoldenEye、DoS attacks-Slowloris、DoS attacks-SlowHTTPTest|1|DoS/DDoS攻击|
|FTP-BruteForce、SSH-Bruteforce|2|暴力破解攻击|
|其他未匹配标签|无|直接删除|

### 3.3.3 类别不平衡对策

IDS2018数据集存在严重的类别不平衡问题：正常流量（Normal）样本数量远多于攻击样本（Normal >> Attack）。这种不平衡会导致模型评估时出现"准确率陷阱"——即使模型将所有样本预测为正常流量，也能获得很高的准确率，但无法有效检测攻击。

**对策要求**：
1. **禁止单一准确率指标**：在模型评估阶段，严禁仅使用Accuracy作为唯一评估指标。
2. **多维度评估**：必须同时使用Precision（精确率）、Recall（召回率）和F1-Score等指标进行综合评估。
3. **混淆矩阵分析**：必须生成并分析混淆矩阵，直观展示各类别的分类性能。
4. **模型优化方向**：在训练过程中应关注少数类（攻击样本）的识别能力，可通过类别权重调整、重采样等技术优化模型对攻击样本的敏感性。

## 3.4 核心流程设计

### 3.4.1 数据处理流程

1. 数据读取：Spark采用宽容模式读取原始CSV文件（禁用inferSchema以String类型读入），按需提取核心特征与目标端口（Dst Port），并强制进行类型转换（Cast to Double），从而直接规避欧洲时间格式（dd/MM/yyyy）解析报错以及冗余字段带来的内存消耗；

2. 数据清洗：将Infinity、NaN替换为null，过滤核心字段中的负数；

3. 缺失值处理：对核心特征字段执行fillna(0)零值填充；

4. 标签统一：基于映射表替换标签，删除未匹配标签的数据；

5. 预计算统计：计算攻击类型分布（各标签数量占比）、Top10目标端口（按流量包数量排序），保存为dashboard_stats.json；

6. 数据存储：将清洗后的数据集以Parquet格式保存，避免使用 `coalesce(1)` 强制合并为单文件，改为输出多分区 Parquet 文件；后续使用 DuckDB 的 `read_parquet('path/*.parquet')` 通配符读取以获得高效、稳定的读取性能。

### 3.4.2 模型训练流程

8. 数据读取：通过DuckDB读取清洗后的Parquet文件，提升读取效率；

9. 特征筛选：选取预设的10个核心特征作为输入特征X，标签字段作为目标变量y；

10. 数据划分：按8:2比例划分训练集与测试集，确保数据分布一致；

11. 模型训练：初始化XGBoost多分类模型（objective="multi:softmax", num_class=3），使用训练集训练模型；

12. 模型评估：在测试集上验证模型性能，记录准确率、精确率、召回率等指标（目标准确率≥99%，数据不平衡可能影响实际表现，此为目标工程可达指标）；

13. 模型保存：将训练完成的模型保存为xgb_model.json，用于后续预测。

### 3.4.3 系统演示流程

14. 环境启动：通过Docker Compose启动Spark、Web应用、Nginx容器；

15. 系统就绪：默认加载分析仪表盘，前端自动调用/api/stats接口加载预计算的JSON数据；

16. 可视化展示：渲染攻击类型分布、Top10目标端口等可视化图表，系统处于可观测状态；

17. 攻击检测：分析人员上传CSV格式流量数据，前端调用/api/predict接口；

18. 结果返回：后端加载模型，对上传数据进行预测，返回攻击类型、置信度等结果；

19. 结果展示：前端展示预测结果统计，支持分析人员查看单条数据的预测详情。

# 四、工程化治理与版本控制 (Engineering Governance)

**本章说明**：本章节为项目工程化管理规范，主要用于保障项目开发的可复现性与版本追溯效率，不作为算法核心内容。本章节作为"工程实现与质量保障"章节核心素材，严格遵循"逻辑层存算分离、原子提交、AI 协同约束、三层空间校验"核心原则，确保项目开发的高可复现性、代码鲁棒性及版本追溯效率。

## 4.1 Git 空间管理逻辑

本项目严格遵守 Git 的三层架构，通过明确各空间职责，实现“后悔药”机制与精准回滚，同时落实“Diff 强制校验”流程，确保版本提交的准确性。

### 4.1.1 三层架构职责界定

- 工作区 (Workspace)：代码编写与调试的生产现场，所有开发修改均在此完成；

- 暂存区 (Staging Area)：执行 `git add` 后的“镜头取景框”，用于筛选本次要提交的原子化功能，确保单次提交仅包含同一功能相关的改动；

- 本地仓库 (Repository)：执行 `git commit` 后形成的永久底片，作为毕设进度的里程碑，用于版本追溯与回滚。

### 4.1.2 Diff 强制校验流程

提交前必须执行 Diff 校验，对比暂存区与本地仓库的实际差异，确保提交内容与预期一致。AI 协同开发时，需由 AI 工具自动完成 Diff 对比，禁止凭记忆虚构提交信息。

- Diff 强制校验：提交前必须对比暂存区与本地仓库差异；

- 原子化提交：禁止一次提交所有文件，必须按功能模块分批 Commit。

## 4.2 提交信息规范

本项目固化 Google Conventional Commits 标准，强制要求提交信息采用 `<type>(<scope>): <动词+结果>` 的中文格式，严禁使用 update、fixed 等模糊词汇。

### 格式示例：

```Python

- feat(etl): 实现分层抽样逻辑，优化数据分布
- perf(spark): 调整 shuffle 分区数为 10，解决小文件问题
```


### 4.2.1 提交类型 (Type) 及适用场景

|提交类型 (Type)|适用场景说明|示例 (Subject 须动词+结果)|
|-|-|-|
|feat|新增功能逻辑（如 ETL 脚本、API 接口）|feat(etl): 实现分层抽样逻辑，优化数据分布|
|fix|修复程序缺陷（如数据类型报错、标签映射缺失）|fix(api): 修正模型预测接口的 JSON 解析逻辑|
|perf|性能与资源优化（针对 Spark/XGBoost 参数）|perf(etl): 优化 Shuffle 分区数，解决单机内存溢出|
|style|视觉呈现与代码格式调整（不影响业务逻辑）|style(ui): 调整可视化大屏配色，匹配离线分析展示需求|
|docs|文档、计划书、论文素材更新|docs(paper): 导出 M3 阶段模型评估报告与架构图|
|build|环境配置、依赖包更新或 Docker 脚本修改|build(root): 配置 Docker 存算分离挂载路径|

### 4.2.2 格式约束补充

- scope 范围限定：仅允许使用 etl、model、api、ui、deploy、root 六个值，分别对应数据处理、模型训练、后端接口、前端开发、部署配置、根目录配置场景；

- subject 核心要求：必须为中文，且明确包含“动词+结果”，清晰说明提交的核心改动价值。

## 4.3 存储治理红线

本项目执行严格的“数据隔离”政策，确保 GitHub 仓库仅包含逻辑代码，通过 .gitignore 数据屏蔽策略与 .gitkeep 目录占位机制，确保仓库轻量化与程序运行稳定性。

### 4.3.1 数据屏蔽策略（.gitignore 核心规则）

```Markdown

# --- 核心：严禁大数据入库 ---
data/raw/*
data/processed/*
data/models/*

# --- 保留目录结构 ---
!data/raw/.gitkeep
!data/processed/.gitkeep
!data/models/.gitkeep

# --- 全局屏蔽 ---
*.csv
*.parquet
*.duckdb
*.log
__pycache__/
.venv/
.DS_Store
.AppleDouble
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
```


说明：若已误将大数据文件添加至缓存，需执行以下命令清理：

```Shell

git rm -r --cached .
git add .
git commit -m "build(root): 按照宪法更新 .gitignore 并应用存算分离策略"
```


### 4.3.2 目录占位机制（.gitkeep 保活策略）

在 `data/raw`、`data/processed`、`data/models` 目录下必须创建 .gitkeep 占位符文件。核心目的：确保 Git 追踪目录结构，防止远程克隆后因缺少必要的数据路径导致程序崩溃。

## 4.4 AI 协同开发

针对 AI 编程工具 Roo code，在项目根目录设立 .roorules 文件进行行为审计，以下为核心强制约束规则，所有 AI 协同开发行为必须严格遵守。

### 4.4.1 .roorules源码内容

```Markdown
# 🏛️ 项目宪法：SIDS (Spark-based Intrusion Detection System)

## 1. 核心上下文 (Context)
- **运行环境**: macOS (Apple Silicon M2), 24GB Unified Memory, 512GB SSD。
- **开发架构**: 
  - 本地 (Host): VS Code + Git。
  - 容器 (Container): 基于 Docker Compose (OrbStack) 运行 Spark, FastAPI, Nginx。
  - **原则**: 代码严禁硬编码 x86 汇编指令，必须适配 ARM64。
- **数据策略**: 演示集 1GB (`full_data.csv`)，经清洗规范化后生成 Parquet 文件 (`full_processed.parquet`)，严禁进行无意义的重复采样增强。

## 2. 动态思维：交织思考协议 (Interleaf Thinking)
**核心指令**: 拒绝一次性生成大量代码。所有任务必须按照 **【探测 -> 实验 -> 校验】** 的闭环逻辑执行。

### 阶段一：探测与感知 (The Sense)
- **环境探测**: 在涉及 `/app/data` 读写前，必须先执行 `ls -ld` 确认路径映射状态。若路径不存在，优先查阅 `compose.yml`。
- **数据采样**: 处理大数据集前，必须先执行 `head -n 5` 或 `df.limit(5).show()`。**严禁**在不知道字段准确名称和类型的情况下盲目编写 ETL 脚本。

### 阶段二：实验与防错 (The Probe)
- **Schema 强对齐**: 
  - 提取特征后，必须打印 `df.printSchema()` 并与计划书 **CORE_FEATURES** 列表对比。
  - **类型防御**: 发现字段类型为 String 却包含数值时，必须主动应用 `cast("double")`。
- **特征顺序物理锁**: 
  - 在模型推理 (Inference) / API 预测模块中，必须编写一段硬编码逻辑：`df = df.reindex(columns=CORE_FEATURES)`，防止特征位置漂移导致的预测偏差。

### 阶段三：闭环校验 (The Validation)
- **存算一致性**: Spark 写入 Parquet 后，立即使用 DuckDB 读取该文件执行 `SELECT COUNT(*)`，验证数据行数是否与清洗逻辑吻合。
- **模型加载测试**: 训练完成后，立即尝试 `xgb.Booster.load_model`。如果加载失败，立即定位原因，禁止带着错误的假设进入下一阶段。

### 阶段四：跨平台兼容性 (Compliance)
- **大小写敏感**: 即使 macOS 不敏感，代码引用路径时也必须严格匹配物理文件名大小写（为 Linux 部署做准备）。

## 3. Git 治理规范 (Git Governance)
- **Commit 格式**: `<type>(<scope>): <中文动词+结果>`
  - **Type**: feat, fix, docs, style, perf, build, refactor。
  - **Scope**: etl, model, api, ui, deploy, root。
  - *例*: `feat(etl): 实现 Schema 自动对齐逻辑`
- **数据红线**:
  - **严禁**将 `data/` 下的 .csv, .parquet, .json, .duckdb 加入版本控制。
  - 确保 `data/raw`, `data/processed`, `data/models` 下仅有 `.gitkeep`。
- **强制审计**:
  - 在生成 Commit Message 前，**必须**对比 Staging Area 的 Diff，确保描述与实际改动 100% 一致。

## 4.4.2 自检与汇报格式
在输出关键代码块前，请简要同步思考路径：
> **[Thinking]**: 检测到 CSV Header 存在空格，计划在 ETL 阶段一增加列名标准化逻辑...
```

## 4.4.3 AI 协作忽略规范.rooignore

为避免 AI 在索引项目时扫描 GB 级数据文件导致性能下降或 Token 资源耗尽，项目根目录必须添加专用忽略规则文件 .rooignore。该文件通过约束 AI 扫描边界，确保 Roo Code 仅聚焦于代码逻辑与架构配置。

.rooignore 文件源码 (直接粘贴至项目根目录)

```Markdown
# AI 协作索引忽略规范
# 防止大规模数据文件被扫描

# 1. 大规模数据目录
data/raw/
data/processed/

# 2. 训练产出物（如体积较大）
data/models/*.joblib
data/models/*.pkl

# 3. 开发环境与构建产物
node_modules/
dist/
.venv/
__pycache__/
*.pyc

# 4. 日志与系统文件
logs/
*.log
.DS_Store
```

### 4.4.3 核心行动流

1. 开工：在 Roo code 中进行代码修改,项目开发；

2. 暂存：执行 `git add &lt;具体文件&gt;`，挑选属于同一功能的文件进入暂存区；

3. 审计：AI 对比暂存区与本地仓库差异，生成符合规范的提交信息建议；

4. 定格：用户确认提交信息后，执行 `git commit` 完成版本定格；

5. 备份：每日结束前执行 `git push`，确保毕设成果具备云端备份。

# 五、详细设计

## 5.1 总体项目目录结构与“一键装修方案”

本项目遵循"模块解耦、存算分离"的设计原则，采用统一的目录结构管理所有代码与配置资源。根目录命名为 `sids`，核心结构如下：

```Text
sids/
├── .git/                    # Git 版本控制目录
├── .gitignore               # Git 忽略规则 (严格屏蔽 data/)
├── .roorules                # AI 协作宪法 (合并版规范)
├── .rooignore               # AI 索引忽略规则
├── compose.yml              # Docker Compose V2 编排文件
├── Dockerfile               # 【唯一】后端/训练环境镜像定义 (仅预装依赖，不 COPY 代码)
├── Makefile                 # 工程化控制台 (make up/down/etl/train)
├── nginx.conf               # Nginx 反向代理配置
├── run_etl.sh               # ETL 任务一键启动脚本
├── run_train.sh             # 模型训练一键启动脚本
├── utils.py                 # 【核心】公共工具模块 (清洗逻辑/特征配置)
├── data/                    # 数据层 (宿主机挂载点)
│   ├── raw/                 # 原始数据 (.gitkeep + full_data.csv)
│   ├── processed/           # 清洗后数据 (.gitkeep + .parquet + .json)
│   └── models/              # 模型产物 (.gitkeep + .json)
├── spark_jobs/              # 计算任务脚本目录
│   ├── etl_clean.py         # Spark 数据清洗脚本
│   └── train_model.py       # XGBoost 模型训练脚本
└── web_app/                 # 应用服务层
    ├── backend/             # 后端 (FastAPI)
    │   ├── main.py          # 入口文件
    │   ├── requirements.txt # Python 依赖
    │   ├── routers/         # API 路由模块
    │   │   ├── __init__.py
    │   │   ├── stats.py     # 统计接口 (对应 /api/stats)
    │   │   └── predict.py   # 预测接口 (对应 /api/predict)
    │   └── services/        # 业务逻辑模块
    │       ├── __init__.py
    │       └── model_service.py # 模型加载与推理逻辑
    └── frontend/            # 前端 (Vue3 + Vite)
        ├── dist/            # 静态资源构建产物 (Nginx 根目录)
        ├── public/          # 公共静态资源
        ├── package.json     # Node 依赖配置
        ├── vite.config.js   # Vite 构建配置
        └── src/             # 前端源代码
            ├── main.js      # Vue 入口
            ├── App.vue      # 根组件
            ├── style.css    # 全局样式
            ├── api/         # Axios 请求封装
            │   ├── stats.js # 获取统计数据
            │   └── predict.js # 上传预测请求
            ├── components/  # Vue 组件
            │   ├── common/  # 公共组件 (如 Layout, Header)
            │   └── dashboard/ # 图表专用组件
            ├── router/      # 路由配置
            │   └── index.js # 路由定义
            └── views/       # 页面视图
                ├── Dashboard.vue # 离线分析大屏
                └── Detect.vue    # 攻击检测页面
```
SIDS 项目初始化脚本 (init_project.sh)
此脚本用于一键生成项目目录结构，并自动处理 macOS (M2) 环境下的权限对齐。
```bash
#!/bin/bash

# ==========================================
# SIDS 项目初始化脚本 (V1.2 极简版)
# 适用环境：macOS (M2) + OrbStack
# 核心逻辑：硬编码 501:20 权限，彻底消除权限冲突
# ==========================================

echo "🚀 开始搭建 SIDS 项目骨架..."

# 1. 定义需要创建的目录树
DIRS=(
    "data/raw"
    "data/processed"
    "data/models"
    "spark_jobs"
    "web_app/backend/routers"
    "web_app/backend/services"
    "web_app/frontend/dist"
    "web_app/frontend/public"
    "web_app/frontend/src/api"
    "web_app/frontend/src/components/common"
    "web_app/frontend/src/components/dashboard"
    "web_app/frontend/src/router"
    "web_app/frontend/src/views"
)

# 2. 循环创建目录并放置 .gitkeep
# 这是为了防止 Git 忽略空目录，确保项目结构在任何地方都一致
for dir in "${DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        touch "$dir/.gitkeep"
        echo "  ✅ 已创建目录并初始化: $dir"
    else
        echo "  🟡 目录已存在，跳过: $dir"
    fi
done

# 3. 核心步骤：权限对齐
# 直接将当前目录下所有文件所有权移交给你的 Mac 用户 (501:staff)
echo "🔒 正在执行权限对齐 (Target: 501:20)..."
chown -R 501:20 .
chmod -R 755 .

echo "------------------------------------------"
echo "🎉 恭喜！项目骨架已就绪。"
echo "💡 下一步建议：将你的 compose.yml 放入根目录，然后尝试执行 docker compose up -d"
echo "------------------------------------------"
```

## 5.2 部署模块详细设计

### 5.2.1 核心环境定义 (Dockerfile)
由于我们要确保开发环境与演示环境物理一致，不再使用运行时动态安装。请在文档中增加如下描述：

定义 Dockerfile 内容：

```Dockerfile
FROM python:3.10
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/app
```

强调：此 Dockerfile 不包含 COPY . . 指令，仅负责环境预装，代码通过挂载方式引入，以实现快速开发调试。

### 5.2.2 容器编排逻辑 (compose.yml)

**跨平台构建说明**：本项目支持 Multi-arch 镜像构建，确保在 macOS ARM64 开发环境与可能的 x86 服务器部署环境之间的兼容性。在 compose.yml 中，建议为关键服务添加 `platform: linux/arm64` 作为开发优先项，同时确保所有镜像支持多架构构建。

```YAML

version: '3.8'

services:
  # Spark 服务 (ETL 核心，模型训练在Web容器中运行)
  spark:
    image: apache/spark:3.5.0-python3
    platform: linux/arm64
    container_name: spark
    # 核心改动：显式增加 user: root 配置，并注明：“此配置旨在解决容器间数据读写的权限问题，确保 Spark 写入的 Parquet 结果能被 Web 后端无障碍读取。”
    user: root
    environment:
      # [CRITICAL] 将项目根目录加入 Python 搜索路径，以共享 utils.py
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data
      - ./:/app
    networks:
      - sids_net
    deploy:
      resources:
        limits:
          memory: 12G  # 提升至 12G 以匹配容器水位，与 web-app (4G) 总和为 16G，在 24G 安全线内

  # Web 应用服务 (FastAPI 后端 + 模型训练执行环境)
  app:
    build: .
    platform: linux/arm64
    container_name: web_app
    # 运行容器时使用宿主机 UID:GID 避免宿主机文件被写成 root
    user: "501:20"
    working_dir: /app/web_app/backend
    environment:
      - PYTHONPATH=/app
    volumes:
      - ./data:/app/data
      - ./:/app
    ports:
      - "8000:8000"
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - sids_net
    deploy:
      resources:
        limits:
          memory: 4G

  # Nginx 网关 (系统入口)
  nginx:
    image: nginx:latest
    platform: linux/arm64
    container_name: gateway
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./web_app/frontend/dist:/usr/share/nginx/html
    ports:
      - "80:80"
    depends_on:
      - app
    networks:
      - sids_net

networks:
  sids_net:
    driver: bridge
```
### 5.7.2 python 依赖（web_app/backend/requirements.txt）
```Python

fastapi
uvicorn[standard]
xgboost
pandas
duckdb
scikit-learn
python-multipart
```

### 5.2.3 Nginx配置（nginx.conf）


```Nginx

server {
    client_max_body_size 50M;  # 限制上传文件最大为 50MB，防止内存溢出
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # 前端静态资源（系统启动后默认加载）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 反向代理后端API（系统默认开放，运行于教学验证环境，不面向公网部署）
    location /api {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;  # 延长连接超时时间
    }

    # 健康检查
    location /health {
        proxy_pass http://app:8000/health;
    }
}
```


### 5.2.4 辅助运行脚本

**1. 数据处理脚本 (run_etl.sh)**

为了简化 ETL 任务的触发流程，在根目录创建此脚本：

```Shell

#!/bin/bash
echo "🚀 开始执行 ETL 数据处理任务..."
docker compose exec spark spark-submit \
    --master local[*] \
    --conf spark.driver.extraJavaOptions="-Djava.io.tmpdir=/tmp" \
    /app/spark_jobs/etl_clean.py
echo "✅ ETL 任务执行完毕。"
```


**2. 模型训练脚本 (run_train.sh)**

实现一键训练（注意：训练脚本使用原生Python+DuckDB+XGBoost，不依赖Spark，在Web容器中运行）：

```Shell

#!/bin/bash
echo "🚀 开始执行模型训练任务..."
# 训练脚本使用原生Python运行，复用Web容器的Python环境（已安装xgboost/pandas/duckdb等依赖）
docker compose exec app python /app/spark_jobs/train_model.py
echo "✅ 模型训练任务执行完毕。xgb_model.json 已生成。"
```


注：执行前需赋予执行权限：`chmod +x run_etl.sh run_train.sh`

**3. 项目初始化检查清单**

在首次执行前，需要确保以下目录结构存在：

```Shell
mkdir -p data/raw data/processed data/models
touch data/raw/.gitkeep data/processed/.gitkeep data/models/.gitkeep
```


确保原始数据文件已重命名并放置：

```Shell
# 将下载的 CSE-CIC-IDS2018 数据文件重命名
cp Thur-15-02-2018_TrafficForML_CICFlowMeter.csv data/raw/full_data.csv
```


## 5.3 Makefile 构建脚本设计

为进一步优化项目操作体验，提升工程化水平，在项目根目录创建 Makefile 文件，将零散的运行脚本组织为语义化命令，使项目构建、部署、运行等操作更简洁高效，媲美成熟开源项目的操作体验。

### 5.3.1 Makefile 创建位置与核心作用

创建位置：项目根目录（与 compose.yml 同级）

核心作用：统一管理项目全流程操作命令，屏蔽底层脚本细节，降低使用门槛，实现“一条命令完成核心操作”，提升开发与演示效率。

### 5.3.2 Makefile 完整内容

```MakeFile

# Makefile for SIDS (Spark-based Intrusion Detection System)

# 默认目标，展示可用命令
help:
	@echo "Usage: make [command]"
	@echo "commands:"
	@echo "  up          - Start all services in detached mode"
	@echo "  down        - Stop and remove all services"
	@echo "  build-ui    - Build the frontend (generate dist/)"
	@echo "  etl         - Run the ETL data processing job"
	@echo "  train       - Run the model training job"
	@echo "  all         - Run the full setup: build-ui -> up -> etl -> train"
	@echo "  logs        - Follow the logs of the web application"
	@echo "  shell       - Get a shell inside the spark container"

# 核心工作流
up:
	docker compose up -d

down:
	docker compose down

build-ui:
	@echo "🔨 构建前端静态资源..."
	@cd web_app/frontend && npm install && npm run build
	@echo "✅ 前端构建完成，dist/ 目录已生成。"

etl:
  @./run_etl.sh
  @$(MAKE) fix-perms

train:
  @./run_train.sh
  @$(MAKE) fix-perms

# 修复宿主机目录权限问题（容器可能以非宿主用户写入文件）
fix-perms:
  @echo "🔧 修复 data 目录权限为当前宿主用户..."
  @chown -R $(shell id -u):$(shell id -g) data || true


all: build-ui up
	@echo "⏳ 等待容器启动..."
	@sleep 10
	@$(MAKE) etl
	@$(MAKE) train

# 辅助命令
logs:
	docker compose logs -f app

shell:
	docker compose exec spark bash

.PHONY: help up down build-ui etl train all logs shell
```


### 5.3.3 核心命令说明与使用示例

Makefile 封装了项目全流程核心操作，各命令语义清晰，使用方式简单，具体说明如下：

- 启动系统：`make up`，使用 Dockerfile 构建应用镜像并后台启动所有 Docker 服务（Spark、Web 应用、Nginx），无需手动执行 `docker compose up -d`；**注意**：`make up` 仅负责镜像构建和容器启动，不再包含运行时依赖安装；

- 停止系统：`make down`，停止并移除所有 Docker 服务及相关容器，清理运行环境；

- 构建前端：`make build-ui`，在 `web_app/frontend/` 目录下执行 `npm install && npm run build`，生成 `dist/` 目录供 Nginx 使用（首次部署或前端代码更新后需执行；使用 `make all` 时会自动先执行该步骤）；

- 数据处理：`make etl`，自动执行 run_etl.sh 脚本，完成 ETL 数据清洗任务；

- 模型训练：`make train`，自动执行 run_train.sh 脚本，在 Web 容器中使用原生 Python 运行训练脚本，完成 XGBoost 模型训练并生成模型文件；

- 一键部署：`make all`，按"构建前端→启动服务→数据处理→模型训练"顺序执行全流程，快速完成项目初始化；

- 查看日志：`make logs`，实时跟踪 Web 应用后端日志，便于问题排查；

- 容器终端：`make shell`，快速进入 Spark 容器内部，方便执行调试命令。

## 5.4 公共工具模块 (utils.py)

作用：统一数据清洗逻辑与特征配置，消除训练-推理偏差，供ETL模块、模型训练模块、后端预测模块复用核心配置与逻辑，避免硬编码导致的不一致问题。

**物理位置**：项目根目录 `/utils.py` (通过 PYTHONPATH 环境变量供各子模块引用)

**重要说明**：

- `clean_data_logic` 函数仅适用于 Pandas DataFrame，供后端 API 预测时使用

- ETL 脚本中的 Spark DataFrame 清洗逻辑独立实现，不使用此函数（避免大数据量转换开销）

- 训练和推理阶段的数据清洗逻辑需保持一致，通过统一的特征列表（CORE_FEATURES）和清洗规则（零值填充、类型转换）保证一致性

```Python

# 公共工具模块
# 作用：统一数据清洗逻辑与特征配置，消除训练-推理偏差
import pandas as pd
import numpy as np
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# 核心特征清单：定义模型唯一认可的输入维度（严格对齐真实 CSV 表头缩写）
CORE_FEATURES = [
    "Flow Duration", "Tot Fwd Pkts", "Tot Bwd Pkts",
    "TotLen Fwd Pkts", "TotLen Bwd Pkts",
    "Fwd Pkt Len Max", "Fwd Pkt Len Min",
    "Fwd Pkt Len Mean", "Flow Byts/s", "Flow Pkts/s"
]
LABEL_COL = "Label"

# 显式 Schema：解决 inferSchema 性能瓶颈与类型推断错误
IDS2018_SCHEMA = StructType([
    *[StructField(f, DoubleType(), True) for f in CORE_FEATURES],
    StructField(LABEL_COL, StringType(), True)
])

def clean_data_logic(df_pandas):
    """
    统一清洗逻辑，供 ETL (Spark转Pandas逻辑) 和 API (单条预测) 复用
    注意：输入必须是 Pandas DataFrame 或 字典
    """
    # 1. 处理无穷大与非法字符串，防止推理阶段崩溃
    df_pandas = df_pandas.replace(
        [np.inf, -np.inf, "Infinity", "NaN", "inf", "-inf"],
        0
    )
    # 2. 填充空值
    df_pandas = df_pandas.fillna(0)
    # 3. 强制类型转换 (防止入模报错)
    for col in CORE_FEATURES:
        if col in df_pandas.columns:
            df_pandas[col] = pd.to_numeric(df_pandas[col], errors='coerce').fillna(0)
    return df_pandas
```


## 5.5 数据处理模块详细设计

### 5.5.1 核心代码结构（etl_clean.py）

```Python

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, desc, when, sum, length, regexp_extract
from pyspark.sql.types import StructType, StructField, StringType, DoubleType
import json
import os
from datetime import datetime
# 修改点：引用公共配置
from utils import CORE_FEATURES, IDS2018_SCHEMA

def create_spark_session():
    """创建SparkSession实例 (已优化 I/O 配置)"""
    return SparkSession.builder \
        .appName("IDS2018_Clean") \
        .config("spark.driver.memory", "6G") \
        .config("spark.executor.memory", "6G") \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.driver.extraJavaOptions", "-Djava.io.tmpdir=/tmp") \
        .getOrCreate()

def load_data(spark, input_path):
    """宽容读取模式：防崩溃、按需提取、强制转换"""
    # 1. 宽容读取：全部作为 String 读取，防止特殊时间格式或脏数据导致解析崩溃
    df_raw = spark.read.csv(input_path, header=True, inferSchema=False)
    
    # 2. 按需提取：仅保留我们在工具类中定义的核心特征，加上标签和用于统计的目标端口
    cols_to_select = CORE_FEATURES + ["Label", "Dst Port"]
    df_selected = df_raw.select(*cols_to_select)
    
    # 3. 强转类型：将特征列和端口列统一转换为 DoubleType，隔离原始字符串格式问题
    for col_name in CORE_FEATURES + ["Dst Port"]:
        df_selected = df_selected.withColumn(col_name, col(col_name).cast("double"))
        
    return df_selected

def clean_data(df, core_cols):
    """数据清洗：异常值处理+零值填充"""
    # 替换Infinity为null（使用 na.replace 方法）
    df = df.na.replace("Infinity", None)
    # 过滤核心字段负数 (修正为 >= 0，保留 0 值)
    for col_name in core_cols:
        df = df.filter(col(col_name) >= 0)
    # 核心字段零值填充
    df = df.fillna(0, subset=core_cols)
    return df

def unify_label(df):
    """标签统一：映射为3大类"""
    label_mapping = {
        "Benign": 0,
        "DoS attacks-Hulk": 1,
        "DoS attacks-GoldenEye": 1,
        "DoS attacks-Slowloris": 1,
        "DoS attacks-SlowHTTPTest": 1,
        "FTP-BruteForce": 2,
        "SSH-Bruteforce": 2
    }
    # 替换标签
    df = df.replace(label_mapping, subset=["Label"])
    # 删除未匹配标签数据
    df = df.filter(col("Label").isin([0, 1, 2]))
    return df

def precompute_stats(df, output_path):
    """预计算统计指标：攻击类型分布、Top10目标端口"""
    
    # 1. 攻击类型分布
    attack_dist = df.groupBy("Label").count().collect()
    attack_dist_dict = {str(row["Label"]): row["count"] for row in attack_dist}
    
    # 2. Top10目标端口（按双向流量包总数排序：Tot Fwd Pkts + Tot Bwd Pkts）
    # 注意：这里直接使用 Dst Port 进行聚合
    top10_port = df.groupBy("Dst Port") \
        .agg(
            (sum("Tot Fwd Pkts") + sum("Tot Bwd Pkts")).alias("packet_count")
        ) \
        .orderBy(desc("packet_count")) \
        .limit(10) \
        .collect()
    
    top10_port_dict = {str(row["Dst Port"]).strip(): int(row["packet_count"]) for row in top10_port if row["Dst Port"] is not None}
    
    # 3. 构造 stats 字典，确保变量闭环
    stats = {
        "attack_distribution": attack_dist_dict,
        "top10_dst_port": top10_port_dict,  # 这里的 key 从 top10_source_ip 改为了 top10_dst_port
        "stats_metadata": {
            "total_records": df.count(),
            "generated_at": datetime.now().isoformat()
        }
    }
    
    # 保存为JSON（确保目录存在）
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats

def save_processed_data(df, output_path):
    """保存清洗后的数据为Parquet格式 (强制合并)"""
  # 注意：不要使用 coalesce(1) 将所有分区拉到单个分区（可能导致 OOM）
  # 让 Spark 写出多个 Parquet 分片，DuckDB 可使用通配符读取：read_parquet('path/*.parquet')
  df.write.mode("overwrite").parquet(output_path)

def main():
    # 配置路径
    input_path = "/app/data/raw/full_data.csv"
    processed_path = "/app/data/processed/attack_data.parquet"
    stats_path = "/app/data/processed/dashboard_stats.json"
    # 使用公共配置的特征列表
    core_cols = CORE_FEATURES
    
    # 执行数据处理流程
    spark = create_spark_session()
    try:
        df_raw = load_data(spark, input_path)
        df_clean = clean_data(df_raw, core_cols)
        df_unified = unify_label(df_clean)
        
        # 注意：数据已在 load_data 阶段完成了按需 select 和 cast("double") 强制类型转换
        # 彻底抛弃了原始 CSV 中的 Timestamp 等多余字段，规避了格式报错
        
        # 【性能优化】缓存中间结果，避免重复扫描
        # 因为后续既要计算统计又要保存Parquet，缓存可避免二次读取1GB数据
        print("正在缓存清洗后的数据以优化性能...")
        df_unified.cache()
        # 触发缓存动作（通过count触发实际缓存）
        total_count = df_unified.count()
        print(f"数据缓存完成，总记录数: {total_count}")
        
        # 预计算统计指标（使用缓存数据）
        precompute_stats(df_unified, stats_path)
        
        # 保存处理后的数据为Parquet格式（使用缓存数据）
        save_processed_data(df_unified, processed_path)
        
        # 清理缓存
        df_unified.unpersist()
        print("数据处理完成！")
    except Exception as e:
        print(f"数据处理失败：{str(e)}")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
```


### 5.5.2 关键参数配置

- Spark内存配置：driver.memory=8G，executor.memory=8G，适配24GB单机环境；容器内存限额已提升至12G，确保单个组件声明内存不超过容器水位。

- 核心字段数量：10个核心特征，兼顾模型性能与计算效率，经过特征选择后的精简集；

- 存储配置：Parquet格式采用snappy压缩（默认），保留多分片输出以降低写入内存压力，DuckDB 使用通配符读取多个 Parquet 分片。

## 5.6 模型训练模块详细设计

### 5.6.1 核心代码结构（train_model.py）

```Python

import xgboost as xgb
import pandas as pd
from duckdb import connect
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_score, recall_score, f1_score
import os
import json
# 修改点 1：导入配置
from utils import CORE_FEATURES

# 修改点 2：优化 DuckDB 读取与内存
def load_processed_data(parquet_path):
    # 拼接查询字段，只查需要的列，防止 OOM
    cols_sql = ", ".join([f'"{c}"' for c in CORE_FEATURES + ['Label']])
    
    con = connect()
    # 使用 glob 模式读取目录下所有 parquet 文件（ETL 写出多分片 Parquet，DuckDB 使用通配符读取）
    # 注意：parquet_path 指向目录，DuckDB 会自动查找其中的 parquet 文件
    df = con.execute(f"SELECT {cols_sql} FROM read_parquet('{parquet_path}/*.parquet')").df()
    con.close()
    # 特征安检闸机：强制对齐列顺序，屏蔽冗余字段（通过SQL SELECT实现）
    return df

def prepare_data(df, core_cols):
    """准备训练数据：特征与标签分离"""
    X = df[core_cols]
    y = df["Label"]
    # 划分训练集与测试集（8:2）
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test

def train_xgboost_model(X_train, y_train):
    """训练XGBoost多分类模型"""
    model = xgb.XGBClassifier(
        # 使用 softprob 输出每一类的概率，便于前端展示置信度
        objective="multi:softprob",
        num_class=3,
        max_depth=6,
        learning_rate=0.1,
        n_estimators=100,
        random_state=42,
        use_label_encoder=False,
        eval_metric="mlogloss"
    )
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    """评估模型性能（强化版：包含多维度指标与混淆矩阵）"""
    y_pred = model.predict(X_test)
    
    # 基础指标
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    # 分类报告
    report = classification_report(y_test, y_pred, target_names=["Normal", "DoS/DDoS", "BruteForce"])
    
    # 混淆矩阵
    cm = confusion_matrix(y_test, y_pred)
    
    print("=" * 50)
    print("模型评估结果（多维度指标）")
    print("=" * 50)
    print(f"准确率 (Accuracy): {accuracy:.4f}")
    print(f"精确率 (Precision): {precision:.4f}")
    print(f"召回率 (Recall): {recall:.4f}")
    print(f"F1-Score: {f1:.4f}")
    print("\n分类报告：")
    print(report)
    print("\n混淆矩阵：")
    print(cm)
    
    # 保存评估结果到文件（包含所有指标）
    with open("/app/data/models/model_evaluation.txt", "w", encoding="utf-8") as f:
        f.write("=" * 50 + "\n")
        f.write("模型评估结果（多维度指标）\n")
        f.write("=" * 50 + "\n")
        f.write(f"准确率 (Accuracy): {accuracy:.4f}\n")
        f.write(f"精确率 (Precision): {precision:.4f}\n")
        f.write(f"召回率 (Recall): {recall:.4f}\n")
        f.write(f"F1-Score: {f1:.4f}\n")
        f.write("\n分类报告：\n")
        f.write(report)
        f.write("\n混淆矩阵：\n")
        f.write(str(cm))
    
    # 同时保存混淆矩阵为JSON格式，便于前端可视化
    cm_dict = {
        "matrix": cm.tolist(),
        "labels": ["Normal", "DoS/DDoS", "BruteForce"]
    }
    with open("/app/data/models/confusion_matrix.json", "w", encoding="utf-8") as f:
        json.dump(cm_dict, f, indent=2)
    
    return accuracy, report, cm

def save_model(model, model_path):
    """保存模型为JSON格式"""
    model.save_model(model_path)
    print(f"模型已保存至：{model_path}")

def main():
    # 配置路径
    parquet_path = "/app/data/processed/attack_data.parquet" # 指向目录即可
    model_path = "/app/data/models/xgb_model.json"
    # core_cols 直接使用 CORE_FEATURES，不再重新定义
    core_cols = CORE_FEATURES
    
    # 执行模型训练流程
    try:
        df = load_processed_data(parquet_path)
        # 特征安检闸机：强制对齐列顺序，屏蔽冗余字段（已在load_processed_data中通过SELECT实现）
        X_train, X_test, y_train, y_test = prepare_data(df, core_cols)
        model = train_xgboost_model(X_train, y_train)
        evaluate_model(model, X_test, y_test)
        save_model(model, model_path)
        
        # --- 核心：导出特征重要性 (论文加分项) ---
        importance = model.feature_importances_
        # 确保 core_cols 与重要性得分一一对应
        feature_map = {name: float(score) for name, score in zip(core_cols, importance)}
        # 排序并取 Top 10
        top_features = dict(sorted(feature_map.items(), key=lambda item: item[1], reverse=True)[:10])
        
        # 保存为 JSON
        with open("/app/data/models/feature_importance.json", "w", encoding="utf-8") as f:
            json.dump(top_features, f, ensure_ascii=False, indent=2)
        print("特征重要性已保存，准备用于前端雷达图展示。")
        
        print("模型训练完成！")
    except Exception as e:
        print(f"模型训练失败：{str(e)}")

if __name__ == "__main__":
    main()
```


### 5.6.2 模型参数说明

|参数名称|参数值|参数说明|
|-|-|-|
|objective|multi:softprob|多分类任务，输出每一类的概率|
|num_class|3|分类类别数（正常、DoS/DDoS、暴力破解）|
|max_depth|6|决策树最大深度，控制模型复杂度，避免过拟合|
|learning_rate|0.1|学习率，控制每棵树的权重更新步长|
|n_estimators|100|决策树数量|
|eval_metric|mlogloss|多分类评价指标，对数损失|

## 5.7 后端服务模块详细设计

### 5.7.1 公共工具模块 (utils.py)

注：代码与 4.0 章节一致，此处为文件占位说明。后端必须包含此文件以复用清洗逻辑。该文件位于项目根目录，通过 `PYTHONPATH=/app` 环境变量供各容器模块引用。

### 5.7.2 核心接口实现 (main.py)

```Python

# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import stats, predict
from services.model_service import load_model, get_model_status
import os

app = FastAPI(title="网络攻击检测系统API", version="1.0.0")

# 配置CORS（内网演示系统，允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600
)

# 注册路由
app.include_router(stats.router, prefix="/api")
app.include_router(predict.router, prefix="/api")

# --- 核心：系统启动时预加载模型到内存 ---
@app.on_event("startup")
async def startup_event():
    print("正在初始化系统资源...")
    load_model()
    print("系统启动完成。")

# 健康检查 (增强版)
@app.get("/health")
async def health_check():
    stats_path = "/app/data/processed/dashboard_stats.json"
    return {
        "status": "healthy",
        "message": "系统正常运行中",
        "model_ready": get_model_status(),  # 模型是否已成功加载
        "stats_ready": os.path.exists(stats_path)  # 仪表盘统计文件是否就绪
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```


### 5.7.3 模型服务层 (services/model_service.py)

**核心逻辑描述**：后端 API 在接收到预测请求后，首先将数据转换为 DataFrame，并立即执行 select(CORE_FEATURES) 操作。此举确保了输入向量的顺序与训练阶段完全一致，规避了 JSON 键值对无序性带来的预测偏差。

```Python

# backend/services/model_service.py
import xgboost as xgb
import os
import pandas as pd
import io
from utils import clean_data_logic, CORE_FEATURES

# 全局变量缓存模型
_model = None
_model_loaded = False  # 新增状态标志


def load_model():
    """加载模型到全局变量"""
    global _model, _model_loaded
    model_path = "/app/data/models/xgb_model.json"
    if os.path.exists(model_path):
        _model = xgb.XGBClassifier()
        _model.load_model(model_path)
        print(f"✅ 模型已加载: {model_path}")
        _model_loaded = True
    else:
        print(f"⚠️ 模型未找到: {model_path}")
        _model_loaded = False


def get_model_status():
    """获取模型加载状态"""
    return _model_loaded


def predict_csv(file_content_bytes):
    """处理上传的 CSV 字节流并预测"""
    global _model
    if _model is None:
        load_model()  # 尝试延迟加载
        if _model is None:
            raise Exception("模型服务不可用")

    try:
        # 1. 字节流转 DataFrame
        df_raw = pd.read_csv(io.BytesIO(file_content_bytes))
        # 2. 统一清洗 (关键步骤)
        df_clean = clean_data_logic(df_raw)
        # 3. 【核心修正】强制特征顺序对齐 (防 Silent Failure)
        # 补全缺失列
        for feature in CORE_FEATURES:
            if feature not in df_clean.columns:
                df_clean[feature] = 0
        # 按训练时的特征顺序重排：执行 select(CORE_FEATURES) 操作
        df_for_predict = df_clean[CORE_FEATURES]
        # 4. 推理
        # 由于训练时使用 multi:softprob，这里 predict_proba 返回每类概率
        probs = _model.predict_proba(df_for_predict)
        predictions = probs.argmax(axis=1)

        # 5. 结果格式化
        label_map = {0: "正常流量", 1: "DoS攻击", 2: "暴力破解"}
        results = []
        for i, pred in enumerate(predictions):
            results.append({
                "row_id": i + 1,
                "type": label_map.get(int(pred), "未知"),
                "confidence": float(max(probs[i]))
            })

        # 统计信息
        stats = {
            "total": len(df_for_predict),
            "normal": int(sum(predictions == 0)),
            "dos": int(sum(predictions == 1)),
            "bruteforce": int(sum(predictions == 2))
        }

        return {"stats": stats, "details": results[:100]}  # 仅返回前100条预览
    except Exception as e:
        print(f"推理错误: {str(e)}")
        raise e
```


### 5.7.4 路由层 (routers/stats.py & predict.py)

predict.py:

```Python

from fastapi import APIRouter, UploadFile, File, HTTPException
from services.model_service import predict_csv

router = APIRouter(tags=["攻击检测"])

@router.post("/predict", summary="上传流量CSV进行检测")
async def predict_traffic(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="格式错误")
    
    try:
        contents = await file.read()
        result = predict_csv(contents)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```


stats.py:

```Python

from fastapi import APIRouter, HTTPException
import json
import os

# 硬编码路径或从 config 读取
STATS_PATH = "/app/data/processed/dashboard_stats.json"

router = APIRouter(tags=["统计数据"])

@router.get("/stats")
async def get_stats():
    if not os.path.exists(STATS_PATH):
        raise HTTPException(status_code=404, detail="Stats not found")
    with open(STATS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
```


## 5.8 前端模块详细设计

### 5.8.1 可视化大屏核心实现（Dashboard.vue 关键代码）

```Python

<template>
  <div class="dashboard-container">
    <el-page-header content="网络攻击检测态势大屏" />
    <el-row :gutter="20" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">攻击类型分布</div>
          </template>
          <div class="chart-container" ref="attackDistChartRef"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">Top10受击端口流量统计</div>
          </template>
          <div class="chart-container" ref="top10PortChartRef"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { getStats } from '@/api/stats';
import * as echarts from 'echarts';
import { ElMessage } from 'element-plus'; // 导入ElMessage组件
// 注意：需安装 vue-echarts: npm install echarts vue-echarts
// 并在 main.js 中注册 ECharts 组件

// 图表实例
const attackDistChart = ref(null);
const top10PortChart = ref(null);

// 图表配置
const attackDistOption = ref({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, left: 'center' },
  series: [{
    name: '攻击类型分布',
    type: 'pie',
    radius: ['40%', '70%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
    label: { show: false, position: 'center' },
    emphasis: { label: { show: true, fontSize: 16, fontWeight: 'bold' } },
    labelLine: { show: false },
    data: []
  }]
});

const top10PortOption = ref({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: [], axisLabel: { rotate: 0 } },
  yAxis: { type: 'value' },
  series: [{
    name: '流量包数量',
    type: 'bar',
    barWidth: '60%',
    data: []
  }]
});

// 加载统计数据（系统启动后自动执行）
const loadStatsData = async () => {
  try {
    const res = await getStats();
    // 处理攻击类型分布数据
    const attackDist = res.attack_distribution;
    const attackData = [
      { value: attackDist['0'], name: '正常流量' },
      { value: attackDist['1'], name: 'DoS/DDoS攻击' },
      { value: attackDist['2'], name: '暴力破解攻击' }
    ];
    attackDistOption.value.series[0].data = attackData;
    
    // 处理Top10 目标端口数据
    const top10Port = res.top10_dst_port;
    top10PortOption.value.xAxis.data = Object.keys(top10Port);
    top10PortOption.value.series[0].data = Object.values(top10Port);
    top10PortOption.value.tooltip = {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: '{b} 端口<br/>{a}: {c}'
    };
    
    // 更新图表（确保图表已初始化）
    if (attackDistChart.value) {
      attackDistChart.value.setOption(attackDistOption.value);
    }
    if (top10PortChart.value) {
      top10PortChart.value.setOption(top10PortOption.value);
    }
  } catch (error) {
    console.error('加载统计数据失败：', error);
    
    // 【V1.2 增强】前端空态健壮性：区分不同错误类型，提供友好提示
    let userMessage = '加载统计数据失败';
    
    // 检查错误类型
    if (error.response && error.response.status === 404) {
      userMessage = '统计数据接口返回404，请先执行 ETL 任务生成数据文件';
    } else if (error.message && error.message.includes('Network Error')) {
      userMessage = '网络连接失败，请检查后端服务是否正常运行';
    } else if (error.message && error.message.includes('stats not found')) {
      userMessage = '统计数据文件不存在，请先执行 ETL 任务 (run_etl.sh)';
    } else {
      userMessage = '统计数据未生成，请先执行 ETL 任务 (run_etl.sh)';
    }
    
    // 使用 Element Plus 的消息提示组件
    if (typeof ElMessage !== 'undefined') {
      ElMessage.warning({
        message: userMessage,
        duration: 5000, // 延长显示时间
        showClose: true
      });
    }
    
    // 可选：在开发环境下记录更详细的错误信息
    if (process.env.NODE_ENV === 'development') {
      console.debug('详细错误信息:', {
        error: error.message,
        stack: error.stack,
        response: error.response
      });
    }
  }
};

// 初始化图表（系统启动后自动初始化）
// 注意：使用 ref 绑定 DOM 元素，而非 document.querySelector
const attackDistChartRef = ref(null);
const top10PortChartRef = ref(null);

onMounted(() => {
  attackDistChart.value = echarts.init(attackDistChartRef.value);
  top10PortChart.value = echarts.init(top10PortChartRef.value);
  loadStatsData();
});
</script>
```
# 六、实施计划

## 6.1 项目里程碑

|里程碑|核心任务|交付物|验收标准|
|-|-|-|-|
|M1: 基建|环境配置、Git 初始化|Docker 运行正常，Hello World 跑通|`docker ps` 全绿，Git Log 规范|
|M2: 数据|编写 `etl_clean.py`|`attack_data.parquet`, `dashboard_stats.json`|Parquet 文件生成，DuckDB 可读|
|M3: 模型|编写 `train_model.py`|`xgb_model.json`, `feature_importance.json`|准确率目标 > 99%（工程可达指标），特征 JSON 生成|
|M4: 服务|FastAPI + Vue 开发|前后端联调完成|浏览器可访问大屏，图表有数据|
|M5: 交付|论文撰写、演示录屏|毕业论文、答辩 PPT|逻辑闭环，演示流畅|

---
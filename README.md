
# SIDS: Spark-based Intrusion Detection System
> **数据科学与大数据技术专业本科毕业设计落地项目**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PySpark](https://img.shields.io/badge/PySpark-3.5.0-orange.svg)](https://spark.apache.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0%2B-red.svg)](https://xgboost.readthedocs.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue.js-3.0-4FC08D.svg)](https://vuejs.org/)

---

## 📖 项目简介

随着网络攻击手段的日益复杂，基于机器学习的网络安全分析成为提升信息系统安全防御能力的关键路径。本项目基于真实权威的 **CSE-CIC-IDS2018** 网络流量数据集，设计并实现了一套端到端的网络入侵检测系统（SIDS）。

本项目不仅聚焦于算法模型的构建，更深度融合了**逻辑层存算分离架构**与**现代数据栈 (Modern Data Stack)** 的工程化理念，实现了从底层大规模海量数据治理 (ETL)、特征工程、机器学习建模分析，到高维数据可视化展示及离线流量预测的全链路闭环。

---

## 🏛️ 系统架构设计

系统严格遵循模块解耦原则，核心架构划分为四层：

* **数据计算层 (Data & Compute)**：采用 `PySpark` 应对初始海量异构 CSV 数据的并发读取与清洗，执行异常值处理与零值填充后，持久化为列式存储 `Parquet` 格式；引入轻量级嵌入式 OLAP 引擎 `DuckDB` 实现数据的零拷贝快速查询。
* **算法模型层 (Algorithm)**：基于特征重要性评估与业务调研，提取 15 个核心流量特征，采用 `XGBoost` 构建多分类模型，实现对正常流量、DoS/DDoS 攻击及暴力破解等行为的精准分类（基准准确率 >97%）。
* **后端服务层 (Backend)**：基于 `FastAPI` 构建异步非阻塞的 API 网关，负责模型内存加载、推理预测及统计数据下发。
* **前端交互层 (Frontend)**：采用 `Vue3 + Element Plus + ECharts` 构建态势感知与学术探索双屏，提供高度交互的数据可视化体验。

---

## ✨ 核心特性与学术贡献

1.  **高保真数据治理框架**
    * 实现了动态防御性 Schema 对齐，解决多批次原始数据集列错位问题。
    * 彻底清除 IEEE 754 标准带来的 `NaN`/`Infinity` 脏数据污染，构建了干净、标准化的特征集。
2.  **多维特征工程与可解释性 (XAI)**
    * 扩充至 15 个核心网络特征（涵盖前/后向包特征、流间隔时间特征等）。
    * 引入特征重要性分析（Feature Importance），提升模型在网安领域的透明度。
3.  **学术级 EDA 深度探索大屏**
    * **混淆矩阵热力图**：直观展示多分类模型在各攻击类别的判定效能。
    * **相关性热力图**：通过皮尔逊相关系数矩阵（Pearson Correlation），深度剖析特征间的多重共线性关系。
    * **特征分布箱线图**：从统计学维度呈现正常流量与异常流量的数据分布异同。
4.  **一键式敏捷工程部署**
    * 全面容器化 (`Docker Compose`)，保证开发、测试与演示环境的绝对物理一致。
    * 封装 `Makefile` 工程化脚本，提供专业的任务调度体验。

---

## 📁 核心工程目录

```text
sids/
├── data/                    # 存算分离：数据挂载层 (Raw / Processed / Models)
├── spark_jobs/              # 大数据计算脚本
│   ├── etl_clean.py         # 核心 ETL 与特征标准化逻辑
│   └── train_model.py       # 模型训练、评估与 EDA 数据生成逻辑
├── web_app/                 # 业务服务层
│   ├── backend/             # FastAPI 后端服务 (RESTful API)
│   └── frontend/            # Vue3 前端视图层 (Dashboard & EDA)
├── utils.py                 # 公共特征字典与跨容器清洗逻辑
├── compose.yml              # 容器编排定义
└── Makefile                 # 一键式构建与任务调度脚本
```

---

## 🚀 快速运行指南

项目环境已通过 Docker 深度隔离。请确保宿主机已安装 **Docker** 及 **Make** 工具。

```bash
# 1. 克隆项目并进入根目录
git clone <repository_url>
cd sids

# 2. 一键执行全链路流程 
# (包含: 构建前端 -> 启动集群 -> 运行 Spark ETL -> 训练 XGBoost 模型 -> 启动服务)
make all

# 单独执行指定任务参考：
# make up        # 仅启动基础容器服务
# make etl       # 触发 Spark 数据预处理任务
# make train     # 触发模型训练与学术数据生成任务
```

服务启动后，在浏览器访问 `http://localhost:80` 即可进入 SIDS 态势感知总览控制台。

---


**Disclaimer**: 本项目为大学本科学位毕业设计工程产物，仅供学术交流与演示验证使用，不作为工业级公网安全防护组件部署。

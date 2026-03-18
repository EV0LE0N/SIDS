import xgboost as xgb
import pandas as pd
import numpy as np
from duckdb import connect
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_score, recall_score, f1_score
import os
import json
# 修改点 1：导入配置与清洗逻辑
from utils import CORE_FEATURES, clean_data_logic

# 修改点 2：优化 DuckDB 读取与内存
def load_processed_data(parquet_path):
    # 拼接查询字段，只查需要的列，防止 OOM
    cols_sql = ", ".join([f'"{c}"' for c in CORE_FEATURES + ['Label']])
  
    con = connect()
    # 使用 glob 模式读取目录下所有 parquet 文件（ETL 写出多分片 Parquet，DuckDB 使用通配符读取）
    # 注意：parquet_path 指向目录，DuckDB 会自动查找其中的 parquet 文件
    df = con.execute(f"SELECT {cols_sql} FROM read_parquet('{parquet_path}/*.parquet')").df()
    con.close()
    
    # 【核心修复】：加上最终安全防线！调用 utils 中的清洗逻辑处理 inf 和 NaN
    # 彻底消除 Spark 遗留的 IEEE 754 脏数据，并保证与 API 推理环境 100% 对齐
    df = clean_data_logic(df)
    
    # 特征安检闸机：强制对齐列顺序，屏蔽冗余字段（通过SQL SELECT实现）
    return df

def prepare_data(df, core_cols):
    """准备训练数据：特征与标签分离"""
    X = df[core_cols]
    # 强制将标签转换为整型，防止 Spark Parquet 写入的字符串类型导致 XGBoost 训练崩溃
    y = df["Label"].astype(int)
  
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
        eval_metric="mlogloss"
    )
    model.fit(X_train, y_train)
    return model

def evaluate_model(model, X_test, y_test):
    """评估模型性能（强化版：包含多维度指标与混淆矩阵）"""
    y_pred = model.predict(X_test)
  
    # 【核心修复】：如果预测结果是二维概率矩阵，使用 argmax 转换为一维类别标签
    if y_pred.ndim > 1:
        y_pred = np.argmax(y_pred, axis=1)
        
    # 强制将 pandas Series 和 numpy Array 统一转为整型，防止底层类型冲突
    y_test_int = y_test.astype(int)
    y_pred_int = y_pred.astype(int)
  
    # 基础指标 (注意：后续全都要使用转换后的 y_test_int 和 y_pred_int)
    accuracy = accuracy_score(y_test_int, y_pred_int)
    precision = precision_score(y_test_int, y_pred_int, average='weighted', zero_division=0)
    recall = recall_score(y_test_int, y_pred_int, average='weighted', zero_division=0)
    f1 = f1_score(y_test_int, y_pred_int, average='weighted', zero_division=0)
  
    # 分类报告
    report = classification_report(y_test_int, y_pred_int, target_names=["Normal", "DoS/DDoS", "BruteForce"], zero_division=0)
  
    # 混淆矩阵
    cm = confusion_matrix(y_test_int, y_pred_int)
  
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
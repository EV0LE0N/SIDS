import xgboost as xgb
import pandas as pd
import numpy as np
from duckdb import connect
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_score, recall_score, f1_score
import os
import json
from utils import CORE_FEATURES, clean_data_logic

def load_processed_data(parquet_path):
    cols_sql = ", ".join([f'"{c}"' for c in CORE_FEATURES + ['Label']])
    con = connect()
    df = con.execute(f"SELECT {cols_sql} FROM read_parquet('{parquet_path}/*.parquet')").df()
    con.close()
    df = clean_data_logic(df)
    return df

def prepare_data(df, core_cols):
    X = df[core_cols]
    y = df["Label"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    return X_train, X_test, y_train, y_test

def train_xgboost_model(X_train, y_train):
    model = xgb.XGBClassifier(
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
    y_pred = model.predict(X_test)
    if y_pred.ndim > 1:
        y_pred = np.argmax(y_pred, axis=1)
        
    y_test_int = y_test.astype(int)
    y_pred_int = y_pred.astype(int)
  
    unique_classes = sorted(list(set(y_test_int) | set(y_pred_int)))
    label_map = {0: "Normal", 1: "DoS/DDoS", 2: "BruteForce"}
    dynamic_target_names = [label_map.get(c, f"Unknown-{c}") for c in unique_classes]
  
    accuracy = accuracy_score(y_test_int, y_pred_int)
    report = classification_report(y_test_int, y_pred_int, target_names=dynamic_target_names, zero_division=0)
    cm = confusion_matrix(y_test_int, y_pred_int)
  
    cm_dict = {
        "matrix": cm.tolist(),
        "labels": dynamic_target_names
    }
    with open("/app/data/models/confusion_matrix.json", "w", encoding="utf-8") as f:
        json.dump(cm_dict, f, indent=2)
  
    return accuracy, report, cm

def save_model(model, model_path):
    model.save_model(model_path)

def main():
    parquet_path = "/app/data/processed/attack_data.parquet"
    model_path = "/app/data/models/xgb_model.json"
    core_cols = CORE_FEATURES
  
    try:
        df = load_processed_data(parquet_path)
        X_train, X_test, y_train, y_test = prepare_data(df, core_cols)
        model = train_xgboost_model(X_train, y_train)
        evaluate_model(model, X_test, y_test)
        save_model(model, model_path)
      
        # 生成特征重要性
        importance = model.feature_importances_
        feature_map = {name: float(score) for name, score in zip(core_cols, importance)}
        top_features = dict(sorted(feature_map.items(), key=lambda item: item[1], reverse=True)[:10])
        with open("/app/data/models/feature_importance.json", "w", encoding="utf-8") as f:
            json.dump(top_features, f, ensure_ascii=False, indent=2)
        
        # 生成 EDA 学术图表数据
        df_test = X_test.copy()
        df_test['Label'] = y_test
        
        sampled_df = pd.DataFrame()
        for label in df_test['Label'].unique():
            subset = df_test[df_test['Label'] == label]
            if len(subset) > 500:
                subset = subset.sample(n=500, random_state=42)
            sampled_df = pd.concat([sampled_df, subset])
        
        corr_matrix = sampled_df[core_cols].corr().fillna(0).round(3)
        
        eda_data = {
            "scatter_data": sampled_df[["Flow Pkts/s", "Flow Byts/s", "Label"]].values.tolist(),
            "boxplot_data": {
                "normal": sampled_df[sampled_df['Label'] == 0]["Fwd Pkt Len Max"].tolist(),
                "dos": sampled_df[sampled_df['Label'] == 1]["Fwd Pkt Len Max"].tolist(),
                "bruteforce": sampled_df[sampled_df['Label'] == 2]["Fwd Pkt Len Max"].tolist(),
            },
            "correlation_matrix": {
                "features": core_cols,
                "values": corr_matrix.values.tolist()
            }
        }
        
        with open("/app/data/models/eda_sample.json", "w", encoding="utf-8") as f:
            json.dump(eda_data, f, ensure_ascii=False)
            
    except Exception as e:
        print(f"模型训练失败：{str(e)}")

if __name__ == "__main__":
    main()
# backend/services/model_service.py
import xgboost as xgb
import os
import pandas as pd
import io
# 注意：模块导入通过 PYTHONPATH=/app 环境变量保证，无需 sys.path.append
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

        # 5. 追加聚合计算逻辑
        
        # attack_distribution
        attack_distribution = {
            "0": int((predictions == 0).sum()),
            "1": int((predictions == 1).sum()),
            "2": int((predictions == 2).sum())
        }
        
        # top10_dst_port
        top10_dst_port = {}
        if "Dst Port" in df_raw.columns:
            # 统计并取前10，将浮点数端口（如 80.0）转为整型字符串
            port_counts = df_raw["Dst Port"].value_counts().head(10)
            top10_dst_port = {str(int(float(k))): int(v) for k, v in port_counts.items()}
            
        # radar_data
        # 提取模型认为比较重要的前 6 个特征（可固化配置）
        radar_features = ["Tot Bwd Pkts", "Flow Pkts/s", "TotLen Bwd Pkts", "Fwd Pkt Len Mean", "Flow Duration", "Tot Fwd Pkts"]
        # 确保这些特征在数据集中
        radar_features = [f for f in radar_features if f in df_for_predict.columns]
        
        radar_data = {
            "features": radar_features,
            "normal": [],
            "dos": [],
            "bruteforce": []
        }
        
        df_for_radar = df_for_predict.copy()
        df_for_radar["predicted_label"] = predictions
        
        for label, key in [(0, "normal"), (1, "dos"), (2, "bruteforce")]:
            subset = df_for_radar[df_for_radar["predicted_label"] == label]
            if len(subset) > 0:
                radar_data[key] = subset[radar_features].mean().fillna(0).round(4).tolist()
            else:
                radar_data[key] = [0.0] * len(radar_features)

        # 6. 结果格式化
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
            "normal": attack_distribution["0"],
            "dos": attack_distribution["1"],
            "bruteforce": attack_distribution["2"]
        }

        # 新的返回契约
        return {
            "stats": stats,
            "attack_distribution": attack_distribution,
            "top10_dst_port": top10_dst_port,
            "radar_data": radar_data,
            "details": results[:100]
        }
    except Exception as e:
        print(f"推理错误: {str(e)}")
        raise e
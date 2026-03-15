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
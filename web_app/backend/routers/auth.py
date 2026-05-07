from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    username: str

@router.post("/auth/login", response_model=LoginResponse, summary="管理员登录")
async def login(request: LoginRequest):
    # 极简预置管理员账号
    if request.username == "admin" and request.password == "admin123":
        # 生成一个伪造的 JWT 格式 token（满足毕设要求即可，避免引入额外依赖）
        # 头部: {"alg": "HS256", "typ": "JWT"} -> eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
        # 负载: {"sub": "admin", "exp": 9999999999} -> eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.dummy_signature_for_academic_defense"
        return LoginResponse(token=token, username="admin")
    
    raise HTTPException(status_code=401, detail="用户名或密码错误")

# routers/assets.py
# 终端节点管理 API — 封闭局域网环境中的节点 CRUD 与封禁/解封
#
# 职责：
#   1. 提供 50 个终端节点的增删改查接口
#   2. 为后续态势大屏的地图可视化提供经纬度数据源
#   3. 支持节点封禁/解封操作，构成 告警 → 封禁 → 解封 的安全治理闭环
#
# 世界观：
#   这 50 个节点就是整个封闭局域网的全部终端（如校园网内的 50 台电脑）。
#   所有流量（正常或攻击）均源自这些节点，不存在"外部攻击者"概念。
#   某台终端发起异常攻击时，系统可一键封禁该终端。

import logging
import json
import os
import random
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# 内存节点数据库（轻量级实现，满足答辩 CRUD 需求）
# =============================================================================

# 中国主要城市的经纬度池，用于初始化探针节点
_CITY_POOL = [
    {"city": "北京", "lng": 116.407, "lat": 39.904},
    {"city": "上海", "lng": 121.474, "lat": 31.230},
    {"city": "广州", "lng": 113.264, "lat": 23.129},
    {"city": "深圳", "lng": 114.058, "lat": 22.543},
    {"city": "杭州", "lng": 120.155, "lat": 30.274},
    {"city": "南京", "lng": 118.797, "lat": 32.060},
    {"city": "成都", "lng": 104.066, "lat": 30.573},
    {"city": "武汉", "lng": 114.305, "lat": 30.593},
    {"city": "西安", "lng": 108.940, "lat": 34.341},
    {"city": "重庆", "lng": 106.551, "lat": 29.563},
    {"city": "天津", "lng": 117.190, "lat": 39.125},
    {"city": "苏州", "lng": 120.585, "lat": 31.299},
    {"city": "郑州", "lng": 113.665, "lat": 34.757},
    {"city": "长沙", "lng": 112.938, "lat": 28.228},
    {"city": "青岛", "lng": 120.383, "lat": 36.067},
    {"city": "大连", "lng": 121.614, "lat": 38.914},
    {"city": "厦门", "lng": 118.089, "lat": 24.479},
    {"city": "合肥", "lng": 117.227, "lat": 31.821},
    {"city": "济南", "lng": 117.120, "lat": 36.651},
    {"city": "福州", "lng": 119.296, "lat": 26.074},
    {"city": "昆明", "lng": 102.832, "lat": 25.040},
    {"city": "哈尔滨", "lng": 126.534, "lat": 45.803},
    {"city": "沈阳", "lng": 123.432, "lat": 41.805},
    {"city": "长春", "lng": 125.323, "lat": 43.817},
    {"city": "南宁", "lng": 108.320, "lat": 22.824},
    {"city": "贵阳", "lng": 106.630, "lat": 26.647},
    {"city": "兰州", "lng": 103.834, "lat": 36.061},
    {"city": "太原", "lng": 112.549, "lat": 37.870},
    {"city": "石家庄", "lng": 114.514, "lat": 38.042},
    {"city": "乌鲁木齐", "lng": 87.617, "lat": 43.793},
]

# 服务器角色名称池
_ROLE_POOL = [
    "Web网关", "核心数据库", "邮件服务器", "DNS解析", "防火墙",
    "负载均衡", "文件服务器", "API网关", "日志收集", "备份服务器",
    "VPN网关", "认证中心", "监控节点", "缓存服务器", "应用服务器",
]

# 责任人池
_OWNER_POOL = ["张伟", "李娜", "王芳", "刘洋", "陈磊", "赵静", "孙鹏", "周强"]


def _generate_seed_nodes(count: int = 50) -> list[dict]:
    """生成初始化种子节点数据，IP 为确定性分配的 192.168.1.{1-50}"""
    nodes = []
    for i in range(count):
        city_info = _CITY_POOL[i % len(_CITY_POOL)]
        role = _ROLE_POOL[i % len(_ROLE_POOL)]
        nodes.append({
            "id": f"N-{i+1:03d}",
            "node_name": f"{city_info['city']}-{role}",
            "owner": random.choice(_OWNER_POOL),
            "ip_address": f"192.168.1.{i+1}",
            "location": city_info["city"],
            "lng": city_info["lng"] + random.uniform(-0.5, 0.5),
            "lat": city_info["lat"] + random.uniform(-0.5, 0.5),
            "status": "active",
        })
    return nodes


# 全局节点数据（内存存储）
_nodes: list[dict] = _generate_seed_nodes(50)

# 导出 IP 池，供回放引擎使用
NODE_IP_POOL: list[str] = [n["ip_address"] for n in _nodes]


# =============================================================================
# 请求/响应模型
# =============================================================================

class NodeUpdateRequest(BaseModel):
    """节点编辑请求"""
    node_name: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None


# =============================================================================
# 路由实现
# =============================================================================

@router.get(
    "/assets/nodes",
    summary="获取全部探针节点列表",
)
async def list_nodes(
    status: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """返回所有探针节点，支持按状态和关键词过滤"""
    result = _nodes

    if status:
        result = [n for n in result if n["status"] == status]

    if keyword:
        kw = keyword.lower()
        result = [
            n for n in result
            if kw in n["node_name"].lower()
            or kw in n["owner"].lower()
            or kw in n["ip_address"]
            or kw in n["location"].lower()
        ]

    return {"total": len(result), "nodes": result}


@router.get(
    "/assets/nodes/{node_id}",
    summary="获取单个探针节点详情",
)
async def get_node(node_id: str):
    """根据 ID 返回单个节点详情"""
    node = next((n for n in _nodes if n["id"] == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
    return node


@router.put(
    "/assets/nodes/{node_id}",
    summary="更新探针节点信息",
)
async def update_node(node_id: str, body: NodeUpdateRequest):
    """更新节点的名称、责任人或状态"""
    node = next((n for n in _nodes if n["id"] == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")

    if body.node_name is not None:
        node["node_name"] = body.node_name
    if body.owner is not None:
        node["owner"] = body.owner
    if body.status is not None:
        if body.status not in ("active", "blocked"):
            raise HTTPException(status_code=400, detail="status 只能是 'active' 或 'blocked'")
        node["status"] = body.status

    logger.info("节点更新 | id=%s | 变更: %s", node_id, body.dict(exclude_none=True))
    return {"message": "更新成功", "node": node}


@router.post(
    "/assets/nodes/{node_id}/block",
    summary="封禁探针节点",
)
async def block_node(node_id: str):
    """将指定节点状态设为封禁"""
    node = next((n for n in _nodes if n["id"] == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")

    node["status"] = "blocked"
    logger.info("节点已封禁 | id=%s | name=%s", node_id, node["node_name"])
    return {"message": f"节点 {node_id} 已封禁", "node": node}


@router.post(
    "/assets/nodes/{node_id}/unblock",
    summary="解封探针节点",
)
async def unblock_node(node_id: str):
    """将指定节点状态恢复为活跃"""
    node = next((n for n in _nodes if n["id"] == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")

    node["status"] = "active"
    logger.info("节点已解封 | id=%s | name=%s", node_id, node["node_name"])
    return {"message": f"节点 {node_id} 已解封", "node": node}


class BlockByIpRequest(BaseModel):
    """按 IP 封禁请求"""
    ip: str


@router.post(
    "/assets/block-by-ip",
    summary="按 IP 地址一键封禁终端节点（SOC 大屏专用）",
)
async def block_by_ip(body: BlockByIpRequest):
    """
    根据 IP 地址查找对应终端节点并执行封禁。
    在封闭局域网设定下，所有流量 IP 必定在 50 节点池内，不可能找不到。
    """
    target = next((n for n in _nodes if n["ip_address"] == body.ip), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"未找到 IP 为 {body.ip} 的终端节点")

    if target["status"] == "blocked":
        return {"message": f"节点 {target['id']} 已处于封禁状态", "node": target, "already_blocked": True}

    target["status"] = "blocked"
    logger.info("一键封禁终端 | ip=%s | id=%s | name=%s", body.ip, target["id"], target["node_name"])
    return {"message": f"节点 {target['id']}（{target['node_name']}）已封禁", "node": target, "already_blocked": False}

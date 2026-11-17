"""AI 助手相关请求/响应模型。

分层约定：
- /api/v1/ai/plan 只负责把一句中文需求解析成 smart_recommend 参数，不直接生成路线；
- /api/v1/ai/explain 只负责对已有路线做中文解说；
- 解析出的 params 字段名必须与 schemas/trip.py::SmartRecommendRequest 保持一致，
  前端可直接把 params 赋给表单后调用现有 /api/v1/trip/smart-recommend。
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List


class AIPlanRequest(BaseModel):
    """一句自然语言旅行需求。"""
    message: str = Field(..., description="中文自然语言需求描述")


class AIPlanParams(BaseModel):
    """与 SmartRecommendRequest 对齐的智能推荐参数子集（仅 6 个字段）。"""
    target_city: str = ""
    days: int = 2
    per_day: int = 3
    preferences: List[str] = Field(default_factory=list)
    travel_type: str = "单人出行"
    start_location: Optional[str] = None


class AIPlanResponse(BaseModel):
    """需求解析结果；degraded=true 表示模型不可用、已走关键词兜底。"""
    ok: bool
    degraded: bool
    reply: str
    missing: List[str] = Field(default_factory=list)
    params: AIPlanParams


class AIRouteSpot(BaseModel):
    """路线解说用的景点摘要。"""
    name: str
    day: Optional[int] = None
    price: Optional[float] = None


class AIRouteSummary(BaseModel):
    """路线摘要：由前端从 smart-recommend 响应中挑选传入。"""
    days: Optional[int] = None
    total_distance: Optional[float] = None
    tips: Optional[str] = None
    spots: List[AIRouteSpot] = Field(default_factory=list)


class AIExplainRequest(BaseModel):
    """路线解说请求：原始需求 + 路线摘要。"""
    message: str = Field(..., description="用户原始需求描述")
    route_summary: AIRouteSummary = Field(..., description="路线摘要数据")


class AIExplainResponse(BaseModel):
    """路线解说结果；degraded=true 时 note 为 None。"""
    ok: bool
    degraded: bool
    note: Optional[str] = None


class AgentPlanRequest(BaseModel):
    """Agent 对话请求：message 必填，session_id 用于多轮记忆。

    panel 为本轮前端面板参数（可选），用于偏好快照隔离：
    传了就以 panel 为准，旧轮次偏好不会覆盖本轮。
    """
    message: str = Field(..., description="用户当前这句话")
    session_id: Optional[str] = Field(None, description="会话 ID，首次为空由后端生成")
    panel: Optional[Dict[str, Any]] = Field(None, description="本轮面板参数快照，可选")


class AgentTraceItem(BaseModel):
    """一次工具调用记录，便于调试与答辩演示。"""
    step: int
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    summary: Optional[str] = None


class AgentPlanResponse(BaseModel):
    """Agent 结果：reply 为最终答复，route 为最后一次路线生成结果。

    self_check 为 critique_route 的完整返回（含分项得分与 summary），
    conflicts 为需求冲突预检测结果，便于前端做可视化提示。
    """
    session_id: str
    trace_id: Optional[str] = None
    reply: str
    route: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    trace: List[AgentTraceItem] = Field(default_factory=list)
    degraded: bool = False
    steps: int = 0
    tool_errors: List[str] = Field(default_factory=list)
    self_check: Optional[Dict[str, Any]] = None
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)


class AgentResetRequest(BaseModel):
    session_id: str


class SpotIntroRequest(BaseModel):
    """按景点名生成介绍文本（偏好面板直接生成路线后使用）。"""
    spot_names: List[str] = Field(default_factory=list)


class SpotIntroResponse(BaseModel):
    note: str = ""
    degraded: bool = False

"""AI 助手接口：自然语言需求解析 + 行程解说。

注意：本模块只做参数解析/解说，不生成路线；
前端拿到 /plan 的 params 后仍需调用现有 /api/v1/trip/smart-recommend。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.database import get_db
from models import User
from schemas.ai import (
    AIExplainRequest,
    AIExplainResponse,
    AIPlanRequest,
    AIPlanResponse,
)
from services import ai_agent

router = APIRouter()


@router.post("/plan", response_model=AIPlanResponse)
def plan(
    payload: AIPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (payload.message or "").strip():
        raise HTTPException(status_code=400, detail="请输入需求描述")
    try:
        return ai_agent.plan_from_message(db, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # AI 层任何意外异常都不能变成 500
        print("[ai] plan 接口异常，返回兜底结果=%s" % exc, flush=True)
        return ai_agent.default_plan_response()


@router.post("/explain", response_model=AIExplainResponse)
def explain(
    payload: AIExplainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return ai_agent.explain_route(payload.message, payload.route_summary.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        # 解说失败同样降级，不抛 500
        print("[ai] explain 接口异常，返回兜底结果=%s" % exc, flush=True)
        return ai_agent.default_explain_response()

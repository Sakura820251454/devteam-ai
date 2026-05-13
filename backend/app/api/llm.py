from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.services.llm.llm_service import llm_service
from app.core.llm_models import AVAILABLE_MODELS, get_model_info
from app.services.llm.cost_tracker import cost_tracker, prompt_cache_service


router = APIRouter(prefix="/llm", tags=["LLM"])


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="消息列表")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    model: Optional[str] = Field(None, description="模型名称")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    track_cost: bool = Field(True, description="是否追踪成本")


class ChatResponse(BaseModel):
    content: str
    usage: Dict[str, int]
    model: str
    finish_reason: str
    cost: Optional[float] = None


class CostRecord(BaseModel):
    agent_id: Optional[str]
    task_id: Optional[str]
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class CostSummary(BaseModel):
    total_cost: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    call_count: int
    by_model: Dict[str, Dict[str, Any]]
    by_agent: Dict[str, Dict[str, Any]]


class ModelInfo(BaseModel):
    provider: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    max_tokens: int
    supports_streaming: bool
    description: str


class RealtimeCostSummary(BaseModel):
    period: str
    start_time: str
    end_time: str
    call_count: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_cost: float


class CostTrendItem(BaseModel):
    period: str
    call_count: int
    total_tokens: int
    total_cost: float


class CostBreakdownItem(BaseModel):
    key: str
    call_count: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_cost: float
    cost_percentage: float


class CostBreakdownResponse(BaseModel):
    group_by: str
    total_cost: float
    items: List[CostBreakdownItem]


class BudgetAlertRequest(BaseModel):
    threshold: float = Field(..., description="预算阈值")
    period: str = Field("monthly", description="周期 (hourly/daily/weekly/monthly)")
    dimension: str = Field("total", description="维度 (total/agent/model)")
    alert_name: Optional[str] = Field(None, description="告警名称")
    agent_id: Optional[str] = Field(None, description="Agent ID (仅在dimension为agent时使用)")
    model: Optional[str] = Field(None, description="模型名称 (仅在dimension为model时使用)")


class BudgetAlertResponse(BaseModel):
    id: str
    alert_name: Optional[str]
    threshold: float
    period: str
    dimension: str
    is_enabled: bool
    is_triggered: bool
    triggered_at: Optional[str]
    created_at: str
    updated_at: str


class TriggeredAlert(BaseModel):
    alert_id: str
    alert_name: Optional[str]
    threshold: float
    current_cost: float
    period: str
    dimension: str
    triggered_at: str


class TokenSummary(BaseModel):
    total_calls: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    avg_prompt_tokens: float
    avg_completion_tokens: float
    by_model: Dict[str, Dict[str, int]]


class TokenHistoryItem(BaseModel):
    period: str
    call_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class CacheStatsResponse(BaseModel):
    total_entries: int
    total_hits: int
    total_misses: int
    hit_rate_percent: float
    cached_tokens: int


@router.get("/models", response_model=Dict[str, ModelInfo])
async def list_models():
    models = llm_service.get_available_models()
    return {
        name: ModelInfo(**info) 
        for name, info in models.items()
    }


@router.get("/providers", response_model=List[str])
async def list_providers():
    return llm_service.get_available_providers()


@router.get("/models/{model_name}")
async def get_model(model_name: str):
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    model_info = get_model_info(model_name)
    return {
        "name": model_info.name,
        "provider": model_info.provider.value,
        "input_cost_per_1k": model_info.input_cost_per_1k,
        "output_cost_per_1k": model_info.output_cost_per_1k,
        "max_tokens": model_info.max_tokens,
        "supports_streaming": model_info.supports_streaming,
        "description": model_info.description
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    from app.core.llm import Message
    
    messages = [Message(role=msg["role"], content=msg["content"]) for msg in request.messages]
    
    agent = None
    if request.agent_id:
        from app.services.agent.agent_service import agent_service
        agent = agent_service.get_agent(request.agent_id)
    
    response = await llm_service.chat(
        messages=messages,
        agent=agent,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        track_cost=request.track_cost
    )
    
    return ChatResponse(
        content=response.content,
        usage=response.usage,
        model=response.model,
        finish_reason=response.finish_reason,
        cost=response.usage.get("estimated_cost") if isinstance(response.usage, dict) else None
    )


@router.get("/costs/summary", response_model=CostSummary)
async def get_cost_summary(
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    task_id: Optional[str] = Query(None, description="Task ID")
):
    summary = llm_service.get_cost_summary(agent_id, task_id)
    return CostSummary(**summary)


@router.get("/costs/records", response_model=List[CostRecord])
async def get_cost_records(
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    task_id: Optional[str] = Query(None, description="Task ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数")
):
    records = llm_service.get_cost_records(agent_id, task_id, limit)
    return [CostRecord(**r) for r in records]


@router.delete("/costs/records")
async def clear_cost_records():
    llm_service.clear_cost_records()
    return {"message": "Cost records cleared"}


@router.get("/costs/realtime", response_model=RealtimeCostSummary)
async def get_realtime_costs(
    period: str = Query("daily", description="周期", regex="^(hourly|daily|weekly|monthly)$")
):
    summary = await cost_tracker.get_realtime_summary(period=period)
    return RealtimeCostSummary(**summary)


@router.get("/costs/trend", response_model=List[CostTrendItem])
async def get_cost_trend(
    period: str = Query("daily", description="周期", regex="^(daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365, description="天数")
):
    trend = await cost_tracker.get_cost_trend(period=period, days=days)
    return [CostTrendItem(**item) for item in trend]


@router.get("/costs/breakdown", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    group_by: str = Query("model", description="分组方式", regex="^(model|agent|provider|task)$")
):
    breakdown = await cost_tracker.get_cost_breakdown(group_by=group_by)
    return CostBreakdownResponse(
        group_by=breakdown["group_by"],
        total_cost=breakdown["total_cost"],
        items=[CostBreakdownItem(**item) for item in breakdown["items"]]
    )


@router.post("/costs/alerts", response_model=Dict[str, str])
async def create_budget_alert(request: BudgetAlertRequest):
    alert_id = await cost_tracker.create_budget_alert(
        threshold=request.threshold,
        period=request.period,
        dimension=request.dimension,
        alert_name=request.alert_name,
        agent_id=request.agent_id,
        model=request.model
    )
    return {"alert_id": alert_id}


@router.get("/costs/alerts", response_model=List[BudgetAlertResponse])
async def get_budget_alerts(
    is_enabled: Optional[bool] = Query(None, description="是否启用")
):
    alerts = await cost_tracker.get_budget_alerts(is_enabled=is_enabled)
    return [BudgetAlertResponse(**alert) for alert in alerts]


@router.delete("/costs/alerts/{alert_id}", response_model=Dict[str, bool])
async def delete_budget_alert(
    alert_id: str = Path(..., description="告警ID")
):
    success = await cost_tracker.delete_budget_alert(alert_id=alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": success}


@router.get("/costs/alerts/check", response_model=List[TriggeredAlert])
async def check_budget_alerts():
    triggered = await cost_tracker.check_budget_alerts()
    return [TriggeredAlert(**alert) for alert in triggered]


@router.get("/tokens/summary", response_model=TokenSummary)
async def get_token_summary(
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    model: Optional[str] = Query(None, description="模型名称")
):
    summary = await cost_tracker.get_token_summary(agent_id=agent_id, model=model)
    return TokenSummary(**summary)


@router.get("/tokens/history", response_model=List[TokenHistoryItem])
async def get_token_history(
    period: str = Query("daily", description="周期", regex="^(hourly|daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365, description="天数"),
    agent_id: Optional[str] = Query(None, description="Agent ID"),
    model: Optional[str] = Query(None, description="模型名称")
):
    history = await cost_tracker.get_token_history(
        period=period,
        days=days,
        agent_id=agent_id,
        model=model
    )
    return [TokenHistoryItem(**item) for item in history]


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    stats = await prompt_cache_service.get_cache_stats()
    return CacheStatsResponse(**stats)
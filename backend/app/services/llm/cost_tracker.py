import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db as get_db_session
from app.models.cost_db import CostRecordDB, PromptCacheDB, BudgetAlertDB
from app.core.llm_models import calculate_cost


class CostTracker:
    async def record_cost(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model: str = "mock-model",
        provider: str = "mock",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> str:
        total_tokens = prompt_tokens + completion_tokens
        cost = calculate_cost(model, prompt_tokens, completion_tokens)
        
        record_id = str(uuid.uuid4())
        
        async for db in get_db_session():
            record = CostRecordDB(
                id=record_id,
                agent_id=agent_id,
                task_id=task_id,
                session_id=session_id,
                model=model,
                provider=provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency_ms,
                error_message=error_message
            )
            db.add(record)
            await db.commit()
            break
        
        return record_id

    async def get_cost_summary(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        filters = []
        if agent_id:
            filters.append(CostRecordDB.agent_id == agent_id)
        if task_id:
            filters.append(CostRecordDB.task_id == task_id)
        if session_id:
            filters.append(CostRecordDB.session_id == session_id)
        if start_date:
            filters.append(CostRecordDB.created_at >= start_date)
        if end_date:
            filters.append(CostRecordDB.created_at <= end_date)
        
        async for db in get_db_session():
            query = select(
                func.count(CostRecordDB.id).label("call_count"),
                func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                func.sum(CostRecordDB.cost).label("total_cost"),
                func.avg(CostRecordDB.latency_ms).label("avg_latency_ms")
            )
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await db.execute(query)
            row = result.first()
            
            model_query = select(
                CostRecordDB.model,
                func.count(CostRecordDB.id).label("calls"),
                func.sum(CostRecordDB.total_tokens).label("tokens"),
                func.sum(CostRecordDB.cost).label("cost")
            ).group_by(CostRecordDB.model)
            if filters:
                model_query = model_query.where(and_(*filters))
            
            model_result = await db.execute(model_query)
            by_model = {}
            for row in model_result:
                by_model[row.model] = {
                    "calls": row.calls,
                    "tokens": row.tokens or 0,
                    "cost": row.cost or 0.0
                }
            
            agent_query = select(
                CostRecordDB.agent_id,
                func.count(CostRecordDB.id).label("calls"),
                func.sum(CostRecordDB.total_tokens).label("tokens"),
                func.sum(CostRecordDB.cost).label("cost")
            ).where(CostRecordDB.agent_id.isnot(None)).group_by(CostRecordDB.agent_id)
            if filters:
                agent_query = agent_query.where(and_(*filters))
            
            agent_result = await db.execute(agent_query)
            by_agent = {}
            for row in agent_result:
                by_agent[row.agent_id or "unknown"] = {
                    "calls": row.calls,
                    "tokens": row.tokens or 0,
                    "cost": row.cost or 0.0
                }
            
            break
        
        return {
            "call_count": row.call_count or 0,
            "total_tokens": row.total_tokens or 0,
            "prompt_tokens": row.prompt_tokens or 0,
            "completion_tokens": row.completion_tokens or 0,
            "total_cost": round(row.total_cost or 0.0, 6),
            "avg_latency_ms": round(row.avg_latency_ms or 0.0, 2),
            "by_model": {k: {kk: round(vv, 6) if kk == "cost" else vv for kk, vv in v.items()} for k, v in by_model.items()},
            "by_agent": {k: {kk: round(vv, 6) if kk == "cost" else vv for kk, vv in v.items()} for k, v in by_agent.items()}
        }

    async def get_cost_records(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        filters = []
        if agent_id:
            filters.append(CostRecordDB.agent_id == agent_id)
        if task_id:
            filters.append(CostRecordDB.task_id == task_id)
        
        async for db in get_db_session():
            query = select(CostRecordDB).order_by(CostRecordDB.created_at.desc()).limit(limit).offset(offset)
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await db.execute(query)
            records = result.scalars().all()
            
            break
        
        return [r.to_dict() for r in records]

    async def get_realtime_summary(
        self,
        period: str = "daily"
    ) -> Dict[str, Any]:
        now = datetime.now()
        if period == "hourly":
            start_time = now.replace(minute=0, second=0, microsecond=0)
        elif period == "daily":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start_time = now - timedelta(days=now.weekday())
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "monthly":
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

        async for db in get_db_session():
            query = select(
                func.count(CostRecordDB.id).label("call_count"),
                func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                func.sum(CostRecordDB.cost).label("total_cost")
            ).where(CostRecordDB.created_at >= start_time)
            
            result = await db.execute(query)
            row = result.first()
            break
        
        return {
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "call_count": row.call_count or 0,
            "total_tokens": row.total_tokens or 0,
            "prompt_tokens": row.prompt_tokens or 0,
            "completion_tokens": row.completion_tokens or 0,
            "total_cost": round(row.total_cost or 0.0, 6)
        }

    async def get_cost_trend(
        self,
        period: str = "daily",
        days: int = 30
    ) -> List[Dict[str, Any]]:
        now = datetime.now()
        start_time = now - timedelta(days=days)

        if period == "daily":
            date_format = "%Y-%m-%d"
            date_trunc = func.date(CostRecordDB.created_at)
        elif period == "weekly":
            date_format = "%Y-W%W"
            date_trunc = func.date(CostRecordDB.created_at - timedelta(days=func.extract('dow', CostRecordDB.created_at)))
        elif period == "monthly":
            date_format = "%Y-%m"
            date_trunc = func.concat(
                func.extract('year', CostRecordDB.created_at),
                '-',
                func.extract('month', CostRecordDB.created_at)
            )
        else:
            date_format = "%Y-%m-%d"
            date_trunc = func.date(CostRecordDB.created_at)

        async for db in get_db_session():
            query = select(
                date_trunc.label("period_start"),
                func.count(CostRecordDB.id).label("call_count"),
                func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                func.sum(CostRecordDB.cost).label("total_cost")
            ).where(
                and_(
                    CostRecordDB.created_at >= start_time,
                    CostRecordDB.created_at <= now
                )
            ).group_by(date_trunc).order_by(date_trunc)
            
            result = await db.execute(query)
            rows = result.all()
            break
        
        trend = []
        for row in rows:
            period_start = row.period_start
            if isinstance(period_start, str):
                period_label = period_start
            elif isinstance(period_start, datetime):
                period_label = period_start.strftime(date_format)
            else:
                period_label = str(period_start)
            
            trend.append({
                "period": period_label,
                "call_count": row.call_count or 0,
                "total_tokens": row.total_tokens or 0,
                "total_cost": round(row.total_cost or 0.0, 6)
            })
        
        return trend

    async def get_cost_breakdown(
        self,
        group_by: str = "model"
    ) -> Dict[str, Any]:
        async for db in get_db_session():
            if group_by == "model":
                query = select(
                    CostRecordDB.model.label("key"),
                    func.count(CostRecordDB.id).label("call_count"),
                    func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                    func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                    func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                    func.sum(CostRecordDB.cost).label("total_cost")
                ).group_by(CostRecordDB.model)
            elif group_by == "agent":
                query = select(
                    func.coalesce(CostRecordDB.agent_id, "unknown").label("key"),
                    func.count(CostRecordDB.id).label("call_count"),
                    func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                    func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                    func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                    func.sum(CostRecordDB.cost).label("total_cost")
                ).group_by(CostRecordDB.agent_id)
            elif group_by == "provider":
                query = select(
                    CostRecordDB.provider.label("key"),
                    func.count(CostRecordDB.id).label("call_count"),
                    func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                    func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                    func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                    func.sum(CostRecordDB.cost).label("total_cost")
                ).group_by(CostRecordDB.provider)
            elif group_by == "task":
                query = select(
                    func.coalesce(CostRecordDB.task_id, "unknown").label("key"),
                    func.count(CostRecordDB.id).label("call_count"),
                    func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                    func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                    func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                    func.sum(CostRecordDB.cost).label("total_cost")
                ).group_by(CostRecordDB.task_id)
            else:
                query = select(
                    CostRecordDB.model.label("key"),
                    func.count(CostRecordDB.id).label("call_count"),
                    func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                    func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                    func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                    func.sum(CostRecordDB.cost).label("total_cost")
                ).group_by(CostRecordDB.model)
            
            result = await db.execute(query)
            rows = result.all()
            break
        
        breakdown = []
        for row in rows:
            breakdown.append({
                "key": row.key,
                "call_count": row.call_count or 0,
                "total_tokens": row.total_tokens or 0,
                "prompt_tokens": row.prompt_tokens or 0,
                "completion_tokens": row.completion_tokens or 0,
                "total_cost": round(row.total_cost or 0.0, 6)
            })
        
        breakdown.sort(key=lambda x: x["total_cost"], reverse=True)
        
        total_cost = sum(item["total_cost"] for item in breakdown)
        
        for item in breakdown:
            item["cost_percentage"] = round((item["total_cost"] / total_cost * 100) if total_cost > 0 else 0, 2)
        
        return {
            "group_by": group_by,
            "total_cost": round(total_cost, 6),
            "items": breakdown
        }

    async def create_budget_alert(
        self,
        threshold: float,
        period: str = "monthly",
        dimension: str = "total",
        alert_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        alert_id = str(uuid.uuid4())
        
        async for db in get_db_session():
            alert = BudgetAlertDB(
                id=alert_id,
                alert_name=alert_name,
                threshold=threshold,
                period=period,
                dimension=dimension,
                is_enabled=True,
                is_triggered=False
            )
            db.add(alert)
            await db.commit()
            break
        
        return alert_id

    async def get_budget_alerts(
        self,
        is_enabled: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        async for db in get_db_session():
            query = select(BudgetAlertDB).order_by(BudgetAlertDB.created_at.desc())
            
            if is_enabled is not None:
                query = query.where(BudgetAlertDB.is_enabled == is_enabled)
            
            result = await db.execute(query)
            alerts = result.scalars().all()
            break
        
        return [alert.to_dict() for alert in alerts]

    async def delete_budget_alert(self, alert_id: str) -> bool:
        async for db in get_db_session():
            result = await db.execute(
                select(BudgetAlertDB).where(BudgetAlertDB.id == alert_id)
            )
            alert = result.scalar_one_or_none()
            
            if alert:
                await db.delete(alert)
                await db.commit()
                return True
            break
        
        return False

    async def check_budget_alerts(self) -> List[Dict[str, Any]]:
        now = datetime.now()
        triggered_alerts = []
        
        async for db in get_db_session():
            alerts_result = await db.execute(
                select(BudgetAlertDB).where(BudgetAlertDB.is_enabled == True)
            )
            alerts = alerts_result.scalars().all()
            
            for alert in alerts:
                if alert.period == "hourly":
                    start_time = now.replace(minute=0, second=0, microsecond=0)
                elif alert.period == "daily":
                    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                elif alert.period == "weekly":
                    start_time = now - timedelta(days=now.weekday())
                    start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                elif alert.period == "monthly":
                    start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                
                filters = [CostRecordDB.created_at >= start_time]
                
                if alert.dimension == "agent":
                    filters.append(CostRecordDB.agent_id.isnot(None))
                elif alert.dimension == "model" and alert.alert_name:
                    filters.append(CostRecordDB.model == alert.alert_name)
                
                cost_query = select(
                    func.sum(CostRecordDB.cost).label("total_cost")
                ).where(and_(*filters))
                
                cost_result = await db.execute(cost_query)
                current_cost = cost_result.scalar() or 0.0
                
                if current_cost >= alert.threshold and not alert.is_triggered:
                    alert.is_triggered = True
                    alert.triggered_at = now
                    await db.commit()
                    
                    triggered_alerts.append({
                        "alert_id": alert.id,
                        "alert_name": alert.alert_name,
                        "threshold": alert.threshold,
                        "current_cost": round(current_cost, 6),
                        "period": alert.period,
                        "dimension": alert.dimension,
                        "triggered_at": now.isoformat()
                    })
                elif current_cost < alert.threshold and alert.is_triggered:
                    alert.is_triggered = False
                    alert.triggered_at = None
                    await db.commit()
            
            break
        
        return triggered_alerts

    async def get_token_summary(
        self,
        agent_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        filters = []
        if agent_id:
            filters.append(CostRecordDB.agent_id == agent_id)
        if model:
            filters.append(CostRecordDB.model == model)
        
        async for db in get_db_session():
            query = select(
                func.count(CostRecordDB.id).label("total_calls"),
                func.sum(CostRecordDB.prompt_tokens).label("total_prompt_tokens"),
                func.sum(CostRecordDB.completion_tokens).label("total_completion_tokens"),
                func.sum(CostRecordDB.total_tokens).label("total_tokens"),
                func.avg(CostRecordDB.prompt_tokens).label("avg_prompt_tokens"),
                func.avg(CostRecordDB.completion_tokens).label("avg_completion_tokens")
            )
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await db.execute(query)
            row = result.first()
            
            model_tokens_query = select(
                CostRecordDB.model,
                func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                func.sum(CostRecordDB.total_tokens).label("total_tokens")
            )
            
            if filters:
                model_tokens_query = model_tokens_query.where(and_(*filters))
            
            model_tokens_query = model_tokens_query.group_by(CostRecordDB.model)
            model_result = await db.execute(model_tokens_query)
            by_model = {}
            for row in model_result:
                by_model[row.model] = {
                    "prompt_tokens": row.prompt_tokens or 0,
                    "completion_tokens": row.completion_tokens or 0,
                    "total_tokens": row.total_tokens or 0
                }
            
            break
        
        return {
            "total_calls": row.total_calls or 0,
            "total_prompt_tokens": row.total_prompt_tokens or 0,
            "total_completion_tokens": row.total_completion_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "avg_prompt_tokens": round(row.avg_prompt_tokens or 0.0, 2),
            "avg_completion_tokens": round(row.avg_completion_tokens or 0.0, 2),
            "by_model": by_model
        }

    async def get_token_history(
        self,
        period: str = "daily",
        days: int = 30,
        agent_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        now = datetime.now()
        start_time = now - timedelta(days=days)
        
        filters = [
            CostRecordDB.created_at >= start_time,
            CostRecordDB.created_at <= now
        ]
        
        if agent_id:
            filters.append(CostRecordDB.agent_id == agent_id)
        if model:
            filters.append(CostRecordDB.model == model)
        
        if period == "daily":
            date_group = func.date(CostRecordDB.created_at)
            date_format = "%Y-%m-%d"
        elif period == "weekly":
            date_group = func.date(CostRecordDB.created_at - timedelta(days=func.extract('dow', CostRecordDB.created_at)))
            date_format = "%Y-W%W"
        elif period == "monthly":
            date_group = func.concat(
                func.extract('year', CostRecordDB.created_at),
                '-',
                func.extract('month', CostRecordDB.created_at)
            )
            date_format = "%Y-%m"
        elif period == "hourly":
            date_group = func.date_trunc('hour', CostRecordDB.created_at)
            date_format = "%Y-%m-%d %H:00"
        else:
            date_group = func.date(CostRecordDB.created_at)
            date_format = "%Y-%m-%d"
        
        async for db in get_db_session():
            query = select(
                date_group.label("period"),
                func.count(CostRecordDB.id).label("call_count"),
                func.sum(CostRecordDB.prompt_tokens).label("prompt_tokens"),
                func.sum(CostRecordDB.completion_tokens).label("completion_tokens"),
                func.sum(CostRecordDB.total_tokens).label("total_tokens")
            ).where(and_(*filters)).group_by(date_group).order_by(date_group)
            
            result = await db.execute(query)
            rows = result.all()
            break
        
        history = []
        for row in rows:
            period_val = row.period
            if isinstance(period_val, datetime):
                period_label = period_val.strftime(date_format)
            else:
                period_label = str(period_val)
            
            history.append({
                "period": period_label,
                "call_count": row.call_count or 0,
                "prompt_tokens": row.prompt_tokens or 0,
                "completion_tokens": row.completion_tokens or 0,
                "total_tokens": row.total_tokens or 0
            })
        
        return history


class PromptCacheService:
    def __init__(self):
        self.default_ttl_hours = 24
        self.max_cache_size = 1000
    
    def _hash_prompt(self, messages: List[Dict[str, str]], model: str) -> str:
        import hashlib
        import json
        content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def get_cached_response(
        self,
        messages: List[Dict[str, str]],
        model: str
    ) -> Optional[Dict[str, Any]]:
        prompt_hash = self._hash_prompt(messages, model)
        now = datetime.now()
        
        async for db in get_db_session():
            query = select(PromptCacheDB).where(
                and_(
                    PromptCacheDB.prompt_hash == prompt_hash,
                    or_(
                        PromptCacheDB.expires_at.is_(None),
                        PromptCacheDB.expires_at > now
                    )
                )
            )
            
            result = await db.execute(query)
            cache_entry = result.scalar_one_or_none()
            
            if cache_entry:
                cache_entry.access_count += 1
                cache_entry.hit_count += 1
                cache_entry.last_accessed_at = now
                await db.commit()
                
                return {
                    "response": cache_entry.response,
                    "prompt_tokens": cache_entry.prompt_tokens,
                    "completion_tokens": cache_entry.completion_tokens,
                    "cached": True
                }
            else:
                cache_entry_miss = await db.execute(
                    select(PromptCacheDB).where(PromptCacheDB.prompt_hash == prompt_hash)
                )
                miss_entry = cache_entry_miss.scalar_one_or_none()
                if miss_entry:
                    miss_entry.miss_count += 1
                    await db.commit()
            
            break
        
        return None
    
    async def cache_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        response: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        ttl_hours: Optional[int] = None
    ) -> str:
        prompt_hash = self._hash_prompt(messages, model)
        cache_id = str(uuid.uuid4())
        ttl = ttl_hours or self.default_ttl_hours
        expires_at = datetime.now() + timedelta(hours=ttl)
        
        import json
        prompt_snapshot = json.dumps(messages, ensure_ascii=False)
        
        async for db in get_db_session():
            existing = await db.execute(
                select(PromptCacheDB).where(PromptCacheDB.prompt_hash == prompt_hash)
            )
            existing_entry = existing.scalar_one_or_none()
            
            if existing_entry:
                existing_entry.response = response
                existing_entry.access_count = 0
                existing_entry.expires_at = expires_at
                existing_entry.prompt_tokens = prompt_tokens
                existing_entry.completion_tokens = completion_tokens
                cache_id = existing_entry.id
            else:
                count_result = await db.execute(select(func.count(PromptCacheDB.id)))
                cache_count = count_result.scalar()
                
                if cache_count >= self.max_cache_size:
                    oldest = await db.execute(
                        select(PromptCacheDB).order_by(PromptCacheDB.last_accessed_at).limit(1)
                    )
                    oldest_entry = oldest.scalar_one_or_none()
                    if oldest_entry:
                        await db.delete(oldest_entry)
                
                cache_entry = PromptCacheDB(
                    id=cache_id,
                    prompt_hash=prompt_hash,
                    prompt_snapshot=prompt_snapshot,
                    response=response,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    expires_at=expires_at
                )
                db.add(cache_entry)
            
            await db.commit()
            break
        
        return cache_id
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        async for db in get_db_session():
            total_result = await db.execute(select(func.count(PromptCacheDB.id)))
            total_entries = total_result.scalar()
            
            hit_result = await db.execute(select(func.sum(PromptCacheDB.hit_count)))
            total_hits = hit_result.scalar() or 0
            
            miss_result = await db.execute(select(func.sum(PromptCacheDB.miss_count)))
            total_misses = miss_result.scalar() or 0
            
            tokens_result = await db.execute(
                select(
                    func.sum(PromptCacheDB.prompt_tokens).label("prompt"),
                    func.sum(PromptCacheDB.completion_tokens).label("completion")
                )
            )
            tokens_row = tokens_result.first()
            total_tokens = (tokens_row.prompt or 0) + (tokens_row.completion or 0)
            
            break
        
        total_requests = total_hits + total_misses
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_tokens": total_tokens
        }
    
    async def clear_expired_cache(self) -> int:
        now = datetime.now()
        deleted_count = 0
        
        async for db in get_db_session():
            result = await db.execute(
                select(PromptCacheDB).where(
                    and_(
                        PromptCacheDB.expires_at.isnot(None),
                        PromptCacheDB.expires_at <= now
                    )
                )
            )
            expired_entries = result.scalars().all()
            
            for entry in expired_entries:
                await db.delete(entry)
                deleted_count += 1
            
            await db.commit()
            break
        
        return deleted_count


cost_tracker = CostTracker()
prompt_cache_service = PromptCacheService()

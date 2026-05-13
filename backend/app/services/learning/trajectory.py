"""
轨迹记录器 - Phase 4.3

记录 Agent 执行任务的完整轨迹，包括：
- 思考过程
- 决策步骤
- 执行结果
- 成功/失败状态
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.memory_db import TrajectoryModel


@dataclass
class Decision:
    """决策记录"""
    step: int
    action: str
    reasoning: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Trajectory:
    """完整任务轨迹"""
    id: str
    agent_id: str
    session_id: Optional[str]
    task_id: Optional[str]
    content: str
    decisions: List[Decision] = field(default_factory=list)
    outcomes: Dict[str, Any] = field(default_factory=dict)
    success: Optional[str] = None  # "success", "partial", "failure"
    created_at: datetime = field(default_factory=datetime.now)


class TrajectoryRecorder:
    """轨迹记录器"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.current_trajectories: Dict[str, Trajectory] = {}  # in-memory cache
    
    def start_trajectory(
        self,
        agent_id: str,
        task_description: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """
        开始记录新轨迹
        
        Returns:
            trajectory_id
        """
        trajectory_id = f"traj_{agent_id}_{datetime.now().timestamp()}"
        
        trajectory = Trajectory(
            id=trajectory_id,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            content=task_description,
        )
        
        self.current_trajectories[trajectory_id] = trajectory
        return trajectory_id
    
    def record_decision(
        self,
        trajectory_id: str,
        step: int,
        action: str,
        reasoning: str,
    ) -> bool:
        """记录决策步骤"""
        if trajectory_id not in self.current_trajectories:
            return False
        
        trajectory = self.current_trajectories[trajectory_id]
        decision = Decision(
            step=step,
            action=action,
            reasoning=reasoning,
        )
        trajectory.decisions.append(decision)
        return True
    
    def record_outcome(
        self,
        trajectory_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """记录执行结果"""
        if trajectory_id not in self.current_trajectories:
            return False
        
        trajectory = self.current_trajectories[trajectory_id]
        trajectory.outcomes[key] = value
        return True
    
    def end_trajectory(
        self,
        trajectory_id: str,
        success: str = "success",
        final_content: Optional[str] = None,
    ) -> Optional[Trajectory]:
        """
        结束轨迹记录
        
        Args:
            success: "success", "partial", "failure"
        """
        if trajectory_id not in self.current_trajectories:
            return None
        
        trajectory = self.current_trajectories[trajectory_id]
        trajectory.success = success
        
        if final_content:
            trajectory.content = final_content
        
        del self.current_trajectories[trajectory_id]
        return trajectory
    
    async def save_trajectory(
        self,
        trajectory: Trajectory,
    ) -> bool:
        """保存轨迹到数据库"""
        if not self.db:
            return False
        
        model = TrajectoryModel(
            id=trajectory.id,
            agent_id=trajectory.agent_id,
            session_id=trajectory.session_id,
            task_id=trajectory.task_id,
            content=trajectory.content,
            decisions=[
                {
                    "step": d.step,
                    "action": d.action,
                    "reasoning": d.reasoning,
                    "timestamp": d.timestamp,
                }
                for d in trajectory.decisions
            ],
            outcomes=trajectory.outcomes,
            success=trajectory.success,
            created_at=trajectory.created_at,
        )
        
        self.db.add(model)
        await self.db.commit()
        return True
    
    async def get_trajectory(
        self,
        trajectory_id: str,
    ) -> Optional[Trajectory]:
        """从数据库获取轨迹"""
        if not self.db:
            return None
        
        result = await self.db.execute(
            select(TrajectoryModel).where(TrajectoryModel.id == trajectory_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return Trajectory(
            id=model.id,
            agent_id=model.agent_id,
            session_id=model.session_id,
            task_id=model.task_id,
            content=model.content,
            decisions=[
                Decision(**d) for d in model.decisions
            ],
            outcomes=model.outcomes,
            success=model.success,
            created_at=model.created_at,
        )
    
    async def get_agent_trajectories(
        self,
        agent_id: str,
        limit: int = 50,
        success_only: bool = False,
    ) -> List[Trajectory]:
        """获取 Agent 的历史轨迹"""
        if not self.db:
            return []
        
        query = select(TrajectoryModel).where(
            TrajectoryModel.agent_id == agent_id
        )
        
        if success_only:
            query = query.where(TrajectoryModel.success == "success")
        
        query = query.order_by(TrajectoryModel.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        models = result.scalars().all()
        
        return [
            Trajectory(
                id=m.id,
                agent_id=m.agent_id,
                session_id=m.session_id,
                task_id=m.task_id,
                content=m.content,
                decisions=[Decision(**d) for d in m.decisions],
                outcomes=m.outcomes,
                success=m.success,
                created_at=m.created_at,
            )
            for m in models
        ]
    
    def get_in_progress_trajectories(self) -> List[Trajectory]:
        """获取所有进行中的轨迹"""
        return list(self.current_trajectories.values())

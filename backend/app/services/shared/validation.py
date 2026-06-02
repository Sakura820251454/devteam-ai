"""AI 输出 Pydantic 验证 Schema。

每个 AI 输出的 JSON 格式都有对应的 Schema 类。
与 json_extractor.extract_and_validate() 配合使用，
替代代码中散落的 .get() 默认值调用。
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


# ========== pipeline_orchestrator ==========


class TaskBreakdownItem(BaseModel):
    """单个拆解任务（来自 LLM 任务拆解响应）。"""

    title: str
    description: str = ""
    assigned_role: str = ""
    priority: str = "medium"
    phase: str = "execution"
    dependencies: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)


class TaskBreakdownResult(BaseModel):
    """任务拆解结果（来自 LLM 响应）。

    两种模式：
    - 简单项目: simple=True, direct_answer 有值, tasks 为空
    - 复杂项目: simple=False, tasks 非空
    """

    tasks: List[TaskBreakdownItem] = Field(default_factory=list)
    summary: str = ""
    simple: bool = False
    direct_answer: str = ""


# ========== task_analyzer ==========


class TaskAnalysisResult(BaseModel):
    """项目分析结果（来自 task_analyzer LLM 响应）。"""

    domain: str = "其他领域"
    task_type: str = "探索研究型"
    sub_types: List[str] = Field(default_factory=list)
    complexity: str = "中"
    breakdown: List[str] = Field(default_factory=list)
    key_challenge: str = ""
    analysis_summary: str = ""


# ========== team_suggester ==========


class RoleSuggestion(BaseModel):
    """团队角色建议。"""

    role_name: str = ""
    responsibilities: str = ""
    required_capabilities: List[str] = Field(default_factory=list)
    suggested_soul: str = ""
    matching_reason: str = ""
    priority: str = "recommended"


class StrategyAlternative(BaseModel):
    strategy: str = ""
    reason: str = ""


class StrategyConfig(BaseModel):
    recommended: str = "sequential"
    reasoning: str = ""
    alternatives: List[StrategyAlternative] = Field(default_factory=list)


class TeamSuggestionResult(BaseModel):
    """团队建议结果（来自 team_suggester LLM 响应）。"""

    team_name: str = ""
    roles: List[RoleSuggestion] = Field(default_factory=list)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    overall_rationale: str = ""


# ========== agent_trait_service ==========


class AgentTraitResult(BaseModel):
    """Agent 能力画像（来自 agent_trait_service LLM 响应）。"""

    role_label: str = ""
    skills: List[str] = Field(default_factory=list)
    strength_areas: List[str] = Field(default_factory=list)
    collaboration_style: str = "务实型"
    communication_style: str = "简洁型"
    summary: str = ""


# ========== strategy_recommender ==========


class StrategyRecommendationResult(BaseModel):
    """策略推荐结果（来自 strategy_recommender LLM 响应）。"""

    recommended_strategy: str = "sequential"
    confidence: float = 0.5
    reasoning: str = ""
    suggested_coordinator: Optional[str] = None
    alternative_strategies: List[dict] = Field(default_factory=list)


# ========== discussion_orchestrator ==========


class ConsensusCheckResult(BaseModel):
    """共识检查结果（来自 discussion LLM 响应）。"""

    consensus: bool = False
    conclusion: Optional[str] = None


class CoordinatorElectionResult(BaseModel):
    """协调者选举结果（来自 election LLM 响应）。"""

    elected_agent_id: str = ""
    reason: str = ""


# ========== agent_executor ==========


class TaskStep(BaseModel):
    """任务执行步骤。"""

    name: str
    description: str = ""
    expected_output: str = ""


class TaskStepPlan(BaseModel):
    """任务步骤规划（来自 agent_executor LLM 响应）。"""

    steps: List[TaskStep] = Field(default_factory=list)


# ========== pipeline_templates ==========


class StageAdjustment(BaseModel):
    """阶段调整条目（用于 add / final_stages）。"""

    key: str
    label: str
    description: str = ""
    expected_artifact: str = ""
    parallel_group: Optional[str] = None


class StageReorder(BaseModel):
    """阶段重排序条目。"""

    key: str
    new_position: int = 0


class StageRename(BaseModel):
    """阶段重命名条目。"""

    key: str
    new_label: str = ""


class StageAdjustmentChanges(BaseModel):
    """阶段变更集 — 字段类型严格匹配 prompt 输出格式。"""

    add: List[StageAdjustment] = Field(default_factory=list)
    remove: List[str] = Field(default_factory=list)         # ["stage_key_to_remove"]
    reorder: List[StageReorder] = Field(default_factory=list)  # [{"key","new_position"}]
    rename: List[StageRename] = Field(default_factory=list)    # [{"key","new_label"}]


class StageAdjustmentResult(BaseModel):
    """阶段调整结果（来自 pipeline_templates LLM 响应）。"""

    analysis: str = ""
    recommended_strategy: str = ""
    changes: StageAdjustmentChanges = Field(default_factory=StageAdjustmentChanges)
    final_stages: List[StageAdjustment] = Field(default_factory=list)

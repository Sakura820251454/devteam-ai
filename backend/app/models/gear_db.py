"""
装备数据模型 - Phase 5.1

定义装备系统的数据结构：
1. Gear: 装备基类
2. SkillGear: 技能装备
3. MemoryGear: 记忆装备
4. ToolGear: MCP工具装备
"""

from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field

from sqlalchemy import Column, String, Text, JSON, Float, DateTime, Boolean, Integer
from app.database import Base


class GearType(str, Enum):
    """装备类型"""
    SKILL = "skill"           # 技能装备
    MEMORY = "memory"         # 记忆装备
    TOOL = "tool"             # MCP工具装备
    KNOWLEDGE = "knowledge"   # 知识库装备


class GearRarity(str, Enum):
    """装备稀有度"""
    COMMON = "common"       # 普通
    UNCOMMON = "uncommon"   # 优秀
    RARE = "rare"           # 稀有
    EPIC = "epic"           # 史诗
    LEGENDARY = "legendary" # 传说


class GearSlot(str, Enum):
    """装备槽位"""
    PRIMARY = "primary"       # 主槽位
    SECONDARY = "secondary"   # 副槽位
    UTILITY = "utility"       # 工具槽位
    PASSIVE = "passive"       # 被动槽位


class GearModel(Base):
    """装备数据库模型"""
    __tablename__ = "gear"
    
    id = Column(String, primary_key=True)
    agent_id = Column(String, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    gear_type = Column(String, nullable=False)
    rarity = Column(String, default="common")
    slot = Column(String)
    power = Column(Float, default=1.0)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    cooldown_seconds = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    gear_metadata = Column("metadata", JSON)
    source_id = Column(String)  # 关联的技能/记忆/工具ID
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)
    equipped = Column(Boolean, default=False)


@dataclass
class Gear:
    """装备基类"""
    id: str
    name: str
    description: str
    gear_type: GearType
    rarity: GearRarity
    slot: GearSlot
    power: float = 1.0
    level: int = 1
    experience: int = 0
    cooldown_seconds: int = 0
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    success_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_id: Optional[str] = None
    equipped: bool = False
    
    @property
    def cooldown_remaining(self) -> int:
        """计算冷却剩余时间"""
        if self.last_used_at is None:
            return 0
        elapsed = (datetime.now() - self.last_used_at).total_seconds()
        return max(0, self.cooldown_seconds - int(elapsed))
    
    @property
    def is_ready(self) -> bool:
        """检查装备是否就绪"""
        return self.cooldown_remaining == 0
    
    def use(self, success: bool = True):
        """使用装备"""
        self.last_used_at = datetime.now()
        self.usage_count += 1
        
        if success:
            self.experience += 10
            self.success_rate = (self.success_rate * (self.usage_count - 1) + 1.0) / self.usage_count
            
            if self.experience >= self.level * 100:
                self.level_up()
        else:
            self.success_rate = (self.success_rate * (self.usage_count - 1) + 0.0) / self.usage_count
    
    def level_up(self):
        """升级装备"""
        self.level += 1
        self.power = min(10.0, self.power * 1.2)
        self.experience = 0


@dataclass
class SkillGear(Gear):
    """技能装备"""
    skill_category: Optional[str] = None
    trigger_keywords: List[str] = field(default_factory=list)
    implementation: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.gear_type = GearType.SKILL


@dataclass
class MemoryGear(Gear):
    """记忆装备"""
    memory_level: Optional[str] = None
    relevance_score: float = 1.0
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.gear_type = GearType.MEMORY


@dataclass
class ToolGear(Gear):
    """MCP工具装备"""
    tool_name: Optional[str] = None
    tool_description: Optional[str] = None
    tool_parameters: Dict[str, Any] = field(default_factory=dict)
    tool_server: Optional[str] = None
    
    def __post_init__(self):
        self.gear_type = GearType.TOOL


@dataclass
class AgentEquipment:
    """Agent装备栏"""
    agent_id: str
    gears: List[Gear] = field(default_factory=list)
    
    def __post_init__(self):
        self._gears_by_slot = {slot: None for slot in GearSlot}
        self._equipped_gears = []
    
    @property
    def equipped_gears(self) -> List[Gear]:
        """获取已装备的装备"""
        return [g for g in self.gears if g.equipped]
    
    def equip(self, gear: Gear) -> bool:
        """装备物品"""
        if not gear.is_ready:
            return False
        
        if gear.equipped:
            return False
        
        if len(self.equipped_gears) >= 4:  # 最多4个装备槽
            return False
        
        gear.equipped = True
        return True
    
    def unequip(self, gear_id: str) -> bool:
        """卸载装备"""
        for gear in self.gears:
            if gear.id == gear_id:
                gear.equipped = False
                return True
        return False
    
    def get_gear_by_slot(self, slot: GearSlot) -> Optional[Gear]:
        """获取指定槽位的装备"""
        for gear in self.equipped_gears:
            if gear.slot == slot:
                return gear
        return None
    
    def get_ready_gears(self) -> List[Gear]:
        """获取就绪的装备"""
        return [g for g in self.equipped_gears if g.is_ready]


@dataclass
class GearRecommendation:
    """装备推荐"""
    gear_id: str
    gear_name: str
    gear_type: GearType
    relevance_score: float
    recommended_slot: GearSlot
    reason: str

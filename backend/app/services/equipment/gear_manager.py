"""
装备管理器 - Phase 5.1

核心服务，管理Agent的装备系统：
1. 装备的CRUD操作
2. 装备装配/卸载
3. 装备升级和经验管理
4. 装备使用和冷却管理
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy import update, delete
from sqlalchemy.future import select

from app.models.gear_db import (
    GearModel,
    Gear,
    SkillGear,
    MemoryGear,
    ToolGear,
    AgentEquipment,
    GearType,
    GearRarity,
    GearSlot,
)
from app.models.memory_db import SkillModel, MemoryEntryModel


class GearManager:
    """装备管理器"""
    
    def __init__(self, db):
        self.db = db
    
    async def create_gear(
        self,
        agent_id: str,
        name: str,
        gear_type: GearType,
        description: str = "",
        slot: GearSlot = GearSlot.UTILITY,
        rarity: GearRarity = GearRarity.COMMON,
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Gear:
        """创建装备"""
        gear_id = f"gear_{uuid.uuid4().hex[:8]}"
        
        db_gear = GearModel(
            id=gear_id,
            agent_id=agent_id,
            name=name,
            description=description,
            gear_type=gear_type.value,
            rarity=rarity.value,
            slot=slot.value,
            source_id=source_id,
            metadata=metadata or {},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        self.db.add(db_gear)
        await self.db.commit()
        
        return await self.get_gear(gear_id)
    
    async def get_gear(self, gear_id: str) -> Optional[Gear]:
        """获取装备详情"""
        result = await self.db.execute(
            select(GearModel).where(GearModel.id == gear_id)
        )
        db_gear = result.scalar_one_or_none()
        
        if not db_gear:
            return None
        
        return self._db_to_gear(db_gear)
    
    async def get_agent_gears(self, agent_id: str) -> List[Gear]:
        """获取Agent的所有装备"""
        result = await self.db.execute(
            select(GearModel).where(GearModel.agent_id == agent_id)
        )
        db_gears = result.scalars().all()
        
        return [self._db_to_gear(g) for g in db_gears]
    
    async def update_gear(
        self,
        gear_id: str,
        **kwargs,
    ) -> Optional[Gear]:
        """更新装备"""
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.now()
        
        await self.db.execute(
            update(GearModel)
            .where(GearModel.id == gear_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        return await self.get_gear(gear_id)
    
    async def delete_gear(self, gear_id: str) -> bool:
        """删除装备"""
        result = await self.db.execute(
            delete(GearModel).where(GearModel.id == gear_id)
        )
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def equip_gear(self, gear_id: str) -> bool:
        """装备物品"""
        gear = await self.get_gear(gear_id)
        if not gear:
            return False
        
        if gear.equipped:
            return False
        
        result = await self.db.execute(
            select(GearModel)
            .where(GearModel.agent_id == gear.agent_id)
            .where(GearModel.equipped == True)
        )
        equipped_count = len(result.scalars().all())
        
        if equipped_count >= 4:
            return False
        
        await self.update_gear(gear_id, equipped=True)
        return True
    
    async def unequip_gear(self, gear_id: str) -> bool:
        """卸载装备"""
        gear = await self.get_gear(gear_id)
        if not gear:
            return False
        
        if not gear.equipped:
            return False
        
        await self.update_gear(gear_id, equipped=False)
        return True
    
    async def use_gear(self, gear_id: str, success: bool = True) -> Optional[Gear]:
        """使用装备"""
        gear = await self.get_gear(gear_id)
        if not gear:
            return None
        
        if not gear.is_ready:
            return None
        
        gear.use(success)
        
        update_data = {
            "last_used_at": gear.last_used_at,
            "usage_count": gear.usage_count,
            "experience": gear.experience,
            "level": gear.level,
            "power": gear.power,
            "success_rate": gear.success_rate,
            "updated_at": datetime.now(),
        }
        
        await self.update_gear(gear_id, **update_data)
        
        return await self.get_gear(gear_id)
    
    async def create_skill_gear(
        self,
        agent_id: str,
        skill: SkillModel,
    ) -> SkillGear:
        """从技能创建装备"""
        gear = await self.create_gear(
            agent_id=agent_id,
            name=skill.name,
            description=skill.description,
            gear_type=GearType.SKILL,
            slot=GearSlot.PRIMARY,
            rarity=self._get_rarity_from_success_rate(skill.success_rate),
            source_id=skill.id,
            metadata={
                "category": skill.category,
                "trigger_keywords": skill.trigger_keywords or [],
                "implementation": skill.implementation or {},
            },
        )
        
        return SkillGear(
            **self._gear_to_dict(gear),
            skill_category=skill.category,
            trigger_keywords=skill.trigger_keywords or [],
            implementation=skill.implementation or {},
        )
    
    async def create_memory_gear(
        self,
        agent_id: str,
        memory: MemoryEntryModel,
    ) -> MemoryGear:
        """从记忆创建装备"""
        gear = await self.create_gear(
            agent_id=agent_id,
            name=f"记忆: {memory.content[:20]}...",
            description=memory.content[:100],
            gear_type=GearType.MEMORY,
            slot=GearSlot.SECONDARY,
            rarity=self._get_rarity_from_relevance(memory.relevance_score),
            source_id=memory.id,
            metadata={
                "memory_level": memory.level,
                "tags": memory.tags or [],
            },
        )
        
        return MemoryGear(
            **self._gear_to_dict(gear),
            memory_level=memory.level,
            relevance_score=memory.relevance_score,
            tags=memory.tags or [],
        )
    
    async def create_tool_gear(
        self,
        agent_id: str,
        tool_name: str,
        tool_description: str,
        tool_parameters: Dict[str, Any],
        tool_server: str,
    ) -> ToolGear:
        """创建工具装备"""
        gear = await self.create_gear(
            agent_id=agent_id,
            name=tool_name,
            description=tool_description,
            gear_type=GearType.TOOL,
            slot=GearSlot.UTILITY,
            rarity=GearRarity.RARE,
            metadata={
                "tool_parameters": tool_parameters,
                "tool_server": tool_server,
            },
        )
        
        return ToolGear(
            **self._gear_to_dict(gear),
            tool_name=tool_name,
            tool_description=tool_description,
            tool_parameters=tool_parameters,
            tool_server=tool_server,
        )
    
    async def get_agent_equipment(self, agent_id: str) -> AgentEquipment:
        """获取Agent的装备栏"""
        gears = await self.get_agent_gears(agent_id)
        return AgentEquipment(agent_id=agent_id, gears=gears)
    
    async def get_equipped_gears(self, agent_id: str) -> List[Gear]:
        """获取已装备的装备"""
        result = await self.db.execute(
            select(GearModel)
            .where(GearModel.agent_id == agent_id)
            .where(GearModel.equipped == True)
        )
        db_gears = result.scalars().all()
        
        return [self._db_to_gear(g) for g in db_gears]
    
    def _db_to_gear(self, db_gear: GearModel) -> Gear:
        """数据库模型转装备对象"""
        gear_type = GearType(db_gear.gear_type)
        
        if gear_type == GearType.SKILL:
            return SkillGear(
                id=db_gear.id,
                name=db_gear.name,
                description=db_gear.description,
                gear_type=gear_type,
                rarity=GearRarity(db_gear.rarity),
                slot=GearSlot(db_gear.slot),
                power=db_gear.power,
                level=db_gear.level,
                experience=db_gear.experience,
                cooldown_seconds=db_gear.cooldown_seconds,
                last_used_at=db_gear.last_used_at,
                usage_count=db_gear.usage_count,
                success_rate=db_gear.success_rate,
                metadata=db_gear.metadata or {},
                source_id=db_gear.source_id,
                equipped=db_gear.equipped,
                skill_category=db_gear.metadata.get("category"),
                trigger_keywords=db_gear.metadata.get("trigger_keywords", []),
                implementation=db_gear.metadata.get("implementation", {}),
            )
        elif gear_type == GearType.MEMORY:
            return MemoryGear(
                id=db_gear.id,
                name=db_gear.name,
                description=db_gear.description,
                gear_type=gear_type,
                rarity=GearRarity(db_gear.rarity),
                slot=GearSlot(db_gear.slot),
                power=db_gear.power,
                level=db_gear.level,
                experience=db_gear.experience,
                cooldown_seconds=db_gear.cooldown_seconds,
                last_used_at=db_gear.last_used_at,
                usage_count=db_gear.usage_count,
                success_rate=db_gear.success_rate,
                metadata=db_gear.metadata or {},
                source_id=db_gear.source_id,
                equipped=db_gear.equipped,
                memory_level=db_gear.metadata.get("memory_level"),
                relevance_score=db_gear.metadata.get("relevance_score", 1.0),
                tags=db_gear.metadata.get("tags", []),
            )
        elif gear_type == GearType.TOOL:
            return ToolGear(
                id=db_gear.id,
                name=db_gear.name,
                description=db_gear.description,
                gear_type=gear_type,
                rarity=GearRarity(db_gear.rarity),
                slot=GearSlot(db_gear.slot),
                power=db_gear.power,
                level=db_gear.level,
                experience=db_gear.experience,
                cooldown_seconds=db_gear.cooldown_seconds,
                last_used_at=db_gear.last_used_at,
                usage_count=db_gear.usage_count,
                success_rate=db_gear.success_rate,
                metadata=db_gear.metadata or {},
                source_id=db_gear.source_id,
                equipped=db_gear.equipped,
                tool_name=db_gear.metadata.get("tool_name", db_gear.name),
                tool_description=db_gear.description,
                tool_parameters=db_gear.metadata.get("tool_parameters", {}),
                tool_server=db_gear.metadata.get("tool_server"),
            )
        else:
            return Gear(
                id=db_gear.id,
                name=db_gear.name,
                description=db_gear.description,
                gear_type=gear_type,
                rarity=GearRarity(db_gear.rarity),
                slot=GearSlot(db_gear.slot),
                power=db_gear.power,
                level=db_gear.level,
                experience=db_gear.experience,
                cooldown_seconds=db_gear.cooldown_seconds,
                last_used_at=db_gear.last_used_at,
                usage_count=db_gear.usage_count,
                success_rate=db_gear.success_rate,
                metadata=db_gear.metadata or {},
                source_id=db_gear.source_id,
                equipped=db_gear.equipped,
            )
    
    def _gear_to_dict(self, gear: Gear) -> Dict[str, Any]:
        """装备对象转字典"""
        return {
            "id": gear.id,
            "name": gear.name,
            "description": gear.description,
            "gear_type": gear.gear_type,
            "rarity": gear.rarity,
            "slot": gear.slot,
            "power": gear.power,
            "level": gear.level,
            "experience": gear.experience,
            "cooldown_seconds": gear.cooldown_seconds,
            "last_used_at": gear.last_used_at,
            "usage_count": gear.usage_count,
            "success_rate": gear.success_rate,
            "metadata": gear.metadata,
            "source_id": gear.source_id,
            "equipped": gear.equipped,
        }
    
    def _get_rarity_from_success_rate(self, success_rate: float) -> GearRarity:
        """根据成功率确定稀有度"""
        if success_rate >= 0.9:
            return GearRarity.LEGENDARY
        elif success_rate >= 0.7:
            return GearRarity.EPIC
        elif success_rate >= 0.5:
            return GearRarity.RARE
        elif success_rate >= 0.3:
            return GearRarity.UNCOMMON
        else:
            return GearRarity.COMMON
    
    def _get_rarity_from_relevance(self, relevance: float) -> GearRarity:
        """根据相关性确定稀有度"""
        if relevance >= 0.9:
            return GearRarity.LEGENDARY
        elif relevance >= 0.7:
            return GearRarity.EPIC
        elif relevance >= 0.5:
            return GearRarity.RARE
        elif relevance >= 0.3:
            return GearRarity.UNCOMMON
        else:
            return GearRarity.COMMON

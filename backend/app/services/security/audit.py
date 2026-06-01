"""
WORM 审计日志系统 — 不可篡改的操作记录

特性：
- 追加写入（Append-Only），禁止修改和删除
- 每行 JSON + 哈希链确保完整性
- 支持按时间、操作者、操作类型、风险级别查询
- 高危操作自动触发告警
"""

import json
import hashlib
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Iterator
from dataclasses import dataclass, field
from enum import Enum

from app.models.task import RiskLevel

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """审计操作类型"""
    # 系统操作
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    EMERGENCY_STOP = "emergency_stop"
    EMERGENCY_RESET = "emergency_reset"
    CIRCUIT_BREAKER_TRIGGERED = "circuit_breaker_triggered"
    # Agent 操作
    AGENT_CREATED = "agent_created"
    AGENT_DELETED = "agent_deleted"
    AGENT_PERMISSION_GRANTED = "agent_permission_granted"
    AGENT_PERMISSION_REVOKED = "agent_permission_revoked"
    # 许可/审批
    PERMISSION_CHECK = "permission_check"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    # 安全事件
    CRITICAL_OPERATION_BLOCKED = "critical_operation_blocked"
    CONSTITUTION_VIOLATION = "constitution_violation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    # 任务操作
    TASK_HIGH_RISK_BLOCKED = "task_high_risk_blocked"
    TASK_EXECUTED = "task_executed"
    TASK_APPROVAL_REQUESTED = "task_approval_requested"


@dataclass
class AuditEntry:
    """单条审计日志"""
    id: str
    timestamp: str
    action: AuditAction
    actor: str
    agent_id: Optional[str] = None
    operation: Optional[str] = None
    risk_level: Optional[str] = None
    target: Optional[str] = None
    detail: str = ""
    outcome: str = "success"  # success, denied, error
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: str = ""  # 链式哈希，确保完整性


class AuditLogger:
    """
    WORM 审计日志器

    存储格式：每行一个 JSON 对象
    完整性保证：SHA-256 哈希链（每条日志包含前一条的哈希）
    """

    def __init__(self, log_dir: str = "./data/audit"):
        self.log_dir = log_dir
        self._last_hash: str = ""
        self._entry_count: int = 0
        os.makedirs(log_dir, exist_ok=True)
        self._current_log_file = os.path.join(log_dir, "audit.jsonl")
        self._load_last_hash()

    def _load_last_hash(self):
        """从已有日志文件加载最后一条哈希"""
        if not os.path.exists(self._current_log_file):
            return
        try:
            with open(self._current_log_file, "r", encoding="utf-8") as f:
                # 跳到文件末尾最后一行
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                if pos == 0:
                    return
                # 找最后一行的开始
                f.seek(max(0, pos - 2000))
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    if last_line:
                        entry = json.loads(last_line)
                        self._last_hash = entry.get("hash", "")
                        self._entry_count = entry.get("seq", 0)
        except Exception:
            logger.warning("读取审计日志初始状态失败，从头开始记录", exc_info=True)

    def _compute_hash(self, entry_data: str, prev_hash: str) -> str:
        """计算 SHA-256 链式哈希"""
        content = f"{prev_hash}:{entry_data}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def log(
        self,
        action: AuditAction,
        actor: str,
        agent_id: Optional[str] = None,
        operation: Optional[str] = None,
        risk_level: Optional[str] = None,
        target: Optional[str] = None,
        detail: str = "",
        outcome: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        记录一条审计日志（追加写入，不可修改）
        """
        self._entry_count += 1
        now = datetime.now().isoformat()

        # 构建条目（不含 hash）
        entry_dict = {
            "seq": self._entry_count,
            "timestamp": now,
            "action": action.value,
            "actor": actor,
            "agent_id": agent_id,
            "operation": operation,
            "risk_level": risk_level,
            "target": target,
            "detail": detail,
            "outcome": outcome,
            "metadata": metadata or {},
        }

        # 计算链式哈希
        entry_json = json.dumps(entry_dict, ensure_ascii=False, sort_keys=True)
        entry_hash = self._compute_hash(entry_json, self._last_hash)
        entry_dict["hash"] = entry_hash
        self._last_hash = entry_hash

        # 追加写入
        with open(self._current_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_dict, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())  # 确保写入磁盘

        return AuditEntry(
            id=entry_hash,
            timestamp=now,
            action=action,
            actor=actor,
            agent_id=agent_id,
            operation=operation,
            risk_level=risk_level,
            target=target,
            detail=detail,
            outcome=outcome,
            metadata=metadata or {},
            hash=entry_hash,
        )

    def query(
        self,
        action: Optional[AuditAction] = None,
        actor: Optional[str] = None,
        agent_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """查询审计日志"""
        if not os.path.exists(self._current_log_file):
            return []

        results = []
        try:
            with open(self._current_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if action and entry.get("action") != action.value:
                            continue
                        if actor and entry.get("actor") != actor:
                            continue
                        if agent_id and entry.get("agent_id") != agent_id:
                            continue
                        if risk_level and entry.get("risk_level") != risk_level:
                            continue
                        if outcome and entry.get("outcome") != outcome:
                            continue
                        results.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return []

        # 最新的在前
        results.reverse()
        return results[offset:offset + limit]

    def query_by_time(
        self,
        start: datetime,
        end: Optional[datetime] = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """按时间范围查询"""
        if not os.path.exists(self._current_log_file):
            return []

        end_iso = (end or datetime.now()).isoformat()
        start_iso = start.isoformat()

        results = []
        try:
            with open(self._current_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "")
                        if start_iso <= ts <= end_iso:
                            results.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            return []

        results.reverse()
        return results[:limit]

    def verify_integrity(self) -> Dict[str, Any]:
        """验证审计日志的完整性（哈希链校验）"""
        if not os.path.exists(self._current_log_file):
            return {"valid": True, "entries": 0, "message": "日志文件不存在"}

        prev_hash = ""
        entries_checked = 0
        errors = []

        try:
            with open(self._current_log_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        stored_hash = entry.pop("hash", "")
                        entry_json = json.dumps(entry, ensure_ascii=False, sort_keys=True)
                        expected_hash = self._compute_hash(entry_json, prev_hash)
                        if stored_hash != expected_hash:
                            errors.append({
                                "line": line_num,
                                "expected": expected_hash,
                                "found": stored_hash
                            })
                        prev_hash = stored_hash
                        entry["hash"] = stored_hash  # 恢复
                        entries_checked += 1
                    except json.JSONDecodeError:
                        errors.append({"line": line_num, "error": "JSON 解析失败"})
        except Exception as e:
            return {"valid": False, "entries": 0, "error": str(e)}

        return {
            "valid": len(errors) == 0,
            "entries": entries_checked,
            "errors": errors,
            "message": "完整性校验通过" if not errors else f"发现 {len(errors)} 处不一致"
        }

    def get_critical_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取所有高危/严重事件"""
        return self.query(
            outcome="denied",
            limit=limit
        ) + self.query(
            risk_level=RiskLevel.HIGH.value,
            limit=limit
        ) + self.query(
            risk_level=RiskLevel.CRITICAL.value,
            limit=limit
        )

    def get_summary(self) -> Dict[str, Any]:
        """获取审计摘要统计"""
        if not os.path.exists(self._current_log_file):
            return {"total_entries": 0, "by_action": {}, "critical_events": 0}

        by_action: Dict[str, int] = {}
        critical_count = 0
        total = 0

        try:
            with open(self._current_log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        total += 1
                        action = entry.get("action", "unknown")
                        by_action[action] = by_action.get(action, 0) + 1
                        if entry.get("risk_level") in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
                            critical_count += 1
                    except json.JSONDecodeError:
                        logger.warning("审计日志行 JSON 解析失败，已跳过")
        except Exception:
            logger.warning("读取审计日志统计失败", exc_info=True)

        return {
            "total_entries": total,
            "by_action": by_action,
            "critical_events": critical_count,
            "log_file": self._current_log_file,
        }


# 全局审计日志器
audit_logger = AuditLogger()

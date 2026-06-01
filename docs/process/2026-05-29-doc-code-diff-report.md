# 文档与代码差异报告
日期: 2026-05-29 | 状态: 已完成

## 背景

文档系统需要重构，使其真实反映代码实现。本报告对比了 `docs/` 中 97 个文档与实际代码的差异，分为三部分：目录结构差异、功能实现差异、设计理念冲突。

---

## 一、目录结构差异

### 1.1 structure.md 过于简化

文档 `docs/03-development/structure.md` 描述的目录结构与实际严重不符：

| 实际存在的目录 | 文档是否提到 |
|---------------|-------------|
| `backend/app/database/` | ❌ 未提及 |
| `backend/app/prompts/` | ❌ 未提及 |
| `backend/app/services/` 下 13 个子模块 | ❌ 只写"业务服务"，未展开 |
| `backend/agents/`（9 个 Agent 人才库） | ❌ 未提及 |
| `frontend/src/hooks/` | ❌ 未提及 |
| `frontend/src/test/` | ❌ 未提及 |

### 1.2 README.md 目录结构完全过时

`README.md` 第 134-172 行描述的 docs 结构是旧版：

```
# README 写的（旧版，不存在）
docs/design/01-overview/
docs/development/01-setup/

# 实际结构
docs/01-project/
docs/02-design/
docs/03-development/
...
```

README 还提到 `frontend/src/api/` 目录，但实际不存在（API 调用在 `src/lib/api.ts`）。

### 1.3 根目录游离文件

根目录散落 6 个不属于任何模块的文件：
- `test_agent_config.py`（应在 `backend/tests/`）
- `test_ids.txt`（临时文件）
- `verify_collaboration.py`（应在 `scripts/`）
- `agents_check.json`（数据文件）
- `多智能体协作工具特性报告.md`（应在 `docs/`）

---

## 二、功能实现差异

### 2.1 文档描述了但代码未实现（8 项）

| # | 功能 | 文档位置 | 代码现状 | 严重程度 |
|---|------|---------|---------|---------|
| 1 | 自我学习"模式发现" | self-learning.md 第125行 | 完全未实现 | 高 |
| 2 | soul.md 优化建议生成 | self-learning.md 第70行 | 未实现 | 高 |
| 3 | 复盘产出到共享向量库 | self-learning.md 第79行 | 未实现 | 高 |
| 4 | 统筹 Agent 汇总执行数据 | self-learning.md 第30行 | 简化为直接调用 | 中 |
| 5 | Skill 应为 SKILL.md 文件 | self-learning.md 第48行 | 实际存数据库 | 中 |
| 6 | soul.md 持续更新 | collaboration.md 第32行 | 只更新 growth.json | 中 |
| 7 | Agent 间纠错建议 | collaboration.md 第98行 | 未实现 | 中 |
| 8 | 复盘手动触发记忆晋升 | memory-system.md 第79行 | 只有自动规则 | 中 |

**关键发现**：自我学习系统的三条产出路径只实现了约 1/3：
- 路径 1（SKILL.md）：部分实现（存数据库，非文件）
- 路径 2（soul 优化）：未实现
- 路径 3（共享向量库）：未实现

### 2.2 代码实现了但文档未描述（10 项）

| # | 功能 | 代码位置 | 文档现状 |
|---|------|---------|---------|
| 1 | Pipeline IDLE 状态 | pipeline_orchestrator.py:24 | task-model.md 未记录 |
| 2 | WAITING_FOR_USER 状态 | task.py:16 | task-model.md 未记录 |
| 3 | 上下文压缩（6种策略） | memory_compressor.py | memory-system.md 未提及 |
| 4 | 记忆增强（衰减/去重/隐私） | memory_enhancement.py | memory-system.md 未详述 |
| 5 | CapacityManager | memory_forget.py:308 | memory-system.md 未描述算法 |
| 6 | 项目级消息方法 | message_bus.py:200 | collaboration.md 未记录 |
| 7 | Token 预算管理 | speaking_controller.py:26 | 无文档 |
| 8 | escalate_to_human 机制 | arbitrator.py:253 | collaboration.md 未详述 |
| 9 | Coordinator 选举机制 | discussion_orchestrator.py:415 | collaboration.md 未描述 |
| 10 | Kahn 拓扑排序 | pipeline_orchestrator.py:1090 | task-model.md 仅概述 |

### 2.3 文档与代码不一致（7 项）

| # | 差异点 | 文档描述 | 代码实际 |
|---|--------|---------|---------|
| 1 | Task 状态转移 | in_progress 可回 todo | 代码不允许回退 |
| 2 | auto 策略行为 | LLM 自动推荐 | 运行时退化为 FIFO 轮询 |
| 3 | 复盘触发时机 | 大任务验收后触发 | 每个 pipeline 完成都触发 |
| 4 | L1 记忆生命周期 | 会话期间 | 代码持久化到数据库 |
| 5 | 复盘手动晋升 | 双轨晋升 | 只有自动规则 |
| 6 | web_application 策略 | hierarchical | 代码是 pipeline |
| 7 | 任务状态数量 | 8 种 | 实际 9 种（含 WAITING_FOR_USER） |

---

## 三、设计理念冲突（20 处）

### 3.1 严重矛盾（直接影响系统理解）

**冲突 1：Pipeline 阶段数量**
- task-model.md：固定五阶段（需求分析→任务拆解→DAG并行→互审→完成）
- project-service.md：另一套五阶段（需求→设计→开发→测试→部署）
- ADR-002：标准六阶段（但枚举只列了 5 个）
- collaboration.md：动态阶段（LLM 可调整）
- **四处互不一致，无文档说明关系**

**冲突 2：向量检索技术选型**
- architecture.md：Chroma / FAISS 并列
- memory-system-research.md：明确选 FAISS
- memory-service.md：依赖 FAISS
- **architecture.md 落后于实际决策**

**冲突 3：changelog 与设计文档版本脱节**
- changelog.md 最新：v2.7（2026-05-19）
- collaboration.md：v3.1（2026-05-27）
- **v2.8-v3.1 的变更完全未记录**

### 3.2 中等矛盾（版本管理问题）

**冲突 4-10：6 个文件内部版本号不一致**

| 文件 | 头部版本 | 尾部版本 |
|------|---------|---------|
| task-model.md | v2.0 | v2.1 |
| communication.md | v3.0 | v2.1 |
| memory-system.md | v2.0 | v2.1 |
| self-learning.md | v2.0 | v2.1 |
| agent-model.md | v2.0 | v2.1 |
| intervention.md | v2.0 | v2.1 |
| pipeline-orchestrator.md | v3.0 | 混乱（v2.1/v2.2/v3.0 并存） |

**冲突 11：Pipeline 模板数量**
- changelog：18 种
- collaboration.md 实际列出：17 种

### 3.3 理念张力（设计演进未同步）

**冲突 12：Agent 角色分配**
- vision.md：无预设角色，任务驱动临时职责
- vision.md（同一文件）：固定统筹 Agent 主导协作
- ADR-002：人工选择 + 系统建议
- **三种理念并存，早期文档未更新**

**冲突 13："文档驱动" vs "动态阶段"**
- vision.md：文档驱动，确保每个环节有可追溯产出
- ADR-002：不做固定阶段，LLM 动态决定
- **确定性 vs 灵活性的张力未解决**

**冲突 14：灰盒模型措辞**
- vision.md：内部过程对用户透明
- task-model.md：透明但默认不看
- agent-model.md：用户可查看但默认不需要关心
- **措辞差异虽小，但语义有微妙区别**

---

## 四、开发进度评估

### 4.1 已实现且文档较完整

- ✅ Pipeline 编排系统（状态机、模板、阶段门控）
- ✅ 消息总线（发布-订阅、多维频道）
- ✅ 仲裁系统（投票、冲突解决）
- ✅ 记忆系统基础（三层存储、遗忘策略、晋升规则）
- ✅ Agent 人才库（soul.md、growth.json）
- ✅ 任务看板（状态机、DAG 依赖）
- ✅ 装备系统
- ✅ 安全审计

### 4.2 已实现但文档缺失/不足

- ⚠️ 上下文压缩（6 种策略，无文档）
- ⚠️ 记忆增强（衰减/去重/隐私，文档不足）
- ⚠️ Token 预算管理（无文档）
- ⚠️ Coordinator 选举机制（无文档）
- ⚠️ Pipeline 状态机（代码有 IDLE 状态，文档未记录）
- ⚠️ WAITING_FOR_USER 任务状态（代码有，文档未记录）

### 4.3 文档描述但未实现

- ❌ 模式发现（4 种模式分析）
- ❌ soul.md 优化建议流程
- ❌ 复盘产出到共享向量库
- ❌ Agent 间纠错建议
- ❌ 复盘手动触发记忆晋升

### 4.4 版本状态混乱

- changelog 停留在 v2.7
- 设计文档已到 v3.1
- 6 个文件内部版本号不一致
- v2.8-v3.1 变更无记录

---

## 五、重构建议优先级

### P0：修复严重矛盾

1. 统一 Pipeline 阶段描述（确认是动态阶段后，更新 task-model.md 和 project-service.md）
2. 更新 changelog 到 v3.1
3. 统一所有文件的版本号
4. 更新 architecture.md 向量检索为 FAISS

### P1：补充缺失文档

1. 为已实现但无文档的功能补充文档（上下文压缩、Token 预算等）
2. 更新 task-model.md 增加 WAITING_FOR_USER 状态
3. 更新 task-model.md 增加 Pipeline 状态机

### P2：标记未实现功能

1. 在 self-learning.md 中明确标注哪些功能未实现
2. 在 collaboration.md 中标注 soul.md 更新未实现

### P3：修复目录结构文档

1. 更新 structure.md 反映实际目录
2. 更新 README.md 目录结构
3. 清理根目录游离文件

---

## 六、用户确认与决策（2026-05-29）

### 一、目录结构差异处理

- 过时的目录结构描述要及时清理
- 与实际不符的目录结构按照实际情况更新
- 根目录游离文件需要评估：是什么、有没有用、应该放哪里

### 二、功能实现差异处理

| 类型 | 处理方式 |
|------|---------|
| 文档描述但代码未实现 | **保留文档**，是计划中没来得及实现的功能，后续继续开发 |
| 代码实现但文档未描述 | **补充文档**，开发中调整了代码但没更新文档 |
| 文档与代码不一致 | **新建"差异追踪"区域**，专门记录不一致的地方，后续 BUG 修复期间逐个修复 |

### 三、设计理念决策

| 冲突 | 决策 |
|------|------|
| Pipeline 阶段数量 | **预设标准阶段 + LLM 可调整**。用户可直接用预设阶段，也可让 LLM 调整后使用 |
| 向量检索技术选型 | **以代码实现为准**（FAISS） |
| changelog 版本脱节 | **MVP 后再记录**，项目还没调通，暂不维护 changelog |
| 文件内版本号 | **统一版本号**，发生更改及时更新。需要制定版本管理规则 |
| Pipeline 模板数量 | **以实际代码为准**更新文档 |
| Agent 角色分配 | **无预设角色，任务驱动临时职责**。统筹 Agent 不是角色，是协作模式下分配给某个 Agent 的任务。人工选择和系统建议只是选择 Agent 的方法，不是选择角色 |
| "文档驱动" vs "动态阶段" | **不做固定阶段，LLM 动态决定**。文档是为了更好衔接阶段，阶段间不一定用文档传递信息，只是当文档传递效率高时可以用文档 |
| 灰盒模型 | **改为白盒模型**。内部细节用户都能掌控 |

### 四、开发进度评估

由 AI 自行评估，基于代码实现状态。

---

## 七、信息保留说明

本报告基于 2026-05-29 的代码和文档状态。重构过程中：

- **不会删除任何设计文档**（只更新内容使其反映代码）
- **不会删除过程文档**（保留本报告作为历史记录）
- **备份已创建**：`docs_backup_20260529/`

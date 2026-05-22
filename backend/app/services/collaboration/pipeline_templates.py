"""
Pipeline 阶段模板定义

Pipeline（WHAT）与 协作策略（HOW）正交：
- Pipeline = 任务分哪些阶段、每个阶段产出什么
- 协作策略 = Agent 之间如何互动

用户选择模板后，LLM 在需求分析阶段可以调整（增加/删除/重排/改名）。
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from app.services.shared.prompt_registry import registry


@dataclass
class StageDefinition:
    """单个阶段定义"""
    key: str
    label: str
    description: str = ""
    expected_artifact: str = ""  # 预期产出物描述
    parallel_group: Optional[str] = None  # 同组可并行执行


@dataclass
class PipelineTemplate:
    """Pipeline 阶段模板"""
    id: str
    name: str
    description: str
    category: str  # "simple" | "development" | "design" | "complex"
    suggested_strategy: str  # "sequential" | "hierarchical" | "discussion"
    stages: List[StageDefinition] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "suggested_strategy": self.suggested_strategy,
            "stages": [
                {
                    "key": s.key,
                    "label": s.label,
                    "description": s.description,
                    "expected_artifact": s.expected_artifact,
                    "parallel_group": s.parallel_group,
                }
                for s in self.stages
            ],
        }


def get_all_templates() -> List[PipelineTemplate]:
    """获取所有预定义 Pipeline 模板"""
    return [
        # ======================== 📝 简单任务 ========================
        PipelineTemplate(
            id="script_automation",
            name="脚本自动化",
            description="编写自动化脚本，如数据导出、文件处理、定时任务",
            category="simple",
            suggested_strategy="sequential",
            stages=[
                StageDefinition("requirement", "需求理解", "理解脚本需求和输入输出", "需求摘要.md"),
                StageDefinition("coding", "脚本编写", "编写脚本代码", "脚本代码/"),
                StageDefinition("verify", "运行验证", "运行脚本验证输出正确性", "验证结果.md"),
            ],
        ),
        PipelineTemplate(
            id="knowledge_research",
            name="知识查询与研究",
            description="查询技术知识、分析概念、调研方案",
            category="simple",
            suggested_strategy="sequential",
            stages=[
                StageDefinition("analyze", "问题拆解", "拆解问题，确定研究方向", "问题分析.md"),
                StageDefinition("research", "信息检索", "搜索和分析相关资料", "调研笔记.md"),
                StageDefinition("summary", "总结输出", "整理研究结果，输出报告", "研究报告.md"),
            ],
        ),
        PipelineTemplate(
            id="bug_fix",
            name="Bug 修复",
            description="排查和修复代码缺陷",
            category="simple",
            suggested_strategy="sequential",
            stages=[
                StageDefinition("reproduce", "问题复现", "复现 Bug，确认问题", "复现步骤.md"),
                StageDefinition("analysis", "根因分析", "分析代码找出根因", "根因分析.md"),
                StageDefinition("fix", "代码修复", "修复代码并自测", "修复代码/"),
                StageDefinition("regression", "回归验证", "验证修复不影响其他功能", "验证结果.md"),
            ],
        ),
        PipelineTemplate(
            id="doc_improvement",
            name="文档编写",
            description="编写或改进技术文档、API 文档、用户手册",
            category="simple",
            suggested_strategy="sequential",
            stages=[
                StageDefinition("assess", "现状评估", "评估现有文档的完整性和质量", "评估记录.md"),
                StageDefinition("write", "内容编写", "编写文档内容", "文档/"),
                StageDefinition("review", "审核校对", "审核文档准确性和可读性", "审核意见.md"),
            ],
        ),
        PipelineTemplate(
            id="config_setup",
            name="环境配置",
            description="搭建开发环境、配置 CI/CD、设置部署环境",
            category="simple",
            suggested_strategy="sequential",
            stages=[
                StageDefinition("analyze", "环境分析", "分析目标环境和依赖", "环境说明.md"),
                StageDefinition("setup", "配置实施", "执行配置和安装", "配置文件/"),
                StageDefinition("verify", "验证", "验证环境可用性", "验证结果.md"),
            ],
        ),

        # ======================== 🏗️ 开发项目 ========================
        PipelineTemplate(
            id="web_application",
            name="Web 应用",
            description="全栈 Web 应用，前后端分离架构",
            category="development",
            suggested_strategy="pipeline",
            stages=[
                StageDefinition("requirement", "需求分析", "分析用户需求，明确功能范围", "需求文档.md"),
                StageDefinition("design", "架构设计", "设计系统架构和技术方案", "技术方案.md"),
                StageDefinition("backend", "后端开发", "实现后端 API 和数据库", "后端代码/", parallel_group="dev"),
                StageDefinition("frontend", "前端开发", "实现前端页面和交互", "前端代码/", parallel_group="dev"),
                StageDefinition("integration", "集成测试", "前后端联调和端到端测试", "测试报告.md"),
                StageDefinition("deployment", "部署上线", "部署到生产环境", "部署配置/"),
            ],
        ),
        PipelineTemplate(
            id="api_service",
            name="API 服务",
            description="纯后端 API 服务开发",
            category="development",
            suggested_strategy="pipeline",
            stages=[
                StageDefinition("requirement", "需求分析", "分析 API 需求和使用场景", "需求文档.md"),
                StageDefinition("design", "接口设计", "设计 API 接口和数据结构", "API设计.md"),
                StageDefinition("implement", "开发实现", "实现 API 逻辑", "代码/"),
                StageDefinition("test", "测试", "接口测试和性能测试", "测试报告.md"),
                StageDefinition("deploy", "部署", "部署 API 服务", "部署配置/"),
            ],
        ),
        PipelineTemplate(
            id="data_pipeline",
            name="数据处理",
            description="数据 ETL、数据仓库、数据分析流水线",
            category="development",
            suggested_strategy="pipeline",
            stages=[
                StageDefinition("requirement", "需求分析", "分析数据处理需求", "需求文档.md"),
                StageDefinition("modeling", "数据建模", "设计数据模型和 schema", "数据模型.md"),
                StageDefinition("etl", "ETL开发", "实现数据抽取、转换、加载", "ETL代码/"),
                StageDefinition("validate", "质量验证", "验证数据质量和准确性", "验证报告.md"),
                StageDefinition("deploy", "部署", "部署数据处理流水线", "部署配置/"),
            ],
        ),
        PipelineTemplate(
            id="cli_tool",
            name="CLI 工具",
            description="命令行工具开发",
            category="development",
            suggested_strategy="pipeline",
            stages=[
                StageDefinition("requirement", "需求分析", "分析 CLI 工具用法和交互", "需求文档.md"),
                StageDefinition("develop", "核心开发", "实现核心功能", "代码/"),
                StageDefinition("test", "测试", "功能测试和边界测试", "测试报告.md"),
                StageDefinition("release", "文档+发布", "编写 README 和发布说明", "README.md"),
            ],
        ),
        PipelineTemplate(
            id="mobile_app",
            name="移动应用",
            description="跨平台移动应用开发",
            category="development",
            suggested_strategy="pipeline",
            stages=[
                StageDefinition("requirement", "需求分析", "分析移动端功能需求", "需求文档.md"),
                StageDefinition("prototype", "原型设计", "设计 UI 原型和交互流程", "原型/"),
                StageDefinition("frontend", "前端开发", "实现移动端界面", "代码/", parallel_group="dev"),
                StageDefinition("backend", "后端开发", "实现后端 API", "代码/", parallel_group="dev"),
                StageDefinition("test", "适配测试", "多设备兼容性和性能测试", "测试报告.md"),
                StageDefinition("release", "打包发布", "打包和发布到应用商店", None),
            ],
        ),
        PipelineTemplate(
            id="browser_extension",
            name="浏览器扩展",
            description="浏览器扩展/插件开发",
            category="development",
            suggested_strategy="pipeline",
            stages=[
                StageDefinition("requirement", "需求分析", "分析扩展功能和权限", "需求文档.md"),
                StageDefinition("develop", "功能开发", "实现扩展功能", "代码/"),
                StageDefinition("test", "兼容测试", "多浏览器兼容性测试", "测试报告.md"),
                StageDefinition("publish", "打包发布", "打包和发布到应用商店", "发布包/"),
            ],
        ),

        # ======================== 🧭 方案设计 ========================
        PipelineTemplate(
            id="tech_evaluation",
            name="技术选型评估",
            description="对比评估技术方案和工具选型",
            category="design",
            suggested_strategy="discussion",
            stages=[
                StageDefinition("requirement", "需求梳理", "梳理技术需求和约束条件", "需求清单.md"),
                StageDefinition("research", "方案调研", "调研候选技术和方案", "候选方案.md"),
                StageDefinition("compare", "对比分析", "多维度对比分析", "对比表.md"),
                StageDefinition("recommend", "决策建议", "输出推荐方案和理由", "推荐方案.md"),
            ],
        ),
        PipelineTemplate(
            id="architecture_design",
            name="架构方案设计",
            description="系统架构设计和技术方案制定",
            category="design",
            suggested_strategy="discussion",
            stages=[
                StageDefinition("current", "现状分析", "分析现有系统或需求现状", "现状报告.md"),
                StageDefinition("draft", "方案设计", "设计架构方案草案", "设计草案/"),
                StageDefinition("review", "评审讨论", "团队评审和讨论", "评审记录.md"),
                StageDefinition("finalize", "设计定稿", "确定最终架构方案", "架构设计.md"),
            ],
        ),
        PipelineTemplate(
            id="refactor_plan",
            name="重构方案设计",
            description="代码重构计划和技术债务清理",
            category="design",
            suggested_strategy="discussion",
            stages=[
                StageDefinition("analysis", "代码分析", "分析代码质量和问题点", "代码评估.md"),
                StageDefinition("design", "重构设计", "设计重构方案和目标", "重构方案.md"),
                StageDefinition("risk", "风险评估", "评估重构风险和控制措施", "风险评估.md"),
                StageDefinition("plan", "实施计划", "制定分步实施计划", "执行计划.md"),
            ],
        ),

        # ======================== 🏢 复杂系统 ========================
        PipelineTemplate(
            id="saas_platform",
            name="SaaS 平台",
            description="多租户 SaaS 平台开发",
            category="complex",
            suggested_strategy="hierarchical",
            stages=[
                StageDefinition("requirement", "需求分析", "分析多租户需求和业务模型", "需求文档.md"),
                StageDefinition("architecture", "系统架构", "设计高可用系统架构", "架构设计.md"),
                StageDefinition("modules", "模块拆分", "拆分功能模块和边界", "模块清单.md"),
                StageDefinition("develop", "并行开发", "多模块并行开发", "各模块代码/", parallel_group="dev"),
                StageDefinition("integrate", "集成测试", "全系统集成和性能测试", "测试报告.md"),
                StageDefinition("deploy", "部署上线", "生产部署和运维配置", "运维手册.md"),
            ],
        ),
        PipelineTemplate(
            id="microservice_system",
            name="微服务系统",
            description="微服务架构系统设计和开发",
            category="complex",
            suggested_strategy="hierarchical",
            stages=[
                StageDefinition("domain", "业务分析", "领域分析和限界上下文划分", "领域分析.md"),
                StageDefinition("split", "服务拆分", "定义服务边界和接口契约", "服务边界图.md"),
                StageDefinition("develop", "并行开发", "多服务并行开发", "各服务代码/", parallel_group="dev"),
                StageDefinition("integrate", "集成测试", "服务间集成和契约测试", "测试报告.md"),
                StageDefinition("deploy", "容器化部署", "容器编排和服务部署", "部署配置/"),
            ],
        ),
        PipelineTemplate(
            id="ai_application",
            name="AI 应用",
            description="AI/LLM 应用开发",
            category="complex",
            suggested_strategy="hierarchical",
            stages=[
                StageDefinition("scenario", "场景分析", "定义 AI 应用场景和评估指标", "场景定义.md"),
                StageDefinition("data", "数据准备", "数据收集、清洗和标注", "数据说明.md"),
                StageDefinition("model", "模型开发", "模型训练/调优/Prompt 工程", "模型代码/"),
                StageDefinition("evaluate", "评估优化", "效果评估和迭代优化", "评估报告.md"),
                StageDefinition("deploy", "集成部署", "模型部署和 API 集成", "部署配置/"),
            ],
        ),
        PipelineTemplate(
            id="custom",
            name="自定义",
            description="LLM 根据需求描述动态生成阶段和产出物",
            category="development",
            suggested_strategy="auto",
            stages=[],  # 由 LLM 在需求分析阶段生成
        ),
    ]


def get_template_by_id(template_id: str) -> Optional[PipelineTemplate]:
    """根据 ID 获取模板"""
    for t in get_all_templates():
        if t.id == template_id:
            return t
    return None


def get_templates_by_category(category: str) -> List[PipelineTemplate]:
    """按类别获取模板"""
    return [t for t in get_all_templates() if t.category == category]


# ========== LLM 动态调整 Pipeline 阶段 ==========

async def suggest_stage_adjustments(
    project_name: str,
    project_description: str,
    template_id: str,
) -> dict:
    """
    使用 LLM 分析项目需求，建议对 Pipeline 模板进行调整。
    返回结构化建议，供用户确认。
    """
    from app.services.llm.llm_service import llm_service
    from app.core.llm import Message as LLMMessage

    template = get_template_by_id(template_id)
    if not template:
        return {"error": f"Template not found: {template_id}"}

    current_stages = [
        {
            "key": s.key,
            "label": s.label,
            "description": s.description,
            "expected_artifact": s.expected_artifact,
            "parallel_group": s.parallel_group,
        }
        for s in template.stages
    ]

    prompt = registry.render("collaboration.pipeline_templates.adjustment", {
        "project_name": project_name,
        "project_description": project_description,
        "template_name": template.name,
        "template_description": template.description,
        "current_stages": json.dumps(current_stages, ensure_ascii=False, indent=2),
    })

    try:
        llm_messages = [
            LLMMessage(role="system", content=registry.render("collaboration.pipeline_templates.adjustment_system", {})),
            LLMMessage(role="user", content=prompt),
        ]
        response = await llm_service.chat(llm_messages, track_cost=True, task_id="pipeline_adjustment")
        result_text = response.content

        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            return json.loads(json_match.group())
        else:
            # LLM didn't return valid JSON, return no changes
            return {
                "analysis": "无法解析 LLM 响应，保持原模板不变",
                "recommended_strategy": template.suggested_strategy,
                "changes": {"add": [], "remove": [], "reorder": [], "rename": []},
                "final_stages": current_stages,
            }
    except Exception as e:
        return {
            "analysis": f"LLM 分析失败: {str(e)}",
            "recommended_strategy": template.suggested_strategy,
            "changes": {"add": [], "remove": [], "reorder": [], "rename": []},
            "final_stages": current_stages,
        }


def apply_stage_adjustments(
    template_id: str,
    adjustments: dict,
) -> List[dict]:
    """将 LLM 建议的 final_stages 应用到模板，返回调整后的阶段列表"""
    final_stages = adjustments.get("final_stages", [])
    if not final_stages:
        template = get_template_by_id(template_id)
        if template:
            return [
                {
                    "key": s.key, "label": s.label,
                    "description": s.description,
                    "expected_artifact": s.expected_artifact,
                    "parallel_group": s.parallel_group,
                }
                for s in template.stages
            ]
        return []

    # 确保每个 stage 有 key
    for i, s in enumerate(final_stages):
        if "key" not in s or not s["key"]:
            s["key"] = f"stage_{i+1}"

    return final_stages

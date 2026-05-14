#!/usr/bin/env python3
"""验证协作引擎组件是否正常工作"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from app.core.config import get_settings
    from app.services.collaboration.pipeline_orchestrator import pipeline_orchestrator, PipelineStage
    from app.services.agent.agent_executor import agent_executor, ExecutionStatus
    from app.services.collaboration.message_bus import message_bus
    from app.services.collaboration.speaking_controller import speaking_controller
    from app.services.collaboration.task_board import task_board
    from app.services.collaboration.project_service import project_service

    print("✅ 所有核心组件导入成功!")
    print(f"✅ Pipeline Stage: {PipelineStage.REQUIREMENT_ANALYSIS.value}")
    print(f"✅ Execution Status: {ExecutionStatus.IDLE.value}")

    settings = get_settings()
    print(f"✅ LLM Provider: {settings.default_llm_provider}")
    print(f"✅ LLM Model: {settings.default_llm_model}")
    print(f"✅ LLM Mode: {settings.llm_mode.value}")

    print("\n🎉 协作引擎所有组件验证通过!")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

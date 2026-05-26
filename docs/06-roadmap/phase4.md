# Phase 4: 自我学习

**版本**: v2.0  
**最后更新**: 2026-05-25

---

## 目标

实现知识沉淀和自我学习机制。

---

## 已完成

- **知识提取**：`ExperienceExtractor` 从执行轨迹中提取经验模式
- **技能沉淀**：`SkillManager` 将经验转化为可复用技能，自动更新 `growth.json`
- **经验积累**：`TrajectoryRecorder` 记录完整执行轨迹，支持断点恢复
- **知识应用**：`SkillMatcher` 根据任务需求推荐匹配技能
- **Pipeline 阶段 AI 动态调整**：LLM 分析项目需求 → 建议增删改重排阶段 → 用户一键应用到 Pipeline

- [x] 知识提取
- [x] 技能沉淀
- [x] 经验积累
- [x] 知识应用
- [x] Pipeline 阶段 AI 动态调整（含一键应用）

---

## 相关文档

- [自我学习设计](../02-design/self-learning.md)
- [记忆系统设计](../02-design/memory-system.md)

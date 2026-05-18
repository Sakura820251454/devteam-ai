import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DevTeam-AI',
  description: '多 Agent 协作开发平台文档',
  ignoreDeadLinks: [
    /^http:\/\/localhost/
  ],

  themeConfig: {
    siteTitle: 'DevTeam-AI',

    nav: [
      { text: '首页', link: '/' },
      { text: '项目', link: '/01-project/' },
      { text: '设计', link: '/02-design/' },
      { text: '开发', link: '/03-development/' },
      { text: '模块', link: '/04-modules/' },
      { text: 'API', link: '/05-api/' },
      { text: '路线图', link: '/06-roadmap/' },
      { text: '贡献', link: '/07-contributing/' },
      { text: 'GitHub', link: 'https://github.com/Sakura820251454/devteam-ai' }
    ],

    sidebar: {
      '/01-project/': [
        {
          text: '项目概览',
          items: [
            { text: '项目首页', link: '/01-project/' },
            { text: '项目愿景', link: '/01-project/vision' },
            { text: '系统架构', link: '/01-project/architecture' },
            { text: '设计原则', link: '/01-project/principles' },
            { text: '术语表', link: '/01-project/glossary' },
            { text: '变更日志', link: '/01-project/changelog' }
          ]
        }
      ],
      '/02-design/': [
        {
          text: '设计文档',
          items: [
            { text: '设计首页', link: '/02-design/' }
          ]
        },
        {
          text: '核心概念',
          items: [
            { text: 'Agent 模型', link: '/02-design/agent-model' },
            { text: '记忆系统', link: '/02-design/memory-system' },
            { text: '任务模型', link: '/02-design/task-model' },
            { text: '通信机制', link: '/02-design/communication' }
          ]
        },
        {
          text: '功能特性',
          items: [
            { text: '团队协作', link: '/02-design/collaboration' },
            { text: '任务看板', link: '/02-design/task-board' },
            { text: '干预系统', link: '/02-design/intervention' },
            { text: '自我学习', link: '/02-design/self-learning' }
          ]
        },
        {
          text: '调研与规格',
          items: [
            { text: '记忆系统调研', link: '/02-design/memory-system-research' },
            { text: '设计规格书', link: '/02-design/design-spec' }
          ]
        },
        {
          text: '架构决策',
          items: [
            { text: 'ADR 索引', link: '/02-design/decisions/' },
            { text: 'ADR-001: VitePress', link: '/02-design/decisions/2026-05-13-vitepress-decision' }
          ]
        }
      ],
      '/03-development/': [
        {
          text: '开发指南',
          items: [
            { text: '开发首页', link: '/03-development/' },
            { text: '环境搭建', link: '/03-development/setup' },
            { text: '项目结构', link: '/03-development/structure' },
            { text: '编码规范', link: '/03-development/coding-standards' },
            { text: 'API 规范', link: '/03-development/api-guidelines' },
            { text: '测试指南', link: '/03-development/testing' }
          ]
        }
      ],
      '/04-modules/': [
        {
          text: '模块文档',
          items: [
            { text: '模块首页', link: '/04-modules/' }
          ]
        },
        {
          text: '后端模块',
          items: [
            { text: '后端首页', link: '/04-modules/backend/' },
            { text: 'Agent 服务', link: '/04-modules/backend/agent-service' },
            { text: 'Agent 执行器', link: '/04-modules/backend/agent-executor' },
            { text: '消息总线', link: '/04-modules/backend/message-bus' },
            { text: '发言控制器', link: '/04-modules/backend/speaking-controller' },
            { text: '任务看板', link: '/04-modules/backend/task-board' },
            { text: 'Pipeline 编排器', link: '/04-modules/backend/pipeline-orchestrator' },
            { text: '项目管理', link: '/04-modules/backend/project-service' },
            { text: '冲突仲裁', link: '/04-modules/backend/arbitration-service' },
            { text: '安全服务', link: '/04-modules/backend/security-service' },
            { text: '记忆服务', link: '/04-modules/backend/memory-service' },
            { text: 'LLM 服务', link: '/04-modules/backend/llm-service' },
            { text: '装备服务', link: '/04-modules/backend/equipment-service' },
            { text: '知识服务', link: '/04-modules/backend/knowledge-service' },
            { text: '学习服务', link: '/04-modules/backend/learning-service' },
            { text: '共享服务', link: '/04-modules/backend/shared-services' },
            { text: '执行持久化', link: '/04-modules/backend/execution-persistence' },
            { text: '检查点管理', link: '/04-modules/backend/execution-checkpoint' },
            { text: '卡死检测', link: '/04-modules/backend/execution-stuck-detector' }
          ]
        },
        {
          text: '数据模型',
          items: [
            { text: '模型首页', link: '/04-modules/backend/models/' },
            { text: 'Agent 模型', link: '/04-modules/backend/models/agent' },
            { text: 'Agent 上下文', link: '/04-modules/backend/agent-context' },
            { text: '记忆模型', link: '/04-modules/backend/models/memory' },
            { text: '任务模型', link: '/04-modules/backend/models/task' },
            { text: '会话模型', link: '/04-modules/backend/models/session' },
            { text: 'Gear 模型', link: '/04-modules/backend/models/gear' },
            { text: '执行模型', link: '/04-modules/backend/models/execution' }
          ]
        },
        {
          text: '前端模块',
          items: [
            { text: '前端首页', link: '/04-modules/frontend/' },
            { text: '协作视图', link: '/04-modules/frontend/collaboration-view' },
            { text: 'Agent 配置', link: '/04-modules/frontend/agent-config-modal' },
            { text: 'Agent 池', link: '/04-modules/frontend/agent-pool-modal' },
            { text: '流水线视图', link: '/04-modules/frontend/pipeline-view' },
            { text: '任务分配', link: '/04-modules/frontend/task-assignment' },
            { text: '执行进度面板', link: '/04-modules/frontend/execution-progress-panel' }
          ]
        }
      ],
      '/05-api/': [
        {
          text: 'API 文档',
          items: [
            { text: 'API 首页', link: '/05-api/' },
            { text: 'Agents API', link: '/05-api/agents' },
            { text: 'Chat API', link: '/05-api/chat' },
            { text: 'Tasks API', link: '/05-api/tasks' },
            { text: 'Memory API', link: '/05-api/memory' },
            { text: 'Sessions API', link: '/05-api/sessions' },
            { text: 'Messages API', link: '/05-api/messages' },
            { text: 'Skills API', link: '/05-api/skills' },
            { text: 'Pipelines API', link: '/05-api/pipelines' },
            { text: 'Projects API', link: '/05-api/projects' },
            { text: 'Security API', link: '/05-api/security' },
            { text: 'Arbitration API', link: '/05-api/arbitration' },
            { text: 'Speaking API', link: '/05-api/speaking' },
            { text: 'Knowledge API', link: '/05-api/knowledge' },
            { text: 'Equipment API', link: '/05-api/equipment' },
            { text: 'LLM API', link: '/05-api/llm' },
            { text: 'Execution API', link: '/05-api/execution' }
          ]
        }
      ],
      '/06-roadmap/': [
        {
          text: '开发路线图',
          items: [
            { text: '路线图首页', link: '/06-roadmap/' },
            { text: 'MVP 阶段', link: '/06-roadmap/mvp' },
            { text: 'Phase 2', link: '/06-roadmap/phase2' },
            { text: 'Phase 3', link: '/06-roadmap/phase3' },
            { text: 'Phase 4', link: '/06-roadmap/phase4' },
            { text: 'Phase 5', link: '/06-roadmap/phase5' },
            { text: 'Phase 6', link: '/06-roadmap/phase6' }
          ]
        }
      ],
      '/07-contributing/': [
        {
          text: '贡献指南',
          items: [
            { text: '贡献首页', link: '/07-contributing/' },
            { text: '如何贡献', link: '/07-contributing/how-to-contribute' },
            { text: '文档风格', link: '/07-contributing/doc-style-guide' },
            { text: '代码风格', link: '/07-contributing/code-style-guide' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Sakura820251454/devteam-ai' }
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2026 DevTeam-AI'
    },

    search: {
      provider: 'local'
    }
  },

  markdown: {
    lineNumbers: true
  }
})

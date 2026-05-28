# Frontend Rules

## Stack

React 18 + TypeScript + Vite + Tailwind CSS.

## Commands

```bash
npm run dev       # port 3000, API proxy → localhost:8000
npx tsc --noEmit  # type check
npm run lint      # ESLint
npm test          # Vitest
```

## Testing

- 单元测试: Vitest
- E2E: Playwright
- 组件测试优先使用 `@testing-library/react`

## Code style

- 组件按功能分目录，每个目录含 `index.tsx` + 样式文件
- API 调用统一走 `src/api/` 下的模块
- 状态管理优先用 React Context，复杂场景用 Zustand

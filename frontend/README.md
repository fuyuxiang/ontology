# 元枢本体前端

元枢本体的 Web 界面，使用 Vue 3、TypeScript、Vite、Pinia 和 Ant Design Vue。项目介绍、后端配置与完整启动方式见[根目录 README](../README.md)。

## 本地开发

使用 Node.js 20.19+（20.x）、22.13+（22.x）或 24+，建议使用 22.13+。该要求同时满足当前锁定的 Vite 8 与 ESLint 10。

先按根目录 README 在项目根目录配置 `.env`，安装后端依赖并启动后端；前端的登录、建模和资产操作依赖后端 API。随后在项目根目录执行：

```bash
cd frontend
npm ci
npm run dev
```

默认访问地址为 `http://localhost:5177`。Vite 将 `/api` 请求（包括 WebSocket）代理到 `http://127.0.0.1:8001`，配置见 [vite.config.ts](vite.config.ts)。

连接其他后端或更换前端端口时，可在启动命令中指定环境变量：

```bash
VITE_PROXY_TARGET=http://127.0.0.1:8002 FRONTEND_PORT=5178 npm run dev
```

后端的 `CORS_ORIGINS` 应与实际前端访问地址匹配。这里的变量用于 Vite 开发服务器；完整启动脚本和后端环境配置以根目录 README 为准。

## 常用命令

以下命令均在 `frontend/` 下执行：

| 命令 | 用途 |
| --- | --- |
| `npm run dev` | 启动开发服务器 |
| `npm run build` | 执行 Vue / TypeScript 类型检查并构建到 `dist/` |
| `npm run test:ui-state` | 运行认证刷新、逻辑流、构建交付和平台配置的状态回归测试 |
| `npm run lint` | 执行 ESLint，要求无警告 |
| `npm run preview` | 本地预览生产构建产物 |

## 页面入口

路由定义见 [src/router/index.ts](src/router/index.ts)，导航根据账号权限显示。登录后默认进入本体列表。

| 模块 | 路由 |
| --- | --- |
| 登录 | `/login` |
| 数据接入 / 资产目录 | `/data/connections`、`/data/assets` |
| 本体列表 / 详情 | `/ontology/list`、`/ontology/list/:code` |
| 手动 / 模板 / 文档 / 资产构建 | `/builder`、`/builder/template`、`/builder/doc`、`/builder/ai` |
| 逻辑 / 动作 | `/logic/functions`、`/logic/actions`，也可在本体详情中访问 |
| 本体发布 / MCP 服务 | `/ontology/publish`、`/service/mcp` |
| 智能体 / 业务技能 | `/agent/manage`、`/skills` |
| 系统看板 / 配置 | `/dashboard`、`/ops/config` |

## 目录

```text
src/
├── api/          # HTTP、SSE 与模块 API
├── components/   # 公共组件与技能编辑组件
├── composables/  # 权限、事件流等可复用逻辑
├── i18n/         # 国际化初始化与基础翻译
├── locales/      # 业务页面翻译
├── router/       # 路由与访问检查
├── store/        # Pinia 状态管理
├── styles/       # 全局样式与设计变量
├── types/        # 业务类型定义
├── utils/        # 请求认证、时间显示、OWL 等工具
└── views/        # 按业务模块组织的页面
tests/            # 状态回归与浏览器验收脚本
public/           # 静态资源
```

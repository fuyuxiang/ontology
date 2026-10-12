# 使用指南

[返回 README](../README.md) · [English](usage.en.md)

本指南从登录后的第一条业务数据开始，介绍如何把本体发布为可供应用与 Agent 使用的能力。安装、启动和初始管理员配置见 [README](../README.md)。

## 最短使用路径

```text
数据接入 / 资产目录 → 对象定义 → 数据映射 → 最终审核 → 验证发布
                                                    ↓
                                    函数 / 行动 → 技能 → Agent
                                                    ↓
                                             MCP / API / SDK
```

首次登录使用 `admin` 和初始化时设置的 `ADMIN_INITIAL_PASSWORD`。平台没有默认管理员密码。开始 AI 构建或对话前，先配置可用的模型接口与凭证；读取真实数据还需要对应的数据连接。

## 1. 接入数据并登记资产

在「数据接入」创建连接，填写服务地址、连接参数和凭证，先测试连接，再到「资产目录」登记需要使用的表、SQL 视图或文档。

建议先选择一张有稳定主键、数据量适中的业务表，检查字段、类型和数据预览，再扩展到其他对象。文档构建可上传业务资料；旧版 `.doc/.xls/.ppt` 的转换需要 LibreOffice `soffice`。

对象绑定分为 Primary 主数据、Enrichment 补充数据和文档证据。实例身份由主数据绑定确定；补充数据需要明确关联键，文档证据用于提供业务背景。

Kafka 连接器提供连接测试、主题列表和有限消息采样。数据资产可以按配置定期刷新。

相关实现：[连接 API](../backend/app/api/v1/data_plane/connections.py)、[资产服务](../backend/app/services/data_plane/asset_service.py)、[Kafka 连接器](../backend/app/connectors/kafka.py)。

## 2. 定义对象、映射数据并完成审核

在「本体列表」选择或新建本体，再进入手动、模板、文档或资产构建入口。AI 生成结果作为候选模型，需要逐项确认。

模板构建支持 JSON / Excel，以及 OWL、RDF/XML 和 Turtle 文件的预览导入；标准本体也可从 Protégé 风格编辑视图打开。导入后检查对象、关系和类型，再进入映射与审核步骤。

1. **对象定义**：检查业务名称、属性类型、必填项、主键和关系方向。
2. **数据映射**：选择资产，将属性映射到物理字段；检查主键、补充数据关联和关系连接字段。
3. **最终审核**：确认对象、关系与实际保留的映射；修改已审核内容后重新审核。
4. **验证发布**：运行连接、字段映射、实例主键与关系检查，处理失败项后发布。

文档映射选择保留已有绑定时，最终发布会沿用实际保留的映射。发布前确认这些映射仍符合当前对象定义。

发布版本保存对象、关系、绑定以及函数和行动的快照。运行时使用相应发布版本的定义，通过绑定读取当前业务数据。

相关实现：[构建步骤](../frontend/src/views/builder/components/BuilderShell.vue)、[发布 API](../backend/app/api/v1/ontology_publish.py)、[发布组件快照](../backend/app/services/version_component_snapshot.py)。

## 3. 配置函数与行动

在「逻辑建模」配置 Expression、SQL 或 Python 函数，定义输入参数、输出结构和对象范围，先用具体业务输入测试。

在「行动建模」配置 API 调用、SQL 执行、属性修改、通知、函数调用或自定义脚本。填写所需连接、参数映射和服务配置，将能力纳入相应本体发布版本后再供技能与 Agent 使用。

函数测试采用模拟写入：遇到第一个业务写入请求时，展示预览并停止该次函数执行。因此，写入之后的分支尚未被此次测试验证。

Python 函数与脚本经过 AST 校验，使用允许的模块接口、受限内置函数和执行时限。禁止宿主系统模块、私有属性与反射式字符串格式化；格式化文本请使用 f-string。

相关实现：[函数执行](../backend/app/services/function_executor.py)、[行动执行器](../backend/app/services/action_executors/__init__.py)、[Python 沙箱](../backend/app/services/function_runtime/sandbox.py)。

## 4. 测试并发布业务技能

在「本体应用 → 业务技能」选择已发布本体版本和对象范围，关联可用的 Function、Action 与参考资料，编写 Markdown 操作指引及输入输出约定。

添加至少一个测试用例，给出输入及预期关键词或工具调用。保存草稿后运行测试；测试使用实际配置的模型与授权工具，需要有效模型凭证和可访问的数据。

当前草稿及依赖对应的全部用例通过真实运行测试后，才能发布固定技能版本。修改指引、用例或依赖后，需要重新测试。

技能可以设为个人私有或工作区可见。归档后停止新挂载，已有发布引用仍保留；存在应用或历史发布引用时，删除会受到保护。

相关实现：[技能 API](../backend/app/api/v1/skills.py)、[技能版本与测试](../backend/app/services/skill_service.py)。

## 5. 配置、测试并发布 Agent

在「本体应用 → Agent 应用」新建 Agent，选择模型、已发布本体版本、对象范围及固定技能版本，再设置指引与工具范围。

技能的本体版本必须与 Agent 匹配，技能需要的对象也必须在 Agent 授权范围内。默认行动模式为 `simulation`；需要实际操作时选择 `confirm`。

保存配置后，在工作台完成当前草稿的对话测试，查看工具结果、技能加载和待确认行动，再发布 Agent。修改配置、升级技能或恢复历史配置后，重新测试并发布。

公开接口为 `POST /api/v1/open/agents/{id}/chat`，使用 `X-Agent-Key`；请求中设置 `stream: false` 可获得完整 JSON 运行结果。

相关实现：[Agent API](../backend/app/api/v1/agents.py)、[发布与依赖检查](../backend/app/services/agent_management.py)。

## 版本、审批与在线运行

| 操作 | 对在线能力的影响 |
| --- | --- |
| 保存 Agent 或技能草稿 | 已发布版本继续使用原快照 |
| 发布 Agent | 固定本体、技能版本和模型行为配置 |
| 更新数据源中的业务数据 | 后续查询按已发布绑定读取当前数据 |
| 本体提交审批 | 从 Draft 进入 Pending Approval；通过后成为 Published |
| 回滚本体 | 基于历史版本新建待审批版本，通过审批后生效 |

版本固定定义与行为配置，凭证可以轮换。上游本体变更可能产生依赖过期提示，应检查影响后调整应用。回滚本体定义不会撤销已经提交的业务写入。

## 行动授权与执行回执

模拟模式不写业务数据。确认模式要求有权限的登录用户逐项授权；拒绝或过期不会执行，同一授权请求最多执行一次。画布中的行动遵守相同边界。

公开 Agent 接口没有登录用户身份，不能代替用户确认写操作。API Key 或应用密钥也不会自动授予用户行动确认权限。

执行结果应结合回执判断。出现 `unknown`、`partial_committed` 或 `committed_unrecorded` 时，先核对数据源、外部服务和运行记录，再按界面提供的核查或恢复操作处理，避免直接重试造成重复执行。

相关实现：[行动授权](../backend/app/services/agent_actions.py)、[确认与核查接口](../backend/app/api/v1/agents.py)、[执行上下文](../backend/app/services/function_runtime/models.py)。

## MCP、实例 API 与 SDK 接入

在「本体服务」检查已发布对象和能力。MCP 入口为 `POST /api/v1/mcp`，当前提供 HTTP JSON-RPC 2.0 的 `initialize`、`tools/list` 和 `tools/call`。

MCP 可以使用登录用户的 Bearer JWT，或环境变量 `MCP_API_KEYS` 中配置的密钥，通过 `X-API-Key` 传入。API Key 当前只有读取权限；执行与写入工具需要拥有相应权限的 JWT 用户。

```bash
curl http://localhost:8001/api/v1/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_MCP_READ_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

TypeScript / Python SDK 从当前活动的已发布本体生成，也可调用 `POST /api/v1/osdk/generate`，传入 `language` 及可选的 `entity_ids`。生成后按返回的使用说明配置客户端地址与认证。

实例标识由已发布主键属性决定，端点及查询元数据通过 `id_property` 声明。业务字段 `id` 可以保留原值；定位实例应使用实际主键属性。

关联查询支持 `limit`、`offset`、`relation_id` 和 `max_nodes`。遇到 `pagination.has_more`，沿 `pagination.next` 继续读取；该路径相对于 `/api/v1`。同时检查 `traversal.truncated` 与 `continuations`，以处理多跳遍历截断。

相关实现：[MCP 认证](../backend/app/services/mcp_tools/auth.py)、[MCP API](../backend/app/api/v1/mcp.py)、[实例 API](../backend/app/api/v1/ontology_api.py)、[SDK 生成](../backend/app/services/osdk_generator.py)。

## 权限与单点登录

RBAC 根据持久化角色配置和当前账号状态校验访问。默认管理员、编辑者和查看者的权限可由管理配置调整，角色名称本身不替代权限检查。

技能可见性、对象范围、运行记录与会话访问还受各自的访问规则约束。调试、发布和执行遇到权限错误时，应检查当前角色权限与应用依赖。

单点登录当前支持 OIDC，需要配置实际身份源、客户端与回调地址。SAML/LDAP 尚需接入实现与验证。

相关实现：[权限校验](../backend/app/core/permissions.py)、[OIDC 登录](../backend/app/api/v1/sso.py)。

## 配置与部署

后端配置读取仓库根目录 `.env`，模板见 [backend/.env.example](../backend/.env.example)。直接运行 `uvicorn` 时，已声明的 Settings 字段以进程环境变量优先；`start.sh` 和 `ctl.ps1` 先读取根 `.env`，会覆盖同名进程变量。

| 配置 | 默认值与使用方式 |
| --- | --- |
| `DATABASE_URL` | `sqlite:///./ontology.db`；相对路径按启动工作目录解析，启动脚本使用 `backend/` |
| `WORKSPACE_ROOT` | 仓库根目录的 `workspace/`；函数与行动的源码工作区 |
| `LOCAL_DATA_ROOT` | 仓库根目录的 `local-data/`；本地数据源访问范围 |
| `CODE_SERVER_PUBLIC_URL` | 默认留空；编辑器经过反向代理时填写其对外基址，如 `https://example.com/code-server` |
| `MONITOR_ENABLED` | 默认 `true`；本地开发可设为 `false` 关闭监控采集 |
| `CORS_ORIGINS` | 显式列出允许访问 API 的前端来源，多个来源用逗号分隔 |

保持 `SECRET_KEY` 稳定，用于 JWT 签名。建议单独设置有效的 Fernet `CREDENTIAL_ENCRYPTION_KEY`；留空时，连接凭据加密密钥由 `SECRET_KEY` 派生。更换加密密钥会影响已有凭据解密，应保留原密钥并处理凭据迁移。

在已创建的虚拟环境中，从仓库根目录先安装后端依赖，再分别生成密钥，将输出保存到根 `.env`：

```bash
python -m pip install -r backend/requirements.txt
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`MCP_API_KEYS` 与 `MCP_REQUIRE_AUTH` 直接读取进程环境，不是 Settings 字段。启动脚本会将根 `.env` 导入进程；直接运行 `uvicorn` 时，应在启动环境中显式设置这两个变量。

启动脚本使用 Vite 开发服务器和 code-server，适合本地开发。生产部署先在 `frontend/` 执行 `npm run build`，由 Web 服务器托管生成的 `dist/`，为 `/api` 和编辑器配置反向代理；将后端与编辑器限制在受控监听地址，并配置认证、HTTPS 和明确的 CORS 来源。

OIDC 在系统配置中设置启用状态、`oidc` 提供商、`issuer_url`、`client_id`、按身份源要求填写的 `client_secret`，以及完整的 `redirect_uri`（路径为 `/api/v1/auth/sso/callback`）。后端需要访问身份源的发现文档、令牌端点和 JWKS；正式地址使用 HTTPS，本机隔离测试可使用 HTTP。

相关实现：[后端 Settings](../backend/app/config.py)、[Linux/macOS 启动](../start.sh)、[Windows 控制脚本](../ctl.ps1)、[凭据加密](../backend/app/services/data_plane/credential_vault.py)、[前端构建命令](../frontend/package.json)。

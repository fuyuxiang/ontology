# 系统截图说明

[中文 README](../README.md) · [English README](../README.en.md)

README 使用少量真实页面，按「本体模型 → 数据资产 → 发布治理 → Agent 配置」说明产品。主图直接展示，其余页面折叠展示，便于读者继续查阅安装步骤。

## 当前截图

截图时间为 2026-10-12，应用源码基于提交 `291912bb`。页面由本机 Chromium 渲染，使用当前 Vue 前端和 FastAPI 生产路由、启动生命周期；业务数据使用独立的 SQLite 演示环境。

| 图片 | 页面入口 | 展示内容 |
| --- | --- | --- |
| [本体图谱](images/screenshots/ontology-graph.png) | `/ontology/list/equipment_ops` → 本体图谱 | 设备、传感器、检修工单、运维人员及四条业务关系 |
| [数据资产](images/screenshots/data-assets.png) | `/data/assets` | 四张业务表和一份运维手册，共 19 行结构化示例数据 |
| [发布管理](images/screenshots/ontology-publish.png) | `/ontology/publish` → 设备运维本体 | 预置的 v1 发布快照，包含四个对象、26 个属性、四条关系和一个逻辑函数 |
| [Agent 工作台](images/screenshots/agent-workbench.png) | `/agent/manage/demo-equipment-agent` → 本体与能力 | 草稿 Agent 固定本体版本、对象范围与可用逻辑；默认模拟模式 |

发布视图中的版本由演示数据初始化，用于展示版本页面。Agent 与业务技能保留为草稿，模型凭证留空；对话、技能测试与行动执行没有生成演示结果。真实业务数据、用户配置与凭证不参与截图。

图片宽度统一为 1440 像素，图谱、资产与 Agent 页面高度为 1000 像素，发布页为 1280 像素，以展示资源快照。图谱通过页面自带的缩放与拖动控件调整位置，保持对象和关系文字可读。

## 更新方式

1. 启动当前版本的前后端，使用独立元数据库、工作区、上传目录和业务数据源。
2. 准备同一套设备运维示例：设备、传感器、检修工单和运维人员，使用明确主键与简短关系名称。
3. 在真实页面完成配置；需要展示发布、测试或运行结果时，保留对应实际记录，注明示例的配置条件。
4. 使用相同语言、浅色主题和窗口宽度，等待数据和字体加载完成后截图。检查正文、下拉框与画布文字完整，页面无错误状态。
5. 确认画面不包含口令、API Key、令牌、实际内网地址或私人数据，将 PNG 保存到 `docs/images/screenshots/`。
6. 同步更新两份 README 的图片说明、替代文本及本页的源码版本和截图日期。

新增页面时，优先考虑有字段映射内容的构建步骤或有真实工具过程的 Agent 调试。系统配置、空列表和监控统计适合放到使用文档中补充。

`docs/images/` 下既有的概念插画与系统截图分开存放；页面展示使用 `screenshots/` 下的文件。

## English notes

The README screenshots were captured on 2026-10-12 from source commit `291912bb`, using the current Vue frontend and production FastAPI routes and startup lifecycle with an independent SQLite demo dataset. All images are 1440 pixels wide; publishing uses a taller viewport to show its resource snapshots.

The example contains four object types, 26 attributes, four relations, one logic function, four business tables with 19 rows, and one manual. Its published ontology snapshot is seeded for the interface demonstration. The Agent and skill remain drafts, model credentials are empty, and no AI conversation, skill test result, or action receipt is fabricated.

To refresh the images, use a separate demo environment, keep language and viewport settings consistent, inspect the real pages after loading, exclude credentials and private data, and update both README captions and the source/date information here.

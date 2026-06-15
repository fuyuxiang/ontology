# ActionBuilderDrawer 重构设计规格

## 概述

将行动管理的"新建/编辑行动"界面从 ActionsView 内嵌的三步向导（createStep 0/1/2）重构为独立的 `ActionBuilderDrawer.vue` 组件，与 `FunctionBuilderDrawer.vue` 保持风格统一的平铺式 Drawer 布局。

## 目标

- 视觉风格与函数管理的 Drawer 一致
- 消除多步向导的认知负担，所有配置一屏可见
- 保留现有功能：类型动态配置、AI 代码生成、Builder 回跳
- 新增：测试面板（dry_run）

## 组件结构

```
ActionBuilderDrawer.vue
├── Section 1: 基本信息
│   ├── 行动名称 *
│   ├── 描述
│   ├── 分类（domain/system）
│   ├── 关联实体（domain 时必填）
│   └── 状态（active/inactive，编辑模式显示）
├── Section 2: 行动类型
│   ├── 类型选择下拉
│   └── 类型配置字段（根据 config_schema 动态渲染）
├── Section 3: 输入参数
│   └── 参数列表（名称/类型/必填/描述/实体绑定/属性绑定）
├── Section 4: 逻辑体（仅 custom_script 显示）
│   ├── 代码编辑器 textarea
│   └── AI 生成按钮
└── Section 5: 测试面板
    ├── 参数输入（JSON）
    ├── 执行按钮（dry_run=true）
    └── 结果展示
```

## Props 接口

```typescript
interface ActionBuilderDrawerProps {
  visible: boolean
  editId?: string           // 有值=编辑模式
  lockedEntityId?: string   // 从实体详情进入时锁定
}

interface ActionBuilderDrawerEmits {
  (e: 'close'): void
  (e: 'saved', val: { id: string; name: string }): void
}
```

## 表单数据结构

```typescript
interface ActionForm {
  name: string
  description: string
  category: 'domain' | 'system'
  entity_id: string
  action_type: string
  status: 'active' | 'inactive'
  parameters_json: ActionParam[]
}

interface ActionParam {
  name: string
  type: string
  required: boolean
  description: string
  entity_id?: string
  attribute_id?: string
}
```

## Section 详细设计

### Section 1: 基本信息

与 FunctionBuilderDrawer 基本信息段一致的布局：
- 第一行：名称（flex:1）
- 第二行：描述 textarea
- 第三行：分类 select + 关联实体 select（inline）
- 分类选 system 时，关联实体隐藏

### Section 2: 行动类型

- 类型选择：复用现有 `actionTypes` 数据（从 actionApi.types() 获取）
- 动态配置：根据选中类型的 `config_schema` 渲染字段
  - type=object / key=script/sql → textarea
  - field.enum → select
  - 其他 → input
- 与现有 Step 2 逻辑完全一致，仅展示位置变化

### Section 3: 输入参数

复用 FunctionBuilderDrawer 的参数列表模式：
- 每行：名称 / 类型 / 描述 / 关联实体 / 关联属性 / 必填 / 删除
- 底部 "+ 添加参数" 按钮
- 实体/属性绑定逻辑同 FunctionBuilderDrawer

### Section 4: 逻辑体

- 仅当 `action_type === 'custom_script'` 时显示此 Section
- textarea 代码编辑器
- "AI 生成" 按钮打开 AiCodePanel（Teleport to body）
- AiCodePanel 的 apply 事件将代码写入 typeConfigValues.script

### Section 5: 测试面板

- 需要先保存行动才能测试（同 FunctionBuilderDrawer 逻辑）
- 输入：JSON textarea（根据 parameters_json 提示）
- 执行：调用 `actionApi.execute(id, params)` 并传 dry_run=true
- 结果：成功绿色框 / 失败红色框

## 与 ActionsView 的集成

### 变更点

1. 删除 ActionsView 中的整个 `<Transition name="drawer">` 块（三步向导）
2. 删除相关状态：`showAdd`, `createStep`, `form`, `typeConfigValues`, `stepLabels`, `currentConfigSchema`, `handleStepNext`
3. 新增：引入 ActionBuilderDrawer 组件
4. "新建行动"按钮 → `drawerVisible = true, drawerEditId = undefined`
5. 列表中点击编辑 → `drawerVisible = true, drawerEditId = action.id`
6. @saved 事件 → 刷新列表 + 处理 builder 回跳逻辑

### Builder 回跳保留

现有从 Builder 进入创建行动的逻辑（route.query.from === 'builder'）移入 ActionBuilderDrawer：
- onMounted 时检查 route.query
- 保存后执行 router.push 回跳

## 复用策略

| 内容 | 来源 | 方式 |
|------|------|------|
| 实体/属性绑定逻辑 | FunctionBuilderDrawer | 相同模式复制 |
| AiCodePanel | 现有组件 | 直接引用 |
| 类型配置动态渲染 | ActionsView Step 2 | 迁移到新组件 |
| 样式 | logic-shared.css | @import 复用 |
| 测试面板 | FunctionBuilderDrawer | 相同模式，API 换为 actionApi |

## 不变的部分

- ActionsView 的列表/详情面板不变
- 后端 API 不变（action CRUD + execute）
- AiCodePanel 组件不变
- actionApi 不变

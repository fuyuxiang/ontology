# exDB2TTL

`exDB2TTL` 用来把数据库元数据整理成 LLM 可消费的上下文，并生成一套能和当前 `backend` 直接对应的文件：

- `telecom-porting.ttl`
- `telecom-shapes.ttl`
- `porting-risk.yaml`
- `mapping.csv`
- `business-rules.md`

它不是只产出“通用草稿”，而是会按当前仓库后端的真实契约来生成和同步：

- 本体文件对应 `backend/ontology/telecom-porting.ttl`
- SHACL 文件对应 `backend/ontology/telecom-shapes.ttl`
- 规则文件对应 `backend/rules/porting-risk.yaml`

同时保留当前后端稳定的 `doim-core.ttl`，不让 LLM 重写它。

## 当前能力

- 支持 `SQLite` 元数据抽取
- 支持 `MySQL` 元数据抽取
- 支持 `CSV` 样例模式
- 支持用 OpenAI-compatible `chat/completions` 生成草案
- 用 `rdflib` 校验 TTL 语法
- 用 `pyshacl` 校验 SHACL
- 校验 `porting-risk.yaml` 是否符合当前 backend decision table 结构
- 可把产物同步为 backend 可直接加载的 generated profile

## 输出目录

默认输出到 `output.directory`，常见产物包括：

- `metadata.json`
- `prompt.txt`
- `drafts.raw.txt`
- `drafts.json`
- `telecom-porting.ttl`
- `telecom-shapes.ttl`
- `porting-risk.yaml`
- `mapping.csv`
- `business-rules.md`
- `sample-data.ttl`
- `shacl-report.ttl`
- `validation-summary.json`

## Backend 对接方式

执行 `run` 后，如果配置里的 `backend_sync.enabled = true`，会自动同步到：

- `backend/runtime/generated-profile/ontology/doim-core.ttl`
- `backend/runtime/generated-profile/ontology/telecom-porting.ttl`
- `backend/runtime/generated-profile/ontology/telecom-shapes.ttl`
- `backend/runtime/generated-profile/rules/porting-risk.yaml`
- `backend/runtime/generated-profile/artifacts/...`
- `backend/runtime/generated-profile/profile.json`
- `backend/runtime/generated-profile/active-profile.json`

后端现在会优先读取 `active-profile.json` 指向的文件路径。  
如果你想临时忽略 generated profile，启动 backend 前设置：

```bash
export ONTOLOGY_IGNORE_ACTIVE_PROFILE=1
```

## 只有数据库名和表名时怎么做

### 1. 生成初始配置

```bash
python -m exDB2TTL bootstrap \
  --database-name telecom_db \
  --dialect mysql \
  --table subscribers \
  --table usage_signals \
  --table commercial_signals \
  --table interaction_events \
  --config-path exDB2TTL/project.json \
  --output-dir exDB2TTL/out
```

这一步会生成：

- `exDB2TTL/project.json`
- `exDB2TTL/metadata-request.md`

### 2. 补充配置

如果是 `SQLite`，填 `database.sqlite_path`。  
如果是 `MySQL`，填 `host / port / username / password_env`。  
如果每张表都有同名 CSV，则可以直接使用 `csv` 模式，并设置 `sample_csv_dir`。

`bootstrap` 生成的默认配置已经按当前 backend 预填：

- `ontology.ontology_namespace = http://example.com/telecom#`
- `ontology.data_namespace = http://example.com/telecom/data/`
- `backend_sync.enabled = true`

### 3. 抽取元数据

```bash
python -m exDB2TTL extract --config exDB2TTL/project.json
```

### 4. 生成草案

```bash
export OPENAI_API_KEY=...
python -m exDB2TTL draft --config exDB2TTL/project.json
```

### 5. 校验草案

```bash
python -m exDB2TTL validate --config exDB2TTL/project.json
```

### 6. 同步到 backend

```bash
python -m exDB2TTL sync-backend --config exDB2TTL/project.json
```

### 7. 一步跑完

```bash
python -m exDB2TTL run --config exDB2TTL/project.json
```

或者直接：

```bash
bash exDB2TTL/run.sh
```

## 配置示例

### MySQL + 同名 CSV 样例覆盖

```json
{
  "database": {
    "dialect": "mysql",
    "database_name": "crm_db",
    "tables": ["subscribers", "usage_signals", "commercial_signals", "interaction_events"],
    "host": "127.0.0.1",
    "port": 3306,
    "username": "root",
    "password_env": "DB_PASSWORD",
    "mysql_charset": "utf8mb4",
    "sample_csv_dir": "exDB2TTL/sample-csv",
    "sample_rows": 5
  },
  "ontology": {
    "ontology_namespace": "http://example.com/telecom#",
    "data_namespace": "http://example.com/telecom/data/"
  },
  "backend_sync": {
    "enabled": true,
    "backend_project_dir": "backend",
    "activate_profile": true
  }
}
```

### 纯 CSV 模式

```json
{
  "database": {
    "dialect": "csv",
    "database_name": "crm_db",
    "tables": ["subscribers", "usage_signals"],
    "sample_csv_dir": "exDB2TTL/sample-csv",
    "sample_csv_encoding": "utf-8",
    "sample_rows": 5
  }
}
```

目录下需要有：

- `sample-csv/subscribers.csv`
- `sample-csv/usage_signals.csv`

## LLM 输出契约

`prompts.py` 现在要求 LLM 返回一个 JSON 对象，必须包含：

- `telecom_ontology_ttl`
- `telecom_shacl_ttl`
- `mapping_csv`
- `rules_yaml`
- `business_rules_markdown`

其中：

- `telecom_ontology_ttl` 对应 `backend/ontology/telecom-porting.ttl`
- `telecom_shacl_ttl` 对应 `backend/ontology/telecom-shapes.ttl`
- `rules_yaml` 对应 `backend/rules/porting-risk.yaml`

`rules_yaml` 必须符合当前 backend 的 decision table 结构：

- `risk_actions`
- `factor_rules`
- `decision_rules`

## 当前边界

现在已经打通的是：

- 数据库 / CSV -> 元数据抽取
- 元数据 -> LLM 草案
- 草案 -> TTL / SHACL / YAML 校验
- 草案 -> backend generated profile 同步

当前还没有打通的是“任意数据库记录直接替换 backend 里现有 CSV 物化逻辑”。  
也就是说，`exDB2TTL` 已经把本体、SHACL、规则文件和 backend 加载链路对应上了，但 backend 的实例数据构建仍然是当前电信场景的定制实现。

# exDB2TTL

`exDB2TTL` 是一个独立的小工具链，用来把关系数据库元数据整理成 LLM 可消费的上下文，再生成并校验以下草案：

- `ontology.ttl`
- `shacl.ttl`
- `mapping.csv`
- `business-rules.md`

当前实现重点:

- 支持 `SQLite` 直连抽取元数据
- 支持 `MySQL` 元数据抽取
- 支持 `CSV` 样例模式：每张表一个同名 csv
- LLM 调用走通用 OpenAI-compatible `chat/completions`
- 用 `rdflib` 检查 TTL 可解析
- 用 `pyshacl` 执行 SHACL 校验
- 用 `mapping.csv` 和样例行物化一份 `sample-data.ttl`

## 目录产物

运行后默认会在 `output.directory` 下产出:

- `metadata.json`
- `prompt.txt`
- `drafts.raw.txt`
- `drafts.json`
- `ontology.ttl`
- `shacl.ttl`
- `mapping.csv`
- `business-rules.md`
- `sample-data.ttl`
- `shacl-report.ttl`
- `validation-summary.json`

## 先只有数据库名和表名时怎么做

如果当前只有数据库名和表名，还无法直接抽字段级元数据。可以先：

1. `bootstrap`
2. 补充连接信息
3. 再执行 `extract` 或 `run`

### 1. 生成初始配置

```bash
python -m exDB2TTL bootstrap \
  --database-name telecom_db \
  --dialect sqlite \
  --table subscribers \
  --table orders \
  --config-path exDB2TTL/project.json \
  --output-dir exDB2TTL/out
```

这一步会生成：

- `exDB2TTL/project.json`
- `exDB2TTL/metadata-request.md`

### 2. 补充配置

如果是 SQLite，至少把 `database.sqlite_path` 改成真实文件路径。  
如果是 MySQL，补上 `host / port / username / password_env`，并确保环境里有 `pymysql`。  
如果你只有每张表的样例 CSV，把 `database.dialect` 改成 `csv`，并把 `database.sample_csv_dir` 指向样例目录。

### 3. 抽取元数据

```bash
python -m exDB2TTL extract --config exDB2TTL/project.json
```

### MySQL 示例

```json
{
  "database": {
    "dialect": "mysql",
    "database_name": "crm_db",
    "tables": ["customers", "orders"],
    "host": "127.0.0.1",
    "port": 3306,
    "username": "root",
    "password_env": "DB_PASSWORD",
    "mysql_charset": "utf8mb4",
    "sample_csv_dir": "exDB2TTL/sample-csv",
    "sample_rows": 5
  }
}
```

说明：

- 如果 `sample_csv_dir` 下存在 `customers.csv`、`orders.csv`，抽取时会优先用这些样例文件覆盖数据库取样。
- 如果没有样例 CSV，就直接对 MySQL 执行 `SELECT * LIMIT n`。

### CSV 样例模式

如果没有数据库连接，但每张表都有一个同名 CSV，例如：

- `sample-csv/customers.csv`
- `sample-csv/orders.csv`

可以使用：

```json
{
  "database": {
    "dialect": "csv",
    "database_name": "crm_db",
    "tables": ["customers", "orders"],
    "sample_csv_dir": "exDB2TTL/sample-csv",
    "sample_csv_encoding": "utf-8",
    "sample_rows": 5
  }
}
```

这种模式会：

- 从 CSV 文件头推断字段名
- 从样例值粗略推断字段类型
- 读取样例行
- 不自动推断主键、外键、注释

### 4. 生成 LLM 草案

需要先设置 API Key 环境变量，例如：

```bash
export OPENAI_API_KEY=...
python -m exDB2TTL draft --config exDB2TTL/project.json
```

### 5. 校验草案

```bash
python -m exDB2TTL validate --config exDB2TTL/project.json
```

### 6. 一步跑完

```bash
python -m exDB2TTL run --config exDB2TTL/project.json
```

或者直接用脚本：

```bash
bash exDB2TTL/run.sh
```

如果配置文件不在默认位置：

```bash
bash exDB2TTL/run.sh exDB2TTL/project.json
```

脚本会自动：

- 选择 `backend/.venv/bin/python` 或回退到 `python3`
- 检查 `rdflib`、`pyshacl`
- 在 `mysql` 模式下检查 `pymysql`
- 检查配置里的 LLM API Key 环境变量是否已设置
- 调用 `python -m exDB2TTL run --config ...`

## 实现步骤

### 步骤 1：数据库元数据抽取

入口在 `metadata.py`。

- 从 SQLite / MySQL / CSV 样例读取表信息
- 读取字段名、字段类型、主键、外键
- 从数据库或同名 CSV 抽取样例数据
- 写出 `metadata.json`

### 步骤 2：构造提示词

入口在 `prompts.py`。

- 把 `metadata.json` 和业务上下文拼成结构化 prompt
- 明确要求 LLM 返回 JSON 对象
- 固定 `mapping.csv` 的表头，便于程序后处理

### 步骤 3：LLM 生成草案

入口在 `llm.py` 和 `drafts.py`。

- 调用 `chat/completions`
- 要求返回 `ontology_ttl / shacl_ttl / mapping_csv / business_rules_markdown`
- 解析并落盘

### 步骤 4：自动校验

入口在 `validate.py`。

- `rdflib` 解析 `ontology.ttl`
- `rdflib` 解析 `shacl.ttl`
- `materialize.py` 根据 `mapping.csv` + 样例数据物化 `sample-data.ttl`
- `pyshacl` 执行 SHACL 校验

### 步骤 5：固化结果

校验通过后，把 `ontology.ttl`、`shacl.ttl`、`mapping.csv` 作为稳定草案保存。后续可以继续人工审阅再进入正式版本。

## 约束说明

现在如果“真的只有数据库名和表名”，代码能做的是：

- 生成项目骨架
- 固定输出格式
- 约束后续流程

但不能凭空抽出字段名、主键、外键和样例数据。  
所以真正自动化的分界点是：必须能连库，或者至少拿到一套同名 CSV 样例文件，或者拿到 DBA 导出的完整元数据。

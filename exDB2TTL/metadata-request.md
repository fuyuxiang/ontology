# Metadata Checklist

当前项目只知道数据库名和表名时，代码可以先 bootstrap，但还不能做真实元数据抽取。

数据库:
- 名称: sample_db
- 方言: sqlite

表:
- customers
- orders

要完成自动化流程，至少还需要:
1. 连接信息
2. 字段名和字段类型
3. 主键与外键信息
4. 3 到 10 行样例数据
5. 可选的字段注释和枚举值

如果暂时不能直连数据库，可由 DBA 导出这些信息，再写入 output/metadata.json。

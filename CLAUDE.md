# 项目说明

## Git 规则

- 两个远端都在 GitHub：
  - `origin` = 同事仓库 https://github.com/fuyuxiang/ontology
  - `github` = 个人仓库 https://github.com/854875058/ontology-driven-platform

- **拉代码**：从同事仓库 origin 拉取
  ```
  git pull origin master
  ```

- **推代码**：每次修改后同步推送到两个远程
  ```
  git push origin master   # 同事仓库（fuyuxiang）
  git push github master   # 个人仓库（854875058）
  ```

- GitHub 需要代理：`127.0.0.1:7897`

# Contributing

## 开发原则

这是一个 ChatGPT Skill，不是普通 Python 包。

开发时请优先理解这四块：

- `SKILL.md`
- `agents/openai.yaml`
- `references/`
- `scripts/`

本项目的核心模式必须保持一致：

1. 探测前先收集上下文
2. 先探测，再配置
3. 配置后必须给验证命令
4. 必须保留回滚方式

优先级：

1. Windows PowerShell
2. Linux
3. macOS

## 如何开发

- 修改 Skill 行为，优先改 `SKILL.md` 和 `references/`
- 修改上下文检测，优先改 `scripts/collect_network_context.py`
- 修改测速逻辑，优先改 `scripts/diagnose_network.py`
- 修改命令生成，优先改 `scripts/generate_mirror_commands.py`
- 默认只使用 Python 标准库
- 不要引入复杂依赖
- 不要自动执行系统配置修改

## 如何修改 Skill 文档

更新文档时请确保：

- 先收集上下文
- 再测速或探测
- 再选择当前最快稳定源
- 再给配置命令
- 再给验证命令
- 再给回滚方案

不要把镜像源、Docker Hub proxy、GitHub proxy、Hugging Face mirror 写成永久可信基础设施。

## 如何新增镜像源

新增镜像源时，必须同时补充以下内容：

- 来源
- 适用生态
- 风险说明
- 验证命令
- 回滚方式

至少说明：

- 这是官方、学校、云厂商还是社区代理
- 它适用于 registry、包索引、镜像拉取，还是二进制下载
- 是否需要先探测
- 是否不适合生产或私有仓库

## 新增镜像源的提交要求

每个新增镜像源条目都应保留下面模式：

- Probe
- Configure
- Verify
- Rollback

如果是 Docker 相关，还必须区分：

- Docker CE 安装源
- Docker Hub registry mirror

如果是 Node 或浏览器生态，还必须区分：

- npm registry
- postinstall binary downloads

## 脚本约束

- `collect_network_context.py` 必须保持只读
- `diagnose_network.py` 必须保持只读
- `generate_mirror_commands.py` 只能生成命令，不能执行命令
- 所有输出凭证必须脱敏
- 不要上传任何用户数据

## Pull Request 自查

- 是否仍然把这个仓库保持为 Skill 项目
- 是否保留 Windows PowerShell 优先
- 是否保留探测、配置、验证、回滚结构
- 是否避免把不可信代理当作默认生产方案
- 是否避免提交本机路径、token、账号密码、公司内网地址

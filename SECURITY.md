# Security Policy

## 基本要求

- 不要提交 token、代理账号密码、私有 registry 地址、公司内网地址、私有仓库地址。
- 任何输出 proxy URL 的地方都必须脱敏用户名和密码。
- 任何输出 token、password、secret、authorization 的地方都必须脱敏。

## 脚本安全边界

- 诊断脚本必须只读。
- `scripts/collect_network_context.py` 只能读取上下文，不能改系统配置。
- `scripts/diagnose_network.py` 只能探测网络，不能改系统配置。
- `scripts/generate_mirror_commands.py` 只能生成命令，不能执行命令。

## 代理和镜像使用风险

- 不要把第三方代理用于私有仓库 push、私有包下载、私有模型下载或敏感生产环境。
- Docker Hub proxy、GitHub proxy、Hugging Face mirror 都应视为会变化、可能失效的外部依赖。
- 替换生产源之前必须审查安全影响，包括包完整性、证书链、源可信度、更新延迟和审计要求。

## 数据处理原则

- 不要引入任何会自动上传用户数据、配置文件或诊断结果的行为。
- 如果读取本机配置文件，输出前必须做脱敏处理。
- 不要把用户本机上下文样本直接写入仓库内容。

## 报告方式

如果你发现会导致凭证泄露、误改系统配置、错误引导到不可信代理、或把敏感流量送到第三方服务的缺陷，请不要公开贴出敏感样本。请在 issue 或私下报告中使用脱敏后的最小复现信息。

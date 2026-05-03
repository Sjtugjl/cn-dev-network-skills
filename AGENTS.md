# AGENTS.md

## Repository Type

这是一个 ChatGPT Skill，不是普通 Python 包。

不要把它当成需要打包发布到 PyPI 的项目来改造。优先维护 Skill 行为、Skill 文档和只读诊断脚本。

## Priority Files

- 修改 Skill 行为：优先改 `SKILL.md` 和 `references/`
- 修改上下文检测：优先改 `scripts/collect_network_context.py`
- 修改测速逻辑：优先改 `scripts/diagnose_network.py`
- 修改命令生成：优先改 `scripts/generate_mirror_commands.py`

## Engineering Rules

- 脚本默认只用 Python 标准库
- `collect_network_context.py` 必须只读
- `diagnose_network.py` 必须只读
- `generate_mirror_commands.py` 只能生成命令，不能自动执行命令
- 不要引入会上传用户数据的行为
- 任何输出凭证都要脱敏
- 不要把本机绝对路径、个人信息、token、proxy 密码写进仓库

## Product Rules

- Windows PowerShell 是第一优先级
- Linux 第二
- macOS 第三
- 所有建议必须保持 `探测 -> 配置 -> 验证 -> 回滚`
- 先收集上下文，再探测，再选最快稳定源

## Network-Specific Rules

- Docker Hub mirror、GitHub proxy、Hugging Face mirror 都必须描述为会变化、需要先探测
- 必须区分 Docker CE mirror 和 Docker Hub registry mirror
- 必须区分 npm registry 和 postinstall binary downloads
- 不要把不可信代理作为默认生产方案

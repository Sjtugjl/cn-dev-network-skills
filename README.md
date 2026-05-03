# cn-dev-network-skills

一键教会你的 agents 解决网络问题。

仓库主体包含：

- `SKILL.md`
- `agents/openai.yaml`
- `references/`
- `scripts/`

## 快速安装

把这句话直接复制给你的 Agent，即可安装：

`Install this skill from https://github.com/Sjtugjl/cn-dev-network-skills.git into your default skills directory and keep the full repository structure intact.`

### 安装到 Claude Code

如果你使用 Claude Code 默认 Skill 目录，可以直接执行：

Windows PowerShell：

```powershell
git clone https://github.com/Sjtugjl/cn-dev-network-skills.git "$env:USERPROFILE\.claude\skills\cn-dev-network"
```

Linux/macOS：

```bash
git clone https://github.com/Sjtugjl/cn-dev-network-skills.git "$HOME/.claude/skills/cn-dev-network"
```

如果目录已存在，更新即可：

Windows PowerShell：

```powershell
git -C "$env:USERPROFILE\.claude\skills\cn-dev-network" pull
```

Linux/macOS：

```bash
git -C "$HOME/.claude/skills/cn-dev-network" pull
```

### 安装到 Codex

如果你使用 Codex 默认 Skill 目录，可以直接执行：

Windows PowerShell：

```powershell
git clone https://github.com/Sjtugjl/cn-dev-network-skills.git "$env:USERPROFILE\.codex\skills\cn-dev-network"
```

Linux/macOS：

```bash
git clone https://github.com/Sjtugjl/cn-dev-network-skills.git "$HOME/.codex/skills/cn-dev-network"
```

如果目录已存在，更新即可：

Windows PowerShell：

```powershell
git -C "$env:USERPROFILE\.codex\skills\cn-dev-network" pull
```

Linux/macOS：

```bash
git -C "$HOME/.codex/skills/cn-dev-network" pull
```

### 安装到 OpenClaw / .agents

如果你使用 `.agents/skills` 作为默认目录，可以直接执行：

Windows PowerShell：

```powershell
git clone https://github.com/Sjtugjl/cn-dev-network-skills.git "$env:USERPROFILE\.agents\skills\cn-dev-network"
```

Linux/macOS：

```bash
git clone https://github.com/Sjtugjl/cn-dev-network-skills.git "$HOME/.agents/skills/cn-dev-network"
```

如果目录已存在，更新即可：

Windows PowerShell：

```powershell
git -C "$env:USERPROFILE\.agents\skills\cn-dev-network" pull
```

Linux/macOS：

```bash
git -C "$HOME/.agents/skills/cn-dev-network" pull
```

## 目录要求

安装后请确认目标目录中至少包含：

- `SKILL.md`
- `agents/openai.yaml`
- `references/`
- `scripts/`

## 手动安装

如果你的 Agent 不是默认目录结构，就把整个仓库放进你自己的 Skill 目录，并保留完整文件结构，不要只复制单个文件。

## 说明

- `collect_network_context.py` 是只读脚本
- `diagnose_network.py` 是只读脚本
- `generate_mirror_commands.py` 只生成命令，不自动执行

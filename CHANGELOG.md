# Changelog

## Unreleased

- 整理仓库为可开源发布的 ChatGPT Skill 结构
- 补充 `README.md`、`LICENSE`、`CONTRIBUTING.md`、`SECURITY.md`、`CHANGELOG.md`、`AGENTS.md`、`.gitignore`
- 新增 `agents/openai.yaml`
- 重写 `SKILL.md`，明确上下文收集、探测、选源、配置、验证、回滚工作流
- 更新 `references/`，补强 Windows 优先、Docker 区分、Node 与浏览器二进制区分、AI 下载与风险提示
- 修复 `scripts/diagnose_network.py` 的 DNS 解析实现并改进 reachability 语义
- 强化脚本输出脱敏与 JSON 稳定性
- 清理 `__pycache__` 和 `.pyc` 产物

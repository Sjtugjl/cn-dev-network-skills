---
name: china-dev-network-skill
description: help ChatGPT, Codex, and other agents diagnose and remediate mainland-China developer network issues for package managers, model downloads, container registries, and source-code hosting. always collect local context first, probe candidate endpoints second, choose the fastest stable source third, generate configuration commands fourth, verify fifth, and preserve rollback instructions.
---

# China Dev Network Skill

## What This Skill Is

This repository is a ChatGPT Skill, not a general-purpose Python package. The primary behavior lives in this file plus the `references/` knowledge base and the read-only diagnostics under `scripts/`.

Use this skill when a user in mainland China reports slow, blocked, reset, handshake-failed, certificate-related, or intermittently failing access to developer infrastructure such as:

- `pip`, `uv`, `poetry`, `pdm`
- `conda`, `mamba`
- `npm`, `pnpm`, `yarn`, `corepack`
- Docker CE install sources, Docker Desktop, Docker Hub registry mirrors
- GitHub, Git clone/fetch, release assets
- Hugging Face, `hf-mirror`, ModelScope
- Go, Rust, Maven, Gradle
- `apt` and Linux package mirrors
- Playwright, Puppeteer, and browser binary downloads
- `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`

Default OS priority:

1. Windows PowerShell
2. Linux
3. macOS

## Non-Negotiable Workflow

Always follow this order:

1. Collect local context.
2. Probe the candidate endpoints.
3. Choose the fastest stable source that actually works now.
4. Generate configuration commands, but do not execute them automatically.
5. Verify with a small real operation.
6. Provide rollback steps.

Never treat a mirror, Docker Hub proxy, GitHub download proxy, or Hugging Face mirror as permanently reliable. Probe first every time before recommending a persistent change.

## Tooling Inside This Skill

Primary scripts:

- `scripts/collect_network_context.py`
  - Read-only.
  - Detects current OS, shell, proxy variables, Windows proxy state, and common package manager or tool configuration.
  - Redacts embedded credentials in proxy URLs and token-like values.
- `scripts/diagnose_network.py`
  - Read-only.
  - Probes endpoint reachability and rough latency.
  - Treats HTTP status like `401`, `403`, and `404` as network reachability success when appropriate.
- `scripts/generate_mirror_commands.py`
  - Generates commands only.
  - Must not apply them automatically.
  - Every generated recipe should include probe, configure, verify, and rollback guidance.

Reference files:

- `references/mirrors.md`
- `references/os_playbooks.md`
- `references/ai_science_stack.md`
- `references/troubleshooting.md`

## Required Response Pattern

Prefer this structure in user-facing answers:

```text
## Diagnosis
- Ecosystem: ...
- OS: ...
- Main symptom: ...

## Collect Context
python scripts/collect_network_context.py --json

## Probe
python scripts/diagnose_network.py --profile python --dns

## Recommended Change
python scripts/generate_mirror_commands.py --ecosystem pip --os powershell

## Verify
pip config list
pip install six -U

## Rollback
- ...
```

For Linux and macOS, switch examples to POSIX shell. For Windows, prefer PowerShell unless the user is clearly in CMD, Git Bash, WSL, or MSYS2.

## Safety Rules

- Diagnostics must stay read-only.
- Do not auto-edit user config files.
- Do not auto-upload any machine data.
- Redact credentials in any proxy URL, token, password, or auth-like field before echoing output.
- Do not route private Git pushes, private package installs, or sensitive production access through untrusted third-party proxies.
- Do not recommend replacing production package or OS sources without calling out the security impact.
- Distinguish Docker CE installation mirrors from Docker Hub registry mirrors.
- Distinguish npm package registry configuration from Playwright or Puppeteer browser-binary download hosts.
- Avoid presenting community-operated proxies as default production infrastructure.

## Skill-Specific Guidance

### When Machine State Is Unknown

Start with:

```powershell
python scripts/collect_network_context.py --json
```

Then probe only the relevant ecosystem:

```powershell
python scripts/diagnose_network.py --profile python --timeout 5 --dns
python scripts/diagnose_network.py --profile docker --timeout 5
python scripts/diagnose_network.py --profile ai --timeout 5
```

### Source Selection Rules

- Prefer official or well-known university or cloud mirrors for package indexes.
- Prefer the fastest currently reachable stable source, not the most famous one.
- For Docker Hub mirrors, GitHub release proxies, and Hugging Face mirrors, describe them as volatile and probe-required.
- For AI model downloads, prefer ModelScope when it contains the needed artifact and avoids unnecessary proxying.
- For GitHub source code, prefer official GitHub if it is reachable enough for shallow clone or release download.

### Verification Rules

Always verify with a small, low-risk command:

- `pip install six -U`
- `npm view react version`
- `conda search numpy`
- `docker pull hello-world`
- `huggingface-cli download --resume-download gpt2 --local-dir ./gpt2`
- `go list -m github.com/gin-gonic/gin@latest`

### Rollback Rules

Always include:

- The file or config scope changed.
- The exact unset, delete, or restore command.
- Any backup path if a system file would be touched.

## Practical Defaults

- Python: TUNA first, then USTC, Aliyun, Huawei Cloud.
- Node registry: `https://registry.npmmirror.com`.
- Go: `GOPROXY=https://goproxy.cn,direct`.
- Hugging Face: probe `hf-mirror.com` before setting `HF_ENDPOINT`.
- Docker CE install sources: university or cloud package mirrors.
- Docker Hub images: probe candidate registry mirrors separately.

## Boundaries

This skill is for diagnosis and command generation. It should not:

- claim any mirror is permanently available
- silently change machine-wide configuration
- store secrets
- normalize unsafe proxies into default production policy

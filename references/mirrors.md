# Mirror and Alternative Source Inventory

Use this file as an operational inventory, not as permanent truth. Every source in this file must be probed before persistent use.

## Source Selection Policy

Apply this model every time:

1. Collect context first.
2. Probe candidate endpoints.
3. Choose the fastest stable source that is actually reachable now.
4. Generate configuration commands.
5. Verify with a small install or download.
6. Preserve rollback.

Do not assume historical availability means current availability.

## Python: pip, uv, poetry, pdm

Recommended PyPI candidates:

- TUNA: `https://pypi.tuna.tsinghua.edu.cn/simple`
- TUNA alternate path: `https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple`
- USTC: `https://mirrors.ustc.edu.cn/pypi/simple`
- Aliyun: `https://mirrors.aliyun.com/pypi/simple/`
- Huawei Cloud: `https://repo.huaweicloud.com/repository/pypi/simple`
- Tencent Cloud: `https://mirrors.cloud.tencent.com/pypi/simple`

Probe examples:

```bash
python scripts/diagnose_network.py --profile python --url https://mirrors.cloud.tencent.com/pypi/simple
```

Verification examples:

```bash
pip config list
pip install six -U
```

Rollback examples:

```bash
pip config unset global.index-url
pip config unset global.timeout
```

`uv` config locations:

- Windows user: `%AppData%\uv\uv.toml`
- Windows machine: `%ProgramData%\uv\uv.toml`
- Linux or macOS user: `~/.config/uv/uv.toml`
- Linux system: `/etc/uv/uv.toml`

`uv.toml` example:

```toml
[[index]]
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

Notes:

- `uv`, `poetry`, and `pdm` should be treated separately from plain `pip`.
- Warn before committing lockfile changes produced under a temporary or domestic mirror if CI later resolves against the official index.

## Conda and Mamba

Recommended channel roots:

- TUNA Anaconda: `https://mirrors.tuna.tsinghua.edu.cn/anaconda/`
- USTC Anaconda: `https://mirrors.ustc.edu.cn/anaconda/`
- BFSU Anaconda: `https://mirrors.bfsu.edu.cn/anaconda/`

Typical `.condarc` shape:

```yaml
channels:
  - defaults
show_channel_urls: true
default_channels:
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
custom_channels:
  conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
  nvidia: https://mirrors.sustech.edu.cn/anaconda-extra/cloud
```

Notes:

- Nightly or fast-changing channels may be incomplete.
- Solver issues are not always network issues.
- `mamba` shares much of the channel model but still needs verification after configuration.

## Node.js: npm, pnpm, yarn, Corepack

Preferred npm registry:

```bash
npm config set registry https://registry.npmmirror.com
pnpm config set registry https://registry.npmmirror.com
yarn config set registry https://registry.npmmirror.com
```

Other candidate registries:

- Tencent: `https://mirrors.tencent.com/npm/`
- Huawei: `https://repo.huaweicloud.com/repository/npm/`

Important distinction:

- npm registry settings affect package metadata and tarballs.
- Playwright, Puppeteer, Electron, Cypress, and other tools may still download browser or binary artifacts from separate hosts during install or postinstall.
- `corepack` itself is not the registry. It bootstraps package managers that then use their own configured registry.

Verification:

```bash
npm config get registry
npm view react version
```

Rollback:

```bash
npm config delete registry
pnpm config delete registry
yarn config delete registry
```

## Docker

Treat these as different systems:

1. Docker CE installation repository mirror
2. Docker Hub registry mirror or proxy for `docker pull`

Docker CE installation mirrors:

- TUNA Docker CE: `https://mirrors.tuna.tsinghua.edu.cn/docker-ce`
- XMCloud Docker CE: `https://mirrors.xmcloud.io/docker-ce/`

Docker Hub registry mirror candidates to probe:

- `https://docker.m.daocloud.io`
- `https://docker.1ms.run`
- `https://docker.xuanyuan.me`
- `https://dockerproxy.net`
- account-specific or region-specific cloud vendor mirrors

Notes:

- Docker CE mirrors do not accelerate `docker pull`.
- Public Docker Hub proxies are volatile.
- Docker Desktop on Windows and macOS should usually be configured via Docker Engine JSON, not Linux daemon instructions pasted blindly.

Verification:

```bash
docker info
docker pull hello-world
```

Rollback:

- Remove `registry-mirrors` from Docker Engine config.
- Restore any previous `daemon.json`.
- Restart Docker.

## GitHub, Git, and Release Assets

Preferred order:

1. Official GitHub if it is usable.
2. Shallow clone or targeted asset download.
3. Verified public release-asset proxy for read-only public downloads.
4. A maintained mirror on Gitee, GitCode, or vendor-hosted alternatives if the project actually exists there.

Examples:

```bash
git clone --depth 1 <repo-url>
git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=600 clone <repo-url>
```

Warnings:

- Do not push private repositories through third-party proxies.
- Do not route credentials through public GitHub proxies.
- GitHub release asset proxies must be treated as unstable and probe-required.

## Hugging Face, hf-mirror, ModelScope

Recommended pattern:

- Probe Hugging Face official.
- Probe `https://hf-mirror.com`.
- Check whether the model or dataset exists on ModelScope.
- Prefer ModelScope when it avoids proxy fragility and still provides the needed artifact.

Session examples:

```bash
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download --resume-download gpt2 --local-dir ./gpt2
```

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
huggingface-cli download --resume-download gpt2 --local-dir .\gpt2
```

Warnings:

- Do not claim `hf-mirror.com` is always available.
- Some model repos, gated access flows, or Git LFS operations may still behave differently than ModelScope.

## Go

Recommended default:

```bash
go env -w GOPROXY=https://goproxy.cn,direct
go env -w GOSUMDB=sum.golang.google.cn
```

Other candidates:

- `https://goproxy.io,direct`
- `https://mirrors.aliyun.com/goproxy/,direct`

Verification:

```bash
go env GOPROXY GOSUMDB
go list -m github.com/gin-gonic/gin@latest
```

## Rust

Candidate mirrors:

- USTC sparse index: `sparse+https://mirrors.ustc.edu.cn/crates.io-index/`
- TUNA git index: `https://mirrors.tuna.tsinghua.edu.cn/git/crates.io-index.git`

Example:

```toml
[source.crates-io]
replace-with = "ustc"

[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
```

Notes:

- Newer Cargo prefers sparse registries.
- Older Cargo may still require git-index syntax.

## Java: Maven and Gradle

Common Maven mirror candidates:

- Aliyun: `https://maven.aliyun.com/repository/public`
- Huawei: `https://repo.huaweicloud.com/repository/maven/`
- Tencent: `https://mirrors.cloud.tencent.com/nexus/repository/maven-public/`

Maven snippet:

```xml
<mirror>
  <id>aliyunmaven</id>
  <mirrorOf>*</mirrorOf>
  <name>Aliyun Maven</name>
  <url>https://maven.aliyun.com/repository/public</url>
</mirror>
```

Gradle note:

- Prefer project-level `repositories` configuration when reproducibility matters.
- Do not hide enterprise repository policy behind a global user-level override without documenting rollback.

## Linux OS Package Mirrors

Recommended families:

- TUNA: `https://mirrors.tuna.tsinghua.edu.cn/`
- USTC: `https://mirrors.ustc.edu.cn/`
- BFSU: `https://mirrors.bfsu.edu.cn/`
- Aliyun: `https://mirrors.aliyun.com/`
- Huawei: `https://repo.huaweicloud.com/`

Notes:

- Ubuntu 24.04 and newer often use DEB822 files such as `/etc/apt/sources.list.d/ubuntu.sources`.
- Older Ubuntu commonly uses `/etc/apt/sources.list`.
- Replacing security sources in production requires an explicit security tradeoff review.

## Browser and Binary Downloads

These are separate from package registries:

- Playwright browser binaries
- Puppeteer Chromium downloads
- Electron headers and artifacts
- language-server or toolchain bootstrap binaries

Rules:

- Do not assume npm or pip registry changes fix these downloads.
- Probe the binary host separately.
- Prefer session-local or project-local overrides where available.

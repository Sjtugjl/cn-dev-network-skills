#!/usr/bin/env python3
"""Generate OS-aware mirror and proxy configuration commands.

This script generates commands only. It does not execute them.
"""
from __future__ import annotations

import argparse
import platform
import textwrap


def detect_os() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "macos"
    return "linux"


def block(text: str) -> str:
    return textwrap.dedent(text).strip() + "\n"


def wrap_recipe(probe: str, configure: str, verify: str, rollback: str, notes: str = "") -> str:
    sections = [
        "## Probe",
        probe.strip(),
        "",
        "## Configure",
        configure.strip(),
        "",
        "## Verify",
        verify.strip(),
        "",
        "## Rollback",
        rollback.strip(),
    ]
    if notes.strip():
        sections.extend(["", "## Notes", notes.strip()])
    return "\n".join(sections).rstrip() + "\n"


def pip(os_name: str, mirror: str) -> str:
    py = "py" if os_name in {"windows", "powershell"} else "python3"
    probe = f"python scripts/diagnose_network.py --profile python --url {mirror}"
    configure = f"""
    {py} -m pip install -i {mirror} --upgrade pip
    pip config set global.index-url {mirror}
    pip config set global.timeout 60
    """
    verify = """
    pip config list
    pip install six -U
    """
    rollback = """
    pip config unset global.index-url
    pip config unset global.timeout
    """
    notes = "Prefer user-level configuration first. Re-check before committing lockfile changes generated under a temporary mirror."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def uv(os_name: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile python --url {mirror}"
    if os_name in {"windows", "powershell"}:
        configure = f"""
        New-Item -ItemType Directory -Force (Split-Path $env:AppData\\uv\\uv.toml) | Out-Null
        @'
        [[index]]
        url = "{mirror}"
        default = true
        '@ | Set-Content -Encoding UTF8 $env:AppData\\uv\\uv.toml
        Get-Content $env:AppData\\uv\\uv.toml
        """
        rollback = r"""
        Remove-Item $env:AppData\uv\uv.toml -ErrorAction SilentlyContinue
        """
    else:
        configure = f"""
        mkdir -p ~/.config/uv
        cat > ~/.config/uv/uv.toml <<'EOF'
        [[index]]
        url = "{mirror}"
        default = true
        EOF
        cat ~/.config/uv/uv.toml
        """
        rollback = """
        rm -f ~/.config/uv/uv.toml
        """
    verify = """
    uv --version
    """
    notes = "uv uses its own config file. This script only writes a command recipe; review before use."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def poetry(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile python --url {mirror}"
    configure = f"""
    poetry source add --priority=primary china-mirror {mirror}
    poetry source show
    """
    verify = """
    poetry source show
    poetry add six
    """
    rollback = """
    poetry source remove china-mirror
    """
    notes = "Review project-level `pyproject.toml` changes before committing."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def pdm(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile python --url {mirror}"
    configure = f"""
    pdm config pypi.url {mirror}
    pdm config pypi.verify_ssl true
    """
    verify = """
    pdm config pypi.url
    pdm add six
    """
    rollback = """
    pdm config --delete pypi.url
    """
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback))


def conda(_: str, mirror: str) -> str:
    base = mirror.rstrip("/")
    probe = f"python scripts/diagnose_network.py --profile python --url {base}/pkgs/main"
    configure = f"""
    conda config --set show_channel_urls yes
    cat > .condarc.mirror.example <<'EOF'
    channels:
      - defaults
    show_channel_urls: true
    default_channels:
      - {base}/pkgs/main
      - {base}/pkgs/r
      - {base}/pkgs/msys2
    custom_channels:
      conda-forge: {base}/cloud
      pytorch: {base}/cloud
    EOF
    """
    verify = """
    conda config --show channels
    conda search numpy
    """
    rollback = """
    Remove the injected mirror entries from ~/.condarc or %USERPROFILE%\\.condarc, then run:
    conda clean -i
    """
    notes = "Review the generated example before copying it into the real user config."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def mamba(_: str, mirror: str) -> str:
    base = mirror.rstrip("/")
    probe = f"python scripts/diagnose_network.py --profile python --url {base}/pkgs/main"
    configure = f"""
    mamba config set show_channel_urls yes
    cat > .condarc.mirror.example <<'EOF'
    channels:
      - defaults
    show_channel_urls: true
    default_channels:
      - {base}/pkgs/main
      - {base}/pkgs/r
      - {base}/pkgs/msys2
    custom_channels:
      conda-forge: {base}/cloud
      pytorch: {base}/cloud
    EOF
    """
    verify = """
    mamba config list
    mamba repoquery search numpy
    """
    rollback = """
    Remove the injected mirror entries from ~/.condarc or %USERPROFILE%\\.condarc, then clear the index cache if needed.
    """
    notes = "Review the generated example before copying it into the real user config."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def npm(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile node --url {mirror}"
    configure = f"""
    npm config set registry {mirror}
    pnpm config set registry {mirror}
    yarn config set registry {mirror}
    """
    verify = """
    npm config get registry
    npm view react version
    """
    rollback = """
    npm config delete registry
    pnpm config delete registry
    yarn config delete registry
    """
    notes = "Registry changes do not automatically fix postinstall binary downloads."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def corepack(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile node --url {mirror}"
    configure = f"""
    corepack enable
    npm config set registry {mirror}
    pnpm config set registry {mirror}
    yarn config set registry {mirror}
    """
    verify = """
    corepack --version
    npm config get registry
    """
    rollback = """
    npm config delete registry
    pnpm config delete registry
    yarn config delete registry
    """
    notes = "Corepack bootstraps package managers. The actual registry remains npm, pnpm, or yarn configuration."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def docker(os_name: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile docker --url {mirror}/v2/"
    if os_name in {"windows", "powershell", "macos"}:
        configure = f"""
        {{
          "registry-mirrors": ["{mirror}"]
        }}
        """
        rollback = """
        Remove the `registry-mirrors` entry from Docker Desktop -> Settings -> Docker Engine, then Apply & Restart.
        """
    else:
        configure = f"""
        sudo mkdir -p /etc/docker
        sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
        sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
        {{
          "registry-mirrors": ["{mirror}"]
        }}
        JSON
        sudo systemctl daemon-reload
        sudo systemctl restart docker
        """
        rollback = """
        Restore the backup daemon.json or remove the `registry-mirrors` key, then restart Docker.
        """
    verify = """
    docker info
    docker pull hello-world
    """
    notes = "This config is for Docker Hub image pulls, not Docker CE package installation."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def github_proxy(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile git --url {mirror}"
    configure = f"""
    # Use only for public, read-only downloads after probing.
    # Example:
    # curl -L {mirror}/https://github.com/OWNER/REPO/releases/download/TAG/asset.zip -o asset.zip
    """
    verify = """
    Confirm the target asset downloads successfully and matches the expected checksum.
    """
    rollback = """
    Stop using the proxy URL. Do not set it as a global Git push path.
    """
    notes = "Never route private repository credentials or pushes through third-party GitHub proxies."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def huggingface(os_name: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile ai --url {mirror}"
    if os_name in {"windows", "powershell"}:
        configure = f"""
        $env:HF_ENDPOINT = "{mirror}"
        """
        rollback = """
        Remove-Item Env:HF_ENDPOINT -ErrorAction SilentlyContinue
        """
    else:
        configure = f"""
        export HF_ENDPOINT={mirror}
        """
        rollback = """
        unset HF_ENDPOINT
        """
    verify = """
    huggingface-cli download --resume-download gpt2 --local-dir ./gpt2
    """
    notes = "Treat Hugging Face mirrors as volatile. Prefer ModelScope when it contains the required artifact."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def modelscope(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile ai --url {mirror}"
    configure = """
    pip install -U modelscope
    """
    verify = """
    modelscope download --model Qwen/Qwen2.5-0.5B-Instruct --local_dir ./Qwen2.5-0.5B-Instruct
    """
    rollback = """
    Remove any temporary MODEL_SCOPE related environment overrides if you added them for the session.
    """
    notes = "ModelScope is a domestic alternative, not a transparent Hugging Face registry mirror."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def go(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --url {mirror}"
    configure = f"""
    go env -w GOPROXY={mirror},direct
    go env -w GOSUMDB=sum.golang.google.cn
    """
    verify = """
    go env GOPROXY GOSUMDB
    go list -m github.com/gin-gonic/gin@latest
    """
    rollback = """
    go env -u GOPROXY
    go env -u GOSUMDB
    """
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback))


def rust(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --url {mirror}"
    configure = f"""
    mkdir -p ~/.cargo
    cat > ~/.cargo/config.toml <<'EOF'
    [source.crates-io]
    replace-with = "china"

    [source.china]
    registry = "{mirror}"
    EOF
    """
    verify = """
    cargo search serde
    """
    rollback = """
    rm -f ~/.cargo/config.toml
    """
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback))


def maven(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --url {mirror}"
    configure = f"""
    <!-- Add inside ~/.m2/settings.xml <mirrors> -->
    <mirror>
      <id>china-mirror</id>
      <mirrorOf>*</mirrorOf>
      <name>China Maven Mirror</name>
      <url>{mirror}</url>
    </mirror>
    """
    verify = """
    mvn -v
    mvn dependency:get -Dartifact=junit:junit:4.13.2
    """
    rollback = """
    Remove the mirror entry from ~/.m2/settings.xml.
    """
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback))


def gradle(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --url {mirror}"
    configure = f"""
    // Add to the relevant repositories block
    repositories {{
      maven {{
        url "{mirror}"
      }}
    }}
    """
    verify = """
    ./gradlew dependencies
    """
    rollback = """
    Remove the injected repository block from the project or init script.
    """
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback))


def apt(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile os --url {mirror}"
    configure = f"""
    sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
    sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
    # Edit your apt source file and replace the base mirror with:
    # {mirror}
    """
    verify = """
    sudo apt update
    apt-cache policy
    """
    rollback = """
    Restore the backed-up apt source file, then run:
    sudo apt update
    """
    notes = "Review security repository handling before replacing production apt sources."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def playwright(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile browser --url {mirror}"
    configure = f"""
    # Example session override. Review the exact host expected by your Playwright install workflow.
    export PLAYWRIGHT_DOWNLOAD_HOST={mirror}
    """
    verify = """
    python -m playwright install chromium
    """
    rollback = """
    unset PLAYWRIGHT_DOWNLOAD_HOST
    """
    notes = "Playwright browser binaries are separate from npm or pip registry settings."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def puppeteer(_: str, mirror: str) -> str:
    probe = f"python scripts/diagnose_network.py --profile browser --url {mirror}"
    configure = f"""
    export PUPPETEER_DOWNLOAD_BASE_URL={mirror}
    """
    verify = """
    npm install puppeteer
    """
    rollback = """
    unset PUPPETEER_DOWNLOAD_BASE_URL
    """
    notes = "Puppeteer binary download configuration is separate from the npm registry."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


def proxy(os_name: str, mirror: str) -> str:
    if os_name in {"windows", "powershell"}:
        configure = f"""
        $proxy = "{mirror}"
        $env:HTTP_PROXY = $proxy
        $env:HTTPS_PROXY = $proxy
        $env:http_proxy = $proxy
        $env:https_proxy = $proxy
        $env:NO_PROXY = "localhost,127.0.0.1,::1,.local,.lan"
        $env:no_proxy = $env:NO_PROXY
        """
        rollback = """
        Remove-Item Env:HTTP_PROXY, Env:HTTPS_PROXY, Env:http_proxy, Env:https_proxy, Env:NO_PROXY, Env:no_proxy -ErrorAction SilentlyContinue
        """
    else:
        configure = f"""
        export HTTP_PROXY={mirror}
        export HTTPS_PROXY={mirror}
        export http_proxy={mirror}
        export https_proxy={mirror}
        export NO_PROXY=localhost,127.0.0.1,::1,.local,.lan
        export no_proxy="$NO_PROXY"
        """
        rollback = """
        unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy
        """
    probe = "# Proxy itself should be validated locally before exporting these variables."
    verify = """
    python scripts/collect_network_context.py
    """
    notes = "Prefer session-level proxy variables first. Do not commit proxy credentials or use untrusted proxies for private production traffic."
    return wrap_recipe(block(probe), block(configure), block(verify), block(rollback), notes)


DEFAULTS = {
    "pip": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "uv": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "poetry": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "pdm": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "conda": "https://mirrors.tuna.tsinghua.edu.cn/anaconda",
    "mamba": "https://mirrors.tuna.tsinghua.edu.cn/anaconda",
    "npm": "https://registry.npmmirror.com",
    "corepack": "https://registry.npmmirror.com",
    "docker": "https://docker.m.daocloud.io",
    "github-proxy": "https://your-verified-github-proxy.example",
    "huggingface": "https://hf-mirror.com",
    "modelscope": "https://www.modelscope.cn",
    "go": "https://goproxy.cn",
    "rust": "sparse+https://mirrors.ustc.edu.cn/crates.io-index/",
    "maven": "https://maven.aliyun.com/repository/public",
    "gradle": "https://maven.aliyun.com/repository/public",
    "apt": "https://mirrors.tuna.tsinghua.edu.cn/ubuntu",
    "playwright": "https://playwright.azureedge.net",
    "puppeteer": "https://storage.googleapis.com",
    "proxy": "http://127.0.0.1:7890",
}

GENERATORS = {
    "pip": pip,
    "uv": uv,
    "poetry": poetry,
    "pdm": pdm,
    "conda": conda,
    "mamba": mamba,
    "npm": npm,
    "corepack": corepack,
    "docker": docker,
    "github-proxy": github_proxy,
    "huggingface": huggingface,
    "modelscope": modelscope,
    "go": go,
    "rust": rust,
    "maven": maven,
    "gradle": gradle,
    "apt": apt,
    "playwright": playwright,
    "puppeteer": puppeteer,
    "proxy": proxy,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate mirror configuration commands without executing them.")
    parser.add_argument("--ecosystem", required=True, choices=sorted(GENERATORS))
    parser.add_argument("--os", default=detect_os(), choices=["windows", "powershell", "linux", "macos"])
    parser.add_argument("--mirror", help="Override the default mirror or proxy endpoint.")
    args = parser.parse_args()
    mirror = args.mirror or DEFAULTS[args.ecosystem]
    print(GENERATORS[args.ecosystem](args.os, mirror))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

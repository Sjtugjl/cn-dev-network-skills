# OS-Specific Playbooks

## Windows First

Windows PowerShell is the default recommendation surface for this skill.

Use user-level configuration first when possible. Do not silently switch to CMD syntax unless the user environment requires it.

### Collect Context

```powershell
python scripts/collect_network_context.py --json
```

### Pip

```powershell
py -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set global.timeout 60
pip config list
```

Rollback:

```powershell
pip config unset global.index-url
pip config unset global.timeout
```

### Conda and Mamba

```powershell
conda config --set show_channel_urls yes
notepad $env:USERPROFILE\.condarc
conda clean -i
```

### npm, pnpm, yarn, Corepack

```powershell
npm config set registry https://registry.npmmirror.com
pnpm config set registry https://registry.npmmirror.com
yarn config set registry https://registry.npmmirror.com
npm config get registry
```

Rollback:

```powershell
npm config delete registry
pnpm config delete registry
yarn config delete registry
```

### Docker Desktop

Important distinction:

- Docker CE package mirrors are for installing Docker.
- Docker Hub registry mirrors are for pulling images.

Docker Desktop configuration example:

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
```

Apply in Docker Desktop -> Settings -> Docker Engine -> Apply & Restart.

Verification:

```powershell
docker info
docker pull hello-world
```

### Hugging Face

Session-only:

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
huggingface-cli download --resume-download gpt2 --local-dir .\gpt2
```

Rollback:

```powershell
Remove-Item Env:HF_ENDPOINT -ErrorAction SilentlyContinue
```

## Linux

### Collect Context

```bash
python3 scripts/collect_network_context.py --json
```

### Probe

```bash
python3 scripts/diagnose_network.py --profile ai --timeout 5 --dns
```

### apt

Back up first:

```bash
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
cat /etc/os-release
```

Notes:

- Ubuntu 24.04+ often uses DEB822 `ubuntu.sources`.
- Older Ubuntu often uses `/etc/apt/sources.list`.
- Do not replace security sources in production without explicit acceptance of the security tradeoff.

### Docker Daemon

```bash
sudo mkdir -p /etc/docker
sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.bak.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
JSON
sudo systemctl daemon-reload
sudo systemctl restart docker
```

Rollback:

- restore the backup
- or remove the `registry-mirrors` key
- restart Docker

## macOS

Prefer user-level configuration unless the user explicitly wants machine-wide changes.

```bash
python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
npm config set registry https://registry.npmmirror.com
```

Docker Desktop mirrors are configured through Docker Engine settings, same operational model as Windows.

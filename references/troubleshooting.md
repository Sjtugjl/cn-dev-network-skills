# Troubleshooting and Fallbacks

## Error Pattern Map

### `ReadTimeout`, `Connection timed out`, `TLS handshake timeout`

Likely an endpoint quality or path-quality issue. Probe multiple candidates, then select the fastest stable source.

### `Could not find a version that satisfies the requirement`

This is not always a network problem. Check:

- package name
- Python version
- platform tag
- channel freshness
- whether the mirror is missing metadata

### `certificate verify failed`

Do not disable TLS verification globally. Check:

- system time
- enterprise or local proxy certificates
- Python `certifi`
- whether the mirror or proxy is terminating TLS correctly

### `Temporary failure in name resolution`

This is often DNS-specific.

Examples:

```bash
nslookup pypi.org
nslookup pypi.tuna.tsinghua.edu.cn
```

```powershell
Resolve-DnsName pypi.org
Resolve-DnsName pypi.tuna.tsinghua.edu.cn
```

### Docker `pull access denied`, `manifest unknown`, or repeated retries

Possible causes:

- wrong image name
- missing namespace such as `library/ubuntu`
- architecture mismatch
- stale mirror cache
- mirror itself is reachable but not serving the needed artifact

### Conda or Mamba Solver Hangs

Do not assume this is a pure bandwidth problem.

Try:

```bash
conda clean -i
conda create -n probe python=3.11 -y
```

Reduce mixed channels where possible.

### GitHub Clone Fails Mid-Way

Try:

```bash
git clone --depth 1 <url>
git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=600 clone <url>
```

For public release assets, a tested read-only proxy may help. Do not send credentials or private repositories through third-party proxies.

## Verification Commands

Pip:

```bash
pip config list
pip install six -U
```

npm:

```bash
npm config get registry
npm view react version
```

Conda:

```bash
conda config --show channels
conda search numpy
```

Docker:

```bash
docker info
docker pull hello-world
```

Hugging Face:

```bash
python - <<'PY'
import os
print(os.environ.get("HF_ENDPOINT", "official"))
PY
```

Go:

```bash
go env GOPROXY GOSUMDB
go list -m github.com/gin-gonic/gin@latest
```

## Rollback Checklist

- Remove package manager registry overrides.
- Restore backed-up OS package source files.
- Restore Docker `daemon.json` or remove `registry-mirrors`, then restart Docker.
- Clear temporary environment variables such as `HF_ENDPOINT`.
- Remove temporary session proxy variables.
- Keep project lockfiles aligned with the source intended for CI or release use.

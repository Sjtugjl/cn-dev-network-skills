# AI and Scientific Development Playbooks

## Workflow

For AI and scientific environments, keep the same pattern:

1. Collect context.
2. Probe package, model, and binary endpoints.
3. Choose the fastest stable source.
4. Configure with the smallest scope possible.
5. Verify with a small install or model download.
6. Preserve rollback.

## Windows-First Python AI Bootstrap

PowerShell:

```powershell
py -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set global.timeout 60
pip install numpy scipy pandas scikit-learn jupyter
```

Notes:

- Do not assume PyTorch wheels are mirrored in sync with upstream.
- Match CUDA version, Python version, and architecture before recommending a wheel or channel.

## Linux and macOS Python Bootstrap

```bash
python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip3 config set global.timeout 60
```

## Conda or Mamba AI Stack

```bash
conda config --set show_channel_urls yes
conda clean -i
conda create -n ai python=3.11 -y
conda activate ai
conda install numpy scipy pandas scikit-learn jupyter -y
```

Notes:

- Prefer fewer mixed channels when the solver is unstable.
- `mamba` can improve solve speed but does not remove the need for verified channel reachability.

## Hugging Face and Model Downloads

Probe first:

```bash
python scripts/diagnose_network.py --profile ai --dns
```

Hugging Face mirror session override:

```bash
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download --resume-download <org/model> --local-dir ./models/<model>
```

PowerShell:

```powershell
$env:HF_ENDPOINT = "https://hf-mirror.com"
huggingface-cli download --resume-download <org/model> --local-dir .\models\<model>
```

If the model exists on ModelScope, prefer checking that path as a first-class domestic alternative:

```bash
pip install -U modelscope
modelscope download --model <namespace/model> --local_dir ./models/<model>
```

## Playwright, Puppeteer, Selenium

These tools often fail in a different phase than the package install itself.

Important distinction:

- npm or pip registry configuration affects the package install path.
- browser and driver binaries may still come from separate download hosts during install or postinstall.

Playwright:

```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright
python -m playwright install chromium
```

Puppeteer:

```bash
npm config set registry https://registry.npmmirror.com
npm install puppeteer
```

If browser binary downloads fail:

- probe the binary host separately
- prefer local or session-scoped overrides
- use system Chrome or Edge only when the project accepts it

## VS Code and Jupyter

- Jupyter packages follow pip or conda mirror behavior.
- VS Code extensions often depend on Microsoft Marketplace and should be treated separately.
- If Python tooling fails inside VS Code, verify whether the issue is package download, extension marketplace access, or proxy misconfiguration.

## CUDA and GPU Tooling

Do not blindly mirror CUDA or NVIDIA package sources.

Always match:

- GPU and driver version
- framework version
- CUDA toolkit version
- Python version
- OS and architecture

Prefer official framework selectors for final package choice. Use mirrors mainly for generic dependency layers unless a verified exact-version mirror is known.

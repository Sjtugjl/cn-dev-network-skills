#!/usr/bin/env python3
"""Collect local developer network context without changing system state.

This script is intentionally read-only. It detects OS, shell, proxy settings,
and common package-manager/network tool configuration so an agent can choose
safe mirror/proxy fixes based on the user's actual environment.

Examples:
  python scripts/collect_network_context.py
  python scripts/collect_network_context.py --json
  python scripts/collect_network_context.py --include-files
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

PROXY_ENV_NAMES = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
]

RECOMMENDED = {
    "pip_index": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "npm_registry": "https://registry.npmmirror.com/",
    "pnpm_registry": "https://registry.npmmirror.com/",
    "yarn_registry": "https://registry.npmmirror.com/",
    "goproxy": "https://goproxy.cn,direct",
    "gosumdb": "sum.golang.google.cn",
}

SENSITIVE_OUTPUT_HINTS = ("proxy", "token", "secret", "password", "passwd", "authorization", "_auth")


def run_cmd(cmd: list[str], timeout: float = 5.0) -> dict[str, Any]:
    """Run a command safely and return captured output."""
    exe = shutil.which(cmd[0])
    if exe is None:
        return {"available": False, "cmd": cmd, "returncode": None, "stdout": "", "stderr": f"{cmd[0]} not found"}
    try:
        proc = subprocess.run(
            [exe, *cmd[1:]],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        return {
            "available": True,
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"available": True, "cmd": cmd, "returncode": None, "stdout": "", "stderr": "timeout"}
    except Exception as exc:  # noqa: BLE001 - diagnostics should not crash
        return {"available": True, "cmd": cmd, "returncode": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def redact(value: str | None) -> str | None:
    """Redact credentials in URLs and obvious token-like values."""
    if value is None or value == "":
        return value
    # Redact URL userinfo such as http://user:pass@host:port
    try:
        parts = urlsplit(value)
        if parts.scheme and parts.netloc and "@" in parts.netloc:
            userinfo, host = parts.netloc.rsplit("@", 1)
            user = userinfo.split(":", 1)[0]
            safe_netloc = f"{user}:***@{host}" if user else f"***@{host}"
            value = urlunsplit((parts.scheme, safe_netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    # Redact common inline secret assignments.
    value = re.sub(r"(?i)(token|password|passwd|secret|_authToken)=([^\s,;]+)", r"\1=***", value)
    value = re.sub(r"(?i)(authorization:\s*)([^\s,;]+)", r"\1***", value)
    return value


def sanitize_text(value: str) -> str:
    return redact(value) or ""


def sanitize_result(result: dict[str, Any], sensitive: bool = False) -> dict[str, Any]:
    if not result:
        return result
    updated = dict(result)
    if sensitive:
        updated["stdout"] = sanitize_text(str(updated.get("stdout") or ""))
        updated["stderr"] = sanitize_text(str(updated.get("stderr") or ""))
    return updated


def detect_shell() -> dict[str, Any]:
    env = os.environ
    shell = "unknown"
    evidence: list[str] = []
    system = platform.system().lower()

    if env.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().lower():
        shell = "wsl"
        evidence.append("WSL_DISTRO_NAME or Microsoft kernel marker")
    if env.get("MSYSTEM"):
        shell = "msys2/git-bash"
        evidence.append(f"MSYSTEM={env.get('MSYSTEM')}")
    if env.get("PSModulePath") and system == "windows":
        shell = "powershell-or-windows-shell"
        evidence.append("PSModulePath present")
    if env.get("ComSpec") and system == "windows" and shell == "unknown":
        shell = "cmd-or-windows-shell"
        evidence.append(f"ComSpec={env.get('ComSpec')}")
    if env.get("SHELL"):
        sh = Path(env["SHELL"]).name
        if sh in {"bash", "zsh", "fish", "sh", "dash", "ksh"}:
            shell = sh if shell == "unknown" else f"{shell} with {sh}"
            evidence.append(f"SHELL={env.get('SHELL')}")
    if env.get("TERM_PROGRAM"):
        evidence.append(f"TERM_PROGRAM={env.get('TERM_PROGRAM')}")
    if env.get("WT_SESSION"):
        evidence.append("Windows Terminal session")

    return {"detected": shell, "evidence": evidence}


def detect_environment() -> dict[str, Any]:
    return {
        "os": platform.system() or sys.platform,
        "platform": sys.platform,
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version.split()[0],
        "cwd": str(Path.cwd()),
        "home": str(Path.home()),
        "shell": detect_shell(),
        "is_wsl": bool(os.environ.get("WSL_DISTRO_NAME")) or "microsoft" in platform.release().lower(),
    }


def detect_env_proxy() -> dict[str, Any]:
    values = {name: redact(os.environ.get(name)) for name in PROXY_ENV_NAMES}
    set_names = [name for name, value in values.items() if value]
    notes: list[str] = []
    if (values.get("HTTP_PROXY") and not values.get("HTTPS_PROXY")) or (values.get("HTTPS_PROXY") and not values.get("HTTP_PROXY")):
        notes.append("uppercase HTTP_PROXY and HTTPS_PROXY are not both set")
    if (values.get("http_proxy") and not values.get("https_proxy")) or (values.get("https_proxy") and not values.get("http_proxy")):
        notes.append("lowercase http_proxy and https_proxy are not both set")
    if set_names and not (values.get("NO_PROXY") or values.get("no_proxy")):
        notes.append("proxy is set but NO_PROXY/no_proxy is missing")
    return {"values": values, "set_names": set_names, "notes": notes}


def detect_windows_proxy() -> dict[str, Any]:
    if platform.system().lower() != "windows":
        return {"applicable": False}
    result: dict[str, Any] = {"applicable": True}
    result["winhttp"] = run_cmd(["netsh", "winhttp", "show", "proxy"], timeout=5)
    try:
        import winreg  # type: ignore

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            for name in ["ProxyEnable", "ProxyServer", "AutoConfigURL", "ProxyOverride"]:
                try:
                    value, _ = winreg.QueryValueEx(key, name)
                    result[name] = redact(str(value))
                except FileNotFoundError:
                    result[name] = None
    except Exception as exc:  # noqa: BLE001
        result["registry_error"] = f"{type(exc).__name__}: {exc}"
    return result


def parse_config_lines(output: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = redact(value.strip()) or ""
        elif ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = redact(value.strip()) or ""
    return data


def detect_pip() -> dict[str, Any]:
    commands = [["python", "-m", "pip", "config", "list"], ["py", "-m", "pip", "config", "list"], ["pip", "config", "list"]]
    chosen = None
    for cmd in commands:
        res = run_cmd(cmd, timeout=6)
        if res["available"] and res["returncode"] == 0:
            chosen = res
            break
    if chosen is None:
        chosen = run_cmd(["pip", "config", "list"], timeout=6)
    parsed = parse_config_lines(chosen.get("stdout", "")) if chosen else {}
    index = parsed.get("global.index-url") or parsed.get("site.index-url") or parsed.get("user.index-url")
    status = "ok" if index and "pypi.tuna.tsinghua.edu.cn" in index else "check_or_set_mirror"
    return {"installed": bool(chosen and chosen["available"]), "command": chosen, "config": parsed, "index_url": index, "recommended_index_url": RECOMMENDED["pip_index"], "status": status}


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def detect_node_tool(tool: str) -> dict[str, Any]:
    data: dict[str, Any] = {"installed": shutil.which(tool) is not None}
    if not data["installed"]:
        return data
    data["version"] = run_cmd([tool, "--version"], timeout=5)
    data["registry"] = sanitize_result(run_cmd([tool, "config", "get", "registry"], timeout=5))
    if data["registry"].get("returncode") != 0:
        # Some npm builds protect direct retrieval of registry. Fallback to JSON config dump.
        listing = sanitize_result(run_cmd([tool, "config", "list", "--json"], timeout=8), sensitive=True)
        data["config_list_json"] = listing
        parsed = parse_json_object(listing.get("stdout", ""))
        if parsed.get("registry"):
            data["registry"] = {
                "available": True,
                "cmd": [tool, "config", "list", "--json"],
                "returncode": 0,
                "stdout": redact(str(parsed.get("registry"))) or "",
                "stderr": "",
            }
        elif tool == "npm":
            data["registry"] = {
                "available": True,
                "cmd": [tool, "config", "get", "registry"],
                "returncode": 0,
                "stdout": "https://registry.npmjs.org/",
                "stderr": "default assumed after npm refused direct registry retrieval",
            }
    if tool in {"npm", "pnpm", "yarn"}:
        data["proxy"] = sanitize_result(run_cmd([tool, "config", "get", "proxy"], timeout=5), sensitive=True)
        data["https_proxy"] = sanitize_result(run_cmd([tool, "config", "get", "https-proxy"], timeout=5), sensitive=True)
    registry = data.get("registry", {}).get("stdout") or ""
    key = f"{tool}_registry" if tool in {"npm", "pnpm", "yarn"} else "npm_registry"
    data["recommended_registry"] = RECOMMENDED.get(key, RECOMMENDED["npm_registry"])
    data["status"] = "ok" if "registry.npmmirror.com" in registry else "change_recommended_if_slow_in_mainland_china"
    return data


def detect_project_node_files() -> dict[str, Any]:
    names = [".npmrc", ".yarnrc", ".yarnrc.yml", "pnpm-workspace.yaml", "package.json"]
    found: dict[str, Any] = {}
    cwd = Path.cwd()
    for name in names:
        path = cwd / name
        if path.exists():
            item: dict[str, Any] = {"path": str(path), "exists": True}
            if name in {".npmrc", ".yarnrc", ".yarnrc.yml"}:
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    item["interesting_lines"] = [redact(line.strip()) for line in text.splitlines() if any(k in line.lower() for k in ["registry", "proxy", "cafile", "strict-ssl"])]
                except Exception as exc:  # noqa: BLE001
                    item["read_error"] = f"{type(exc).__name__}: {exc}"
            found[name] = item
    return found


def detect_simple_tool(name: str) -> dict[str, Any]:
    data: dict[str, Any] = {"installed": shutil.which(name) is not None}
    if not data["installed"]:
        return data
    data["version"] = run_cmd([name, "--version"], timeout=5)
    return data


def detect_poetry() -> dict[str, Any]:
    data = detect_simple_tool("poetry")
    if not data.get("installed"):
        return data
    data["config"] = sanitize_result(run_cmd(["poetry", "config", "--list"], timeout=8), sensitive=True)
    return data


def detect_pdm() -> dict[str, Any]:
    data = detect_simple_tool("pdm")
    if not data.get("installed"):
        return data
    data["config"] = sanitize_result(run_cmd(["pdm", "config"], timeout=8), sensitive=True)
    return data


def detect_uv() -> dict[str, Any]:
    data = detect_simple_tool("uv")
    if not data.get("installed"):
        return data
    data["config_files"] = {
        "windows_user": str(Path.home() / "AppData" / "Roaming" / "uv" / "uv.toml") if platform.system().lower() == "windows" else None,
        "posix_user": str(Path.home() / ".config" / "uv" / "uv.toml") if platform.system().lower() != "windows" else None,
    }
    return data


def detect_mamba() -> dict[str, Any]:
    data = detect_simple_tool("mamba")
    if not data.get("installed"):
        return data
    data["config"] = sanitize_result(run_cmd(["mamba", "config", "list"], timeout=8), sensitive=True)
    return data


def detect_conda() -> dict[str, Any]:
    data: dict[str, Any] = {"installed": shutil.which("conda") is not None}
    if not data["installed"]:
        return data
    for key, args in {
        "version": ["conda", "--version"],
        "channels": ["conda", "config", "--show", "channels"],
        "default_channels": ["conda", "config", "--show", "default_channels"],
        "custom_channels": ["conda", "config", "--show", "custom_channels"],
        "proxy_servers": ["conda", "config", "--show", "proxy_servers"],
    }.items():
        data[key] = run_cmd(args, timeout=8)
    return data


def detect_docker(include_files: bool) -> dict[str, Any]:
    data: dict[str, Any] = {"installed": shutil.which("docker") is not None}
    if not data["installed"]:
        return data
    data["version"] = run_cmd(["docker", "--version"], timeout=5)
    info = run_cmd(["docker", "info"], timeout=10)
    data["info"] = info
    extracted: dict[str, Any] = {}
    if info.get("stdout"):
        for line in info["stdout"].splitlines():
            stripped = line.strip()
            for label in ["Registry Mirrors", "HTTP Proxy", "HTTPS Proxy", "No Proxy", "Docker Root Dir", "Operating System"]:
                if stripped.startswith(label + ":"):
                    extracted[label] = redact(stripped.split(":", 1)[1].strip())
    data["extracted"] = extracted
    if include_files:
        for file_path in ["/etc/docker/daemon.json", "/etc/systemd/system/docker.service.d/http-proxy.conf"]:
            path = Path(file_path)
            if path.exists():
                try:
                    data.setdefault("files", {})[file_path] = redact(path.read_text(encoding="utf-8", errors="replace"))
                except Exception as exc:  # noqa: BLE001
                    data.setdefault("files", {})[file_path] = f"read error: {type(exc).__name__}: {exc}"
    return data


def detect_git() -> dict[str, Any]:
    data: dict[str, Any] = {"installed": shutil.which("git") is not None}
    if not data["installed"]:
        return data
    queries = {
        "global_http_proxy": ["git", "config", "--global", "--get", "http.proxy"],
        "global_https_proxy": ["git", "config", "--global", "--get", "https.proxy"],
        "github_scoped_proxy": ["git", "config", "--global", "--get", "http.https://github.com.proxy"],
        "system_http_proxy": ["git", "config", "--system", "--get", "http.proxy"],
        "local_http_proxy": ["git", "config", "--local", "--get", "http.proxy"],
        "global_url_rewrites": ["git", "config", "--global", "--get-regexp", r"^url\..*\.insteadOf$"],
    }
    for key, cmd in queries.items():
        sensitive = any(hint in key for hint in SENSITIVE_OUTPUT_HINTS)
        res = sanitize_result(run_cmd(cmd, timeout=5), sensitive=True if sensitive or "proxy" in key else False)
        if res.get("stdout"):
            res["stdout"] = sanitize_text(str(res["stdout"]))
        data[key] = res
    return data


def detect_go() -> dict[str, Any]:
    data: dict[str, Any] = {"installed": shutil.which("go") is not None}
    if not data["installed"]:
        return data
    res = run_cmd(["go", "env", "GOPROXY", "GOSUMDB"], timeout=5)
    data["env"] = res
    lines = res.get("stdout", "").splitlines()
    if len(lines) >= 2:
        data["GOPROXY"] = lines[0].strip()
        data["GOSUMDB"] = lines[1].strip()
    data["recommended"] = {"GOPROXY": RECOMMENDED["goproxy"], "GOSUMDB": RECOMMENDED["gosumdb"]}
    return data


def detect_java_and_rust() -> dict[str, Any]:
    return {
        "cargo": detect_simple_tool("cargo"),
        "rustup": detect_simple_tool("rustup"),
        "mvn": detect_simple_tool("mvn"),
        "gradle": detect_simple_tool("gradle"),
    }


def detect_config_files() -> dict[str, Any]:
    home = Path.home()
    candidates = [
        home / ".cargo" / "config.toml",
        home / ".cargo" / "config",
        home / ".m2" / "settings.xml",
        home / ".condarc",
        home / "pip" / "pip.ini",
        home / ".pip" / "pip.conf",
    ]
    return {str(path): path.exists() for path in candidates}


def build_report(include_files: bool = False) -> dict[str, Any]:
    report = {
        "environment": detect_environment(),
        "proxy": {
            "env": detect_env_proxy(),
            "windows": detect_windows_proxy(),
        },
        "package_managers": {
            "pip": detect_pip(),
            "uv": detect_uv(),
            "poetry": detect_poetry(),
            "pdm": detect_pdm(),
            "npm": detect_node_tool("npm"),
            "pnpm": detect_node_tool("pnpm"),
            "yarn": detect_node_tool("yarn"),
            "corepack": {"installed": shutil.which("corepack") is not None, "version": run_cmd(["corepack", "--version"], timeout=5) if shutil.which("corepack") else None},
            "conda": detect_conda(),
            "mamba": detect_mamba(),
            "docker": detect_docker(include_files=include_files),
            "git": detect_git(),
            "go": detect_go(),
            "toolchains": detect_java_and_rust(),
        },
        "project_files": {
            "node": detect_project_node_files(),
            "common_config_files": detect_config_files(),
        },
    }
    report["suggested_actions"] = suggest_actions(report)
    return report


def get_stdout(d: dict[str, Any], *path: str) -> str:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(key)
    if isinstance(cur, dict):
        return str(cur.get("stdout") or "")
    return str(cur or "")


def suggest_actions(report: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    env_proxy = report["proxy"]["env"]
    actions.extend(env_proxy.get("notes", []))

    pip_status = report["package_managers"]["pip"].get("status")
    if pip_status == "check_or_set_mirror":
        actions.append(f"pip index-url is not a recommended mainland-China mirror; consider {RECOMMENDED['pip_index']} if pip is slow.")

    for tool in ["npm", "pnpm", "yarn"]:
        info = report["package_managers"].get(tool, {})
        if info.get("installed") and info.get("status") != "ok":
            actions.append(f"{tool} registry is not npmmirror; consider https://registry.npmmirror.com if installs are slow.")

    docker = report["package_managers"].get("docker", {})
    if docker.get("installed") and "Registry Mirrors" not in docker.get("extracted", {}):
        actions.append("Docker is installed but no registry mirror was detected in docker info; probe Docker Hub mirrors before changing daemon config.")

    git = report["package_managers"].get("git", {})
    if git.get("installed"):
        rewrites = get_stdout(report, "package_managers", "git", "global_url_rewrites")
        if rewrites:
            actions.append("Git global url.insteadOf rewrite rules are configured; inspect them before diagnosing GitHub failures.")

    go = report["package_managers"].get("go", {})
    if go.get("installed") and go.get("GOPROXY") and "goproxy.cn" not in go.get("GOPROXY", ""):
        actions.append("Go GOPROXY is not goproxy.cn; consider GOPROXY=https://goproxy.cn,direct in mainland China.")

    if not actions:
        actions.append("No obvious configuration conflict detected. Run endpoint probes next before changing mirrors or proxies.")
    return actions


def print_cmd_result(label: str, res: dict[str, Any] | None, max_lines: int = 8) -> None:
    if not res:
        print(f"  {label}: not checked")
        return
    if not res.get("available"):
        print(f"  {label}: not installed/on PATH")
        return
    stdout = res.get("stdout") or ""
    stderr = res.get("stderr") or ""
    if stdout:
        lines = stdout.splitlines()[:max_lines]
        print(f"  {label}: " + lines[0])
        for line in lines[1:]:
            print(f"    {line}")
        if len(stdout.splitlines()) > max_lines:
            print("    ...")
    elif stderr:
        print(f"  {label}: {stderr}")
    else:
        print(f"  {label}: empty")


def print_human(report: dict[str, Any]) -> None:
    env = report["environment"]
    print("# Network Context Report")
    print("\n## Environment")
    print(f"OS: {env['os']} {env['release']} ({env['platform']})")
    print(f"Arch: {env['machine']}")
    print(f"Python: {env['python']}")
    print(f"Shell: {env['shell']['detected']}")
    print(f"WSL: {'yes' if env['is_wsl'] else 'no'}")
    if env["shell"].get("evidence"):
        print("Shell evidence: " + "; ".join(env["shell"]["evidence"][:4]))

    print("\n## Proxy")
    values = report["proxy"]["env"]["values"]
    for name in PROXY_ENV_NAMES:
        print(f"{name}: {values.get(name) or 'not set'}")
    notes = report["proxy"]["env"].get("notes", [])
    for note in notes:
        print(f"Proxy note: {note}")
    win = report["proxy"].get("windows", {})
    if win.get("applicable"):
        print_cmd_result("WinHTTP", win.get("winhttp"))
        for name in ["ProxyEnable", "ProxyServer", "AutoConfigURL", "ProxyOverride"]:
            if name in win:
                print(f"  Windows user {name}: {win.get(name) or 'not set'}")

    print("\n## Package Managers and Network Tools")
    pip = report["package_managers"]["pip"]
    print(f"pip: {'installed' if pip.get('installed') else 'not installed/on PATH'}")
    print(f"  current index-url: {pip.get('index_url') or 'not set/unknown'}")
    print(f"  recommended: {pip.get('recommended_index_url')}")
    print(f"  status: {pip.get('status')}")

    for tool in ["uv", "poetry", "pdm"]:
        info = report["package_managers"][tool]
        print(f"{tool}: {'installed' if info.get('installed') else 'not installed/on PATH'}")

    for tool in ["npm", "pnpm", "yarn"]:
        info = report["package_managers"][tool]
        print(f"{tool}: {'installed' if info.get('installed') else 'not installed/on PATH'}")
        if info.get("installed"):
            print_cmd_result("version", info.get("version"), max_lines=1)
            print_cmd_result("registry", info.get("registry"), max_lines=1)
            print(f"  recommended registry: {info.get('recommended_registry')}")
            print(f"  status: {info.get('status')}")

    print(f"corepack: {'installed' if report['package_managers']['corepack'].get('installed') else 'not installed/on PATH'}")

    conda = report["package_managers"]["conda"]
    print(f"conda: {'installed' if conda.get('installed') else 'not installed/on PATH'}")
    if conda.get("installed"):
        print_cmd_result("channels", conda.get("channels"))
        print_cmd_result("proxy_servers", conda.get("proxy_servers"))

    mamba = report["package_managers"]["mamba"]
    print(f"mamba: {'installed' if mamba.get('installed') else 'not installed/on PATH'}")

    docker = report["package_managers"]["docker"]
    print(f"docker: {'installed' if docker.get('installed') else 'not installed/on PATH'}")
    if docker.get("installed"):
        print_cmd_result("version", docker.get("version"), max_lines=1)
        for key, value in docker.get("extracted", {}).items():
            print(f"  {key}: {value}")

    git = report["package_managers"]["git"]
    print(f"git: {'installed' if git.get('installed') else 'not installed/on PATH'}")
    if git.get("installed"):
        for key in ["global_http_proxy", "global_https_proxy", "github_scoped_proxy", "global_url_rewrites"]:
            print_cmd_result(key, git.get(key), max_lines=4)

    go = report["package_managers"]["go"]
    print(f"go: {'installed' if go.get('installed') else 'not installed/on PATH'}")
    if go.get("installed"):
        print(f"  GOPROXY: {go.get('GOPROXY') or 'unknown'}")
        print(f"  GOSUMDB: {go.get('GOSUMDB') or 'unknown'}")

    toolchains = report["package_managers"]["toolchains"]
    for tool in ["cargo", "rustup", "mvn", "gradle"]:
        info = toolchains[tool]
        print(f"{tool}: {'installed' if info.get('installed') else 'not installed/on PATH'}")

    print("\n## Project Files")
    node_files = report["project_files"]["node"]
    if node_files:
        for name, data in node_files.items():
            print(f"{name}: {data.get('path')}")
            for line in data.get("interesting_lines", [])[:8]:
                print(f"  {line}")
    else:
        print("No Node project config files detected in current directory.")

    print("\n## Suggested Next Actions")
    for idx, action in enumerate(report["suggested_actions"], start=1):
        print(f"{idx}. {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect read-only developer network configuration context.")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON.")
    parser.add_argument("--include-files", action="store_true", help="Include selected readable system config file contents. Off by default.")
    args = parser.parse_args()

    report = build_report(include_files=args.include_files)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

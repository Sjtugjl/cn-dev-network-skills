"""Tests for collect_network_context.py"""
from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path
from unittest import mock

import pytest

# Import the module under test
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_network_context as mod


# ---------------------------------------------------------------------------
# run_cmd
# ---------------------------------------------------------------------------

class TestRunCmd:
    def test_command_not_found(self):
        result = mod.run_cmd(["nonexistent_cmd_xyz"])
        assert result["available"] is False
        assert result["returncode"] is None
        assert "not found" in result["stderr"]

    @mock.patch("shutil.which", return_value="/usr/bin/echo")
    @mock.patch("subprocess.run")
    def test_success(self, mock_run, mock_which):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="hello\n", stderr=""
        )
        result = mod.run_cmd(["echo", "hello"])
        assert result["available"] is True
        assert result["returncode"] == 0
        assert result["stdout"] == "hello"

    @mock.patch("shutil.which", return_value="/usr/bin/slow")
    @mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="slow", timeout=5))
    def test_timeout(self, mock_run, mock_which):
        result = mod.run_cmd(["slow"], timeout=5)
        assert result["available"] is True
        assert result["returncode"] is None
        assert "timeout" in result["stderr"]

    @mock.patch("shutil.which", return_value="/usr/bin/fail")
    @mock.patch("subprocess.run", side_effect=OSError("boom"))
    def test_generic_exception(self, mock_run, mock_which):
        result = mod.run_cmd(["fail"])
        assert result["available"] is True
        assert "OSError" in result["stderr"]


# ---------------------------------------------------------------------------
# redact
# ---------------------------------------------------------------------------

class TestRedact:
    def test_none_passthrough(self):
        assert mod.redact(None) is None

    def test_empty_passthrough(self):
        assert mod.redact("") == ""

    def test_url_with_credentials(self):
        result = mod.redact("http://user:secret@example.com:8080/path")
        assert "secret" not in result
        assert "user:***@example.com" in result

    def test_url_without_credentials(self):
        url = "https://registry.npmjs.org/"
        assert mod.redact(url) == url

    def test_token_assignment(self):
        result = mod.redact("npmAuthToken=abc123secret")
        assert "abc123secret" not in result
        assert "npmAuthToken=***" in result

    def test_password_assignment(self):
        result = mod.redact("password=hunter2 rest")
        assert "hunter2" not in result
        assert "password=***" in result

    def test_plain_text_no_secrets(self):
        text = "just a normal string"
        assert mod.redact(text) == text


# ---------------------------------------------------------------------------
# detect_shell
# ---------------------------------------------------------------------------

class TestDetectShell:
    def test_returns_dict_with_expected_keys(self):
        result = mod.detect_shell()
        assert "detected" in result
        assert "evidence" in result
        assert isinstance(result["evidence"], list)

    @mock.patch.dict(os.environ, {"MSYSTEM": "MINGW64", "SHELL": "/usr/bin/bash", "PSModulePath": ""}, clear=True)
    def test_msys2_detected(self):
        result = mod.detect_shell()
        assert "msys2" in result["detected"].lower() or "git-bash" in result["detected"].lower()


# ---------------------------------------------------------------------------
# detect_environment
# ---------------------------------------------------------------------------

class TestDetectEnvironment:
    def test_returns_required_keys(self):
        result = mod.detect_environment()
        for key in ["os", "platform", "release", "version", "machine", "processor", "python", "cwd", "home", "shell", "is_wsl"]:
            assert key in result

    def test_python_is_string(self):
        result = mod.detect_environment()
        assert isinstance(result["python"], str)
        assert "." in result["python"]  # looks like a version


# ---------------------------------------------------------------------------
# detect_env_proxy
# ---------------------------------------------------------------------------

class TestDetectEnvProxy:
    @mock.patch.dict(os.environ, {}, clear=True)
    def test_no_proxy_set(self):
        result = mod.detect_env_proxy()
        assert result["set_names"] == []
        assert result["notes"] == []

    @mock.patch.dict(os.environ, {"HTTP_PROXY": "http://proxy:8080"}, clear=True)
    def test_partial_proxy_warns(self):
        result = mod.detect_env_proxy()
        assert "HTTP_PROXY" in result["set_names"]
        assert any("not both set" in n for n in result["notes"])

    @mock.patch.dict(os.environ, {
        "HTTP_PROXY": "http://proxy:8080",
        "HTTPS_PROXY": "http://proxy:8080",
        "NO_PROXY": "localhost",
    }, clear=True)
    def test_both_set_no_warn(self):
        result = mod.detect_env_proxy()
        # On Windows env vars are case-insensitive, so upper/lower variants both appear
        assert len(result["set_names"]) >= 2
        assert "NO_PROXY" in result["set_names"] or "no_proxy" in result["set_names"]
        # Both HTTP and HTTPS are set, plus NO_PROXY — no missing-proxy notes
        assert not any("not both set" in n for n in result["notes"])


# ---------------------------------------------------------------------------
# parse_config_lines
# ---------------------------------------------------------------------------

class TestParseConfigLines:
    def test_empty_input(self):
        assert mod.parse_config_lines("") == {}

    def test_key_value_pairs(self):
        output = "global.index-url = https://pypi.tuna.tsinghua.edu.cn/simple"
        result = mod.parse_config_lines(output)
        assert "global.index-url" in result
        assert "tuna" in result["global.index-url"]

    def test_colon_separated(self):
        output = "registry: https://registry.npmjs.org/"
        result = mod.parse_config_lines(output)
        assert result["registry"] == "https://registry.npmjs.org/"

    def test_comments_skipped(self):
        output = "# comment\n; another\nkey = value"
        result = mod.parse_config_lines(output)
        assert len(result) == 1
        assert result["key"] == "value"


# ---------------------------------------------------------------------------
# parse_json_object
# ---------------------------------------------------------------------------

class TestParseJsonObject:
    def test_valid_json(self):
        assert mod.parse_json_object('{"a": 1}') == {"a": 1}

    def test_invalid_json(self):
        assert mod.parse_json_object("not json") == {}

    def test_non_dict_json(self):
        assert mod.parse_json_object("[1, 2, 3]") == {}


# ---------------------------------------------------------------------------
# get_stdout
# ---------------------------------------------------------------------------

class TestGetStdout:
    def test_nested_path(self):
        d = {"a": {"b": {"stdout": "hello"}}}
        assert mod.get_stdout(d, "a", "b") == "hello"

    def test_missing_path(self):
        d = {"a": {"b": {"stdout": "hello"}}}
        assert mod.get_stdout(d, "a", "x") == ""

    def test_non_dict_at_path(self):
        d = {"a": "string"}
        assert mod.get_stdout(d, "a", "b") == ""


# ---------------------------------------------------------------------------
# suggest_actions
# ---------------------------------------------------------------------------

class TestSuggestActions:
    def test_no_issues_detected(self):
        report = {
            "proxy": {"env": {"notes": []}},
            "package_managers": {
                "pip": {"status": "ok"},
                "npm": {"installed": False},
                "pnpm": {"installed": False},
                "yarn": {"installed": False},
                "docker": {"installed": False},
                "git": {"installed": False},
                "go": {"installed": False},
            },
        }
        actions = mod.suggest_actions(report)
        assert len(actions) == 1
        assert "No obvious" in actions[0]

    def test_pip_mirror_not_set(self):
        report = {
            "proxy": {"env": {"notes": []}},
            "package_managers": {
                "pip": {"status": "check_or_set_mirror"},
                "npm": {"installed": False},
                "pnpm": {"installed": False},
                "yarn": {"installed": False},
                "docker": {"installed": False},
                "git": {"installed": False},
                "go": {"installed": False},
            },
        }
        actions = mod.suggest_actions(report)
        assert any("pip" in a for a in actions)

    def test_npm_registry_suggestion(self):
        report = {
            "proxy": {"env": {"notes": []}},
            "package_managers": {
                "pip": {"status": "ok"},
                "npm": {"installed": True, "status": "change_recommended_if_slow_in_mainland_china"},
                "pnpm": {"installed": False},
                "yarn": {"installed": False},
                "docker": {"installed": False},
                "git": {"installed": False},
                "go": {"installed": False},
            },
        }
        actions = mod.suggest_actions(report)
        assert any("npm" in a for a in actions)

    def test_go_proxy_suggestion(self):
        report = {
            "proxy": {"env": {"notes": []}},
            "package_managers": {
                "pip": {"status": "ok"},
                "npm": {"installed": False},
                "pnpm": {"installed": False},
                "yarn": {"installed": False},
                "docker": {"installed": False},
                "git": {"installed": False},
                "go": {"installed": True, "GOPROXY": "https://proxy.golang.org,direct"},
            },
        }
        actions = mod.suggest_actions(report)
        assert any("GOPROXY" in a for a in actions)


# ---------------------------------------------------------------------------
# detect_pip (with mocks)
# ---------------------------------------------------------------------------

class TestDetectPip:
    @mock.patch.object(mod, "run_cmd")
    def test_pip_not_available(self, mock_run_cmd):
        mock_run_cmd.return_value = {"available": False, "cmd": ["pip"], "returncode": None, "stdout": "", "stderr": "pip not found"}
        result = mod.detect_pip()
        assert result["installed"] is False

    @mock.patch.object(mod, "run_cmd")
    def test_pip_with_tuna_mirror(self, mock_run_cmd):
        mock_run_cmd.return_value = {
            "available": True,
            "cmd": ["pip", "config", "list"],
            "returncode": 0,
            "stdout": "global.index-url = https://pypi.tuna.tsinghua.edu.cn/simple",
            "stderr": "",
        }
        # First call for python -m pip, second fallback
        mock_run_cmd.side_effect = [
            {"available": True, "cmd": ["python", "-m", "pip", "config", "list"], "returncode": 0,
             "stdout": "global.index-url = https://pypi.tuna.tsinghua.edu.cn/simple", "stderr": ""},
        ]
        result = mod.detect_pip()
        assert result["installed"] is True
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# detect_node_tool (with mocks)
# ---------------------------------------------------------------------------

class TestDetectNodeTool:
    @mock.patch("shutil.which", return_value=None)
    def test_not_installed(self, _):
        result = mod.detect_node_tool("npm")
        assert result["installed"] is False

    @mock.patch("shutil.which", return_value="/usr/bin/npm")
    @mock.patch.object(mod, "run_cmd")
    def test_installed_with_registry(self, mock_run_cmd, _):
        mock_run_cmd.side_effect = [
            {"available": True, "returncode": 0, "stdout": "9.0.0", "stderr": ""},  # version
            {"available": True, "returncode": 0, "stdout": "https://registry.npmmirror.com/", "stderr": ""},  # registry
            {"available": True, "returncode": 0, "stdout": "", "stderr": ""},  # proxy
            {"available": True, "returncode": 0, "stdout": "", "stderr": ""},  # https-proxy
        ]
        result = mod.detect_node_tool("npm")
        assert result["installed"] is True
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# detect_conda (with mocks)
# ---------------------------------------------------------------------------

class TestDetectConda:
    @mock.patch("shutil.which", return_value=None)
    def test_not_installed(self, _):
        result = mod.detect_conda()
        assert result["installed"] is False

    @mock.patch("shutil.which", return_value="/usr/bin/conda")
    @mock.patch.object(mod, "run_cmd")
    def test_installed(self, mock_run_cmd, _):
        mock_run_cmd.return_value = {"available": True, "returncode": 0, "stdout": "conda 24.1.0", "stderr": ""}
        result = mod.detect_conda()
        assert result["installed"] is True
        assert "version" in result


# ---------------------------------------------------------------------------
# detect_docker (with mocks)
# ---------------------------------------------------------------------------

class TestDetectDocker:
    @mock.patch("shutil.which", return_value=None)
    def test_not_installed(self, _):
        result = mod.detect_docker(include_files=False)
        assert result["installed"] is False

    @mock.patch("shutil.which", return_value="/usr/bin/docker")
    @mock.patch.object(mod, "run_cmd")
    def test_installed_with_info(self, mock_run_cmd, _):
        mock_run_cmd.side_effect = [
            {"available": True, "returncode": 0, "stdout": "Docker version 24.0.0", "stderr": ""},
            {"available": True, "returncode": 0, "stdout": "Registry Mirrors: https://mirror.example.com\nHTTP Proxy: http://proxy:8080", "stderr": ""},
        ]
        result = mod.detect_docker(include_files=False)
        assert result["installed"] is True
        assert "Registry Mirrors" in result["extracted"]


# ---------------------------------------------------------------------------
# detect_git (with mocks)
# ---------------------------------------------------------------------------

class TestDetectGit:
    @mock.patch("shutil.which", return_value=None)
    def test_not_installed(self, _):
        result = mod.detect_git()
        assert result["installed"] is False

    @mock.patch("shutil.which", return_value="/usr/bin/git")
    @mock.patch.object(mod, "run_cmd")
    def test_installed(self, mock_run_cmd, _):
        mock_run_cmd.return_value = {"available": True, "returncode": 0, "stdout": "", "stderr": ""}
        result = mod.detect_git()
        assert result["installed"] is True
        assert "global_http_proxy" in result


# ---------------------------------------------------------------------------
# detect_go (with mocks)
# ---------------------------------------------------------------------------

class TestDetectGo:
    @mock.patch("shutil.which", return_value=None)
    def test_not_installed(self, _):
        result = mod.detect_go()
        assert result["installed"] is False

    @mock.patch("shutil.which", return_value="/usr/bin/go")
    @mock.patch.object(mod, "run_cmd")
    def test_installed(self, mock_run_cmd, _):
        mock_run_cmd.return_value = {
            "available": True, "returncode": 0,
            "stdout": "https://goproxy.cn,direct\nsum.golang.google.cn",
            "stderr": "",
        }
        result = mod.detect_go()
        assert result["installed"] is True
        assert result["GOPROXY"] == "https://goproxy.cn,direct"
        assert result["GOSUMDB"] == "sum.golang.google.cn"


# ---------------------------------------------------------------------------
# detect_config_files
# ---------------------------------------------------------------------------

class TestDetectConfigFiles:
    def test_returns_dict(self):
        result = mod.detect_config_files()
        assert isinstance(result, dict)
        # All values should be bools
        for v in result.values():
            assert isinstance(v, bool)


# ---------------------------------------------------------------------------
# detect_project_node_files
# ---------------------------------------------------------------------------

class TestDetectProjectNodeFiles:
    def test_returns_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = mod.detect_project_node_files()
        assert isinstance(result, dict)

    def test_finds_npmrc(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".npmrc").write_text("registry=https://registry.npmmirror.com/\n")
        result = mod.detect_project_node_files()
        assert ".npmrc" in result
        assert result[".npmrc"]["exists"] is True
        assert any("registry" in line for line in result[".npmrc"]["interesting_lines"])


# ---------------------------------------------------------------------------
# build_report (integration-ish)
# ---------------------------------------------------------------------------

class TestBuildReport:
    def test_returns_complete_structure(self):
        report = mod.build_report(include_files=False)
        assert "environment" in report
        assert "proxy" in report
        assert "package_managers" in report
        assert "project_files" in report
        assert "suggested_actions" in report
        assert isinstance(report["suggested_actions"], list)

    def test_json_serializable(self):
        report = mod.build_report(include_files=False)
        # Should not raise
        json.dumps(report, ensure_ascii=False)


# ---------------------------------------------------------------------------
# main / CLI
# ---------------------------------------------------------------------------

class TestMain:
    def test_json_output(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["collect_network_context.py", "--json"])
        exit_code = mod.main()
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "environment" in data

    def test_human_output(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["collect_network_context.py"])
        exit_code = mod.main()
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Network Context Report" in captured.out

from __future__ import annotations

from agent.tools.shell import _validate_network_command


def test_validate_network_command_rejects_non_http_url():
    assert "URL" in (_validate_network_command("curl ftp://x") or "")


def test_validate_network_command_rejects_upload_and_file_writes():
    assert "上传/写文件" in (
        _validate_network_command("curl -o out http://x.com") or ""
    )


def test_validate_network_command_rejects_intranet_targets():
    assert "禁止访问内网" in (_validate_network_command("curl http://127.0.0.1") or "")


def test_validate_network_command_allows_non_network_command():
    assert _validate_network_command("echo hi") is None

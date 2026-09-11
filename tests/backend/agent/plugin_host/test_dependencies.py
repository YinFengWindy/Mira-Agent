"""Access checks for declared strong and optional plugin APIs."""

from unittest.mock import Mock

import pytest

from agent.plugin_host.dependencies import PluginDependencies, PluginDependencyError


def test_strong_and_optional_reads_use_their_declared_access_modes():
    resolve = Mock(return_value={"ready": True})
    dependencies = PluginDependencies(
        ("required",), resolve, optional_declared=("optional",)
    )
    assert dependencies.require("required") == {"ready": True}
    resolve.assert_called_once_with("required", False)
    resolve.reset_mock()
    assert dependencies.get_optional("optional") == {"ready": True}
    resolve.assert_called_once_with("optional", True)


@pytest.mark.parametrize("method", ["require", "get_optional"])
def test_undeclared_reads_fail_before_resolving(method: str):
    resolve = Mock()
    dependencies = PluginDependencies((), resolve)
    with pytest.raises(PluginDependencyError, match="未声明"):
        getattr(dependencies, method)("unknown")
    resolve.assert_not_called()


def test_optional_declaration_does_not_grant_strong_require():
    dependencies = PluginDependencies((), Mock(), optional_declared=("optional",))
    with pytest.raises(PluginDependencyError, match="未声明"):
        dependencies.require("optional")


def test_optional_lookup_rechecks_provider_and_propagates_resolver_errors():
    resolve = Mock(
        side_effect=[{"version": 1}, None, {"version": 2}, ValueError("broken")]
    )
    dependencies = PluginDependencies((), resolve, optional_declared=("provider",))
    assert dependencies.get_optional("provider") == {"version": 1}
    assert dependencies.get_optional("provider") is None
    assert dependencies.get_optional("provider") == {"version": 2}
    with pytest.raises(ValueError, match="broken"):
        dependencies.get_optional("provider")

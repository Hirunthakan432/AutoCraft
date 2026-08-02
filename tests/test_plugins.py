import pytest

from src.plugins.registry import PluginRegistry, create_default_registry


def test_marketplace_lists_catalog():
    reg = PluginRegistry()
    names = {p["name"] for p in reg.marketplace()}
    assert "echo" in names
    assert "summarize" in names


def test_install_and_run():
    reg = PluginRegistry()
    reg.install("echo")
    assert reg.run("echo", "hi") == "echo: hi"
    assert "echo" in reg.list_plugins()


def test_disable_blocks_run():
    reg = create_default_registry()
    reg.disable("echo")
    with pytest.raises(PermissionError):
        reg.run("echo", "x")


def test_unknown_install():
    reg = PluginRegistry()
    with pytest.raises(KeyError):
        reg.install("no-such-plugin")

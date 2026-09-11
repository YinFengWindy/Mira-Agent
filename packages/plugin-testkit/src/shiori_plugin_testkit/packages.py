"""Location of explicitly available plugin packages, without repository assumptions."""

from importlib.util import find_spec
from pathlib import Path


def plugin_directory(plugin_id: str) -> Path:
    """Returns the installed/imported plugin package owning its manifest and backend."""
    spec = find_spec(f"plugins.{plugin_id}")
    if spec is None or not spec.submodule_search_locations:
        raise ModuleNotFoundError(f"Plugin dependency is not installed: {plugin_id}")
    return Path(next(iter(spec.submodule_search_locations))).resolve()

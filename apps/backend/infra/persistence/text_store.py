"""Atomic UTF-8 text persistence shared by configuration writers."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def atomic_save_text(path: Path, content: str) -> None:
    """Durably replaces a UTF-8 file; interrupted writes leave the old file intact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

from __future__ import annotations
from pathlib import Path

def envelope(command, root: Path, revision=0, *, argv=None, data=None, artifacts=None, warnings=None, errors=None, next_steps=None, status="ok"):
    return {"schema_version": "1.0", "command": command, "argv": argv or command.split(), "status": status, "project_root": str(root.resolve()), "revision": revision, "data": data or {}, "artifacts": artifacts or {}, "warnings": warnings or [], "errors": errors or [], "next_steps": next_steps or []}

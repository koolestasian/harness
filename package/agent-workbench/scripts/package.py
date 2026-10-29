#!/usr/bin/env python3
"""Package source only; never walk runtime, credential or model directories."""
import hashlib
from pathlib import Path
import sys
import zipfile

root = Path(__file__).resolve().parent.parent
output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root.parent / "shared/agent-workbench-mvp.zip"
files = [root / name for name in [
    ".gitignore", ".dockerignore", "README.md", "STATUS.md", "workbench.py", "local_gateway.py", "desktop_ui.py", "ui/index.html",
    "versions.json", "requirements.in", "requirements.lock", "cli-package-lock.json",
    ".vscode/extensions.json", "deploy/Dockerfile", "deploy/compose.yaml",
]]
for folder, patterns in {"docs": ["*.md"], "templates": ["*.md"],
                         "scripts": ["*.sh", "*.ps1", "*.py", "*.command"],
                         "tests": ["test_*.py"], "deploy": ["*.py", "*.sh", "*.md"]}.items():
    for pattern in patterns:
        files.extend((root / folder).glob(pattern))
files = sorted(set(files))
manifest = root / "MANIFEST.sha256"
manifest.write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(root).as_posix() + "\n" for p in files))
output.parent.mkdir(parents=True, exist_ok=True)
temporary = output.with_suffix(".zip.tmp")
with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files + [manifest]:
        archive.write(path, "agent-workbench/" + path.relative_to(root).as_posix())
temporary.replace(output)
print(f"{output}: {len(files) + 1} source files, {output.stat().st_size} bytes")
print("SHA256 " + hashlib.sha256(output.read_bytes()).hexdigest())

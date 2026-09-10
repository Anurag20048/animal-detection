import py_compile
from pathlib import Path

root = Path('.').resolve()
errors = []
files = list(root.rglob('*.py'))
for path in files:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:
        errors.append((path, exc))
print(f'checked {len(files)} files')
if errors:
    for path, exc in errors:
        print(path)
        print(exc)
    raise SystemExit(1)

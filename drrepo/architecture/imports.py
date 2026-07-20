from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


IGNORED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "site-packages",
    "vendor",
}


@dataclass
class PythonModuleInfo:
    path: str
    module: str
    imports: list[str] = field(default_factory=list)
    internal_imports: list[str] = field(default_factory=list)
    external_imports: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    framework_signals: list[str] = field(default_factory=list)
    route_count: int = 0
    has_main_guard: bool = False
    syntax_error: str | None = None


def is_ignored(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except Exception:
        return True
    return any(part in IGNORED_DIRS for part in rel.parts)


def rel_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def module_name_for_path(path: Path, root: Path) -> str:
    rel = Path(rel_path(path, root))
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def iter_python_files(root: Path, *, limit: int = 350) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if is_ignored(path, root):
            continue
        files.append(path)
        if len(files) >= limit:
            break
    return files


def _resolve_relative_import(module: str, level: int, current_module: str, current_path: Path) -> str:
    parts = current_module.split(".") if current_module else []
    if current_path.name != "__init__.py" and parts:
        parts = parts[:-1]
    if level > 1:
        parts = parts[: max(0, len(parts) - (level - 1))]
    if module:
        parts.extend(module.split("."))
    return ".".join(part for part in parts if part)


def _has_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    text = ast.dump(node.test)
    return "__name__" in text and "__main__" in text


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Attribute):
        base = _decorator_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def parse_python_module(path: Path, root: Path, internal_modules: set[str]) -> PythonModuleInfo:
    module = module_name_for_path(path, root)
    info = PythonModuleInfo(path=rel_path(path, root), module=module)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(text)
    except SyntaxError as exc:
        info.syntax_error = f"syntax error at line {exc.lineno or '?'}"
        return info
    except OSError as exc:
        info.syntax_error = str(exc)
        return info

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                imports.append(_resolve_relative_import(node.module or "", node.level, module, path))
            elif node.module:
                imports.append(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            info.symbols.append(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = [_decorator_name(item) for item in node.decorator_list]
                if any(name.split(".")[-1] in {"get", "post", "put", "delete", "patch", "route"} for name in decorators):
                    info.route_count += 1
        elif isinstance(node, ast.Assign):
            call = node.value
            if isinstance(call, ast.Call):
                func = _decorator_name(call.func)
                if func in {"FastAPI", "Flask"}:
                    info.framework_signals.append(func)
        elif _has_main_guard(node):
            info.has_main_guard = True

    info.imports = sorted(set(imports))
    for imported in info.imports:
        root_name = imported.split(".")[0]
        if imported in internal_modules or root_name in {m.split(".")[0] for m in internal_modules}:
            info.internal_imports.append(imported)
        else:
            info.external_imports.append(root_name)
    info.internal_imports = sorted(set(info.internal_imports))
    info.external_imports = sorted(set(info.external_imports))
    info.framework_signals = sorted(set(info.framework_signals))
    info.symbols = sorted(set(info.symbols))[:12]
    return info


def collect_python_import_graph(root: Path) -> tuple[list[PythonModuleInfo], list[str]]:
    files = iter_python_files(root)
    internal_modules = {module_name_for_path(path, root) for path in files}
    modules = [parse_python_module(path, root, internal_modules) for path in files]
    parse_errors = [f"{info.path}: {info.syntax_error}" for info in modules if info.syntax_error]
    return modules, parse_errors


def read_json_file(path: Path) -> dict[str, Any]:
    import json

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}

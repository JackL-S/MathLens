"""架构约束：模型不依赖服务、模型依赖无环、核心导入不加载执行后端。"""

import ast
import importlib.util
from pathlib import Path
import subprocess
import sys

from mathlens.control import ExecutionControl
from mathlens.execution import ExecutionControl as ExportedControl


def test_runtime_control_reexport_preserves_identity():
    assert ExportedControl is ExecutionControl


def test_application_import_does_not_load_math_or_process_backends():
    code = """
import sys
import mathlens.application
assert 'mathlens.execution' not in sys.modules
assert 'multiprocessing' not in sys.modules
assert 'sympy' not in sys.modules
assert 'latex2sympy2' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_all_internal_imports_are_acyclic_including_lazy_imports():
    """扫描函数体中的导入，避免用延迟导入隐藏 application/execution 依赖环。"""
    source_root = Path(__file__).resolve().parents[1] / "src/mathlens"
    modules = {}
    for path in source_root.rglob("*.py"):
        parts = path.relative_to(source_root).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        name = ".".join(("mathlens", *parts))
        modules[name] = path
    graph = {}
    for name, path in modules.items():
        package = name if path.stem == "__init__" else name.rpartition(".")[0]
        imports = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                target = "." * node.level + (node.module or "")
                target = importlib.util.resolve_name(target, package) if node.level else target
                imports.add(target)
                imports.update(target + "." + alias.name for alias in node.names)
        graph[name] = imports & modules.keys()
    for name in ("mathlens.execution", "mathlens.pipeline", "mathlens.preflight"):
        assert "mathlens.application" not in graph[name]

    visiting = set()
    visited = set()

    def visit(name):
        assert name not in visiting, f"项目模块存在循环依赖：{name}"
        if name in visited:
            return
        visiting.add(name)
        for target in graph[name]:
            visit(target)
        visiting.remove(name)
        visited.add(name)

    for name in graph:
        visit(name)


def test_schema_dependencies_are_acyclic_and_do_not_import_services():
    schema_root = Path(__file__).resolve().parents[1] / "src/mathlens/schemas"
    graph = {}
    forbidden = {
        "mathlens.application", "mathlens.execution", "mathlens.control",
        "mathlens.preflight", "mathlens.pipeline", "mathlens.codec",
        "sympy", "latex2sympy2", "multiprocessing",
    }
    for path in schema_root.glob("*.py"):
        name = "mathlens.schemas" + ("." + path.stem if path.stem != "__init__" else "")
        imports = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                target = "." * node.level + (node.module or "")
                imports.add(importlib.util.resolve_name(target, "mathlens.schemas") if node.level else target)
        assert not any(
            target == blocked or target.startswith(blocked + ".")
            for target in imports for blocked in forbidden
        ), (name, imports)
        graph[name] = {target for target in imports if target.startswith("mathlens.schemas")}
    visiting = set()
    visited = set()

    def visit(name):
        assert name not in visiting, f"模型依赖存在循环：{name}"
        if name in visited:
            return
        visiting.add(name)
        for target in graph.get(name, ()):
            visit(target)
        visiting.remove(name)
        visited.add(name)

    for name in graph:
        visit(name)

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


def test_schema_dependencies_are_acyclic_and_do_not_import_services():
    schema_root = Path(__file__).resolve().parents[1] / "src/mathlens/schemas"
    graph = {}
    forbidden = {
        "mathlens.application", "mathlens.execution", "mathlens.control",
        "mathlens.policies", "mathlens.jobs", "mathlens.codec", "mathlens.media",
        "mathlens.ocr", "sympy", "latex2sympy2", "multiprocessing",
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

"""回归测试：运行时代码用到的第三方依赖必须都在依赖清单里声明。

背景：openpyxl 曾被漏登记进依赖清单 —— 本地开发环境恰好装过它所以没暴露，
容器严格按清单安装后启动即崩（ModuleNotFoundError: No module named 'openpyxl'）。
本测试扫描 app/alembic/scripts 中所有顶层 import，逐个核对是否被三个依赖清单
（requirements.txt / requirements-ai.txt / requirements-all.txt）覆盖，
防止同类"用了但没登记"的问题再次出现。
"""

import ast
import re
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
CODE_DIRS = ("app", "alembic", "scripts")
REQ_FILES = ("requirements.txt", "requirements-ai.txt", "requirements-all.txt")

# 依赖清单里每行开头的包名（版本号、环境标记等后面部分不参与匹配）。
PACKAGE_PATTERN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")


def normalize(name: str) -> str:
    """按 PEP 503 归一化包名：转小写并去掉 - _ . 分隔符。"""
    return name.lower().replace("-", "").replace("_", "").replace(".", "")


def collect_third_party_imports() -> dict:
    """收集 {顶层模块名: 首次出现的文件}，排除标准库和本地 app 包。"""
    imports = {}
    for directory in CODE_DIRS:
        for path in (BACKEND_DIR / directory).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level == 0 and node.module:
                        names = [node.module]
                    else:
                        names = []
                else:
                    continue
                for name in names:
                    imports.setdefault(name.split(".")[0], path)

    stdlib = sys.stdlib_module_names
    return {name: path for name, path in imports.items() if name not in stdlib and name != "app"}


def collect_declared_packages() -> set:
    """收集三个依赖清单里声明过的归一化包名。"""
    declared = set()
    for filename in REQ_FILES:
        content = (BACKEND_DIR / filename).read_text(encoding="utf-8")
        for line in content.splitlines():
            match = PACKAGE_PATTERN.match(line.strip())
            if match:
                declared.add(normalize(match.group(1)))
    return declared


class DependencyDeclarationTest(unittest.TestCase):
    def test_runtime_imports_are_declared(self):
        declared = collect_declared_packages()
        # 判断规则：import 名归一化后是某个已声明包名的一部分
        # （覆盖 jwt→PyJWT、sqlalchemy→SQLAlchemy、pydantic_settings→pydantic-settings 等名称差异）。
        missing = {
            name: str(path.relative_to(BACKEND_DIR))
            for name, path in collect_third_party_imports().items()
            if not any(normalize(name) in package for package in declared)
        }
        self.assertEqual({}, missing, f"以下依赖被代码引用但未在依赖清单中声明：{missing}")


if __name__ == "__main__":
    unittest.main()

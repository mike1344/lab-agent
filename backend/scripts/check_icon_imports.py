"""检查 .vue 模板里使用的图标组件是否都在本文件显式 import（用于移除全局图标注册）。

用法：python scripts/check_icon_imports.py
"""

import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "fronted/src"
TAG_PATTERN = re.compile(r"<([A-Z][A-Za-z0-9]+)")
ICON_IMPORT_PATTERN = re.compile(r"import\s*\{([^}]+)\}\s*from\s*['\"]@element-plus/icons-vue['\"]")

# 非图标的大写组件（本地组件/路由组件等）
IGNORE = {"RouterLink", "RouterView", "App", "Layout"}


def main() -> None:
    missing = []
    for path in SRC.rglob("*.vue"):
        text = path.read_text("utf-8")
        imported = set()
        for match in ICON_IMPORT_PATTERN.finditer(text):
            imported.update(name.strip() for name in match.group(1).split(","))
        # 本地导入的组件（相对路径或 @/components）
        for match in re.finditer(r"import\s+([A-Z][A-Za-z0-9]+)\s+from", text):
            imported.add(match.group(1))
        used = set(TAG_PATTERN.findall(text)) - IGNORE
        unknown = {name for name in used if name not in imported and not name.startswith("El")}
        if unknown:
            missing.append((str(path.relative_to(SRC.parent)), sorted(unknown)))
    if missing:
        for path, names in missing:
            print(f"MISSING {path}: {', '.join(names)}")
        sys.exit(1)
    print("所有模板图标均已显式导入，可移除 main.js 的全局注册")


if __name__ == "__main__":
    main()

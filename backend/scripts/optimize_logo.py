"""压缩前端 Logo：按最大边长缩放并优化 PNG，避免 800KB+ 的图片进入构建产物。

用法（在 backend 目录执行）：
    .\\.venv\\Scripts\\python.exe scripts\\optimize_logo.py
"""

from pathlib import Path

from PIL import Image

LOGO = Path(__file__).resolve().parent.parent.parent / "fronted/src/assets/css/images/logo.png"
MAX_SIDE = 256


def main() -> None:
    if not LOGO.exists():
        raise SystemExit(f"未找到 Logo：{LOGO}")
    before = LOGO.stat().st_size
    image = Image.open(LOGO)
    print(f"原始：{image.size[0]}x{image.size[1]} {image.mode} {before / 1024:.0f} KB")

    if max(image.size) > MAX_SIDE:
        ratio = MAX_SIDE / max(image.size)
        image = image.resize(
            (max(1, int(image.size[0] * ratio)), max(1, int(image.size[1] * ratio))),
            Image.LANCZOS,
        )

    if image.mode not in ("RGBA", "RGB"):
        image = image.convert("RGBA")

    image.save(LOGO, format="PNG", optimize=True)
    after = LOGO.stat().st_size
    print(f"输出：{image.size[0]}x{image.size[1]} {after / 1024:.0f} KB（节省 {(1 - after / before) * 100:.0f}%）")


if __name__ == "__main__":
    main()

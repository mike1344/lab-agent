"""可选病毒扫描钩子（ClamAV 等）。

约定：`CLAMAV_COMMAND` 为可执行命令（如 `clamdscan --no-summary`），
服务端会在命令后追加文件路径，退出码 0 视为干净、1 视为感染。
未配置命令时直接放行（开发环境常见）；配置了但扫描器异常时：
- `CLAMAV_REQUIRED=false`（默认）：放行并记 warning，保证上传可用；
- `CLAMAV_REQUIRED=true`：拒绝上传（生产环境建议开启）。
"""

import logging
import shlex
import subprocess

from app.config import settings

logger = logging.getLogger("lab_agent")

SCAN_TIMEOUT_SECONDS = 15


def antivirus_configured() -> bool:
    return bool(settings.CLAMAV_COMMAND.strip())


def scan_uploaded_file(file_path: str) -> tuple[bool, str]:
    """扫描上传文件，返回 (是否放行, 状态)。状态：skipped/clean/infected/scanner_error。"""
    if not antivirus_configured():
        return True, "skipped"
    command = shlex.split(settings.CLAMAV_COMMAND) + [file_path]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=SCAN_TIMEOUT_SECONDS,
        )
    except Exception:  # noqa: BLE001 - 扫描器不可用不能炸掉上传接口
        logger.warning("病毒扫描失败：扫描器不可执行或超时")
        return (not settings.CLAMAV_REQUIRED), "scanner_error"

    if result.returncode == 0:
        return True, "clean"
    if result.returncode == 1:
        return False, "infected"
    # clamdscan 常见返回码 1=感染、2=出错；其他非零统一按异常处理
    logger.warning("病毒扫描异常：returncode=%s", result.returncode)
    return (not settings.CLAMAV_REQUIRED), "scanner_error"

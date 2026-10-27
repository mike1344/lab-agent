"""通用 Excel 导出：openpyxl 组装工作簿并包装为下载响应。

预约导出、设备台账、报修记录、用户列表共用这一套封装，
新增导出维度时只需要准备表头与数据行，避免每个接口各写一遍 Workbook 样板代码。
"""

from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from fastapi.responses import Response as FastAPIResponse
from openpyxl import Workbook

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def build_excel_response(
    *,
    sheet_title: str,
    headers: list[str],
    rows: list[list],
    filename_prefix: str,
    extra_sheets: list[tuple[str, list[str], list[list]]] | None = None,
) -> FastAPIResponse:
    """生成 .xlsx 下载响应。

    文件名使用 RFC 5987 编码（filename*=UTF-8''...），中文文件名在各浏览器下不乱码；
    同时保留 filename= 兼容旧客户端。extra_sheets 用于一张报表导出多个维度。
    """
    workbook = Workbook()
    sheet = workbook.active
    # Excel 工作表名上限 31 个字符，超长会被 openpyxl 拒绝
    sheet.title = sheet_title[:31]
    sheet.append(headers)
    for row in rows:
        sheet.append(row)

    for title, extra_headers, extra_rows in extra_sheets or []:
        extra_sheet = workbook.create_sheet(title=title[:31])
        extra_sheet.append(extra_headers)
        for row in extra_rows:
            extra_sheet.append(row)

    buffer = BytesIO()
    workbook.save(buffer)
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    disposition = f"attachment; filename={quote(filename)}; filename*=UTF-8''{quote(filename)}"
    return FastAPIResponse(
        content=buffer.getvalue(),
        media_type=EXCEL_MEDIA_TYPE,
        headers={"Content-Disposition": disposition},
    )

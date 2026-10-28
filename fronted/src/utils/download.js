/** 从 Content-Disposition 解析下载文件名（优先 RFC 5987 的 filename*=UTF-8''...）。
 *
 * 单独导出纯函数，便于 Node 单测；downloadBlobResponse 只负责创建 <a> 触发下载。
 */
export function parseFilename(disposition, fallbackName = '导出.xlsx') {
  const encoded = String(disposition || '').match(/filename\*=UTF-8''([^;]+)/i)
  const plain = String(disposition || '').match(/filename=([^;]+)/i)

  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim())
    } catch {
      return encoded[1].trim()
    }
  }
  if (plain) {
    return plain[1].trim().replace(/"/g, '')
  }
  return fallbackName
}

/** 下载后端返回的 Excel blob。 */
export function downloadBlobResponse(response, fallbackName = '导出.xlsx') {
  const filename = parseFilename(response?.headers?.['content-disposition'], fallbackName)
  const blob = response?.data
  if (!blob) return

  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

import { ElMessageBox } from 'element-plus'

/** 危险操作二次确认：弹出密码输入框，返回密码字符串；用户取消返回 null。 */
export async function promptSignature(message) {
  try {
    const { value } = await ElMessageBox.prompt(message, '危险操作确认', {
      inputType: 'password',
      inputPlaceholder: '请输入当前登录密码',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    })
    return value || ''
  } catch {
    // 点击取消或关闭弹窗时 Element Plus 会 reject
    return null
  }
}

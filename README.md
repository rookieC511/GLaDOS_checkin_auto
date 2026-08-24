# GLaDOS 自动签到

每天通过 GitHub Actions 调用 GLaDOS 签到接口，并在仓库长期无人工提交时自动保持定时工作流可用。

## 配置

在仓库的 **Settings → Secrets and variables → Actions** 中配置：

- `GLADOS_COOKIE`：必需，GLaDOS 登录 Cookie。为了兼容旧配置，也会读取名为 `COOKIE` 的 Secret。
- `PUSHPLUS_TOKEN`：可选，用于推送签到结果。

多个账号仍可用 `&` 分隔，也可以每行放一个 Cookie。

> Cookie 是登录凭据。只应放进 GitHub Actions Secret，不要写入代码、Issue 或公开日志。

## 运行方式

- 自动签到：每天北京时间约 08:37 运行。GitHub 的定时任务可能有排队延迟。
- 手动验证：进入 **Actions → GLaDOS Checkin → Run workflow**。
- 防自动停用：`Keep scheduled workflows active` 每月运行两次，只更新 `MAINTENANCE.md`。它不接触 GLaDOS Cookie。

如果仓库曾因 60 天无活动而被 GitHub 停用，需要先在 Actions 页面分别打开工作流并点击 **Enable workflow**。

## 失败行为

脚本会在以下情况返回非零状态，让 GitHub Actions 明确显示失败：

- Secret 缺失；
- Cookie 过期或无权限；
- GLaDOS 接口连续请求失败；
- 所有当前签到 token 均被拒绝。

脚本会依次尝试 `glados.network`、`glados.cloud` 和 `glados.rocks`，并对临时网络故障进行有限重试。日志只显示“账号 1/2…”，不会输出 Cookie 或邮箱。

## 本地测试

```bash
python -m pip install requests==2.32.5
python -m unittest discover -s tests -v
```

原始项目：[domeniczz/GLaDOS_checkin_auto](https://github.com/domeniczz/GLaDOS_checkin_auto)

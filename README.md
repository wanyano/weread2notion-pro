# WeRead2Notion 安全迁移分支

本分支用于从旧版 `weread2notion-pro` 迁移到上游新版 `malinkang/weread2notion`，不会覆盖旧 `main` 分支。

- 迁移分支：`migration/weread2notion-v1`
- 上游版本：`1.0.8`
- 已固定并审计的上游提交：`36daed3aa7fda67088f97fc23c03f63e418220c4`
- GitHub Actions：仅手动运行，没有定时任务
- 旧版阅读热力图任务：在本迁移分支中已禁用
- 旧 `main` 分支、代码与历史：未修改

> [!CAUTION]
> 新版会在检测到书籍笔记更新时删除并重建相应的 Notion 同步页面。不要把首次迁移指向唯一一份旧数据，也不要在新版自动生成的书籍页面中保存无法恢复的个人内容。

## 迁移前：备份和隔离 Notion 数据

首次运行前必须完成以下操作：

1. 在 Notion 中打开旧版微信读书主页或数据库，使用 **Export** 导出完整备份；建议选择 Markdown & CSV，并包含子页面。
2. 按上游最新教程复制开发者提供的新版 WeRead2Notion 模板，作为独立迁移目标。
3. 不要直接使用旧 Pro 数据库、自建数据库或其他模板；它们的字段和结构可能不兼容。
4. 让 Notion Integration 只连接到新模板；保留旧页面不动。
5. 记录旧版书籍数量，并抽查几本书的划线和笔记数量，供迁移后核对。

本仓库不会、也不应保存导出的 Notion 数据或任何密钥。

最新版教程：https://www.notionhub.app/docs/weread2notion

## 需要自行配置的 GitHub Actions Secrets

进入仓库 **Settings → Secrets and variables → Actions**，创建以下 Repository secrets：

| Secret | 用途 | 要求 |
| --- | --- | --- |
| `WEREAD_API_KEY` | 新版微信读书 Gateway API Key | 必填 |
| `NOTION_TOKEN` | Notion Integration Token | 必填 |
| `NOTION_PAGE` | 新复制的官方 WeRead2Notion 模板页面链接 | 必填；不要填写旧 Pro 页面 |

不要在 Issue、PR、提交、Actions 日志或聊天中粘贴这些值，也不要主动给值添加引号。旧版 `WEREAD_COOKIE` 以及 `CC_URL`、`CC_ID`、`CC_PASSWORD` 等不再用于新版迁移。

上游代码也支持 `NOTION_DATABASE_ID` 和 `NOTION_DATA_SOURCE_ID`。为匹配当前官方教程并减少误配置，本迁移分支固定使用 `NOTION_PAGE`，三者不要混用。

## 首次手动验证

1. 打开仓库的 **Actions** 页面，选择原有的 WeRead 工作流。
2. 点击 **Run workflow**，务必把分支切换为 `migration/weread2notion-v1`，不要选择 `main`。
3. 勾选已导出旧数据并使用全新官方模板的确认项，然后运行。
4. 工作流只检查 Secrets 是否存在，不会打印它们的值。
5. 在 Notion 新模板中核对：
   - 书籍是否创建；
   - 划线和笔记数量是否合理；
   - 中文、封面、章节和长笔记是否正常；
   - 再次手动运行时是否只处理有更新的数据；
   - 旧版 Notion 页面是否完全未变化。

若任一项异常，停止运行，保留旧数据与导出文件，并查看 Actions 的错误步骤。不要用包含密钥的截图或日志公开求助。

## 定时同步

本分支故意没有 `schedule`。只有在完成备份、首次手动验证和数量抽查后，才应在独立新版仓库或正式分支中加入定时任务。

上游示例的定时表达式是每天 UTC 00:00（北京时间 08:00）：

```yaml
schedule:
  - cron: "0 0 * * *"
```

不要在验证前启用定时同步，也不要把新版直接指向旧版唯一数据副本。

## 代码与安全核验摘要

- 新版使用 `WEREAD_API_KEY`，不再依赖微信读书 Cookie。
- 上游 Action 固定到已审计提交，避免 `@main` 后续变化直接进入任务。
- 权限限制为 `contents: read`。
- 工作流没有检出或执行旧 Pro 包，因此不会走旧版 Cookie、Cloudflare 或旧数据库写入逻辑。
- 新版源代码包含删除并重建已同步书籍页面的逻辑，因此 Notion 导出备份和全新官方模板是强制前置条件。
- Secrets 只能由仓库所有者在 GitHub 设置中填写；本分支不包含任何明文密钥。

上游仓库：https://github.com/malinkang/weread2notion

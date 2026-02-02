# Changelog

遵循 Keep a Changelog 约定，所有显著变更都会记录在此。版本号与 `pyproject.toml` 对齐。

## [Unreleased]

### Added
- **OpenAI Video API 兼容接口**：新增 `/v1/videos` 系列端点，完全兼容 OpenAI Sora Video API 规范：
  - `POST /v1/videos` - 创建视频生成任务
  - `GET /v1/videos` - 列出视频任务（支持分页）
  - `GET /v1/videos/{video_id}` - 获取任务状态
  - `DELETE /v1/videos/{video_id}` - 删除视频任务
  - `POST /v1/videos/{video_id}/remix` - 混剪视频
  - `GET /v1/videos/{video_id}/content` - 下载视频内容
- **视频任务服务**：`app/services/video_task.py` 提供异步视频生成任务管理，支持任务状态持久化到 `data/video_tasks.json`。
- **Sora 模型兼容**：新增 `sora-2` 和 `sora-2-pro` 模型别名，映射到 `grok-imagine-0.9`，便于使用标准 OpenAI SDK 调用。
- **视频响应模型**：`app/models/video_schema.py` 定义完整的 OpenAI Video API 请求/响应数据结构。

### Changed
- **后台主页统计**：修复 Chat/Image 总剩余统计偏低（未使用 Token 的 `-1` 不再被忽略；SuperSSO 以相关剩余 `max(normal, heavy)` 计入），并新增全局配置 `assumed_chat_quota_per_token`（默认 80）用于未拉取配额时的估算展示。
- **后台主页统计（分页）**：总剩余统计改为后端全量汇总（新增 `/api/stats/remaining`），不再受 Token 列表分页（默认每页 10 个）影响。
- **主页跳转**：根路径 `/` 默认跳转到 `/manage`（未登录仍会由后台页面自动跳转至 `/login`）。
- **模型映射**：调整 `grok-4.1` / `grok-4.1-thinking` 的内部模型映射，修复部分模型不可用/拦截导致的调用失败。
- **后台反馈链接**：将管理后台右上角「反馈」入口指向 `miuzhaii/grok2api-pro` 的 Issues。
- **后台日志详情媒体渲染**：支持在 `grok-3-fast` 模型的成功调用日志中展示 `media_urls`（图片/视频预览）。
- **代理管理 / 当前绑定**：新增已绑定 SSO 的搜索/清除（模糊匹配，支持回车触发），便于快速定位解绑。

## [1.4.3] - 2026-01-22

### Added
- **调用日志服务**：新增 `app/services/call_log.py` 及后台 `/api/logs*` 接口，默认以批量写入方式持久化 `data/call_logs.json`。
- **多代理池 / SSO 绑定**：`app/core/proxy_pool.py` 支持同时维护静态代理、代理池 API 与 `proxy_urls` 列表，附带 SSO 绑定、失败熔断与 `proxy_state.json` 持久化。
- **代理管理面板**：后台新增 `/api/proxies`、`/api/proxies/assign`、`/api/proxies/test` 等端点，可视化操作代理、执行健康检测。
- **配置示例**：提供 `data/setting.example.toml`，便于在容器化/流水线场景下模板化配置。
- **Token 状态刷新**：新增定时刷新任务，支持连续 0 次数阈值失效与「仅失效/全部」范围配置。

### Changed
- **启动流程**：`main.py` 先初始化存储，再加载配置、代理、调用日志，并在退出阶段倒序关闭，保证文件模式与多进程一致性。
- **依赖**：`requirements.txt` 新增 `aiohttp-socks`、`pytest`、`pytest-asyncio`、`hypothesis`，方便代理检测和单元测试；`pyproject.toml` 中 `version` 升级至 `1.4.3`。
- **配置项**：`app/core/config.py` 支持 `proxy_urls`、`log_max_count`、`retry_status_codes` 等新字段，同时自动规范 `socks5`/`cf_clearance`。
- **Token 存储兼容**：读取旧 `sso` key 时自动迁移到 `ssoNormal`，并兼容管理端 `ssoNormal` 请求，避免新增 Token 时报错。

### Removed
- 默认仓库不再直接提交运行时生成的 `data/setting.toml` 与 `token.json`，改为在首次启动或复制示例文件后再生成，避免误提交。

> 历史版本沿用上游 `chenyme/grok2api`，如需查看 1.4.3 之前的变更，请参考上游仓库对应的 `git log`。

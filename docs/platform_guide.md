# 平台运营手册（闲鱼卡密版）

面向卖家（你自己）的日常操作指南。所有 admin 接口需要请求头 `X-Admin-Token: $ADMIN_TOKEN`。

## 0. 首次部署

```bash
cp .env.example .env   # 填 PLATFORM_JWT_SECRET / ADMIN_TOKEN / 上游模型 key
.venv/bin/python scripts/seed_demo.py          # 可选：建演示套餐和卡密
.venv/bin/python server.py --host 0.0.0.0      # 后端 :14420
cd web && pnpm dev                             # 前端 :3000
```

生产建议：`PLATFORM_DATABASE_URL` 换 Postgres；`PLATFORM_ALLOWED_ORIGINS` 填真实域名；
crontab 加每日备份 `0 4 * * * /path/to/scripts/backup_db.sh`。

## 1. 上架一个新模型（新模型发布当天可完成）

前提：在火山方舟/阿里云百炼开通该模型，拿到 model name。

```bash
curl -X POST localhost:14420/api/admin/models -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{
  "display_name": "Qwen3-Max",
  "model_name": "qwen3-max",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "api_key_env": "DASHSCOPE_API_KEY",
  "provider": "阿里云百炼"
}'
```

⚠️ `display_name` 必须与真实调用的上游模型一致——宣传什么就调用什么，这是红线。

## 2. 建套餐（SKU = 套餐 × 模型 = 一个闲鱼商品链接）

```bash
curl -X POST localhost:14420/api/admin/plans -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "标准卡 20次/30天", "total_uses": 20, "valid_days": 30}'
```

对外只有「次数 + 有效天数」两个维度。`token_reserve` 是隐藏熔断，一般不用设
（单任务熔断 `PLATFORM_TASK_TOKEN_CAP` + 每日预算 `PLATFORM_DAILY_TOKEN_BUDGET` 已兜底）。

## 3. 发货：批量预生成卡密 + 闲鱼自动发货

```bash
curl -X POST localhost:14420/api/admin/codes -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": 2, "model_id": 1, "count": 50, "order_ref": "闲鱼-标准卡-批次1"}'
```

把返回的卡密列表导入闲鱼自动发货工具，实现秒发。买家拿到卡密后打开网址输入即用
（首次输入自动激活，之后凭同一卡密登录，任何设备都行）。

## 4. 售后场景速查

| 场景 | 操作 |
|---|---|
| 买家丢卡密 | `GET /api/admin/codes?order_ref=xxx` 凭订单号/批次查回 |
| 补偿次数/延期 | `PATCH /api/admin/users/{id}` `{"add_uses": 3}` 或 `{"extend_days": 7}` |
| 上游模型下线，迁移用户 | `PATCH /api/admin/users/{id}` `{"model_id": 新id}`（立即生效） |
| 封禁滥用账号 | `PATCH /api/admin/users/{id}` `{"banned": true}` |
| 作废未售出的卡 | `POST /api/admin/codes/{id}/void`（已激活的不能作废） |
| 买家续费 | 卖新卡密即可，买家在页面「续费」入口输入：次数叠加、有效期顺延、模型按新卡生效 |

## 5. 成本核算

```bash
curl localhost:14420/api/admin/stats/daily -H "X-Admin-Token: $ADMIN_TOKEN"
```

返回每日 run 数、token 总量、成功计次数。用 token 总量 × 上游单价对比卡密收入定价。
上新套餐前先自己跑几次典型任务，看单次 token 消耗（runs 表里有每次的明细）。

## 6. 计费规则（前端也是这样承诺买家的，别改破）

- **成功产出报告/文件才扣 1 次**；失败、超时、审核拦截、闲聊对话都不扣
- 单任务 token 超过 `PLATFORM_TASK_TOKEN_CAP` 会中止且不扣次（买家看到「任务过于复杂」提示）
- 每日总 token 达到 `PLATFORM_DAILY_TOKEN_BUDGET` 后全站暂停接新任务（告警 webhook 会通知你）
- 同一账号同时只能跑 1 个任务；同时在线只允许 1 处登录（新登录踢旧，防合买）

## 7. 产物文件与服务器流量

- 产物统一落 `PLATFORM_FILES_DIR`（默认 ./generated_files，按 user_id 分目录），
  用户凭 token 只能下载自己的文件；重复下载不会重复生成（不烧 token）
- 过期清理：`0 5 * * * .venv/bin/python scripts/cleanup_files.py 30`（删 30 天前的文件）
- 小带宽服务器（轻量云 3~5Mbps）建议 nginx 反代加单连接限速，防个别用户反复下载拖垮别人：
  ```nginx
  location /api/runs/ { limit_rate 512k; proxy_pass http://127.0.0.1:14420; }
  ```
- 规模化后（日单两位数+）把文件挪到对象存储：生成后上传 OSS/COS，`file_path` 存
  object key，下载接口改成返回**预签名 URL 302 跳转**——文件流量完全不走服务器，
  OSS 流量约 ¥0.5/GB；配 30 天生命周期规则自动过期，清理脚本都省了

## 8. 技能（skills）

前端聊天页顶部有技能选择器，当前 6 个技能都已上线、走「成功才扣次」计量：

| 技能 | 接口 | 产出 | 依赖 |
|---|---|---|---|
| 深度研究 | POST /api/chat/stream (SSE) | 长报告（网页展示） | 搜索引擎（spark） |
| 做 PPT | POST /api/ppt/generate `{content}` | .pptx（原生图表，3 主题 10 版式） | python-pptx |
| 办公文档 | POST /api/doc/generate `{prompt}` | 周报/纪要/策划/公告/简历 .docx | python-docx |
| 数据表格 | POST /api/sheet/generate `{prompt}` | 课程表/排班/预算/进度 .xlsx | openpyxl |
| 智能组卷 | POST /api/exam/generate `{prompt}` | 试卷 .docx（题+答案+解析） | python-docx |
| 教案生成 | POST /api/lesson/generate `{prompt}` | 教案 .docx | python-docx |

新增技能 = 后端加一个 `src/skills/xxx.py`（LLM 出结构化 JSON → 导出）+ 一个端点 + 前端 `web/src/core/skills.ts` 加一项。

### 附件（图片粘贴 / 文件上传解析）

- `POST /api/attachments`（multipart，`file` 字段）上传，**不扣次**；返回 `{id, name, kind, chars, error}`
- 支持 pdf/docx/xlsx/txt/md/csv（服务端抽取文本）与 png/jpg/webp/gif 图片；单文件 ≤15MB，每次请求 ≤5 个
- 各生成端点带可选 `attachment_ids: [id]`：文档解析文本以「参考资料」注入提示词（单文件截 2 万字、合计 4 万字）；
  图片仅深度研究链路以 multimodal 透传，**模型无视觉能力时任务失败不扣次——对外文案勿承诺识图**
- 附件落 `PLATFORM_FILES_DIR/uploads/{user_id}/`，与产物共用 30 天清理脚本
- 依赖：`pip install openpyxl==3.1.5 pypdf==5.1.0`（已入 requirements-platform.txt；纯 Python，无系统库）
- 前端：输入框 📎 上传 + 直接粘贴截图；启动台另有 12 张办公模板卡（`web/src/core/templates.ts`，纯前端改文案即可上新）

### PPT / 文档图表（2026-07 起为纯 Python 管线）

- **PPT 默认走 mck 引擎**（`src/skills/mck_ppt/`，vendored 自
  [Mck-ppt-design-skill](https://github.com/likaku/Mck-ppt-design-skill)，Apache-2.0，
  保留原版权头与 NOTICE）：麦肯锡咨询风设计系统，行动标题 + 25 个精选版式
  （执行摘要/环图/分组柱状/KPI 进度/SWOT/流程箭头…），LLM 出 storyline JSON，
  `mck_adapter.py` 注入配色并执行防坑规则（标题 ≤40 字、chevron ≤5 步等）。
  设 `PLATFORM_PPT_ENGINE=classic` 回退自研 `pptx_export.py` 多主题管线
  （3 主题 × 10 版式、原生可编辑图表）。两条管线都不依赖 marp / chrome。
- **Word 统一样式基建**（`docx_export._new_doc`）：微软雅黑藏蓝标题、页脚页码域、
  标题分隔线；公告（doc:notice）自动走公文红头（红标题 + 红线 + 首行缩进）。
- **办公文档可嵌数据图表**（`src/skills/charts.py`）：matplotlib(Agg) 出 PNG 嵌入 docx；
  中文标签依赖系统 CJK 字体（服务器已有 `fonts-noto-cjk`），探测不到时自动降级为文字列举。
- 依赖：`python-pptx>=1.0.2`、`matplotlib>=3.9`（已入 requirements-platform.txt）。

**遗留基础设施**：服务器上的 marp + chrome-headless-shell（`/opt/chrome-*`、
`CHROME_PATH` 环境）现仅 `src/ppt/graph/`（已不被平台端点调用）使用，可保留备用，
重建服务器时**无需再装**。历史安装步骤见 git 历史中本节旧版。

## 9. 风险提醒

- 上游若用 coding plan 类订阅：注意其服务条款对共享/转售的限制与 RPM/TPM 上限，
  `PLATFORM_MAX_CONCURRENT_RUNS` 要设得比上游限流低
- 每日备份必须配置；服务器磁盘上的 `deerflow_platform.db` 就是全部家当
- 面向公众提供生成式 AI 服务的备案/内容安全要求请自行评估

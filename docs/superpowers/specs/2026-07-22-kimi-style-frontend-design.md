# 设计：Kimi 风格前端改版 —— 能力扩容 + 办公模板 + 附件上传解析

> 状态：自主模式定稿（/goal 无人值守，未经用户逐条确认，关键取舍见 §9）
> 日期：2026-07-22 ｜ 前置：技能二级细分 v2 已上线（4 技能 × 5 子能力）

## 1. 目标

参考 Kimi 官网（kimi.com）的首页信息架构，改版启动台：

1. **能力扩容**：对标 Kimi Agent 的产出类型（Documents / Slides / Sheets / Report），
   在现有 4 技能之外新增「办公文档」「数据表格」两个一级技能，各带 5 个子能力。
   Kimi 的「K3 集群」（重型多智能体模式）明确不做（用户指定排除）。
2. **办公模板**：新增启动台「模板灵感库」画廊（对应 Kimi 的 Explore inspiration），
   办公场景为主，点卡片即选中技能+子能力+预填提示词。
3. **附件能力**：输入框支持图片粘贴、文件上传；后端解析文件文本并注入生成链路。

**红线（项目既定）**：宣传 = 真实调用。所有新能力必须真实产出文件，模板只封装
后端真做得到的东西；图片理解依赖卡密绑定模型的视觉能力，UI 不作卖点宣传。

## 2. 新能力设计（后端）

### 2.1 办公文档（doc）→ .docx

复用组卷/教案的成熟模式：LLM 出结构化 JSON → python-docx 导出（零新依赖）。
统一 schema `{title, meta, sections: [{heading, content}]}`，一个通用导出器
（`build_speech_docx` 同构，抽公共函数）。子能力 = 预设文本注入（presets.py）：

| id | 名称 | emoji | 预设要点 |
|---|---|---|---|
| `weekly` | 周报总结 | 🗓️ | 本周完成(量化)→数据/亮点→问题风险→下周计划；要点式 |
| `minutes` | 会议纪要 | 🧾 | 会议信息→议题结论→决议事项→行动项(负责人/期限)→待定问题 |
| `plan` | 活动策划 | 🎪 | 背景目标→时间地点对象→流程安排(时间表)→分工→物料预算→风险预案 |
| `notice` | 通知公告 | 📢 | 公文体：标题→称谓→正文(事由/安排/要求)→落款；语气得体 |
| `resume` | 个人简历 | 🧑‍💼 | 基本信息→求职意向→教育→工作/项目经历(STAR、量化)→技能证书 |

- 端点 `POST /api/doc/generate {prompt, sub_skill?, attachment_ids?}`，
  走 `_run_docx_skill` 现成管线；计费同现状：成功产出扣 1 次。
- 新文件 `src/skills/document.py`（仿 lesson.py，单 system prompt + 预设注入）。
- 无默认「通用」子能力：办公文档天然按场景分，`weekly` 为默认首选。

### 2.2 数据表格（sheet）→ .xlsx

LLM 出 `{title, sheets: [{name, headers, rows, note?}]}` → openpyxl 导出
（新依赖，纯 Python，无系统库）。样式：表头加粗底色、细边框、自适应列宽。

| id | 名称 | emoji | 预设要点 |
|---|---|---|---|
| `general` | 通用表格 | 📋 | 默认；按需求整理成规范表格 |
| `timetable` | 课程表 | 🕐 | 行=节次(含时间) 列=周一~周五；小学6节/中学8节默认 |
| `duty` | 值日排班 | 🧹 | 按人员/日期轮转排班；均衡分配；附说明列 |
| `budget` | 预算明细 | 💰 | 项目/单价/数量/小计/备注；合计行；金额两位小数 |
| `tracker` | 计划进度 | 📅 | 任务/负责人/起止/状态/备注；按阶段分组 |

- 端点 `POST /api/sheet/generate {prompt, sub_skill?, attachment_ids?}`；
  新文件 `src/skills/spreadsheet.py` + `xlsx_export.py`；媒体类型
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`。

### 2.3 不做的能力（及原因）

- **集群**：用户明确排除。
- **网页生成 / 代码**：与 C 端买家画像（老师/家长/职场人）不匹配，v3 再议。
- **播客**：后端端点已存在但生产未配 TTS 凭据，上架即违反「宣传=真实调用」，
  待凭据配好后只需 skills.ts 加一项。

## 3. 附件系统（图片粘贴 + 文件上传 + 解析）

### 3.1 上传与解析（后端）

`POST /api/attachments`（multipart，需登录，**不扣次**）：

- 文件类型：`.pdf`(pypdf，新纯 Py 依赖) / `.docx`(python-docx) / `.xlsx`(openpyxl)
  / `.txt .md .csv`(直读)；图片 `.png .jpg .jpeg .webp .gif`（存原件，不解析）。
- 限制：单文件 ≤15MB；解析文本单文件截断 20k 字符。
- 落盘 `PLATFORM_FILES_DIR/uploads/{user_id}/{uuid}{ext}`，解析文本同路径加后缀
  `.parsed.txt`；复用 30 天清理脚本目录范围。
- 返回 `{id, name, kind: "image"|"document", chars, error?}`；`id = {uuid}{ext}`
  （服务端按 `^[a-f0-9-]+\.[a-z0-9]+$` 校验，防路径穿越）。解析失败也返回
  （kind=document, error 说明），前端明示，不阻塞其他附件。
- 权限：读取时拼 `uploads/{当前用户id}/{id}`，按用户目录天然隔离。

### 3.2 注入生成链路

所有生成请求（chat/ppt/exam/lesson/doc/sheet）加可选 `attachment_ids: [str]`（≤5 个）：

- **文档附件**：后端读 `.parsed.txt`，多个拼接（总量再截断 40k 字符），以
  `\n\n【参考资料】以下为用户上传文件内容，生成时充分参考：\n…` 追加到 prompt/最后一条用户消息。
- **图片附件**：仅 research（chat/stream）链路生效——转成 OpenAI 风格 multimodal
  content（base64 data URL）进 messages；模型无视觉能力时上游报错→失败不扣次（现状兜底）。
  文件类技能收到图片附件直接 400 提示「该技能暂不支持图片，请上传文档」。

### 3.3 输入框交互（前端）

- 工具栏加 📎 按钮（文件选择，multiple）；textarea `onPaste` 抓 `clipboardData.files`
  （图片截图直贴）；两者共用同一上传函数。
- 附件 chips 行显示在输入框上方：图片显示缩略图，文件显示图标+名+状态
  （上传中 spinner / ✓ xx 字 / ✗ 解析失败），可删除；发送后清空。
- 研究技能外选择了图片 → chip 标红提示；发送前校验。

## 4. 首页（启动台）Kimi 风格重排

现有结构保留（子能力缩略图置顶 + 技能胶囊 + 说明行 + 输入框），增量改动：

1. 技能胶囊扩为 6 个，顺序：深度研究 · 做PPT · 办公文档 · 数据表格 · 智能组卷 · 教案生成；
   主题色：doc=cyan、sheet=teal（现有 blue/orange/green/purple 不动）。
2. hero（空会话）模式下，输入框下方新增「✨ 模板灵感库」区：
   - 精选 ~12 张模板卡（办公为主：周报、会议纪要、简历、课程表、预算表、
     工作汇报PPT、行业分析、随堂测验等），卡片含 emoji、名称、一句话场景、技能色系；
   - 点击 = setSkill + setSubSkill + 预填模板化提示词（含占位符如「【部门】【本周工作】」）；
   - 桌面 grid 3~4 列、移动端横向滚动；会话开始后隐藏（与现有 hero 逻辑一致）。
   - 数据源：`web/src/core/templates.ts` 纯前端静态定义，运营期改文案零部署风险。
3. 输入框 placeholder/说明行随新技能扩展（skills.ts 数据驱动，组件零改动）。

## 5. 改动清单

| 层 | 文件 | 改动 |
|---|---|---|
| 后端 | `src/skills/document.py`、`spreadsheet.py`、`xlsx_export.py`（新） | 两个新技能生成器 |
| 后端 | `src/skills/docx_export.py` | 抽通用 sections 导出器供 doc 复用 |
| 后端 | `src/skills/presets.py` | 增 doc/sheet 两张预设表 |
| 后端 | `src/skills/attachments.py`（新） | 保存/解析/读取附件 |
| 后端 | `src/server/app.py` | `/api/doc/generate`、`/api/sheet/generate`、`/api/attachments`；各生成端点消费 attachment_ids |
| 后端 | `src/server/chat_request.py` | 请求模型加 `attachment_ids` |
| 后端 | `requirements-platform.txt` | + pypdf、openpyxl（版本锁定，pip 用官方源） |
| 前端 | `web/src/core/skills.ts` | + doc/sheet SkillDef、FILE_SKILL_CONFIG、主题色 |
| 前端 | `web/src/core/templates.ts`（新） | 模板灵感库数据 |
| 前端 | `web/src/core/api/attachments.ts`（新）、`generate.ts`、`chat.ts` | 上传 API；请求带 attachment_ids |
| 前端 | `web/src/core/store/store.ts` | 附件状态、发送时携带并清空 |
| 前端 | `input-box.tsx` | 📎 按钮、粘贴处理、附件 chips |
| 前端 | `messages-block.tsx` + 新 `template-gallery.tsx` | hero 模板画廊 |
| 文档 | `docs/platform_guide.md` | 技能表 + 新依赖说明 |

## 6. 验收标准

1. 6 个技能胶囊可用；办公文档 5 子能力、数据表格 5 子能力各真实产出 .docx/.xlsx；
2. 模板卡点击后技能/子能力/输入框正确联动；
3. 截图 Ctrl+V 粘贴出现图片 chip；上传 pdf/docx/txt 显示解析字数；
   带附件的组卷/文档生成内容明显参考了附件；
4. 旧请求（无新字段）行为不变；成功扣 1 次、失败不扣的计费回归不破坏；
5. `next build` 通过；后端 pytest（`-o addopts=""`）通过。

## 7. 里程碑

- P1 附件系统全链路（后端 attachments + 前端输入框）——用户点名的硬需求；
- P2 doc/sheet 两技能（后端生成器 + 端点 + 前端注册）；
- P3 模板画廊 + 首页整合 + 文档更新。

## 8. 风险

- 图片对非视觉模型报错：由「失败不扣次」兜底，文案不承诺识图；
- openpyxl/pypdf 安装：本机 pip 必须 `-i https://pypi.org/simple`（环境备忘录）；
  生产部署时同样注意；
- 附件文本注入拉高 token：单任务 TASK_TOKEN_CAP 熔断已覆盖，另有 40k 字符截断。

## 9. 自主决策记录（用户回来后可复核）

1. 「其他几个能力」取 Kimi Agent 产出类型中可真实落地的两个（文档/表格），
   网页/代码/播客暂缓（§2.3 有原因）；
2. 「办公模板」= doc/sheet 子能力（生成结构模板）+ 前端模板灵感库（提示词模板）双层；
3. 图片仅进研究链路（multimodal 透传），不做 OCR、不虚标识图能力；
4. 上传不扣次，成功产出才扣次的计费模型不变。

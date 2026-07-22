# Kimi 风格前端改版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增办公文档/数据表格两个真实产出技能、启动台办公模板画廊、输入框图片粘贴与文件上传解析。

**Architecture:** 复用「LLM 出结构化 JSON → 导出器 → `_run_docx_skill` 管线」加两个文件技能；附件独立成 `src/skills/attachments.py`（上传/解析/读取），各生成端点以可选 `attachment_ids` 消费；前端 skills.ts 数据驱动扩容，模板画廊纯静态数据。

**Tech Stack:** FastAPI + python-docx + openpyxl + pypdf（后端）；Next.js 15 + Zustand + Tailwind 4（前端）。

## Global Constraints

- 计费模型不变：成功产出扣 1 次，失败/上传不扣；不新增 SKU 维度。
- 红线：宣传=真实调用；UI 文案不承诺「识图」。
- pip 装包必须 `-i https://pypi.org/simple`（本机 pip.conf 的镜像不可用）。
- langchain 栈版本锁定（0.3.x），不得升级依赖大版本。
- pytest 需 `-o addopts=""`（未装 pytest-cov）。
- 附件限制：单文件 ≤15MB、每请求 ≤5 个、单文件解析截 20k 字符、注入合计截 40k。
- 附件 id = `{uuid}{ext}`，正则 `^[a-f0-9-]+\.[a-z0-9]+$` 校验防路径穿越。
- 老请求（无新字段）行为逐字节不变。

---

### Task 1: 依赖 + 附件模块（后端核心）

**Files:**
- Modify: `requirements-platform.txt`（+ `openpyxl==3.1.5`、`pypdf==5.1.0`）
- Create: `src/skills/attachments.py`
- Test: `tests/platform/test_attachments.py`（目录以现有测试布局为准）

**Interfaces (Produces):**
```python
# src/skills/attachments.py
UPLOADS_SUBDIR = "uploads"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
DOC_EXTS = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".csv"}
MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_PARSED_CHARS = 20_000          # 单文件
MAX_INJECT_CHARS = 40_000          # 注入合计
MAX_ATTACHMENTS = 5

def save_attachment(user_id: int, filename: str, data: bytes) -> dict:
    """存文件并解析。返回 {id, name, kind, chars, error}；kind: image|document"""
def load_parsed_texts(user_id: int, ids: list[str]) -> str:
    """拼接解析文本（含文件名标注），超 MAX_INJECT_CHARS 截断；空 ids → \"\""""
def load_image_data_urls(user_id: int, ids: list[str]) -> list[str]:
    """图片附件 → data URL 列表（base64）"""
def split_ids_by_kind(user_id: int, ids: list[str]) -> tuple[list[str], list[str]]:
    """(doc_ids, image_ids)；非法 id（正则不过/文件不存在）直接 ValueError"""
def build_reference_block(text: str) -> str:
    """'\n\n【参考资料】…' 包装；text 为空返回 \"\""""
```
解析实现：txt/md/csv 按 utf-8(errors=replace) 读；docx 用 `docx.Document` 取段落+表格文字；xlsx 用 openpyxl 逐 sheet 逐行 tab 连接；pdf 用 pypdf 逐页 `extract_text`。解析异常捕获 → `{error: "解析失败：…", chars: 0}`（文件保留，kind=document）。

**Steps:**
- [ ] 装依赖进 venv 并写入 requirements-platform.txt
- [ ] 写失败测试：save→load 回路（txt/csv/docx/xlsx/pdf、图片、超限、坏 id 路径穿越拒绝、截断）
- [ ] 实现 attachments.py 使测试通过（pytest -o addopts="" tests/platform/test_attachments.py）
- [ ] Commit `feat(attachments): 附件保存与解析模块`

### Task 2: 附件端点 + 各生成端点消费 attachment_ids

**Files:**
- Modify: `src/server/chat_request.py`（ChatRequest / SkillPromptRequest / GeneratePPTRequest + `attachment_ids: Optional[List[str]] = None`）
- Modify: `src/server/app.py`

**Interfaces (Produces):**
- `POST /api/attachments`：multipart `file`（单个），`Depends(get_current_user)`；返回 save_attachment dict；>15MB → 413；不支持扩展名 → 400。
- 各生成端点：`attachment_ids` 存在时——文档文本经 `build_reference_block` 追加进 prompt（chat: 追加到最后一条用户消息文本；ppt: 拼进 ppt_input；exam/lesson/doc/sheet: 拼进 prompt）；图片 id：chat 转 multimodal content `[{type:"text"},{type:"image_url","image_url":{"url":dataurl}}]`；文件类端点收到图片 id → 400「该技能暂不支持图片附件」。
- 校验失败（ValueError）→ 400。

**Steps:**
- [ ] chat_request.py 加字段
- [ ] app.py：新增 upload 端点 + 六个入口消费逻辑（抽 `_consume_attachments(user, ids, allow_images)` 帮助函数）
- [ ] pytest 全量回归（-o addopts=""）
- [ ] Commit `feat(attachments): 上传端点与生成链路注入`

### Task 3: 办公文档技能（doc）

**Files:**
- Modify: `src/skills/docx_export.py`（把 speech 的「title/meta/sections」导出抽成 `build_sections_docx(data, default_title)`，speech 复用）
- Create: `src/skills/document.py`
- Modify: `src/skills/__init__.py`（导出 `generate_document`）
- Modify: `src/skills/presets.py`（`"doc"` 表：weekly/minutes/plan/notice/resume，文案见设计稿 §2.1）
- Modify: `src/server/app.py`（`POST /api/doc/generate`，`_run_docx_skill(user, skill_label("doc", sub_id), …, "document.docx")`）
- Test: `tests/` 内新增 doc 导出器测试（喂固定 JSON，断言 docx 段落）

**Interfaces (Produces):**
```python
def generate_document(prompt: str, config: dict, preset_text: str = "") -> dict:
    """返回 {"generated_file_path": path, "title": …}；schema {title, meta, sections:[{heading, content}]}"""
```
DOC_SYSTEM_PROMPT：办公文书写手设定 + JSON schema（同 speech 结构）+「用户指定要求优先于预设」。

**Steps:**
- [ ] 抽 build_sections_docx + 失败测试 → 实现 → 通过
- [ ] document.py + presets + 端点
- [ ] pytest 回归；Commit `feat(doc): 办公文档技能`

### Task 4: 数据表格技能（sheet）

**Files:**
- Create: `src/skills/xlsx_export.py`、`src/skills/spreadsheet.py`
- Modify: `src/skills/__init__.py`、`src/skills/presets.py`（`"sheet"` 表：general/timetable/duty/budget/tracker）、`src/server/app.py`（`POST /api/sheet/generate`；响应媒体类型 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`，文件名 `sheet.xlsx`）
- Test: xlsx 导出器测试（固定 JSON → openpyxl 读回断言表头/行数/合计行样式不炸）

**Interfaces (Produces):**
```python
# xlsx_export.py
def build_xlsx(data: dict) -> str:
    """data: {title, sheets:[{name, headers:[str], rows:[[…]], note?}]} → 临时文件路径。
    表头加粗+底色，细边框，列宽=max(len)*1.2 clamp 8~40，note 写在末行下方。"""
# spreadsheet.py
def generate_spreadsheet(prompt: str, config: dict, preset_text: str = "") -> dict:
    """返回 {"generated_file_path": path, "title": …}"""
```
注意 `_run_docx_skill` 命名虽含 docx，逻辑通用（读文件→落盘→Response）；sheet 端点直接复用但传入自定义 media_type——把 `_run_docx_skill` 加 `media_type=_DOCX_MEDIA` 参数。

**Steps:**
- [ ] xlsx_export 失败测试 → 实现 → 通过
- [ ] spreadsheet.py + presets + 端点（改 `_run_docx_skill` 签名，exam/lesson 调用不变）
- [ ] pytest 回归；Commit `feat(sheet): 数据表格技能`

### Task 5: 前端技能注册（doc/sheet）

**Files:**
- Modify: `web/src/core/skills.ts`：`SkillId` 加 `"doc" | "sheet"`；`FileSkillId` 加同两值；`SkillTheme` 加 `"cyan" | "teal"`；SKILLS 数组插入两个 SkillDef（顺序：research, ppt, doc, sheet, exam, lesson；子能力文案含 placeholder/examples 各 2 条办公场景示例）；FILE_SKILL_CONFIG 加 doc(`doc/generate`, bodyKey "prompt", 默认名 `文档.docx`)、sheet(`sheet/generate`, "prompt", `表格.xlsx`)。
- Modify: `web/src/app/chat/components/input-box.tsx`：THEME_CLASSES 加 cyan/teal 两组静态类。

**Steps:**
- [ ] skills.ts 扩容 + THEME_CLASSES；`pnpm build`（或项目现有构建命令）通过
- [ ] Commit `feat(web): 注册办公文档/数据表格技能`

### Task 6: 前端附件系统（粘贴/上传/chips/请求携带）

**Files:**
- Create: `web/src/core/api/attachments.ts`（`uploadAttachment(file): Promise<AttachmentMeta>`，authFetch multipart）
- Modify: `web/src/core/store/store.ts`：新增 attachments 状态 `{localId, id?, name, kind, chars?, status: uploading|ready|error, previewUrl?}[]` + add/remove/clear actions；`sendMessage` 与 `sendFileSkillMessage` 请求体带 `attachment_ids`（仅 ready 的），发送成功后清空。
- Modify: `web/src/core/api/chat.ts`、`generate.ts`：透传 attachment_ids。
- Modify: `web/src/app/chat/components/input-box.tsx`：📎 按钮（`<input type=file multiple hidden>`）、textarea onPaste 抓 `clipboardData.files`、chips 行（图片缩略图 `URL.createObjectURL`、文件名+状态、X 删除）、非 research 技能含图片附件时发送前 toast 阻止。

**Steps:**
- [ ] attachments api + store 状态
- [ ] input-box UI（chips 行放子能力说明行与输入框之间）
- [ ] 构建通过；Commit `feat(web): 图片粘贴与文件上传`

### Task 7: 模板灵感库

**Files:**
- Create: `web/src/core/templates.ts`：`interface TemplateDef {id, name, emoji, scene, skill: SkillId, subSkill: string, prompt}`；`TEMPLATES: TemplateDef[]` 12 张（周报、会议纪要、简历、通知、活动策划、课程表、值日表、预算表、工作汇报PPT、行业分析、随堂测验、新授课教案）。prompt 用「【占位】」引导填空。
- Create: `web/src/app/chat/components/template-gallery.tsx`：hero 专用；桌面 grid-cols-3/4、移动横滚；卡片按技能主题色；点击 → `setCurrentSkill/setCurrentSubSkill` + 通过现有 value 预填机制填 prompt。
- Modify: `web/src/app/chat/components/messages-block.tsx`：hero 状态下输入框下渲染 gallery。

**Steps:**
- [ ] templates.ts + 组件 + 集成；构建通过
- [ ] Commit `feat(web): 办公模板灵感库`

### Task 8: 文档 + 端到端验证

**Files:**
- Modify: `docs/platform_guide.md`（技能表加 doc/sheet 两行 + 附件端点说明 + 新依赖 openpyxl/pypdf）

**Steps:**
- [ ] 后端全量 pytest（-o addopts=""）；前端 build
- [ ] 起本地服务实测：上传 txt→组卷带参考资料；生成一份周报 docx、一份课程表 xlsx（真实 LLM 调用如无凭据则以单测+mock 为准并如实汇报）
- [ ] Commit `docs: 平台指南更新（新技能与附件）`

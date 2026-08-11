# Compass Skill 3.3.0 优化方案

## 目标

参考易思捷平台可正常加载的 `physics-ai-experiment-assistant`，把 Compass 3.2.0 从“管理面发布成功但运行目录为空”升级为具备明确平台兼容包结构、短路由和可复现运行验收的 3.3.0。

## 参考样本证据

- 用户提供 ZIP SHA-256：`87F82EE43413EC9A7E4D8A7055871026109FF604C40A4367802DC2B238F87CCE`。
- 平台回下载包 SHA-256 与原 ZIP 完全一致。
- 参考 ZIP 只有一个 `physics-ai-experiment-assistant/` 顶层目录。
- 平台运行容器成功读取 `/mnt/skills/custom/physics-ai-experiment-assistant/v1.0.0/SKILL.md`。
- 随后成功列出并读取 `knowledge/` 资源。

## 可迁移机制

1. ZIP 使用与 Skill 名同名的单一顶层目录。
2. 主指令采用 `ROUTE → READ → EXECUTE → RESPOND` 短链路。
3. 路由后只选择直接相关知识文件和脚本。
4. 输入、输出和错误处理使用明确契约。
5. 平台测试保留调用、加载、校验和响应的分段证据。

## 不迁移内容

- 不复制物理实验领域知识和脚本。
- 不硬编码平台绝对路径、scope 或版本目录。
- 不假装单个 Skill 能切换平台模型；只有宿主提供相应工具时才切换。
- 不复制 `display-name` 等非标准 SKILL frontmatter 字段。
- 不引入 numpy、scipy、python-docx 等与 Compass 校验无关的依赖。
- 不把 README 或参赛说明打入运行包。

## 3.3.0 改动

- 强化触发描述中的时间预算、缓冲、超载、连续失败和疲惫降载词。
- 新增平台优先四步路由和六个主能力入口。
- 新增 `knowledge/platform-runtime.md`，记录平台路径、路由和运行状态契约。
- 新增标准库 ZIP 校验器，强制单一同名顶层目录并检查版本、必需文件和路径安全。
- 新增 4 个平台 E2E 用例和 4 个包校验单元测试。
- 正式发布包改为 `compass-student-growth/` 顶层目录结构。

## 验收标准

### 本地

- 全部 pytest 通过。
- `quick_validate.py` 通过。
- ZIP 校验器返回 `valid=true`。
- ZIP 只有一个顶层目录，文件无缺失、无多余、无路径穿越。

### 平台管理面

- 版本为 3.3.0，状态 `active / enabled / ready`。
- 回下载文件与本地源一致，允许平台仅追加 manifest 作者字段。

### 平台运行面

- 显式绑定能读取 3.3.0 `SKILL.md` 和 `knowledge/platform-runtime.md`。
- 预算用例得到 1.5 小时缓冲且总和不超过 10 小时。
- 压力用例自动调用并降到约 4–5.5 小时、通常一个核心任务。
- 简单知识负例不调用 Compass，并严格按两句话回答。
- 最终回复不含内部分析、系统路径或 think 标签。

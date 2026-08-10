# Compass 2.5.1 Environment Baseline

## 2.5.1 自主审计基线与最终状态（2026-08-10）

- 工作目录：`E:\codex_my_project\Compass`；分支：`main`；本轮保留既有未提交修改，不重置、不覆盖、不自动提交。
- 修复前功能基线：`196 passed, 1 skipped, 0 failed`；唯一 skip 是可选 `neo4j_agent_memory` 不在当前环境。skill/dev/full 目录 validator 均为 valid。
- 修复前缺陷并非测试红灯，而是测试未覆盖的语义正确性：专业归属、Assessment 否定/不确定、Evidence 信任等级、领域串线、Secondary Goal、压力实际降载、简单 QA 等通过 A—T 探测暴露。
- 修复后完整回归：`239 passed, 1 skipped, 0 failed`；新增 43 个语义/信任/场景验收测试。
- A—T 可重复场景：`20/20 PASS`；34 专业 Golden Matrix：`34/34 PASS`；完整专业对话模拟：`14/14 PASS`。
- 简单 QA 性能抽样：30 次，median `43.26 ms`，max `76.57 ms`；没有 `growth_cycle`、`goal_plan` 或 `tutor` 深层业务键。
- Python compileall 通过；Compass skill/dev/full 目录 validator 通过；skill-creator `quick_validate.py` 输出 `Skill is valid!`。
- 当前 `.venv` Python：CPython 3.11.4；pytest：9.1.1。Docker、Neo4j 仍非核心依赖，SQLite 为默认 canonical backend。

## 2.2 验证记录（2026-08-07）

- 工程虚拟环境：`.venv/Scripts/python.exe`，pytest 9.1.1。
- 修改前：compile 通过；`81 passed`；2.1 validator 不支持 `--mode skill`（退出码 2）。
- 修改后：compile 通过；源目录 `90 passed`；skill/full validation 均 `valid=true`。
- 五个规定 Demo 全通过；persistent memory Demo 使用两个独立 Python 子进程完成恢复。
- skill/full 包均生成；skill ZIP 解压后 `82 passed, 2 skipped`，跳过原因仅为 skill 包按设计不包含 vendor；解压目录 skill validation=true。
- 既有 `pending-spring-guide` 仍产生人工复核 warning，不影响 valid；未静默删除或伪装为已验证。

## 2.0/2.1 历史基线

审计时间：2026-08-07（Asia/Shanghai）

工作目录：`E:\codex_my_project\Compass\compass-student-growth`

## Repository baseline

- Git 分支：`main`，跟踪 `origin/main`
- 基线提交：`6393518193695ff10eea2f5bafcf0326253bf9dd`
- Compass 基线版本：`1.0.0`
- 原始 `python -m pytest -q`：失败，原因是系统 Python 未安装 pytest，并非测试用例失败
- 建立项目本地 `.venv` 后：`48 passed in 2.37s`
- `python scripts/validate_package.py`：`valid=true`，31 个必需文件、16 个 JSON、1 个快照通过；仅有已知的 `pending-spring-guide` 资源复核警告
- `python scripts/demo_pipeline.py`：成功，16 个步骤完成；使用明确标注的合成招聘快照

## Host environment

| Component | Initial status | Version / location | Requirement |
| --- | --- | --- | --- |
| OS | installed | Microsoft Windows 10.0.26200, x64 | required |
| PowerShell | installed | 5.1.26100.8972 | development |
| Python | installed | 3.11.4, `E:\programme\pycharm\python\python.exe` | required, satisfies Python 3.10+ |
| `python3` alias | missing | `python` is used on Windows | optional alias |
| system pip | installed | 23.1.2 | bootstrap only |
| uv | initially missing; installed locally | 0.12.2 in `.tooling/uv` | preferred development tool |
| Node.js | installed | 24.19.0 | full mode / browser integration |
| npm | installed | 11.17.0 | full mode / browser integration |
| npx | installed | 11.17.0 | full mode / browser integration |
| pnpm | installed | 11.16.0 | optional development tool |
| Git | installed | 2.55.0.windows.3 | required for upstream sync |
| Chrome | installed | 151.0.7922.76 | full mode browser runtime |
| Docker | missing | SQLite fallback remains mandatory | optional full mode |
| Neo4j | missing | SQLite/JSON fallback remains mandatory | optional full mode |
| Java | missing | no core Compass dependency identified | optional |
| Rust / Cargo | missing | not required while agent-browser prebuilt package is used | optional |
| markitdown | initially missing; installed locally | 0.1.7 in `.venv` | review material conversion |

## Project-local Python environment

`.venv` was created by project-local uv using CPython 3.11.4. The initial development dependencies are installed only in that virtual environment:

- pytest 9.1.1
- pytest-cov 7.1.0
- jsonschema 4.26.0
- PyYAML 6.0.3
- markitdown 0.1.7 with document-format extras

The uv cache is redirected to `.tooling/uv-cache` because the host user-level uv cache path cannot be initialized. Both `.venv/` and `.tooling/` are ignored by Git and must not enter either distribution.

## Mode decision

Competition mode is available on the current Python runtime and must remain independent of Node, Chrome, Docker, Neo4j, and network access. Full mode can use Node and Chrome after agent-browser installation. Neo4j-dependent tests must report a real skip or use the SQLite fallback until a reachable Neo4j instance is configured; the project must not claim that Neo4j is running on this host.

## Known environment limitations

- Docker and Neo4j are not installed, so graph-memory integration will be validated through adapter contracts and fallback tests unless an external Neo4j endpoint is provided.
- Java, Rust, and Cargo are absent and will not be installed unless an inspected upstream build actually requires them.
- markitdown reports that ffmpeg is absent; audio/video conversion is therefore optional and is not part of the required PDF/DOCX/PPTX/XLSX/HTML/TXT/Markdown review path.
- The workspace `rg.exe` is blocked by Windows access control. Audits use Git and PowerShell enumeration as a fallback.

# Compass 2.0 Environment Baseline

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

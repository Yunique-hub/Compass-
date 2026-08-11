import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def manifest_value(text, name):
    match = re.search(rf"^{re.escape(name)}:\s*(.+)$", text, re.MULTILINE)
    assert match, f"missing manifest field: {name}"
    return match.group(1).strip()


def test_manifest_contract():
    text = (ROOT / "manifest.yaml").read_text(encoding="utf-8")
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest_value(text, "name"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest_value(text, "version"))
    assert manifest_value(text, "scope") == "private"
    assert manifest_value(text, "version") == "3.4.0"
    assert 1 <= len(manifest_value(text, "description")) <= 1024


def test_required_training_assets_exist():
    required = [
        "SKILL.md",
        "manifest.yaml",
        "scripts/validate_plan.py",
        "scripts/validate_research.py",
        "scripts/validate_response.py",
        "scripts/validate_platform_package.py",
        "scripts/build_release.py",
        "agents/openai.yaml",
        "references/examples.md",
        "tests/integration_cases.json",
        "tests/platform_cases.json",
    ]
    assert not [name for name in required if not (ROOT / name).is_file()]


def test_openai_interface_matches_skill():
    text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert 'display_name: "指南针·大学生成长导师"' in text
    assert "$compass-student-growth" in text
    match = re.search(r'^\s*short_description:\s*"(.+)"$', text, re.MULTILINE)
    assert match
    assert 25 <= len(match.group(1)) <= 64


def test_skill_has_input_output_boundaries_and_examples():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("输入、输出与边界", "不应使用", "异常处理", "references/examples.md"):
        assert phrase in text
    for phrase in ("ROUTE → READ → EXECUTE → VERIFY → RESPOND", "规划硬门禁"):
        assert phrase in text
    assert "# 指南针·大学生成长导师" in text
    assert "成长教练" not in text
    assert "第 4 个及以后目标进入可选区或停止清单，默认 `0 小时`" in text
    assert "4 + 2.5 + 2 + 0 + 1.5 = 10h" in text
    assert "最多 3 个正时长任务和 3 张任务卡" in text
    assert "先给保守初版，不用追问阻塞交付" in text
    assert "不得建议从缓冲中抽取时间" in text
    assert "不得调用澄清工具后停在提问阶段" in text
    assert "任何位置都不得出现具体薪资区间或涨跌幅" in text
    assert "复测题和盲测默认只给题目、作答要求和不含答案的评价维度" in text
    assert "预期产出" in text
    assert "| REVIEW |" in text


def test_integration_cases_are_reproducible():
    data = json.loads((ROOT / "tests" / "integration_cases.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    assert len(cases) >= 3
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert case["prompt"].strip()
        assert len(case["expected"]) >= 2


def test_platform_cases_cover_route_load_validate_and_negative():
    data = json.loads((ROOT / "tests" / "platform_cases.json").read_text(encoding="utf-8"))
    assert data["skill_name"] == "compass-student-growth"
    assert data["version"] == "3.4.0"
    cases = data["cases"]
    assert len(cases) >= 4
    assert any(case["binding"] == "explicit" for case in cases)
    assert any(case["binding"] == "auto" for case in cases)
    assert any("LOADED" in case["expected_stages"] for case in cases)
    assert any("not_invoked" in case["expected"] for case in cases)

from scripts.career.job_target_resolver import JobTargetResolver
from scripts.integrations.agent_browser_adapter import AgentBrowserAdapter
from scripts.recruitment.agent_browser_provider import AgentBrowserProvider
from scripts.recruitment.query_expander import QueryExpander
from scripts.recruitment.recruitment_engine import RecruitmentEngine
from scripts.research.browser_policy import validate_command


def _jds(city: str, title: str, count: int = 5) -> list[dict]:
    return [{"job_id": f"jd-{i}", "title": title, "city": city, "text": f"本科岗位，要求 Python、Linux、SIEM、SOC 分析和网络安全能力，负责安全事件响应与项目交付，沟通协作良好。样本{i}", "synthetic": True} for i in range(count)]


def test_open_vocabulary_targets_and_query_expansion_have_no_whitelist() -> None:
    resolver = JobTargetResolver()
    security = resolver.resolve("我是电子信息专业大二学生，毕业准备去深圳做网络安全工程师。")
    commerce = resolver.resolve("我是市场营销专业，毕业想去成都做跨境电商运营。")
    assert security["research_mode"] == "DYNAMIC_JOB_RESEARCH" and security["target_city"] == "深圳"
    assert commerce["research_mode"] == "DYNAMIC_JOB_RESEARCH" and commerce["target_job_normalized"] == "跨境电商运营"
    assert any("AI产品经理" in item for item in QueryExpander().expand("上海", "AI产品经理"))


def test_recruitment_pipeline_uses_actual_jds_and_never_fabricates_empty_market() -> None:
    engine = RecruitmentEngine()
    market = engine.analyze({"target_city": "深圳", "target_job": "网络安全工程师", "jds": _jds("深圳", "网络安全工程师")})
    assert market["valid_sample_count"] == 5 and market["market_data_status"] == "insufficient"
    assert market["synthetic"] and "仅用于功能测试" in market["usage_notice"]
    assert market["skill_statistics"] and market["skill_statistics"][0]["job_ids"]
    empty = engine.analyze({"target_city": "昆明", "target_job": "新媒体运营"})
    assert empty["market_data_status"] == "insufficient" and empty["skill_statistics"] == []
    assert empty["limitations"]


def test_agent_browser_adapter_contract_is_read_only_and_returns_source_evidence() -> None:
    adapter = AgentBrowserAdapter(reader=lambda command: {"content": "招聘岗位要求 Linux 与网络排障"})
    page = adapter.read_public_page("https://example.com/jobs/1")
    assert page["ok"] and page["source_url"] and page["collected_at"]
    provider = AgentBrowserProvider(adapter)
    records = provider.collect("杭州", "IT支持", ["杭州 IT支持 招聘"], {"public_urls": ["https://example.com/jobs/1"], "synthetic": True})
    assert records[0].source_type == "agent_browser" and records[0].synthetic
    for command in ("fill input", "upload resume", "submit application"):
        try:
            adapter.execute(command)
        except PermissionError:
            pass
        else:
            raise AssertionError(f"read-only mode accepted {command}")

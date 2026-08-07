"""Recruitment intelligence provider architecture."""
from .models import JobRecord
from .recruitment_engine import RecruitmentEngine

__all__ = ["JobRecord", "RecruitmentEngine"]

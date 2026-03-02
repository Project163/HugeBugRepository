from typing import Optional, List
from pydantic import BaseModel


class Bug(BaseModel):
    project_id: str
    bug_id: str
    issue_id: Optional[str] = None
    issue_url: Optional[str] = None
    revision_buggy: Optional[str] = None
    revision_fixed: Optional[str] = None
    buggy_commit_url: Optional[str] = None
    fixed_commit_url: Optional[str] = None
    compare_url: Optional[str] = None
    source_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    discussion: Optional[str] = None
    llm_label: Optional[str] = None
    manual_label: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class BugMetaUpdate(BaseModel):
    manual_label: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionStatus(str, Enum):
    pending = "pending"
    submitted = "submitted"
    closed = "closed"
    expired = "expired"


class ContentType(str, Enum):
    mermaid = "mermaid"
    html = "html"
    markdown = "markdown"
    wireframe = "wireframe"


class SessionOption(BaseModel):
    id: str
    label: str
    description: Optional[str] = None


class UserSelection(BaseModel):
    option_id: str
    label: Optional[str] = None


class CommentTarget(BaseModel):
    selector: str
    tag: Optional[str] = None
    snippet: Optional[str] = None
    path: Optional[str] = None


class UserComment(BaseModel):
    section_id: Optional[str] = None
    text: str
    target: Optional[CommentTarget] = None
    question_index: Optional[int] = None


class UserImage(BaseModel):
    source_type: str
    name: Optional[str] = None
    url: Optional[str] = None
    media_type: Optional[str] = None
    data_base64: Optional[str] = None
    note: Optional[str] = None


class SessionContent(BaseModel):
    prompt: str
    body: str
    content_type: ContentType
    title: Optional[str] = None
    options: list[SessionOption] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    selections: list[UserSelection] = Field(default_factory=list)
    comments: list[UserComment] = Field(default_factory=list)
    images: list[UserImage] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=utc_now)


class BrainstormSession(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    working_dir: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    status: SessionStatus = SessionStatus.pending
    content: SessionContent
    response: Optional[SessionResponse] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionSummary(BaseModel):
    session_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    url: Optional[str] = None
    title: Optional[str] = None


class StartSessionInput(BaseModel):
    prompt: str
    content_type: ContentType
    content: Optional[str] = None
    title: Optional[str] = None
    working_dir: Optional[str] = None
    options: list[Union[str, SessionOption]] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StartSessionOutput(BaseModel):
    session_id: str
    url: str
    port: int
    status: SessionStatus
    preferences: Optional["EffectivePreferences"] = None


class GetSessionResponseOutput(BaseModel):
    status: SessionStatus
    timestamp: Optional[datetime] = None
    response: Optional[SessionResponse] = None


class PreferenceScope(str, Enum):
    global_ = "global"
    project = "project"


class BrainstormPreferences(BaseModel):
    uiux_level: Optional[str] = None
    uiux_style: Optional[str] = None
    questioning_style: Optional[str] = None


class PreferenceSources(BaseModel):
    uiux_level: Optional[PreferenceScope] = None
    uiux_style: Optional[PreferenceScope] = None
    questioning_style: Optional[PreferenceScope] = None


class EffectivePreferences(BaseModel):
    values: BrainstormPreferences
    sources: PreferenceSources
    project_key: Optional[str] = None
    project_path: Optional[str] = None


StartSessionOutput.model_rebuild()

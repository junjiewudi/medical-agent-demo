from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    # strip 后再检查长度，因此纯空格也会返回 422。
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    message: str = Field(min_length=1, max_length=1000, description="健康知识问题，请勿填写个人身份信息")


class Source(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    route: Literal["knowledge", "boundary", "urgent_hint", "unknown"]
    sources: list[Source] = Field(default_factory=list)
    steps: list[str]
    mode: str = "rule_demo"
    notice: str = "学习演示，仅提供一般健康知识；不能诊断、开药或判断是否安全。"

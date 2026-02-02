"""OpenAI Video API 请求-响应模型定义"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class VideoStatus(str, Enum):
    """视频任务状态"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoSize(str, Enum):
    """视频尺寸"""
    PORTRAIT_720 = "720x1280"
    LANDSCAPE_720 = "1280x720"
    PORTRAIT_1024 = "1024x1792"
    LANDSCAPE_1024 = "1792x1024"


class VideoSeconds(str, Enum):
    """视频时长"""
    FOUR = "4"
    EIGHT = "8"
    TWELVE = "12"


class VideoModel(str, Enum):
    """视频模型"""
    SORA_2 = "sora-2"
    SORA_2_PRO = "sora-2-pro"
    GROK_IMAGINE = "grok-imagine-0.9"


# === 请求模型 ===

class CreateVideoRequest(BaseModel):
    """创建视频请求"""
    prompt: str = Field(..., description="描述视频内容的文本提示", min_length=1, max_length=32000)
    model: str = Field(default="sora-2", description="视频生成模型")
    input_reference: Optional[str] = Field(default=None, description="可选的参考图片URL或base64")
    seconds: Optional[str] = Field(default="4", description="视频时长（秒）")
    size: Optional[str] = Field(default="720x1280", description="输出分辨率")
    user: Optional[str] = Field(default=None, description="用户标识")


class RemixVideoRequest(BaseModel):
    """视频混剪请求"""
    prompt: str = Field(..., description="混剪提示词", min_length=1, max_length=32000)


class ListVideosRequest(BaseModel):
    """列出视频请求参数"""
    after: Optional[str] = Field(default=None, description="分页游标")
    limit: Optional[int] = Field(default=20, ge=1, le=100, description="返回数量")
    order: Optional[str] = Field(default="desc", description="排序方式 asc/desc")


# === 响应模型 ===

class VideoError(BaseModel):
    """视频错误信息"""
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")


class VideoJob(BaseModel):
    """视频任务对象"""
    id: str = Field(..., description="视频任务ID")
    object: str = Field(default="video", description="对象类型")
    model: str = Field(..., description="使用的模型")
    status: VideoStatus = Field(..., description="任务状态")
    progress: int = Field(default=0, ge=0, le=100, description="完成进度百分比")
    created_at: int = Field(..., description="创建时间戳（秒）")
    completed_at: Optional[int] = Field(default=None, description="完成时间戳（秒）")
    expires_at: Optional[int] = Field(default=None, description="过期时间戳（秒）")
    prompt: Optional[str] = Field(default=None, description="生成提示词")
    size: Optional[str] = Field(default=None, description="视频尺寸")
    seconds: Optional[str] = Field(default=None, description="视频时长")
    quality: Optional[str] = Field(default="standard", description="视频质量")
    error: Optional[VideoError] = Field(default=None, description="错误信息")
    remixed_from_video_id: Optional[str] = Field(default=None, description="混剪源视频ID")
    
    # 扩展字段（非OpenAI标准）
    video_url: Optional[str] = Field(default=None, description="视频URL（完成后可用）")
    thumbnail_url: Optional[str] = Field(default=None, description="缩略图URL")


class VideoListResponse(BaseModel):
    """视频列表响应"""
    object: str = Field(default="list", description="对象类型")
    data: List[VideoJob] = Field(default_factory=list, description="视频任务列表")
    has_more: bool = Field(default=False, description="是否有更多数据")
    first_id: Optional[str] = Field(default=None, description="首个ID")
    last_id: Optional[str] = Field(default=None, description="最后一个ID")


class VideoDeleteResponse(BaseModel):
    """视频删除响应"""
    id: str = Field(..., description="删除的视频ID")
    object: str = Field(default="video", description="对象类型")
    deleted: bool = Field(default=True, description="是否已删除")


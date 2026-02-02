"""视频API路由 - OpenAI兼容的视频生成接口

实现OpenAI Video API规范:
- POST /v1/videos - 创建视频生成任务
- GET /v1/videos - 列出视频任务
- GET /v1/videos/{video_id} - 获取视频任务状态
- DELETE /v1/videos/{video_id} - 删除视频任务
- POST /v1/videos/{video_id}/remix - 混剪视频
- GET /v1/videos/{video_id}/content - 获取视频内容
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.core.auth import auth_manager
from app.core.logger import logger
from app.models.video_schema import (
    CreateVideoRequest,
    RemixVideoRequest,
    VideoJob,
    VideoListResponse,
    VideoDeleteResponse,
    VideoStatus,
    VideoError
)
from app.services.video_task import video_task_service


router = APIRouter(prefix="/videos", tags=["视频"])


def _build_error_response(status_code: int, message: str, error_type: str = "invalid_request_error") -> Dict[str, Any]:
    """构建错误响应"""
    return {
        "error": {
            "message": message,
            "type": error_type,
            "code": error_type
        }
    }


@router.post("", response_model=VideoJob)
@router.post("/", response_model=VideoJob, include_in_schema=False)
async def create_video(
    raw_request: Request,
    request: CreateVideoRequest,
    _: Optional[str] = Depends(auth_manager.verify)
) -> VideoJob:
    """创建视频生成任务
    
    创建一个新的视频生成任务。任务将在后台异步执行，
    可以通过 GET /v1/videos/{video_id} 查询任务状态。
    
    Args:
        request: 视频生成请求
        
    Returns:
        创建的视频任务对象
    """
    try:
        # 打印完整请求体用于调试
        try:
            body = await raw_request.body()
            logger.info(f"[VideoAPI] 原始请求体: {body.decode('utf-8', errors='replace')}")
        except Exception as e:
            logger.warning(f"[VideoAPI] 读取请求体失败: {e}")
        
        logger.info(f"[VideoAPI] 解析后请求: {request.model_dump()}")
        logger.info(f"[VideoAPI] 创建视频任务: model={request.model}, prompt={request.prompt[:50]}...")
        
        # 创建任务
        task = await video_task_service.create_task(
            prompt=request.prompt,
            model=request.model,
            input_reference=request.input_reference,
            seconds=request.seconds or "4",
            size=request.size or "720x1280",
            user=request.user
        )
        
        # 转换为OpenAI格式响应
        return VideoJob(**task.to_openai_response())
        
    except Exception as e:
        logger.error(f"[VideoAPI] 创建任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=_build_error_response(500, f"创建视频任务失败: {e}", "internal_error")
        )


@router.post("/generations", response_model=VideoJob, include_in_schema=False)
async def create_video_generations(
    request: CreateVideoRequest,
    _: Optional[str] = Depends(auth_manager.verify)
) -> VideoJob:
    """创建视频生成任务（兼容 /generations 路径）"""
    return await create_video(request, _)


@router.get("", response_model=VideoListResponse)
@router.get("/", response_model=VideoListResponse, include_in_schema=False)
async def list_videos(
    after: Optional[str] = Query(default=None, description="分页游标"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
    order: str = Query(default="desc", description="排序方式 asc/desc"),
    _: Optional[str] = Depends(auth_manager.verify)
) -> VideoListResponse:
    """列出视频任务
    
    获取当前项目最近生成的视频任务列表。
    
    Args:
        after: 分页游标，返回该ID之后的任务
        limit: 返回数量，默认20，最大100
        order: 排序方式，asc升序/desc降序
        
    Returns:
        视频任务列表
    """
    try:
        logger.debug(f"[VideoAPI] 列出视频任务: limit={limit}, order={order}")
        
        tasks, has_more, first_id, last_id = await video_task_service.list_tasks(
            limit=limit,
            after=after,
            order=order
        )
        
        return VideoListResponse(
            data=[VideoJob(**t.to_openai_response()) for t in tasks],
            has_more=has_more,
            first_id=first_id,
            last_id=last_id
        )
        
    except Exception as e:
        logger.error(f"[VideoAPI] 列出任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=_build_error_response(500, f"列出视频任务失败: {e}", "internal_error")
        )


@router.get("/{video_id}", response_model=VideoJob)
async def get_video(
    video_id: str,
    _: Optional[str] = Depends(auth_manager.verify)
) -> VideoJob:
    """获取视频任务状态
    
    获取指定视频任务的最新元数据。
    
    Args:
        video_id: 视频任务ID
        
    Returns:
        视频任务对象
    """
    try:
        logger.debug(f"[VideoAPI] 获取视频任务: {video_id}")
        
        task = await video_task_service.get_task(video_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=_build_error_response(404, f"视频任务不存在: {video_id}", "not_found")
            )
        
        return VideoJob(**task.to_openai_response())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VideoAPI] 获取任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=_build_error_response(500, f"获取视频任务失败: {e}", "internal_error")
        )


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
async def delete_video(
    video_id: str,
    _: Optional[str] = Depends(auth_manager.verify)
) -> VideoDeleteResponse:
    """删除视频任务
    
    永久删除一个已完成或失败的视频任务及其存储资源。
    
    Args:
        video_id: 视频任务ID
        
    Returns:
        删除确认响应
    """
    try:
        logger.info(f"[VideoAPI] 删除视频任务: {video_id}")
        
        task = await video_task_service.delete_task(video_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=_build_error_response(404, f"视频任务不存在: {video_id}", "not_found")
            )
        
        return VideoDeleteResponse(id=video_id, deleted=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VideoAPI] 删除任务失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=_build_error_response(500, f"删除视频任务失败: {e}", "internal_error")
        )


@router.post("/{video_id}/remix", response_model=VideoJob)
async def remix_video(
    video_id: str,
    request: RemixVideoRequest,
    _: Optional[str] = Depends(auth_manager.verify)
) -> VideoJob:
    """混剪视频
    
    基于一个已完成的视频创建混剪版本。
    
    Args:
        video_id: 源视频任务ID
        request: 混剪请求（包含新的提示词）
        
    Returns:
        新创建的混剪视频任务对象
    """
    try:
        logger.info(f"[VideoAPI] 混剪视频: {video_id}, prompt={request.prompt[:50]}...")
        
        # 检查源视频是否存在且已完成
        source_task = await video_task_service.get_task(video_id)
        if not source_task:
            raise HTTPException(
                status_code=404,
                detail=_build_error_response(404, f"视频任务不存在: {video_id}", "not_found")
            )
        
        if source_task.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=_build_error_response(400, "只能混剪已完成的视频", "invalid_request_error")
            )
        
        # 创建混剪任务
        task = await video_task_service.remix_task(video_id, request.prompt)
        if not task:
            raise HTTPException(
                status_code=500,
                detail=_build_error_response(500, "创建混剪任务失败", "internal_error")
            )
        
        return VideoJob(**task.to_openai_response())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VideoAPI] 混剪失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=_build_error_response(500, f"混剪视频失败: {e}", "internal_error")
        )


@router.get("/{video_id}/content")
async def get_video_content(
    video_id: str,
    variant: str = Query(default="mp4", description="下载格式"),
    _: Optional[str] = Depends(auth_manager.verify)
):
    """获取视频内容
    
    下载生成的视频文件。
    
    Args:
        video_id: 视频任务ID
        variant: 下载格式，默认mp4
        
    Returns:
        视频文件流
    """
    try:
        logger.debug(f"[VideoAPI] 获取视频内容: {video_id}")
        
        # 获取任务
        task = await video_task_service.get_task(video_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=_build_error_response(404, f"视频任务不存在: {video_id}", "not_found")
            )
        
        if task.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=_build_error_response(400, "视频尚未完成生成", "invalid_request_error")
            )
        
        # 获取视频文件
        video_path = await video_task_service.get_video_content(video_id)
        if not video_path:
            # 如果本地没有缓存，重定向到远程URL
            if task.video_url:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=task.video_url, status_code=302)
            
            raise HTTPException(
                status_code=404,
                detail=_build_error_response(404, "视频内容不可用", "not_found")
            )
        
        # 返回视频文件
        return FileResponse(
            path=str(video_path),
            media_type="video/mp4",
            filename=f"{video_id}.mp4",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VideoAPI] 获取内容失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=_build_error_response(500, f"获取视频内容失败: {e}", "internal_error")
        )


"""视频任务服务 - 管理视频生成任务的创建、查询和状态跟踪"""

import uuid
import time
import asyncio
import orjson
import aiofiles
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from app.core.logger import logger
from app.core.config import setting
from app.services.grok.token import token_manager
from app.services.grok.client import GrokClient
from app.services.grok.cache import video_cache_service
from app.services.call_log import call_log_service


class VideoTaskStatus(str, Enum):
    """视频任务状态"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class VideoTask:
    """视频任务数据模型"""
    id: str = field(default_factory=lambda: f"video_{uuid.uuid4().hex[:12]}")
    model: str = "grok-imagine-0.9"
    status: str = "queued"
    progress: int = 0
    created_at: int = field(default_factory=lambda: int(time.time()))
    completed_at: Optional[int] = None
    expires_at: Optional[int] = None
    prompt: str = ""
    size: str = "720x1280"
    seconds: str = "4"
    quality: str = "standard"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    remixed_from_video_id: Optional[str] = None
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    input_reference: Optional[str] = None
    sso_token: Optional[str] = None
    user: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoTask':
        """从字典创建"""
        valid_fields = {k for k in cls.__dataclass_fields__}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def to_openai_response(self) -> Dict[str, Any]:
        """转换为OpenAI格式响应"""
        response = {
            "id": self.id,
            "object": "video",
            "model": self._map_model_name(),
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at,
            "size": self.size,
            "seconds": self.seconds,
            "quality": self.quality,
        }
        
        if self.prompt:
            response["prompt"] = self.prompt
        if self.completed_at:
            response["completed_at"] = self.completed_at
        if self.expires_at:
            response["expires_at"] = self.expires_at
        if self.error_code or self.error_message:
            response["error"] = {
                "code": self.error_code or "unknown_error",
                "message": self.error_message or "Unknown error occurred"
            }
        if self.remixed_from_video_id:
            response["remixed_from_video_id"] = self.remixed_from_video_id
        if self.video_url:
            response["video_url"] = self.video_url
        if self.thumbnail_url:
            response["thumbnail_url"] = self.thumbnail_url
            
        return response
    
    def _map_model_name(self) -> str:
        """映射模型名称为OpenAI风格"""
        model_map = {
            "grok-imagine-0.9": "sora-2",  # 对外显示为sora-2
        }
        return model_map.get(self.model, self.model)


class VideoTaskService:
    """视频任务服务（单例）"""
    
    _instance: Optional['VideoTaskService'] = None
    
    def __new__(cls) -> 'VideoTaskService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.task_file = Path(__file__).parents[2] / "data" / "video_tasks.json"
        self.task_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, VideoTask] = {}
        self._loaded = False
        self._save_pending = False
        self._save_task: Optional[asyncio.Task] = None
        self._shutdown = False
        self._max_tasks = 1000  # 最大任务数
        self._task_expire_hours = 24  # 任务过期时间（小时）
        
        self._initialized = True
        logger.debug(f"[VideoTask] 初始化完成: {self.task_file}")
    
    async def _load_tasks(self) -> None:
        """加载任务数据"""
        if self._loaded:
            return
        
        try:
            if self.task_file.exists():
                async with aiofiles.open(self.task_file, "r", encoding="utf-8") as f:
                    content = await f.read()
                    data = orjson.loads(content)
                    for task_id, task_data in data.get("tasks", {}).items():
                        self._tasks[task_id] = VideoTask.from_dict(task_data)
                    logger.info(f"[VideoTask] 加载 {len(self._tasks)} 个任务")
            else:
                self._tasks = {}
                logger.debug("[VideoTask] 任务文件不存在，创建空列表")
            self._loaded = True
        except Exception as e:
            logger.error(f"[VideoTask] 加载任务失败: {e}")
            self._tasks = {}
            self._loaded = True
    
    async def _save_tasks(self) -> None:
        """保存任务数据"""
        try:
            async with self._lock:
                data = {
                    "tasks": {task_id: task.to_dict() for task_id, task in self._tasks.items()},
                    "meta": {
                        "total_count": len(self._tasks),
                        "last_save": int(time.time())
                    }
                }
                content = orjson.dumps(data, option=orjson.OPT_INDENT_2).decode()
                async with aiofiles.open(self.task_file, "w", encoding="utf-8") as f:
                    await f.write(content)
                logger.debug(f"[VideoTask] 保存 {len(self._tasks)} 个任务")
        except Exception as e:
            logger.error(f"[VideoTask] 保存任务失败: {e}")
    
    def _mark_dirty(self) -> None:
        """标记有待保存的数据"""
        self._save_pending = True
    
    async def _batch_save_worker(self) -> None:
        """批量保存后台任务"""
        interval = 2.0
        logger.info(f"[VideoTask] 存储任务已启动，间隔: {interval}s")
        
        while not self._shutdown:
            await asyncio.sleep(interval)
            
            if self._save_pending and not self._shutdown:
                try:
                    await self._save_tasks()
                    self._save_pending = False
                except Exception as e:
                    logger.error(f"[VideoTask] 存储失败: {e}")
    
    async def start(self) -> None:
        """启动服务"""
        await self._load_tasks()
        if self._save_task is None:
            self._save_task = asyncio.create_task(self._batch_save_worker())
            logger.info("[VideoTask] 服务已启动")
    
    async def shutdown(self) -> None:
        """关闭服务"""
        self._shutdown = True
        
        if self._save_task:
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        
        if self._save_pending:
            await self._save_tasks()
            logger.info("[VideoTask] 关闭时保存完成")
    
    async def create_task(
        self,
        prompt: str,
        model: str = "grok-imagine-0.9",
        input_reference: Optional[str] = None,
        seconds: str = "4",
        size: str = "720x1280",
        user: Optional[str] = None
    ) -> VideoTask:
        """创建视频生成任务"""
        if not self._loaded:
            await self._load_tasks()
        
        # 映射模型名称
        actual_model = self._map_to_grok_model(model)
        
        # 计算过期时间（24小时后）
        expires_at = int(time.time()) + (self._task_expire_hours * 3600)
        
        task = VideoTask(
            model=actual_model,
            prompt=prompt,
            input_reference=input_reference,
            seconds=seconds,
            size=size,
            expires_at=expires_at,
            user=user
        )
        
        async with self._lock:
            self._tasks[task.id] = task
            
            # 自动清理超限任务
            if len(self._tasks) > self._max_tasks:
                await self._cleanup_old_tasks()
        
        self._mark_dirty()
        logger.info(f"[VideoTask] 创建任务: {task.id}, prompt={prompt[:50]}...")
        
        # 异步启动视频生成
        asyncio.create_task(self._process_task(task.id))
        
        return task
    
    async def _process_task(self, task_id: str) -> None:
        """处理视频生成任务"""
        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"[VideoTask] 任务不存在: {task_id}")
            return
        
        start_time = time.time()
        sso_token = ""
        proxy_used = ""
        
        try:
            # 更新状态为进行中
            task.status = VideoTaskStatus.IN_PROGRESS.value
            task.progress = 10
            self._mark_dirty()
            
            # 构建消息
            messages = [{"role": "user", "content": []}]
            
            # 添加参考图片
            if task.input_reference:
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {"url": task.input_reference}
                })
            
            # 添加文本提示
            messages[0]["content"].append({
                "type": "text",
                "text": task.prompt
            })
            
            # 如果没有图片，简化消息格式
            if not task.input_reference:
                messages = [{"role": "user", "content": task.prompt}]
            
            # 构建请求
            request = {
                "model": task.model,
                "messages": messages,
                "stream": False
            }
            
            # 更新进度
            task.progress = 30
            self._mark_dirty()
            
            # 调用Grok客户端
            logger.info(f"[VideoTask] 开始生成: {task_id}")
            result = await GrokClient.openai_to_grok(request)
            
            task.progress = 80
            self._mark_dirty()
            
            # 解析结果
            if isinstance(result, tuple):
                response, media_urls = result
            else:
                response = result
                media_urls = []
            
            # 提取视频URL
            video_url = None
            content = ""
            
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content or ""
            elif isinstance(response, dict) and 'choices' in response:
                content = response['choices'][0]['message']['content']
            
            # 从content中提取视频URL
            import re
            video_pattern = r'<video[^>]+src="([^"]+)"'
            video_matches = re.findall(video_pattern, content)
            if video_matches:
                video_url = video_matches[0]
            
            # 或从media_urls中获取
            if not video_url and media_urls:
                for url in media_urls:
                    if any(ext in url.lower() for ext in ['.mp4', '.webm', '.mov']):
                        video_url = url
                        break
            
            if video_url:
                task.status = VideoTaskStatus.COMPLETED.value
                task.progress = 100
                task.completed_at = int(time.time())
                task.video_url = video_url
                
                # 提取视频路径用于本地缓存
                if '/images/' in video_url:
                    task.video_path = video_url.split('/images/')[-1]
                
                logger.info(f"[VideoTask] 完成: {task_id}, url={video_url}")
                
                # 记录成功日志
                response_time = time.time() - start_time
                asyncio.create_task(call_log_service.record_call(
                    sso=sso_token,
                    model=task.model,
                    success=True,
                    status_code=200,
                    response_time=response_time,
                    proxy_used=proxy_used,
                    media_urls=[video_url]
                ))
            else:
                task.status = VideoTaskStatus.FAILED.value
                task.error_code = "no_video_generated"
                task.error_message = "视频生成失败，未获取到视频URL"
                logger.error(f"[VideoTask] 失败: {task_id}, 未获取到视频URL")
                
        except Exception as e:
            task.status = VideoTaskStatus.FAILED.value
            task.error_code = "generation_error"
            task.error_message = str(e)
            logger.error(f"[VideoTask] 异常: {task_id}, {e}")
            
            # 记录失败日志
            response_time = time.time() - start_time
            asyncio.create_task(call_log_service.record_call(
                sso=sso_token,
                model=task.model,
                success=False,
                status_code=500,
                response_time=response_time,
                error_message=str(e),
                proxy_used=proxy_used
            ))
        
        finally:
            self._mark_dirty()
    
    async def get_task(self, task_id: str) -> Optional[VideoTask]:
        """获取任务"""
        if not self._loaded:
            await self._load_tasks()
        return self._tasks.get(task_id)
    
    async def list_tasks(
        self,
        limit: int = 20,
        after: Optional[str] = None,
        order: str = "desc",
        user: Optional[str] = None
    ) -> Tuple[List[VideoTask], bool, Optional[str], Optional[str]]:
        """列出任务
        
        Returns:
            (任务列表, 是否有更多, 首个ID, 最后ID)
        """
        if not self._loaded:
            await self._load_tasks()
        
        # 获取所有任务
        tasks = list(self._tasks.values())
        
        # 过滤用户
        if user:
            tasks = [t for t in tasks if t.user == user]
        
        # 按创建时间排序
        reverse = order.lower() == "desc"
        tasks.sort(key=lambda t: t.created_at, reverse=reverse)
        
        # 分页
        if after:
            found = False
            filtered = []
            for t in tasks:
                if found:
                    filtered.append(t)
                elif t.id == after:
                    found = True
            tasks = filtered
        
        # 限制数量
        has_more = len(tasks) > limit
        tasks = tasks[:limit]
        
        first_id = tasks[0].id if tasks else None
        last_id = tasks[-1].id if tasks else None
        
        return tasks, has_more, first_id, last_id
    
    async def delete_task(self, task_id: str) -> Optional[VideoTask]:
        """删除任务"""
        if not self._loaded:
            await self._load_tasks()
        
        task = self._tasks.pop(task_id, None)
        if task:
            self._mark_dirty()
            logger.info(f"[VideoTask] 删除任务: {task_id}")
        
        return task
    
    async def remix_task(
        self,
        source_task_id: str,
        prompt: str
    ) -> Optional[VideoTask]:
        """混剪视频任务"""
        source_task = await self.get_task(source_task_id)
        if not source_task:
            return None
        
        if source_task.status != VideoTaskStatus.COMPLETED.value:
            return None
        
        # 使用源视频作为参考
        new_task = await self.create_task(
            prompt=prompt,
            model=source_task.model,
            input_reference=source_task.video_url,
            seconds=source_task.seconds,
            size=source_task.size,
            user=source_task.user
        )
        
        new_task.remixed_from_video_id = source_task_id
        self._mark_dirty()
        
        return new_task
    
    async def get_video_content(self, task_id: str) -> Optional[Path]:
        """获取视频内容文件路径"""
        task = await self.get_task(task_id)
        if not task or task.status != VideoTaskStatus.COMPLETED.value:
            return None
        
        # 尝试从缓存获取
        if task.video_path:
            original_path = "/" + task.video_path.replace('-', '/')
            cache_path = video_cache_service.get_cached(original_path)
            if cache_path and cache_path.exists():
                return cache_path
        
        return None
    
    async def _cleanup_old_tasks(self) -> None:
        """清理过期任务"""
        now = int(time.time())
        expired_ids = []
        
        for task_id, task in self._tasks.items():
            if task.expires_at and task.expires_at < now:
                expired_ids.append(task_id)
        
        for task_id in expired_ids:
            del self._tasks[task_id]
        
        if expired_ids:
            logger.info(f"[VideoTask] 清理 {len(expired_ids)} 个过期任务")
    
    def _map_to_grok_model(self, model: str) -> str:
        """将OpenAI模型名映射到Grok模型"""
        model_map = {
            "sora-2": "grok-imagine-0.9",
            "sora-2-pro": "grok-imagine-0.9",
            "sora": "grok-imagine-0.9",
        }
        return model_map.get(model.lower(), "grok-imagine-0.9")


# 全局实例
video_task_service = VideoTaskService()


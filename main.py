import asyncio
import json
import os
import re
import time
import uuid
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from collections import deque

import aiohttp
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.message_components import Plain, Reply, At
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.star.star_tools import StarTools
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
from urllib.parse import urlencode


# ==================== 记忆管理类（完全修复版） ====================
class MemoryManager:
    """持久化记忆管理器 - 基于配置文件存储"""
    
    def __init__(self, config: AstrBotConfig, context: Context = None):
        self.config = config
        self.context = context
        self._lock = asyncio.Lock()
        
        # 确保 memories 键存在
        if "memories" not in self.config:
            self.config["memories"] = []
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _save_config(self):
        """
        保存配置到文件 - 兼容不同AstrBot版本
        注意：AstrBotConfig继承自dict，没有set方法，要用[]赋值
        """
        try:
            # 方法1: 直接调用 config.save()（如果存在）
            if hasattr(self.config, 'save') and callable(getattr(self.config, 'save')):
                save_method = getattr(self.config, 'save')
                if save_method is not None:
                    save_method()
                    return True
        except Exception as e:
            logger.debug(f"[MemoryManager] 方法1保存失败: {e}")
        
        try:
            # 方法2: 通过 context 保存（v4+版本）
            if self.context and hasattr(self.context, '_config'):
                cfg = self.context._config
                if hasattr(cfg, 'save') and callable(getattr(cfg, 'save')):
                    getattr(cfg, 'save')()
                    return True
        except Exception as e:
            logger.debug(f"[MemoryManager] 方法2保存失败: {e}")
        
        try:
            # 方法3: 如果是文件配置，直接写入（备用方案）
            config_path = None
            if hasattr(self.config, 'config_path'):
                config_path = self.config.config_path
            elif hasattr(self.config, 'path'):
                config_path = self.config.path
            
            if config_path and os.path.exists(os.path.dirname(config_path)):
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(dict(self.config), f, ensure_ascii=False, indent=2)
                return True
        except Exception as e:
            logger.debug(f"[MemoryManager] 方法3保存失败: {e}")
        
        logger.warning("[MemoryManager] 配置已更新但可能需重启后生效（无法自动保存到文件）")
        return False
    
    async def add_memory(self, user_id: str, content: str, tags: list = None, importance: int = 5) -> str:
        """
        添加新记忆
        Args:
            user_id: 用户QQ号
            content: 记忆内容
            tags: 标签列表
            importance: 重要程度 1-10
        Returns:
            memory_id: 记忆唯一ID
        """
        async with self._lock:
            try:
                # 使用 dict.get() 获取现有记忆列表
                memories = self.config.get("memories", [])
                if not isinstance(memories, list):
                    memories = []
                
                memory_id = str(uuid.uuid4())[:8]
                new_memory = {
                    "id": memory_id,
                    "user_id": str(user_id),
                    "content": content,
                    "tags": tags or [],
                    "importance": max(1, min(10, importance)),  # 限制1-10
                    "created_at": self._get_timestamp(),
                    "updated_at": self._get_timestamp()
                }
                
                memories.append(new_memory)
                
                # 关键修复：使用 dict 的 [] 赋值，而不是 set()
                self.config["memories"] = memories
                
                # 尝试保存配置
                saved = self._save_config()
                if not saved:
                    logger.warning("[MemoryManager] 记忆已添加到内存，但文件保存失败，重启后可能丢失")
                
                logger.info(f"[MemoryManager] 添加记忆成功: {memory_id} 用户: {user_id}")
                return memory_id
                
            except Exception as e:
                logger.error(f"[MemoryManager] 添加记忆失败: {e}")
                raise
    
    async def update_memory(self, memory_id: str, content: str = None, tags: list = None, importance: int = None) -> bool:
        """
        更新现有记忆
        Args:
            memory_id: 记忆ID
            content: 新内容（可选）
            tags: 新标签（可选）
            importance: 新重要度（可选）
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            try:
                memories = self.config.get("memories", [])
                if not isinstance(memories, list):
                    return False
                
                for memory in memories:
                    if memory.get("id") == memory_id:
                        if content is not None:
                            memory["content"] = content
                        if tags is not None:
                            memory["tags"] = tags
                        if importance is not None:
                            memory["importance"] = max(1, min(10, importance))
                        memory["updated_at"] = self._get_timestamp()
                        
                        # 关键修复：使用 [] 赋值
                        self.config["memories"] = memories
                        self._save_config()
                        logger.info(f"[MemoryManager] 更新记忆成功: {memory_id}")
                        return True
                
                return False
                
            except Exception as e:
                logger.error(f"[MemoryManager] 更新记忆失败: {e}")
                return False
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        删除记忆
        Args:
            memory_id: 记忆ID
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            try:
                memories = self.config.get("memories", [])
                if not isinstance(memories, list):
                    return False
                
                original_len = len(memories)
                memories = [m for m in memories if m.get("id") != memory_id]
                
                if len(memories) < original_len:
                    # 关键修复：使用 [] 赋值
                    self.config["memories"] = memories
                    self._save_config()
                    logger.info(f"[MemoryManager] 删除记忆成功: {memory_id}")
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"[MemoryManager] 删除记忆失败: {e}")
                return False
    
    async def get_memories(self, user_id: str = None, keyword: str = None, 
                          limit: int = 10, sort_by: str = "updated_at") -> List[dict]:
        """
        查询记忆
        Args:
            user_id: 筛选特定用户（可选）
            keyword: 关键词搜索（可选，支持模糊匹配content和tags）
            limit: 返回数量限制
            sort_by: 排序字段（created_at/updated_at/importance）
        Returns:
            List[dict]: 记忆列表
        """
        try:
            memories = self.config.get("memories", [])
            if not isinstance(memories, list):
                return []
            
            # 筛选用户
            if user_id:
                memories = [m for m in memories if m.get("user_id") == str(user_id)]
            
            # 关键词搜索
            if keyword:
                keyword_lower = keyword.lower()
                filtered = []
                for m in memories:
                    content_match = keyword_lower in m.get("content", "").lower()
                    tags_match = any(keyword_lower in tag.lower() for tag in m.get("tags", []))
                    if content_match or tags_match:
                        filtered.append(m)
                memories = filtered
            
            # 排序
            reverse = True if sort_by in ["updated_at", "created_at", "importance"] else False
            if sort_by == "importance":
                memories.sort(key=lambda x: x.get("importance", 0), reverse=reverse)
            elif sort_by in ["updated_at", "created_at"]:
                memories.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"[MemoryManager] 查询记忆失败: {e}")
            return []
    
    async def get_memory_by_id(self, memory_id: str) -> Optional[dict]:
        """通过ID获取单条记忆"""
        memories = await self.get_memories(limit=10000)  # 获取所有
        for m in memories:
            if m.get("id") == memory_id:
                return m
        return None
    
    async def get_latest_memories_for_inject(self, user_id: str, count: int = 5) -> List[dict]:
        """
        获取用于提示词注入的最新记忆
        Args:
            user_id: 用户ID
            count: 数量
        Returns:
            List[dict]: 最新的N条记忆
        """
        return await self.get_memories(
            user_id=user_id, 
            limit=count, 
            sort_by="updated_at"
        )


# ==================== 数据模型定义（原有代码保留） ====================
@dataclass
class ScheduledCommandModel:
    """定时指令数据模型"""
    id: str
    command_type: str
    params: str
    execute_time: str
    created_at: str
    executed: int = 0
    recurrence: str = "once"
    session_info: dict = None


class DatabaseManager:
    """数据库管理器（原有代码保留）"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "commands_db.json")
        self.status_path = os.path.join(data_dir, "status.json")
        self._lock = asyncio.Lock()
        self._init_storage()
    
    def _init_storage(self):
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.db_path):
            self._save_json(self.db_path, {"scheduled_commands": [], "version": "1.0"})
        if not os.path.exists(self.status_path):
            self._save_json(self.status_path, {"current_status": "online", "status_name": "在线"})
    
    def _load_json(self, filepath: str, default: Any = None) -> Any:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"[QzoneTools] 读取文件失败: {e}")
        return default
    
    def _save_json(self, filepath: str, data: Any) -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath + ".tmp", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(filepath + ".tmp", filepath)
            return True
        except Exception as e:
            logger.error(f"[QzoneTools] 保存文件失败: {e}")
            return False
    
    async def save_scheduled_command(self, task_id: str, command_type: str, 
                                     params: dict, execute_time: datetime,
                                     recurrence: str = "once",
                                     session_info: dict = None) -> bool:
        async with self._lock:
            try:
                db_data = self._load_json(self.db_path, {"scheduled_commands": []})
                commands = db_data.get("scheduled_commands", [])
                
                record = {
                    "id": task_id,
                    "command_type": command_type,
                    "params": json.dumps(params, ensure_ascii=False),
                    "execute_time": execute_time.isoformat(),
                    "created_at": datetime.now().isoformat(),
                    "executed": 0,
                    "recurrence": recurrence,
                    "session_info": session_info
                }
                
                for i, cmd in enumerate(commands):
                    if isinstance(cmd, dict) and cmd.get('id') == task_id:
                        commands[i] = record
                        break
                else:
                    commands.append(record)
                
                db_data["scheduled_commands"] = commands
                return self._save_json(self.db_path, db_data)
            except Exception as e:
                logger.error(f"[QzoneTools] 保存定时指令失败: {e}")
                return False
    
    async def get_pending_commands(self) -> List[dict]:
        db_data = self._load_json(self.db_path, {"scheduled_commands": []})
        commands = db_data.get("scheduled_commands", [])
        return [cmd for cmd in commands if isinstance(cmd, dict) and cmd.get("executed") == 0]
    
    async def get_all_commands(self, include_executed: bool = False) -> List[dict]:
        db_data = self._load_json(self.db_path, {"scheduled_commands": []})
        commands = db_data.get("scheduled_commands", [])
        if include_executed:
            return commands
        return await self.get_pending_commands()
    
    async def mark_command_executed(self, task_id: str, executed: int = 1):
        async with self._lock:
            db_data = self._load_json(self.db_path, {"scheduled_commands": []})
            commands = db_data.get("scheduled_commands", [])
            for cmd in commands:
                if isinstance(cmd, dict) and cmd.get('id') == task_id:
                    cmd['executed'] = executed
                    cmd['completed_at'] = datetime.now().isoformat()
                    break
            db_data["scheduled_commands"] = commands
            self._save_json(self.db_path, db_data)
    
    async def delete_command(self, task_id: str):
        async with self._lock:
            db_data = self._load_json(self.db_path, {"scheduled_commands": []})
            commands = db_data.get("scheduled_commands", [])
            commands = [cmd for cmd in commands if isinstance(cmd, dict) and cmd.get('id') != task_id]
            db_data["scheduled_commands"] = commands
            self._save_json(self.db_path, db_data)
    
    async def cancel_command(self, task_id: str):
        await self.mark_command_executed(task_id, 2)
    
    async def save_status(self, status_key: str, status_name: str, end_time: Optional[datetime]):
        async with self._lock:
            record = {
                "current_status": status_key,
                "status_name": status_name,
                "end_time": end_time.isoformat() if end_time else "",
                "updated_at": datetime.now().isoformat()
            }
            self._save_json(self.status_path, record)
    
    async def load_status(self) -> Optional[dict]:
        return self._load_json(self.status_path)
    
    async def clear_status(self):
        await self.save_status("online", "在线", None)


class QzoneSession:
    """QQ空间会话管理（原有代码保留）"""
    
    def __init__(self):
        self.uin: str = ""
        self.cookie: str = ""
        self.gtk: str = ""
        self.client = None
        self.initialized = False
    
    def _calc_gtk(self, skey: str) -> str:
        hash_val = 5381
        for char in skey:
            hash_val += (hash_val << 5) + ord(char)
        return str(hash_val & 0x7fffffff)
    
    async def initialize(self, client) -> bool:
        try:
            self.client = client
            login_info = await client.api.call_action('get_login_info')
            self.uin = str(login_info.get('user_id', ''))
            if not self.uin:
                return False
            
            try:
                creds = await client.api.call_action('get_credentials', domain='qzone.qq.com')
                self.cookie = creds.get('cookies', '')
            except Exception:
                try:
                    cookies = await client.api.call_action('get_cookies', domain='qzone.qq.com')
                    self.cookie = cookies.get('cookies', '')
                except:
                    return False
            
            if not self.cookie:
                return False
            
            p_skey_match = re.search(r'p_skey=([^;]+)', self.cookie)
            skey_match = re.search(r'skey=([^;]+)', self.cookie)
            key = p_skey_match.group(1) if p_skey_match else (skey_match.group(1) if skey_match else "")
            if not key:
                return False
            
            self.gtk = self._calc_gtk(key)
            self.initialized = True
            logger.info(f"[QzoneTools] QQ空间会话初始化成功")
            return True
        except Exception as e:
            logger.error(f"[QzoneTools] 初始化失败: {e}")
            return False
    
    async def ensure_initialized(self, client) -> bool:
        if self.initialized:
            return True
        return await self.initialize(client)


class QzoneAPI:
    """QQ空间API封装（原有代码保留）"""
    
    def __init__(self, session: QzoneSession):
        self.session = session
    
    async def publish_post(self, text: str, images: list = None) -> dict:
        images = images or []
        if not self.session.initialized:
            return {"success": False, "msg": "会话未初始化"}
        
        try:
            url = f"https://user.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_publish_v6?g_tk={self.session.gtk}"
            payload = {
                'syn_tweet_verson': '1',
                'con': text,
                'feedversion': '1',
                'ver': '1',
                'ugc_right': '1',
                'to_sign': '0',
                'hostuin': self.session.uin,
                'code_version': '1',
                'format': 'fs',
                'qzreferrer': f'https://user.qzone.qq.com/{self.session.uin}/infocenter',
            }
            encoded_data = urlencode(payload)
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cookie': self.session.cookie,
                'Origin': 'https://user.qzone.qq.com',
                'Referer': f'https://user.qzone.qq.com/{self.session.uin}/infocenter',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            async with aiohttp.ClientSession() as sess:
                async with sess.post(url, data=encoded_data, headers=headers, timeout=30) as resp:
                    response_text = await resp.text()
                    if '"code":0' in response_text or '"code": 0' in response_text:
                        return {"success": True, "msg": "发表成功"}
                    return {"success": False, "msg": f"响应: {response_text[:200]}"}
        except Exception as e:
            return {"success": False, "msg": str(e)}


class ScheduledTask:
    def __init__(self, task_id: str, target_id: str, message: str, send_time: datetime, 
                 chat_type: str, target_name: str = ""):
        self.task_id = task_id
        self.target_id = target_id
        self.message = message
        self.send_time = send_time
        self.chat_type = chat_type
        self.target_name = target_name
        self.cancelled = False
        self.completed = False


class QQStatusManager:
    def __init__(self):
        self.current_status: Optional[str] = "online"
        self.current_status_name: str = "在线"
        self.status_end_time: Optional[datetime] = None
        self.restore_task: Optional[asyncio.Task] = None
        self.pending_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.db_manager: Optional[DatabaseManager] = None
    
    def set_db_manager(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def restore_from_db(self, client):
        if not self.db_manager:
            return
        try:
            record = await self.db_manager.load_status()
            if not record:
                return
            status_key = record.get('current_status', 'online')
            end_time_str = record.get('end_time', '')
            if status_key == 'online' or not end_time_str:
                return
            
            end_time = datetime.fromisoformat(end_time_str)
            now = datetime.now()
            
            if end_time <= now:
                await self._force_set_online(client)
            else:
                status_info = self.get_status_info(status_key)
                if status_info:
                    self.current_status = status_key
                    self.current_status_name = status_info['name']
                    self.status_end_time = end_time
                    remain_minutes = (end_time - now).total_seconds() / 60
                    self.restore_task = asyncio.create_task(
                        self._auto_restore_online(client, int(remain_minutes))
                    )
        except Exception as e:
            logger.error(f"[QzoneTools] 恢复状态失败: {e}")
    
    async def _force_set_online(self, client):
        try:
            params = {"status": 10, "ext_status": 0, "battery_status": 0}
            await client.api.call_action('set_online_status', **params)
            self.current_status = "online"
            self.current_status_name = "在线"
            self.status_end_time = None
            if self.db_manager:
                await self.db_manager.clear_status()
        except Exception as e:
            logger.error(f"[QzoneTools] 强制恢复在线失败: {e}")
    
    def get_status_info(self, status_key: str) -> Optional[dict]:
        BASIC_STATUS = {
            "online": {"name": "在线", "status": 10, "ext": 0},
            "qme": {"name": "Q我吧", "status": 60, "ext": 0},
            "away": {"name": "离开", "status": 30, "ext": 0},
            "busy": {"name": "忙碌", "status": 50, "ext": 0},
            "dnd": {"name": "请勿打扰", "status": 70, "ext": 0},
            "invisible": {"name": "隐身", "status": 40, "ext": 0},
        }
        FUN_STATUS = {
            "listening": {"name": "听歌中", "status": 10, "ext": 1028},
            "sleeping": {"name": "睡觉中", "status": 10, "ext": 1016},
            "studying": {"name": "学习中", "status": 10, "ext": 1018},
        }
        if status_key in BASIC_STATUS:
            return BASIC_STATUS[status_key]
        return FUN_STATUS.get(status_key)
    
    def get_current_status_desc(self) -> str:
        if self.current_status == "online":
            return "当前状态：在线"
        now = datetime.now()
        if self.status_end_time and self.status_end_time > now:
            remain = self.status_end_time - now
            remain_min = remain.seconds // 60 + remain.days * 1440
            return f"当前状态：{self.current_status_name}（还剩约{remain_min}分钟）"
        return f"当前状态：{self.current_status_name}"
    
    def is_status_active(self) -> bool:
        if self.current_status == "online":
            return False
        if self.status_end_time and datetime.now() < self.status_end_time:
            return True
        return False
    
    async def set_status(self, client, status_key: str, duration_minutes: int, delay_minutes: int = 0) -> dict:
        async with self._lock:
            status_info = self.get_status_info(status_key)
            if not status_info:
                return {"success": False, "msg": f"无效的状态码: {status_key}"}
            
            if delay_minutes <= 0:
                return await self._execute_set_status(client, status_key, duration_minutes)
            else:
                async def delayed_task():
                    await asyncio.sleep(delay_minutes * 60)
                    await self._execute_set_status(client, status_key, duration_minutes)
                self.pending_task = asyncio.create_task(delayed_task())
                return {"success": True, "msg": f"已设置定时状态：{delay_minutes}分钟后切换", "is_pending": True}
    
    async def _execute_set_status(self, client, status_key: str, duration_minutes: int) -> dict:
        status_info = self.get_status_info(status_key)
        try:
            params = {"status": status_info["status"], "ext_status": status_info["ext"], "battery_status": 0}
            await client.api.call_action('set_online_status', **params)
            
            if status_key == "online":
                if self.restore_task and not self.restore_task.done():
                    self.restore_task.cancel()
                self.current_status = "online"
                self.current_status_name = "在线"
                self.status_end_time = None
                if self.db_manager:
                    await self.db_manager.clear_status()
                return {"success": True, "msg": "状态已恢复为「在线」", "is_online": True}
            
            self.current_status = status_key
            self.current_status_name = status_info['name']
            self.status_end_time = datetime.now() + timedelta(minutes=duration_minutes)
            
            if self.db_manager:
                await self.db_manager.save_status(status_key, status_info['name'], self.status_end_time)
            
            self.restore_task = asyncio.create_task(self._auto_restore_online(client, duration_minutes))
            
            return {
                "success": True,
                "msg": f"状态已设置为「{status_info['name']}」，持续{duration_minutes}分钟",
                "end_time": self.status_end_time.strftime("%H:%M:%S")
            }
        except Exception as e:
            return {"success": False, "msg": f"设置失败: {str(e)}"}
    
    async def _auto_restore_online(self, client, delay_minutes: int):
        try:
            await asyncio.sleep(delay_minutes * 60)
            if not client:
                return
            params = {"status": 10, "ext_status": 0, "battery_status": 0}
            await client.api.call_action('set_online_status', **params)
            async with self._lock:
                self.current_status = "online"
                self.current_status_name = "在线"
                self.status_end_time = None
                self.restore_task = None
                if self.db_manager:
                    await self.db_manager.clear_status()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[QzoneTools] 自动恢复在线失败: {e}")


class ScheduledCommandExecutor:
    def __init__(self, plugin: 'Main'):
        self.plugin = plugin
        self.db_manager = plugin.db_manager
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._stop_check = False
    
    async def start_periodic_check(self):
        self._stop_check = False
        while not self._stop_check:
            await asyncio.sleep(60)
            if not self._stop_check:
                try:
                    await self._check_and_execute_pending()
                except Exception as e:
                    logger.error(f"[QzoneTools] 定时检查失败: {e}")
    
    def stop_periodic_check(self):
        self._stop_check = True
    
    async def schedule_command(self, task_id: str, execute_time: datetime, command_type: str, params: dict, session_info: dict = None):
        """调度单个定时任务（用于立即执行刚创建的近期任务）"""
        now = datetime.now()
        delay_seconds = (execute_time - now).total_seconds()
        
        if delay_seconds > 0:
            async def delayed_execution():
                await asyncio.sleep(delay_seconds)
                await self._execute_command(task_id, command_type, params, session_info)
            
            task = asyncio.create_task(delayed_execution())
            self.running_tasks[task_id] = task
    
    def cancel_task(self, task_id: str):
        """取消正在等待执行的任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            if not task.done():
                task.cancel()
            del self.running_tasks[task_id]
    
    async def _check_and_execute_pending(self):
        pending = await self.db_manager.get_pending_commands()
        now = datetime.now()
        
        for cmd in pending:
            try:
                execute_time_str = cmd.get('execute_time', '')
                if not execute_time_str:
                    continue
                
                execute_time = datetime.fromisoformat(execute_time_str)
                if (now - execute_time).total_seconds() >= 0:
                    task = asyncio.create_task(
                        self._execute_command(cmd['id'], cmd['command_type'], json.loads(cmd['params']), cmd.get('session_info'))
                    )
                    self.running_tasks[cmd['id']] = task
            except Exception as e:
                logger.error(f"[QzoneTools] 处理指令失败: {e}")
    
    async def _execute_command(self, task_id: str, command_type: str, params: dict, session_info: dict = None):
        try:
            client = self.plugin._client
            if not client:
                return
            
            if command_type == "qzone_post":
                content = params.get("content", "")
                if content and self.plugin.session.initialized:
                    await self.plugin.qzone.publish_post(content)
            
            elif command_type == "status_change":
                status = params.get("status", "online")
                duration = params.get("duration_minutes", 30)
                await self.plugin.status_manager.set_status(client, status, duration, 0)
            
            elif command_type == "send_message":
                target_id = params.get("target_id", "")
                message = params.get("message", "")
                chat_type = params.get("chat_type", "group")
                if target_id and message:
                    if chat_type == "group":
                        await client.api.call_action('send_group_msg', group_id=int(target_id), message=message)
                    else:
                        await client.api.call_action('send_private_msg', user_id=int(target_id), message=message)
            
            elif command_type == "llm_remind":
                prompt = params.get("prompt", "")
                if prompt and session_info:
                    unified_msg_origin = session_info.get('unified_msg_origin')
                    if unified_msg_origin:
                        remind_message = f"[定时提醒 #{task_id}]\n{prompt}"
                        await self.plugin.context.send_message(unified_msg_origin, MessageChain().message(remind_message))
            
            await self.db_manager.mark_command_executed(task_id, 1)
            
        except Exception as e:
            logger.error(f"[QzoneTools] 执行任务失败: {e}")
            await self.db_manager.mark_command_executed(task_id, -1)


class Main(Star):
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config or {}
        self.context = context
        
        # 初始化记忆管理器 - 传入context以帮助保存配置
        self.memory_manager = MemoryManager(self.config, context)
        
        try:
            self.data_dir = StarTools.get_data_dir("astrbot_plugin_qzone_tools")
        except RuntimeError:
            self.data_dir = os.path.join(get_astrbot_data_path(), "plugin_data", "astrbot_plugin_qzone_tools")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.db_manager = DatabaseManager(self.data_dir)
        
        self.session = QzoneSession()
        self.qzone = QzoneAPI(self.session)
        self._client = None
        
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        self._groups_cache: List[dict] = []
        self._friends_cache: List[dict] = []
        self._cache_time = 0
        self._cache_expire = 300
        
        self.status_manager = QQStatusManager()
        self.command_executor: Optional[ScheduledCommandExecutor] = None
        self._restored = False
    
    async def initialize(self):
        self.status_manager.set_db_manager(self.db_manager)
        self.command_executor = ScheduledCommandExecutor(self)
        asyncio.create_task(self.command_executor.start_periodic_check())
        asyncio.create_task(self._delayed_restore())
        logger.info(f"[QzoneTools] 插件已加载，包含持久化记忆功能")
    
    async def _delayed_restore(self):
        await asyncio.sleep(10)
        try:
            if hasattr(self.context, 'platform_manager'):
                pm = self.context.platform_manager
                if hasattr(pm, 'get_insts'):
                    platforms = pm.get_insts()
                    for platform in platforms:
                        if hasattr(platform, 'get_client'):
                            self._client = platform.get_client()
                            break
                        elif hasattr(platform, 'client'):
                            self._client = platform.client
                            break
        except Exception as e:
            logger.warning(f"[QzoneTools] 获取客户端失败: {e}")
        
        if self._client:
            await self._do_restore()
    
    async def _do_restore(self):
        if self._restored:
            return
        try:
            if self._client:
                await self.status_manager.restore_from_db(self._client)
                await self.command_executor._check_and_execute_pending()
                self._restored = True
                logger.info("[QzoneTools] 数据恢复完成")
        except Exception as e:
            logger.error(f"[QzoneTools] 恢复失败: {e}")
    
    async def terminate(self):
        if self.command_executor:
            self.command_executor.stop_periodic_check()
        
        for task_id, task in list(self.running_tasks.items()):
            task.cancel()
        
        for task_id, task in list(self.command_executor.running_tasks.items()):
            task.cancel()
        
        if self.status_manager.restore_task and not self.status_manager.restore_task.done():
            self.status_manager.restore_task.cancel()
        if self.status_manager.pending_task and not self.status_manager.pending_task.done():
            self.status_manager.pending_task.cancel()
        
        if self.status_manager.is_status_active() and self.db_manager:
            await self.db_manager.save_status(
                self.status_manager.current_status,
                self.status_manager.current_status_name,
                self.status_manager.status_end_time
            )
        
        logger.info("[QzoneTools] 插件已卸载")
    
    async def _get_client(self, event: AstrMessageEvent):
        if self._client:
            return self._client
        client = getattr(event, 'bot', None)
        if not client:
            msg_obj = getattr(event, 'message_obj', None)
            if msg_obj:
                client = getattr(msg_obj, 'bot', None)
        if client:
            self._client = client
            self.status_manager.set_db_manager(self.db_manager)
        return self._client
    
    async def _ensure_initialized(self, event: AstrMessageEvent) -> bool:
        if self.session.initialized:
            return True
        client = await self._get_client(event)
        if not client:
            return False
        return await self.session.initialize(client)
    
    async def _update_contacts_cache(self, client):
        now = time.time()
        if now - self._cache_time < self._cache_expire and (self._groups_cache or self._friends_cache):
            return
        try:
            try:
                groups_result = await client.api.call_action('get_group_list')
                self._groups_cache = groups_result if isinstance(groups_result, list) else groups_result.get('data', [])
            except:
                self._groups_cache = []
            try:
                friends_result = await client.api.call_action('get_friend_list')
                self._friends_cache = friends_result if isinstance(friends_result, list) else friends_result.get('data', [])
            except:
                self._friends_cache = []
            self._cache_time = now
        except Exception as e:
            logger.error(f"[QzoneTools] 更新缓存失败: {e}")

    def _validate_target_id(self, target_id: str) -> Tuple[bool, str]:
        target_id = str(target_id).strip()
        if not target_id:
            return False, "目标ID不能为空"
        if not target_id.isdigit():
            return False, f"目标ID必须是纯数字"
        return True, target_id
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        time_str = time_str.strip()
        now = datetime.now()
        
        daily_match = re.match(r'每天的(\d{1,2}):(\d{2})', time_str)
        if daily_match:
            hour, minute = int(daily_match.group(1)), int(daily_match.group(2))
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target
        
        formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m-%d %H:%M", "%H:%M"]
        for fmt in formats:
            try:
                parsed = datetime.strptime(time_str, fmt)
                if fmt == "%H:%M":
                    parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                    if parsed <= now:
                        parsed += timedelta(days=1)
                elif fmt == "%m-%d %H:%M":
                    parsed = parsed.replace(year=now.year)
                    if parsed <= now:
                        parsed = parsed.replace(year=now.year + 1)
                return parsed
            except:
                continue
        return None

    # ==================== 持久化记忆LLM工具 ====================
    
    @filter.llm_tool(name="add_memory")
    async def add_memory(self, event: AstrMessageEvent, content: str, tags: str = "", importance: int = 5) -> str:
        '''
        添加重要记忆到存储中。当用户提到重要信息（如喜好、计划、重要日期、个人情况等）时，使用此工具保存。
        
        Args:
            content (string): 记忆内容，简洁明了地描述事实
            tags (string): 标签，用逗号分隔，如"喜好,计划,工作"，方便后续分类检索
            importance (int): 重要程度1-10，默认为5。关键信息用8-10，一般信息用3-5，琐碎信息用1-2
        '''
        try:
            user_id = event.get_sender_id()
            tags_list = [t.strip() for t in tags.split(",")] if tags else []
            
            memory_id = await self.memory_manager.add_memory(
                user_id=user_id,
                content=content,
                tags=tags_list,
                importance=importance
            )
            
            return f"✅ 记忆已保存\nID: {memory_id}\n内容: {content[:50]}{'...' if len(content) > 50 else ''}"
            
        except Exception as e:
            logger.error(f"[MemoryTool] 添加记忆失败: {e}")
            return f"❌ 保存失败: {str(e)}"

    @filter.llm_tool(name="search_memories")
    async def search_memories(self, event: AstrMessageEvent, keyword: str = "", user_specific: bool = True, limit: int = 10) -> str:
        '''
        搜索记忆。支持关键词搜索，可选是否限定当前用户。
        
        Args:
            keyword (string): 搜索关键词，如"生日"、"喜好"、"计划"等，空字符串则返回最新记忆
            user_specific (bool): 是否仅搜索当前用户的记忆，默认为是。设为false可搜索所有用户记忆（需管理员权限上下文）
            limit (int): 返回数量，默认10条，最大20条
        '''
        try:
            user_id = event.get_sender_id() if user_specific else None
            limit = min(limit, 20)  # 限制最大20条
            
            memories = await self.memory_manager.get_memories(
                user_id=user_id,
                keyword=keyword if keyword else None,
                limit=limit,
                sort_by="updated_at"
            )
            
            if not memories:
                return "📭 未找到相关记忆"
            
            lines = [f"📚 找到 {len(memories)} 条记忆："]
            for i, mem in enumerate(memories, 1):
                tags_str = f"[{', '.join(mem.get('tags', []))}]" if mem.get('tags') else ""
                importance = mem.get('importance', 5)
                date = mem.get('updated_at', '未知时间')[:10]  # 只显示日期部分
                content = mem.get('content', '')
                # 截断过长内容
                display_content = content[:40] + "..." if len(content) > 40 else content
                lines.append(f"{i}. [{mem.get('id')}] {display_content} (重要度:{importance}) {tags_str} - {date}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"[MemoryTool] 搜索记忆失败: {e}")
            return f"❌ 搜索失败: {str(e)}"

    @filter.llm_tool(name="update_memory")
    async def update_memory(self, event: AstrMessageEvent, memory_id: str, content: str = None, tags: str = None, importance: int = None) -> str:
        '''
        更新已有记忆的内容、标签或重要度。需要提供记忆ID（可从search_memories获取）。
        
        Args:
            memory_id (string): 记忆ID（8位字符串）
            content (string): 新内容（可选，不提供则不修改）
            tags (string): 新标签，逗号分隔（可选，不提供则不修改，提供空字符串则清空标签）
            importance (int): 新重要度1-10（可选，不提供则不修改）
        '''
        try:
            # 先检查记忆是否存在
            existing = await self.memory_manager.get_memory_by_id(memory_id)
            if not existing:
                return f"❌ 未找到记忆ID: {memory_id}"
            
            # 处理标签
            tags_list = None
            if tags is not None:
                tags_list = [t.strip() for t in tags.split(",")] if tags else []
            
            success = await self.memory_manager.update_memory(
                memory_id=memory_id,
                content=content,
                tags=tags_list,
                importance=importance
            )
            
            if success:
                return f"✅ 记忆已更新\nID: {memory_id}\n原内容: {existing.get('content', '')[:30]}..."
            else:
                return f"❌ 更新失败"
                
        except Exception as e:
            logger.error(f"[MemoryTool] 更新记忆失败: {e}")
            return f"❌ 更新失败: {str(e)}"

    @filter.llm_tool(name="delete_memory")
    async def delete_memory(self, event: AstrMessageEvent, memory_id: str) -> str:
        '''
        删除指定记忆。谨慎使用，删除后无法恢复。
        
        Args:
            memory_id (string): 要删除的记忆ID
        '''
        try:
            # 先获取记忆信息用于确认
            existing = await self.memory_manager.get_memory_by_id(memory_id)
            if not existing:
                return f"❌ 未找到记忆ID: {memory_id}"
            
            content_preview = existing.get('content', '')[:30] + "..."
            success = await self.memory_manager.delete_memory(memory_id)
            
            if success:
                return f"🗑️ 记忆已删除\nID: {memory_id}\n内容: {content_preview}"
            else:
                return f"❌ 删除失败"
                
        except Exception as e:
            logger.error(f"[MemoryTool] 删除记忆失败: {e}")
            return f"❌ 删除失败: {str(e)}"

    @filter.llm_tool(name="get_memory_detail")
    async def get_memory_detail(self, event: AstrMessageEvent, memory_id: str) -> str:
        '''
        获取单条记忆的完整详情。
        
        Args:
            memory_id (string): 记忆ID
        '''
        try:
            memory = await self.memory_manager.get_memory_by_id(memory_id)
            if not memory:
                return f"❌ 未找到记忆ID: {memory_id}"
            
            lines = [
                f"📋 记忆详情",
                f"ID: {memory.get('id')}",
                f"用户: {memory.get('user_id')}",
                f"内容: {memory.get('content')}",
                f"标签: {', '.join(memory.get('tags', [])) if memory.get('tags') else '无'}",
                f"重要度: {memory.get('importance', 5)}/10",
                f"创建时间: {memory.get('created_at')}",
                f"更新时间: {memory.get('updated_at')}"
            ]
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"[MemoryTool] 获取详情失败: {e}")
            return f"❌ 获取详情失败: {str(e)}"

    # ==================== 提示词注入 ====================
    
    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, request: Any, *args, **kwargs) -> None:
        '''
        在LLM请求前注入当前QQ状态信息和用户记忆。
        '''
        try:
            # 注入QQ状态（原有功能）
            status_desc = self.status_manager.get_current_status_desc()
            inject_parts = [f"[系统状态] {status_desc}"]
            
            # 注入用户记忆（新功能）
            if self.config.get("enabled", True) and event.get_platform_name() in ["aiocqhttp", "qq"]:
                # 检查是否启用了记忆注入
                if self.config.get("memory_inject_enabled", True):
                    user_id = event.get_sender_id()
                    max_memories = self.config.get("max_inject_memories", 5)
                    
                    # 获取该用户最新的N条记忆
                    memories = await self.memory_manager.get_latest_memories_for_inject(
                        user_id=user_id, 
                        count=max_memories
                    )
                    
                    if memories:
                        memory_lines = [f"[用户历史记忆] 该用户({user_id})的重要信息："]
                        for i, mem in enumerate(memories, 1):
                            tags = f"[{', '.join(mem.get('tags', []))}]" if mem.get('tags') else ""
                            content = mem.get('content', '')
                            # 清理内容中的换行，避免破坏prompt结构
                            content_clean = content.replace('\n', ' ').replace('\r', '')
                            memory_lines.append(f"{i}. {content_clean} {tags}")
                        
                        memory_text = "\n".join(memory_lines)
                        inject_parts.append(memory_text)
                        logger.info(f"[MemoryInject] 为用户 {user_id} 注入 {len(memories)} 条记忆")
            
            # 组装注入文本
            if inject_parts:
                inject_text = "\n".join(inject_parts)
                if hasattr(request, 'system_prompt') and request.system_prompt:
                    request.system_prompt += f"\n{inject_text}\n"
                elif hasattr(request, 'system_prompt'):
                    request.system_prompt = inject_text + "\n"
                    
        except Exception as e:
            logger.error(f"[MemoryInject] 注入记忆失败: {e}")

    # ==================== 原有其他方法保持不变 ====================
    
    async def search_contacts(self, event: AstrMessageEvent, keyword: str, search_type: str = "all") -> str:
        '''
        搜索联系人（好友或群聊），支持通过昵称或QQ号/群号模糊匹配。
        
        Args:
            keyword (string): 搜索关键词，可以是人名、群名、QQ号或群号
            search_type (string): 搜索范围，可选值：all(全部), friend(仅好友), group(仅群聊)，默认为all
        '''
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取客户端"
            await self._update_contacts_cache(client)
            
            results = []
            if search_type in ["all", "friend"]:
                for friend in self._friends_cache:
                    if keyword.lower() in str(friend.get('nickname', '')).lower() or \
                       keyword.lower() in str(friend.get('user_id', '')).lower():
                        results.append(f"好友: {friend.get('nickname')}({friend.get('user_id')})")
            
            if search_type in ["all", "group"]:
                for group in self._groups_cache:
                    if keyword.lower() in str(group.get('group_name', '')).lower() or \
                       keyword.lower() in str(group.get('group_id', '')).lower():
                        results.append(f"群聊: {group.get('group_name')}({group.get('group_id')})")
            
            if results:
                return f"搜索结果:\n" + "\n".join(results[:10])
            return "未找到匹配的联系人"
        except Exception as e:
            return f"搜索失败: {str(e)}"

    @filter.llm_tool(name="send_message")
    async def send_message_tool(self, event: AstrMessageEvent, target_id: str, message: str, chat_type: str = "auto") -> str:
        '''
        向指定的好友或群聊发送消息。
        
        Args:
            target_id (string): 目标QQ号或群号
            message (string): 要发送的消息内容
            chat_type (string): 聊天类型，可选值：private(私聊), group(群聊), auto(自动判断)，默认为auto
        '''
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取客户端"
            
            is_valid, result = self._validate_target_id(target_id)
            if not is_valid:
                return f"参数错误: {result}"
            
            if chat_type == "auto":
                await self._update_contacts_cache(client)
                is_group = any(str(g.get('group_id')) == target_id for g in self._groups_cache)
                chat_type = "group" if is_group else "private"
            
            if chat_type == "group":
                await client.api.call_action('send_group_msg', group_id=int(target_id), message=message)
            else:
                await client.api.call_action('send_private_msg', user_id=int(target_id), message=message)
            
            return f"✅ 已发送消息到 {target_id}"
        except Exception as e:
            return f"发送失败: {str(e)}"

    @filter.llm_tool(name="schedule_message")
    async def schedule_message(self, event: AstrMessageEvent, target_id: str, message: str, send_time: str, chat_type: str = "group") -> str:
        '''
        创建定时消息任务，在指定时间向目标发送消息。
        
        Args:
            target_id (string): 目标QQ号或群号
            message (string): 要发送的消息内容
            send_time (string): 发送时间，支持格式：YYYY-MM-DD HH:MM:SS、MM-DD HH:MM、HH:MM、每天的HH:MM
            chat_type (string): 聊天类型，可选值：private(私聊), group(群聊)，默认为group
        '''
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取客户端"
            
            is_valid, result = self._validate_target_id(target_id)
            if not is_valid:
                return f"参数错误: {result}"
            
            parsed_time = self._parse_time(send_time)
            if not parsed_time:
                return f"错误：无法理解时间格式"
            
            now = datetime.now()
            if parsed_time <= now:
                return "错误：指定的时间已经过去"
            
            task_id = str(uuid.uuid4())[:8]
            task = ScheduledTask(task_id=task_id, target_id=target_id, message=message, 
                               send_time=parsed_time, chat_type=chat_type)
            self.scheduled_tasks[task_id] = task
            
            delay_seconds = (parsed_time - now).total_seconds()
            asyncio_task = asyncio.create_task(self._execute_scheduled_task(task_id, delay_seconds))
            self.running_tasks[task_id] = asyncio_task
            
            time_str = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
            return f"✅ 定时任务已创建\n任务ID: {task_id}\n时间: {time_str}"
        except Exception as e:
            return f"创建失败: {str(e)}"
    
    async def _execute_scheduled_task(self, task_id: str, delay_seconds: float):
        try:
            await asyncio.sleep(delay_seconds)
            task = self.scheduled_tasks.get(task_id)
            if not task or task.cancelled:
                return
            
            client = self._client
            if not client:
                return
            
            if task.chat_type == "group":
                await client.api.call_action('send_group_msg', group_id=int(task.target_id), message=task.message)
            else:
                await client.api.call_action('send_private_msg', user_id=int(task.target_id), message=task.message)
            
            task.completed = True
        except Exception as e:
            logger.error(f"[QzoneTools] 定时任务执行失败: {e}")

    @filter.llm_tool(name="cancel_scheduled_message")
    async def cancel_scheduled_message(self, event: AstrMessageEvent, task_id: str) -> str:
        '''
        取消已创建的定时消息任务。
        
        Args:
            task_id (string): 任务ID
        '''
        try:
            if task_id not in self.scheduled_tasks:
                return f"错误：未找到任务"
            
            task = self.scheduled_tasks[task_id]
            task.cancelled = True
            
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            return f"✅ 已取消任务 {task_id}"
        except Exception as e:
            return f"取消失败: {str(e)}"

    @filter.llm_tool(name="list_scheduled_messages")
    async def list_scheduled_messages(self, event: AstrMessageEvent, show_all: bool = False) -> str:
        '''
        列出所有定时消息任务。
        
        Args:
            show_all (bool): 是否显示已执行/已取消的任务，默认为False
        '''
        try:
            tasks = list(self.scheduled_tasks.values()) if show_all else [t for t in self.scheduled_tasks.values() if not t.cancelled and not t.completed]
            
            if not tasks:
                return "当前没有定时任务"
            
            lines = [f"📋 任务列表（{len(tasks)}个）"]
            for task in sorted(tasks, key=lambda x: x.send_time):
                status = "✅" if task.completed else "❌" if task.cancelled else "⏳"
                lines.append(f"{status} [{task.task_id}] {task.send_time.strftime('%m-%d %H:%M')}")
            
            return "\n".join(lines)
        except Exception as e:
            return f"获取失败: {str(e)}"

    @filter.llm_tool(name="publish_qzone")
    async def publish_qzone(self, event: AstrMessageEvent, content: str) -> str:
        '''
        发布QQ空间说说。
        
        Args:
            content (string): 说说内容
        '''
        if not await self._ensure_initialized(event):
            return "错误：无法初始化QQ空间"
        
        result = await self.qzone.publish_post(content)
        return result['msg']

    @filter.llm_tool(name="send_poke")
    async def send_poke(self, event: AstrMessageEvent, target_qq: str, chat_type: str = "auto") -> str:
        '''
        向指定用户发送戳一戳（窗口抖动）。
        
        Args:
            target_qq (string): 目标用户QQ号
            chat_type (string): 聊天类型，可选值：private(私聊), group(群聊), auto(自动判断)，默认为auto
        '''
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取客户端"
            
            is_valid, result = self._validate_target_id(target_qq)
            if not is_valid:
                return f"参数错误: {result}"
            
            if chat_type == "auto":
                chat_type = "private" if event.is_private_chat() else "group"
            
            if chat_type == "private":
                await client.api.call_action('friend_poke', user_id=int(target_qq))
            else:
                group_id = event.get_group_id()
                if group_id:
                    await client.api.call_action('group_poke', group_id=int(group_id), user_id=int(target_qq))
                else:
                    return "错误：需要群号"
            
            return f"✅ 已戳一戳 {target_qq}"
        except Exception as e:
            return f"发送失败: {str(e)}"

    @filter.llm_tool(name="update_qq_status")
    async def update_qq_status(self, event: AstrMessageEvent, status: str, duration_minutes: int, delay_minutes: int = 0) -> str:
        '''
        设置QQ在线状态。
        
        Args:
            status (string): 状态码，可选值：online(在线), qme(Q我吧), away(离开), busy(忙碌), dnd(请勿打扰), invisible(隐身), listening(听歌中), sleeping(睡觉中), studying(学习中)
            duration_minutes (int): 持续时间（分钟），最短1分钟
            delay_minutes (int): 延迟执行时间（分钟），默认为0立即执行
        '''
        client = await self._get_client(event)
        if not client:
            return "错误：无法获取客户端"
        
        if duration_minutes < 1:
            duration_minutes = 1
        
        result = await self.status_manager.set_status(client, status, duration_minutes, delay_minutes)
        return result["msg"]

    @filter.llm_tool(name="get_qq_status")
    async def get_qq_status(self, event: AstrMessageEvent) -> str:
        '''
        获取当前QQ在线状态。
        '''
        return self.status_manager.get_current_status_desc()

    @filter.llm_tool(name="get_fun_status_list")
    async def get_fun_status_list(self, event: AstrMessageEvent) -> str:
        '''
        获取娱乐状态列表，用于查看可用的特殊状态码。
        '''
        return "娱乐状态：listening(听歌中), sleeping(睡觉中), studying(学习中)"

    @filter.llm_tool(name="create_scheduled_command")
    async def create_scheduled_command(self, event: AstrMessageEvent, command_type: str, execute_time: str, params: str, recurrence: str = "once") -> str:
        '''
        创建定时指令任务，支持发空间、改状态、发消息、LLM提醒等功能。
        
        Args:
            command_type (string): 指令类型，可选值：qzone_post(发空间), status_change(改状态), send_message(发消息), llm_remind(LLM提醒)
            execute_time (string): 执行时间，支持格式同schedule_message
            params (string): 指令参数，JSON格式字符串
            recurrence (string): 重复模式，可选值：once(单次), daily(每天)，默认为once
        '''
        try:
            parsed_time = self._parse_time(execute_time)
            if not parsed_time:
                return "错误：无法理解时间格式"
            
            try:
                params_dict = json.loads(params)
            except json.JSONDecodeError:
                return "错误：params必须是有效JSON"
            
            valid_types = ["qzone_post", "status_change", "send_message", "llm_remind"]
            if command_type not in valid_types:
                return f"错误：无效类型，可选: {', '.join(valid_types)}"
            
            session_info = None
            if command_type == "llm_remind":
                session_info = {
                    'unified_msg_origin': event.unified_msg_origin,
                    'platform_name': event.get_platform_name(),
                    'sender_id': event.get_sender_id(),
                    'sender_name': event.get_sender_name()
                }
            
            task_id = str(uuid.uuid4())[:8]
            
            success = await self.db_manager.save_scheduled_command(
                task_id, command_type, params_dict, parsed_time, recurrence, session_info
            )
            
            if success:
                if parsed_time > datetime.now():
                    await self.command_executor.schedule_command(task_id, parsed_time, command_type, params_dict, session_info)
                
                return f"✅ 定时指令已创建\n任务ID: {task_id}\n时间: {parsed_time.strftime('%Y-%m-%d %H:%M:%S')}"
            
            return "❌ 保存失败"
        except Exception as e:
            return f"错误: {str(e)}"

    @filter.llm_tool(name="list_scheduled_commands")
    async def list_scheduled_commands(self, event: AstrMessageEvent, include_executed: bool = False) -> str:
        '''
        列出所有定时指令任务。
        
        Args:
            include_executed (bool): 是否包含已执行的指令，默认为False
        '''
        commands = await self.db_manager.get_all_commands(include_executed)
        if not commands:
            return "当前没有定时指令"
        
        lines = [f"📋 指令列表（{len(commands)}条）"]
        for cmd in commands[:15]:
            try:
                status_map = {0: "⏳", 1: "✅", 2: "❌", -1: "⚠️"}
                status = status_map.get(cmd.get('executed'), "❓")
                time_str = datetime.fromisoformat(cmd['execute_time']).strftime("%m-%d %H:%M")
                lines.append(f"{status} [{cmd['id']}] {cmd['command_type']} {time_str}")
            except:
                lines.append(f"• [{cmd.get('id', '?')}] 解析失败")
        
        return "\n".join(lines)

    @filter.llm_tool(name="cancel_scheduled_command")
    async def cancel_scheduled_command(self, event: AstrMessageEvent, task_id: str) -> str:
        '''
        取消指定的定时指令任务（标记为取消状态，保留记录）。
        
        Args:
            task_id (string): 任务ID
        '''
        try:
            await self.db_manager.cancel_command(task_id)
            self.command_executor.cancel_task(task_id)
            return f"✅ 已取消指令 {task_id}"
        except Exception as e:
            return f"取消失败: {str(e)}"

    @filter.llm_tool(name="delete_scheduled_command")
    async def delete_scheduled_command(self, event: AstrMessageEvent, task_id: str) -> str:
        '''
        彻底删除指定的定时指令任务（不保留记录）。
        
        Args:
            task_id (string): 任务ID
        '''
        try:
            await self.db_manager.delete_command(task_id)
            self.command_executor.cancel_task(task_id)
            return f"✅ 已删除指令 {task_id}"
        except Exception as e:
            return f"删除失败: {str(e)}"

    @filter.llm_tool(name="recall_by_reply")
    async def recall_by_reply(self, event: AiocqhttpMessageEvent) -> str:
        '''
        通过引用消息撤回群聊中的消息（仅支持群聊）。
        使用方法：引用要撤回的消息，然后调用此工具。
        '''
        try:
            if event.is_private_chat():
                return "❌ 此功能仅支持群聊中使用"
            
            chain = event.get_messages()
            if not chain or len(chain) == 0:
                return "❌ 请引用要撤回的消息"
            
            first_seg = chain[0]
            if not isinstance(first_seg, Reply):
                return "❌ 请引用要撤回的消息（不支持关键词搜索撤回）"
            
            msg_id = str(first_seg.id)
            if not msg_id or not msg_id.isdigit():
                return "❌ 引用的消息ID无效"
            
            msg_id_int = int(msg_id)
            group_id = event.get_group_id()
            
            if not group_id:
                return "❌ 无法获取群号"
            
            logger.info(f"[QzoneTools] 尝试撤回引用消息: ID={msg_id_int}, 群={group_id}")
            
            try:
                result = await event.bot.delete_msg(message_id=msg_id_int, group_id=int(group_id))
                logger.info(f"[QzoneTools] 撤回成功: {result}")
                return f"✅ 撤回成功\n• 消息ID: {msg_id}\n• 群号: {group_id}"
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[QzoneTools] 撤回失败: {error_msg}")
                
                if "decode failed" in error_msg or "GROUP_ID_INVALID" in error_msg:
                    try:
                        result = await event.bot.delete_msg(message_id=msg_id_int)
                        return f"✅ 撤回成功（兼容模式）\n• 消息ID: {msg_id}"
                    except Exception as e2:
                        pass
                
                if "decode failed" in error_msg:
                    return (f"❌ 撤回失败：消息ID解析失败\n"
                           f"• 可能原因：\n"
                           f"  1. 消息超过2分钟撤回时限\n"
                           f"  2. 引用的消息ID已过期\n"
                           f"  3. Napcat版本不兼容")
                elif "Timeout" in error_msg:
                    return "❌ 撤回超时，请检查Napcat连接状态"
                elif "permission" in error_msg.lower() or "无权" in error_msg:
                    return "❌ 无权撤回此消息（需要管理员权限或消息发送超过2分钟）"
                elif "message not found" in error_msg.lower():
                    return "❌ 未找到该消息（可能已被删除或撤回）"
                else:
                    return f"❌ 撤回失败: {error_msg[:200]}"
                
        except Exception as e:
            logger.error(f"[QzoneTools] 撤回异常: {e}")
            return f"❌ 系统错误：{str(e)}"

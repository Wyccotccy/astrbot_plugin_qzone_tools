# main.py
import asyncio
import json
import re
import time
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig


class QzoneSession:
    """QQ空间会话管理"""
    
    def __init__(self):
        self.uin: str = ""
        self.cookie: str = ""
        self.gtk: str = ""
        self.client = None
        self.initialized = False
    
    def _calc_gtk(self, skey: str) -> str:
        """QQ空间GTK算法"""
        hash_val = 5381
        for char in skey:
            hash_val += (hash_val << 5) + ord(char)
        return str(hash_val & 0x7fffffff)
    
    async def initialize(self, client) -> bool:
        """从NapCat客户端初始化"""
        try:
            self.client = client
            
            login_info = await client.api.call_action('get_login_info')
            self.uin = str(login_info.get('user_id', ''))
            if not self.uin:
                logger.error("[QzoneSession] 获取QQ号失败")
                return False
            
            # 获取QQ空间Cookie
            try:
                creds = await client.api.call_action('get_credentials', domain='qzone.qq.com')
                self.cookie = creds.get('cookies', '')
            except:
                cookies = await client.api.call_action('get_cookies', domain='qzone.qq.com')
                self.cookie = cookies.get('cookies', '')
            
            if not self.cookie:
                logger.error("[QzoneSession] Cookie为空")
                return False
            
            # 提取p_skey计算GTK
            p_skey_match = re.search(r'p_skey=([^;]+)', self.cookie)
            skey_match = re.search(r'skey=([^;]+)', self.cookie)
            
            key = p_skey_match.group(1) if p_skey_match else (skey_match.group(1) if skey_match else "")
            if not key:
                logger.error("[QzoneSession] 未找到skey/p_skey")
                return False
            
            self.gtk = self._calc_gtk(key)
            self.initialized = True
            
            logger.info(f"[QzoneSession] 初始化成功: QQ={self.uin}")
            return True
            
        except Exception as e:
            logger.error(f"[QzoneSession] 初始化失败: {e}")
            return False


class QzoneAPI:
    """QQ空间API封装"""
    
    def __init__(self, session: QzoneSession):
        self.session = session
    
    async def publish_post(self, text: str, images: list = None) -> dict:
        """发表说说"""
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
            
            from urllib.parse import urlencode
            encoded_data = urlencode(payload)
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Cookie': self.session.cookie,
                'Origin': 'https://user.qzone.qq.com',
                'Referer': f'https://user.qzone.qq.com/{self.session.uin}/infocenter',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            }
            
            async with aiohttp.ClientSession() as sess:
                async with sess.post(url, data=encoded_data, headers=headers, timeout=30) as resp:
                    response_text = await resp.text()
                    
                    # 多重判断成功（处理QQ空间的JSONP格式）
                    if '"code":0' in response_text or '"code": 0' in response_text:
                        if text[:10] in response_text or 'conlist' in response_text:
                            return {"success": True, "msg": "发表成功"}
                    
                    # 尝试提取JSON
                    try:
                        json_match = re.search(r'callback\((\{.*\})\)', response_text, re.DOTALL)
                        if not json_match:
                            json_match = re.search(r'_Callback\((\{.*\})\)', response_text, re.DOTALL)
                        
                        if json_match:
                            json_str = json_match.group(1)
                            if not json_str.endswith('}'):
                                json_str += '}'
                            
                            result = json.loads(json_str)
                            if result.get('code') == 0:
                                return {"success": True, "msg": "发表成功", "data": result}
                    except:
                        pass
                    
                    if resp.status == 200 and len(response_text) > 500:
                        return {"success": True, "msg": "发表成功（HTTP 200）"}
                    
                    return {"success": False, "msg": f"未知响应: {response_text[:200]}"}
                    
        except Exception as e:
            logger.error(f"[QzoneAPI] 发表异常: {e}")
            return {"success": False, "msg": str(e)}


class ScheduledTask:
    """定时任务数据结构"""
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


class QzoneToolsPlugin(Star):
    """QzoneTools - QQ空间与消息工具插件"""
    
    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        
        # 读取配置
        if config is None:
            config = {}
        elif hasattr(config, 'get'):
            pass
        else:
            config = {}
        
        self.config = config
        self.enabled = config.get("enabled", True) if isinstance(config, dict) else getattr(config, 'get', lambda x, y: y)("enabled", True)
        
        # 如果未启用，跳过初始化
        if not self.enabled:
            logger.info("[QzoneTools] 插件已禁用，跳过初始化")
            return
        
        self.session = QzoneSession()
        self.qzone = QzoneAPI(self.session)
        self._client = None
        
        # 定时任务存储
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # 联系人缓存
        self._groups_cache: List[dict] = []
        self._friends_cache: List[dict] = []
        self._cache_time = 0
        self._cache_expire = 300  # 5分钟
    
    async def initialize(self):
        """插件初始化"""
        if not self.enabled:
            return
        logger.info("[QzoneTools] 插件已加载")
    
    async def terminate(self):
        """插件卸载"""
        if not self.enabled:
            return
        
        # 取消所有定时任务
        for task_id, task in self.running_tasks.items():
            task.cancel()
            if task_id in self.scheduled_tasks:
                self.scheduled_tasks[task_id].cancelled = True
        logger.info("[QzoneTools] 插件已卸载")
    
    def _check_enabled(self):
        """检查插件是否启用"""
        if not self.enabled:
            return False
        return True
    
    async def _get_client(self, event: AstrMessageEvent):
        """获取NapCat客户端"""
        if not self._check_enabled():
            return None
            
        if self._client:
            return self._client
        
        client = getattr(event, 'bot', None)
        if not client:
            msg_obj = getattr(event, 'message_obj', None)
            if msg_obj:
                client = getattr(msg_obj, 'bot', None)
        
        if client:
            self._client = client
        return client
    
    async def _ensure_initialized(self, event: AstrMessageEvent) -> bool:
        """确保QQ空间已初始化"""
        if not self._check_enabled():
            return False
            
        if self.session.initialized:
            return True
        client = await self._get_client(event)
        if not client:
            return False
        return await self.session.initialize(client)
    
    async def _update_contacts_cache(self, client):
        """更新联系人缓存"""
        if not self._check_enabled():
            return
            
        now = time.time()
        if now - self._cache_time < self._cache_expire and (self._groups_cache or self._friends_cache):
            return
        
        try:
            # 获取群列表
            try:
                groups_result = await client.api.call_action('get_group_list')
                self._groups_cache = groups_result if isinstance(groups_result, list) else groups_result.get('data', [])
            except Exception as e:
                logger.warning(f"[QzoneTools] 获取群列表失败: {e}")
                self._groups_cache = []
            
            # 获取好友列表
            try:
                friends_result = await client.api.call_action('get_friend_list')
                self._friends_cache = friends_result if isinstance(friends_result, list) else friends_result.get('data', [])
            except Exception as e:
                logger.warning(f"[QzoneTools] 获取好友列表失败: {e}")
                self._friends_cache = []
            
            self._cache_time = now
            logger.info(f"[QzoneTools] 联系人缓存已更新: {len(self._groups_cache)}个群, {len(self._friends_cache)}个好友")
            
        except Exception as e:
            logger.error(f"[QzoneTools] 更新联系人缓存失败: {e}")
    
    @filter.llm_tool(name="search_contacts")
    async def search_contacts(self, event: AstrMessageEvent, keyword: str, search_type: str = "all"):
        """
        搜索联系人（群聊或私聊）。用于查找要发送消息的目标。
        当用户要求"搜索群"、"找好友"、"查看群列表"时调用。
        
        Args:
            keyword(string): 搜索关键词，如群名、群号、好友昵称等
            search_type(string): 搜索类型，"group"(仅群聊)、"private"(仅私聊)、"all"(全部，默认)
        """
        if not self._check_enabled():
            return "错误：插件已禁用"
            
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取NapCat客户端"
            
            await self._update_contacts_cache(client)
            
            keyword = keyword.lower()
            results = []
            
            # 搜索群聊
            if search_type in ["all", "group"]:
                for group in self._groups_cache:
                    group_name = str(group.get('group_name', '')).lower()
                    group_id = str(group.get('group_id', ''))
                    
                    if keyword in group_name or keyword in group_id:
                        results.append({
                            "type": "group",
                            "id": group_id,
                            "name": group.get('group_name', '未知群名'),
                            "member_count": group.get('member_count', '未知')
                        })
            
            # 搜索好友
            if search_type in ["all", "private"]:
                for friend in self._friends_cache:
                    nick = str(friend.get('nickname', '')).lower()
                    remark = str(friend.get('remark', '')).lower()
                    user_id = str(friend.get('user_id', ''))
                    
                    if keyword in nick or keyword in remark or keyword in user_id:
                        display_name = friend.get('remark') or friend.get('nickname', '未知')
                        results.append({
                            "type": "private",
                            "id": user_id,
                            "name": display_name,
                            "nickname": friend.get('nickname', '')
                        })
            
            if not results:
                return f"未找到包含'{keyword}'的联系人。"
            
            # 格式化输出（最多10个）
            output_lines = [f"找到 {len(results)} 个匹配结果（显示前10个）："]
            for i, r in enumerate(results[:10], 1):
                type_str = "群聊" if r['type'] == 'group' else '私聊'
                extra = f" ({r['member_count']}人)" if r['type'] == 'group' and 'member_count' in r else ""
                output_lines.append(f"{i}. [{type_str}] {r['name']}{extra} (ID: {r['id']})")
            
            if len(results) > 10:
                output_lines.append(f"...还有 {len(results)-10} 个结果")
            
            return "\n".join(output_lines)
            
        except Exception as e:
            logger.error(f"[QzoneTools] 搜索联系人失败: {e}")
            return f"搜索失败：{str(e)}"
    
    @filter.llm_tool(name="send_message")
    async def send_message_tool(self, event: AstrMessageEvent, target_id: str, message: str, chat_type: str = "auto"):
        """
        主动发送消息到指定群聊或私聊。搜索到目标后，用于发送消息。
        当用户要求"给XX发消息"、"通知大家"、"私聊某人"时调用。
        
        Args:
            target_id(string): 目标ID（群号或QQ号）
            message(string): 要发送的消息内容
            chat_type(string): 类型，"group"(群聊)、"private"(私聊)、"auto"(自动判断，默认auto)
        """
        if not self._check_enabled():
            return "错误：插件已禁用"
            
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取NapCat客户端"
            
            if chat_type == "auto":
                chat_type = "group"
            
            target_id = str(target_id).strip()
            
            # 发送消息
            if chat_type == "group":
                await client.api.call_action('send_group_msg', group_id=int(target_id), message=message)
                return f"✅ 已成功发送消息到群聊({target_id})"
            else:
                await client.api.call_action('send_private_msg', user_id=int(target_id), message=message)
                return f"✅ 已成功发送私聊消息给({target_id})"
                
        except Exception as e:
            logger.error(f"[QzoneTools] 发送消息失败: {e}")
            return f"❌ 发送失败：{str(e)}"
    
    @filter.llm_tool(name="schedule_message")
    async def schedule_message(self, event: AstrMessageEvent, target_id: str, message: str, 
                               send_time: str, chat_type: str = "group"):
        """
        创建定时消息任务，在指定时间自动发送消息。
        当用户要求"定时发送"、"明天提醒我"、"8点叫醒我"时调用。
        
        Args:
            target_id(string): 目标ID（群号或QQ号）
            message(string): 要发送的消息内容
            send_time(string): 发送时间，格式"2026-03-13 08:00:00"或"明天 08:00"或"30分钟后"
            chat_type(string): 类型，"group"(群聊)或"private"(私聊)，默认group
        """
        if not self._check_enabled():
            return "错误：插件已禁用"
            
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取NapCat客户端"
            
            # 解析时间
            parsed_time = self._parse_time(send_time)
            if not parsed_time:
                return f"错误：无法理解时间格式'{send_time}'，请使用'YYYY-MM-DD HH:MM:SS'或'明天 HH:MM'或'30分钟后'"
            
            now = datetime.now()
            if parsed_time <= now:
                return "错误：指定的时间已经过去，请设置未来的时间"
            
            # 生成任务ID
            task_id = str(uuid.uuid4())[:8]
            
            # 创建任务对象
            task = ScheduledTask(
                task_id=task_id,
                target_id=str(target_id),
                message=message,
                send_time=parsed_time,
                chat_type=chat_type
            )
            
            self.scheduled_tasks[task_id] = task
            
            # 创建异步任务
            delay_seconds = (parsed_time - now).total_seconds()
            asyncio_task = asyncio.create_task(self._execute_scheduled_task(task_id, delay_seconds))
            self.running_tasks[task_id] = asyncio_task
            
            asyncio_task.add_done_callback(lambda t: self._task_done_callback(task_id, t))
            
            time_str = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
            return f"✅ 定时任务已创建\n任务ID: {task_id}\n目标: {target_id}\n时间: {time_str}\n内容: {message[:30]}..."
            
        except Exception as e:
            logger.error(f"[QzoneTools] 创建定时任务失败: {e}")
            return f"❌ 创建失败：{str(e)}"
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        time_str = time_str.strip()
        now = datetime.now()
        
        # 标准格式
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%m-%d %H:%M:%S",
            "%m-%d %H:%M",
            "%H:%M:%S",
            "%H:%M",
        ]
        
        for fmt in formats:
            try:
                parsed = datetime.strptime(time_str, fmt)
                if fmt in ["%H:%M:%S", "%H:%M"]:
                    parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                    if parsed <= now:
                        parsed += timedelta(days=1)
                elif fmt in ["%m-%d %H:%M:%S", "%m-%d %H:%M"]:
                    parsed = parsed.replace(year=now.year)
                    if parsed <= now:
                        parsed = parsed.replace(year=now.year + 1)
                return parsed
            except ValueError:
                continue
        
        # 处理相对时间（中文）
        time_str_lower = time_str.lower()
        
        # 明天
        if '明天' in time_str_lower or '明日' in time_str_lower:
            tomorrow = now + timedelta(days=1)
            time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                return tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
        
        # 后天
        if '后天' in time_str_lower:
            day_after = now + timedelta(days=2)
            time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if time_match:
                hour, minute = int(time_match.group(1)), int(time_match.group(2))
                return day_after.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                return day_after.replace(hour=8, minute=0, second=0, microsecond=0)
        
        # X分钟后
        minute_match = re.search(r'(\d+)\s*分钟后?', time_str_lower)
        if minute_match:
            minutes = int(minute_match.group(1))
            return now + timedelta(minutes=minutes)
        
        # X小时后
        hour_match = re.search(r'(\d+)\s*小时后?', time_str_lower)
        if hour_match:
            hours = int(hour_match.group(1))
            return now + timedelta(hours=hours)
        
        return None
    
    async def _execute_scheduled_task(self, task_id: str, delay_seconds: float):
        """执行定时任务"""
        try:
            await asyncio.sleep(delay_seconds)
            
            task = self.scheduled_tasks.get(task_id)
            if not task or task.cancelled:
                logger.info(f"[QzoneTools] 定时任务 {task_id} 已被取消")
                return
            
            client = self._client
            if not client:
                logger.error(f"[QzoneTools] 定时任务 {task_id} 失败：客户端不可用")
                task.completed = True
                return
            
            # 发送消息
            if task.chat_type == "group":
                await client.api.call_action('send_group_msg', 
                    group_id=int(task.target_id), 
                    message=task.message
                )
            else:
                await client.api.call_action('send_private_msg', 
                    user_id=int(task.target_id), 
                    message=task.message
                )
            
            task.completed = True
            logger.info(f"[QzoneTools] 定时任务 {task_id} 执行成功")
            
        except Exception as e:
            logger.error(f"[QzoneTools] 定时任务 {task_id} 执行失败: {e}")
            if task_id in self.scheduled_tasks:
                self.scheduled_tasks[task_id].completed = True
    
    def _task_done_callback(self, task_id: str, task):
        """任务完成后的清理"""
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
    
    @filter.llm_tool(name="cancel_scheduled_message")
    async def cancel_scheduled_message(self, event: AstrMessageEvent, task_id: str):
        """
        取消已创建的定时消息任务。
        当用户要求"取消定时"、"删除提醒"时调用。
        
        Args:
            task_id(string): 定时任务的ID（创建时返回的8位字符）
        """
        if not self._check_enabled():
            return "错误：插件已禁用"
            
        try:
            task_id = task_id.strip()
            
            if task_id not in self.scheduled_tasks:
                matching = [tid for tid in self.scheduled_tasks.keys() if tid.startswith(task_id)]
                if len(matching) == 1:
                    task_id = matching[0]
                elif len(matching) > 1:
                    return f"找到多个匹配的任务ID，请输入完整的任务ID。匹配项: {', '.join(matching)}"
                else:
                    return f"错误：未找到任务ID '{task_id}'"
            
            task = self.scheduled_tasks[task_id]
            task.cancelled = True
            
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            return f"✅ 已取消定时任务 {task_id}\n原定发送时间: {task.send_time.strftime('%Y-%m-%d %H:%M:%S')}\n内容: {task.message[:30]}..."
            
        except Exception as e:
            logger.error(f"[QzoneTools] 取消任务失败: {e}")
            return f"❌ 取消失败：{str(e)}"
    
    @filter.llm_tool(name="list_scheduled_messages")
    async def list_scheduled_messages(self, event: AstrMessageEvent, show_all: bool = False):
        """
        列出所有定时消息任务。
        当用户要求"查看定时任务"、"我的提醒"时调用。
        
        Args:
            show_all(boolean): 是否显示已完成的，默认False只显示待执行的
        """
        if not self._check_enabled():
            return "错误：插件已禁用"
            
        try:
            now = datetime.now()
            active_tasks = []
            completed_tasks = []
            
            for task_id, task in self.scheduled_tasks.items():
                if task.cancelled:
                    continue
                if task.completed:
                    completed_tasks.append(task)
                else:
                    active_tasks.append(task)
            
            if not active_tasks and not (show_all and completed_tasks):
                return "当前没有待执行的定时任务。"
            
            lines = [f"📋 定时任务列表（共{len(active_tasks)}个待执行）"]
            
            for task in sorted(active_tasks, key=lambda x: x.send_time):
                time_str = task.send_time.strftime("%m-%d %H:%M")
                type_str = "群" if task.chat_type == 'group' else '私'
                remain = task.send_time - now
                remain_str = f"{remain.days}天{remain.seconds//3600}小时" if remain.days > 0 else f"{remain.seconds//3600}小时{(remain.seconds%3600)//60}分"
                
                lines.append(f"• [{task.task_id}] [{type_str}] {time_str} (还有{remain_str})\n  内容: {task.message[:20]}...")
            
            if show_all and completed_tasks:
                lines.append(f"\n✓ 已完成（最近5个）：")
                for task in sorted(completed_tasks, key=lambda x: x.send_time, reverse=True)[:5]:
                    time_str = task.send_time.strftime("%m-%d %H:%M")
                    type_str = "群" if task.chat_type == 'group' else '私'
                    lines.append(f"• [{type_str}] {time_str} - {task.message[:20]}...")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"[QzoneTools] 列出任务失败: {e}")
            return f"获取列表失败：{str(e)}"
    
    @filter.llm_tool(name="publish_qzone")
    async def publish_qzone(self, event: AstrMessageEvent, content: str):
        """
        发表QQ空间说说。当用户要求"发空间说说"、"发动态"时调用。
        
        Args:
            content(string): 说说文字内容
        """
        if not self._check_enabled():
            return "错误：插件已禁用"
            
        if not await self._ensure_initialized(event):
            return "错误：无法初始化QQ空间，请检查NapCat是否已登录"
        
        if not content or not content.strip():
            return "错误：内容不能为空"
        
        result = await self.qzone.publish_post(content)
        
        if result["success"]:
            return f"✅ 已成功发表QQ空间说说：{content[:30]}..."
        else:
            return f"❌ 发表失败：{result['msg']}"
    
    @filter.llm_tool(name="send_poke")
    async def send_poke(self, event: AstrMessageEvent, target_qq: str, chat_type: str = "auto"):
        """
        发送QQ戳一戳（双击头像）。用于打招呼、提醒对方。
        
        Args:
            target_qq(string): 目标QQ号
            chat_type(string): 类型，private/group/auto
        """
        if not self._check_enabled():
            return "错误：插件已禁用"
            
        try:
            client = await self._get_client(event)
            if not client:
                return "错误：无法获取客户端"
            
            if chat_type == "auto":
                if hasattr(event, 'is_private_chat') and event.is_private_chat():
                    chat_type = "private"
                else:
                    chat_type = "group"
            
            target_qq = str(target_qq).strip()
            
            if chat_type == "private":
                await client.api.call_action('friend_poke', user_id=int(target_qq))
                return f"✅ 已向 {target_qq} 发送戳一戳"
            else:
                group_id = getattr(event, 'get_group_id', lambda: None)()
                if not group_id:
                    return "错误：需要在群聊中使用"
                await client.api.call_action('group_poke', group_id=int(group_id), user_id=int(target_qq))
                return f"✅ 已在群聊中戳了 {target_qq}"
                
        except Exception as e:
            logger.error(f"[QzoneTools] 戳一戳失败: {e}")
            return f"发送失败：{str(e)}"


# 配置文件结构
CONFIG_SCHEMA = {
    "enabled": {
        "description": "是否启用插件功能",
        "type": "bool",
        "default": True,
        "hint": "关闭后插件所有功能将不可用"
    }
}

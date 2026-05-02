# QzoneTools - AstrBot QQ空间与消息工具插件

为 AstrBot 提供完整的 QQ 空间操作、消息管理、群管理、记忆管理与QQ状态控制功能。

## 功能特性

| 功能 | 描述 | 状态 |
|------|------|------|
| 📝 **发表说说** | 自动发表QQ空间动态 | ✅ 可用 |
| 👆 **戳一戳** | 发送窗口抖动/双击头像 | ✅ 可用 |
| 🔍 **搜索联系人** | 搜索群聊或好友（支持名字/QQ号模糊匹配） | ✅ 可用 |
| 💬 **主动发消息** | 向指定目标发送消息 | ✅ 可用 |
| ⏰ **定时消息** | 创建定时提醒任务（内存存储） | ✅ 可用 |
| 🕐 **定时指令** | 高级定时任务（支持发空间、改状态、LLM提醒，持久化存储） | ✅ 可用 |
| 🌐 **QQ状态管理** | 设置在线状态（在线/Q我吧/离开/忙碌/隐身/听歌中/睡觉中等） | ✅ 可用 |
| ↩️ **消息撤回** | 群聊中通过引用消息撤回（仅支持群聊） | ✅ 可用 |
| 📧 **发送邮件** | 通过QQ邮箱发送邮件 | ✅ 可用 |
| ㊙️ **群内身份获取** | 可以选择默认注入群身份，也可以LLM自动使用工具获取xx群xx人的身份 | ✅ 可用 |
| 👍🏻 **超多超棒的群管功能** | AI自主管群，支持禁言、踢人、全体禁言、改名片、群公告、群文件管理、设置管理员、群名称修改、群荣誉查看、加群方式设置等 | ✅ 可用 |
| 🎉 **AI声聊**（免费tts） | 使用QQ官方的tts | ✅ 可用 |
| 😍 **输入状态同步** | Bot被唤醒时会议设置当前输入状态为对方正在输入中，更拟人 | 自己去配置文件启用功能 |
| 🧠 **记忆管理** | 自动提取并保存用户重要信息，支持搜索、更新、删除 | ✅ 可用 |
| 🎨 **个人资料管理** | 修改机器人昵称、个性签名、QQ头像 | ✅ 可用 |

## 安装方法

### 方式一：通过AstrBot插件市场（推荐）
直接在WebUI搜索 `qzone_tools` 安装

### 方式二：手动安装
1. 下载本插件压缩包
2. 在 AstrBot WebUI → 插件 → 安装插件 → 上传插件文件
3. 重启或重载插件

### 方式三：Git安装

    # 在AstrBot插件目录执行
    cd /AstrBot/data/plugins
    git clone https://github.com/Wyccotccy/astrbot_plugin_qzone_tools.git


## 使用方法

⚠️ **重要提示**：插件采用特殊的三步工具调用机制，LLM **必须**遵循以下流程调用任何功能：

### 工具调用机制（LLM必读）

1. **第一步**：使用 `search_wyc_tools` 工具，传入简短关键词（如"邮箱"、"禁言"、"发说说"、"记忆"），搜索匹配的工具。**禁止使用完整问句！**
2. **第二步**：如果 `search_wyc_tools` 未找到，再使用 `call_wyc_tools` 查看全部可用工具列表。
3. **第三步**：确定工具名称后，使用 `run_wyc_tool` 并传入工具名称和 JSON 格式的参数执行。

### 推荐系统提示词

在你的 AstrBot 配置中，添加以下提示词到 系统提示词 或 人格设定：

    你拥有通过工具调用实现的以下能力，在适当场景下请主动使用：

    **调用任何功能前，必须先使用 search_wyc_tools 搜索工具名称（使用简短关键词），再通过 run_wyc_tool 执行。禁止直接猜测或编造工具名称！**

    可用功能领域包括：
    - QQ空间操作（发说说）
    - 戳一戳提醒
    - 联系人搜索（好友/群聊模糊搜索）
    - 主动发消息（群聊/私聊）
    - 定时消息与高级定时指令（支持发空间、改状态、LLM提醒，高级指令持久化存储）
    - QQ状态管理（在线/离开/忙碌/隐身/听歌中/睡觉中等）
    - 群聊消息撤回（需引用消息）
    - QQ邮件发送
    - 记忆管理（添加/搜索/更新/删除用户记忆）
    - 群管理（禁言/踢人/全体禁言/改名片/群公告/群文件/设置管理员/群荣誉等）
    - AI语音消息（TTS）
    - 个人资料修改（昵称/签名/头像）

    注意：
    - 发表说说和主动发消息需要确保 NapCat 已登录且状态正常
    - 高级定时指令（create_scheduled_command）支持持久化存储，重启后保留
    - 撤回消息仅支持群聊，需引用消息且2分钟内
    - 发送邮件需在插件配置中填写发件人邮箱和授权码

## 使用示例

### 1. 发表QQ空间说说
- 用户："帮我发条空间说说，今天天气真好"
- LLM：`search_wyc_tools("发说说")` → `run_wyc_tool("publish_qzone", {"content": "今天天气真好"})`

### 2. 戳一戳提醒
- 用户："戳一下刚才说话的那个人"
- LLM：`search_wyc_tools("戳")` → `run_wyc_tool("send_poke", {"target_qq": "123456"})`

### 3. 搜索联系人
- 用户："找一下通知群"
- LLM：`search_wyc_tools("搜索")` → `run_wyc_tool("search_contacts", {"keyword": "通知"})`

### 4. 主动发消息
- 用户："给刚才那个群发个通知，说会议取消了"
- LLM：`search_wyc_tools("发消息")` → `run_wyc_tool("send_message", {"target_id": "群号", "message": "会议取消了"})`

### 5. 记忆管理
- 用户："记住我喜欢喝咖啡"
- LLM：`search_wyc_tools("记忆")` → `run_wyc_tool("add_memory", {"content": "用户喜欢喝咖啡", "tags": "偏好,饮食"})`
- 用户："我之前说过我喜欢什么？"
- LLM：`search_wyc_tools("记忆")` → `run_wyc_tool("search_memories", {"keyword": "喜欢"})`

### 6. QQ状态管理
- 用户："我要隐身玩游戏"
- LLM：`search_wyc_tools("状态")` → `run_wyc_tool("update_qq_status", {"status": "invisible", "duration_minutes": 60})`

### 7. 群聊消息撤回
- 用户：[引用一条消息] "撤回这条"
- LLM：`search_wyc_tools("撤回")` → `run_wyc_tool("recall_by_reply", {})`

### 8. 发送邮件
- 用户："给 friend@qq.com 发邮件，主题测试，内容你好"
- LLM：`search_wyc_tools("邮件")` → `run_wyc_tool("send_qq_email", {"to": "friend@qq.com", "subject": "测试", "content": "你好"})`

### 9. AI语音消息
- 用户："用语音说大家好"
- LLM：`search_wyc_tools("语音")` → `run_wyc_tool("send_ai_voice", {"text": "大家好"})`

### 10. 个人资料修改
- 用户："把机器人昵称改成小助手"
- LLM：`search_wyc_tools("资料")` → `run_wyc_tool("set_qq_profile", {"nickname": "小助手"})`

## 完整工具列表

插件提供以下LLM可调用工具（按功能分类）：

### 记忆管理
- `add_memory` - 添加用户记忆
- `search_memories` - 搜索记忆
- `update_memory` - 更新记忆
- `delete_memory` - 删除记忆
- `get_memory_detail` - 获取记忆详情

### 消息与定时
- `send_message` - 发送消息
- `schedule_message` - 创建定时消息（内存存储，重启丢失）
- `cancel_scheduled_message` - 取消定时消息
- `list_scheduled_messages` - 列出定时消息

### QQ空间
- `publish_qzone` - 发表QQ空间说说

### 戳一戳
- `send_poke` - 发送戳一戳

### QQ状态
- `update_qq_status` - 设置QQ在线状态
- `get_qq_status` - 查看当前状态
- `get_fun_status_list` - 获取娱乐状态列表

### 高级定时指令（持久化）
- `create_scheduled_command` - 创建定时指令
- `list_scheduled_commands` - 列出定时指令
- `cancel_scheduled_command` - 取消定时指令
- `delete_scheduled_command` - 删除定时指令

### 消息操作
- `recall_by_reply` - 引用撤回消息

### 邮件
- `send_qq_email` - 发送QQ邮件

### 联系人
- `search_contacts` - 搜索联系人
- `list_contacts` - 列出联系人

### 群管理
- `get_user_group_role` - 查询群成员身份
- `set_essence_msg` - 设置群精华
- `delete_essence_msg` - 取消群精华
- `set_group_ban` - 禁言/解禁用户
- `set_group_kick` - 踢出群成员
- `set_group_whole_ban` - 全体禁言
- `set_group_card` - 修改群名片
- `send_group_notice` - 发布群公告
- `delete_group_notice` - 删除群公告
- `get_group_notice_list` - 获取公告列表
- `list_group_files` - 查看群文件
- `delete_group_file` - 删除群文件
- `upload_group_file` - 上传群文件
- `create_group_file_folder` - 创建群文件夹
- `delete_group_folder` - 删除群文件夹
- `move_group_file` - 移动群文件
- `rename_group_file` - 重命名群文件
- `trans_group_file` - 传输群文件
- `get_group_members_info` - 获取群成员列表
- `set_group_admin` - 设置/取消管理员
- `set_group_name` - 修改群名称
- `get_group_honor_info` - 获取群荣誉信息
- `get_group_at_all_remain` - 查看@全体成员剩余次数
- `set_group_special_title` - 设置专属头衔
- `get_group_shut_list` - 获取禁言列表
- `get_group_ignore_add_request` - 获取被忽略的加群请求
- `set_group_add_option` - 设置加群方式
- `send_group_sign` - 群打卡

### 其他
- `set_qq_avatar` - 设置QQ头像
- `set_qq_profile` - 修改个人资料（昵称/签名）
- `send_like` - 点赞
- `get_group_msg_history` - 获取群历史消息
- `get_friend_msg_history` - 获取好友历史消息
- `set_group_portrait` - 设置群头像
- `fetch_custom_face` - 获取自定义表情列表
- `set_input_status` - 设置输入状态
- `get_ai_characters` - 获取AI语音角色列表
- `send_ai_voice` - 发送AI语音消息

## 配置说明

插件支持通过配置文件灵活启用/禁用各个工具，以及调整各项参数。主要配置项包括：

- `enabled` - 插件总开关
- `enable_<工具名>` - 单独控制每个工具的启用状态（如 `enable_add_memory: true`）
- `group_manage_enabled` - 群管理功能总开关
- `kick_enabled` - 踢人功能开关
- `email_sender` / `email_authorization_code` - 邮件发送配置
- `ai_voice_default_character` - AI语音默认角色
- `max_memories_per_user` - 每用户最大记忆数
- `memory_inject_enabled` - 是否自动注入用户记忆到LLM上下文
- `inject_group_role_enabled` - 是否自动注入群成员身份
- `auto_input_status_enabled` - 是否自动设置输入状态
- `enable_human_typing` - 是否启用拟人化输入延迟

## 注意事项

### 1. NapCat 兼容性
- 需要 NapCat 支持 `get_credentials` 或 `get_cookies` API 来获取 QQ 空间 Cookie
- 消息撤回功能需要 NapCat 支持 `delete_msg` API
- QQ状态设置需要 `set_online_status` API
- AI语音需要 `get_ai_characters` 和 `send_group_ai_record` API

### 2. Cookie 有效期
- QQ 空间 Cookie 通常几天到几周会过期
- 插件每次发空间都会自动获取最新 Cookie，无需手动配置

### 3. 风控提醒
- 频繁发表说说可能导致 QQ 空间被限制
- 主动私聊消息容易被风控，建议主要用于群聊
- 频繁戳一戳可能触发频率限制

### 4. 定时任务区别

| 特性 | 定时消息 (schedule_message) | 定时指令 (create_scheduled_command) |
|------|----------------------------|-----------------------------------|
| 存储方式 | 内存 | JSON文件持久化 |
| 重启保留 | ❌ 丢失 | ✅ 保留 |
| 功能范围 | 仅发送消息 | 发空间、改状态、LLM提醒 |

### 5. 记忆管理说明
- 记忆按用户ID隔离存储
- 超过最大记忆数时自动清理最旧的记忆
- 支持标签和重要度（1-10）分类
- 可配置将记忆自动注入LLM上下文

## 故障排查

### 发表说说失败
**现象：** 返回"Cookie无效"或"会话未初始化"

**解决：**
1. 检查 NapCat 是否已登录
2. 检查 NapCat 版本是否支持 get_credentials API
3. 尝试重新登录 NapCat 刷新 Cookie

### LLM不调用工具
**现象：** LLM 回复不知道如何操作

**解决：**
1. 确认系统提示词中已包含工具使用规范
2. 检查插件是否已启用（enabled: true）
3. 查看日志确认 search_wyc_tools 是否被加载

### 定时任务未执行
**现象：** 到时间后没有执行

**解决：**
- schedule_message：检查插件是否重启（重启丢失）
- create_scheduled_command：检查日志确认任务是否被加载
- 确认目标ID在发送时仍然有效

### 发送邮件失败
**现象：** 返回认证错误

**解决：**
1. 确认插件配置中已正确填写发件人邮箱和授权码
2. 检查授权码是否为最新
3. 确认发件人QQ邮箱已开启SMTP服务

## 管理员命令

插件提供以下管理员命令（需AstrBot管理员权限）：

| 命令 | 说明 |
|------|------|
| /tool_memory list/add/delete/update/get | 记忆管理 |
| /tool_send_message <目标ID> <消息> | 发送消息 |
| /tool_schedule <目标ID> <消息> <时间> | 创建定时消息 |
| /tool_publish_qzone <内容> | 发说说 |
| /tool_status <状态> <分钟> | 设置QQ状态 |
| /tool_status_get | 查看当前状态 |
| /tool_poke <QQ号> | 戳一戳 |
| /tool_recall | 引用撤回消息 |
| /tool_email <收件人> <主题> <内容> | 发送邮件 |
| /tool_search <关键词> | 搜索联系人 |
| /ai_characters | 查看AI语音角色 |
| /ai_voice [角色] <文本> | 发送AI语音 |
| /ban_user <QQ号> <分钟> | 禁言用户 |
| /unban_user <QQ号> | 解禁用户 |
| /kick <QQ号> | 踢出用户 |
| /whole_ban <on/off> | 全体禁言开关 |
| /set_card <QQ号> <昵称> | 修改群名片 |
| /send_notice <内容> | 发布群公告 |
| /set_admin <QQ号> <on/off> | 设置管理员 |
| /set_group_name <名称> | 修改群名称 |
| /set_qq_avatar [图片] | 设置QQ头像 |
| /set_profile nickname=xxx personal_note=xxx | 修改个人资料 |
| /tool_all_help | 查看完整帮助 |

## 开发者信息
- 作者：Wyccotccy
- GitHub：https://github.com/Wyccotccy/astrbot_plugin_qzone_tools
- 问题反馈：请提交 GitHub Issue

## 更新日志

详细更新日志请查看 CHANGELOG.md

### v3.0.0
- 重点优化了LLM工具调用逻辑，采用 search_wyc_tools → run_wyc_tool 三步机制，避免一次性注入过多工具造成token浪费
- 新增记忆管理功能（MemoryManager），支持添加、搜索、更新、删除用户记忆
- 新增个人资料管理（set_qq_profile），支持修改昵称和个性签名
- 新增设置QQ头像功能（set_qq_avatar）
- 新增群文件移动/重命名/传输功能
- 新增点赞、历史消息获取、群头像设置等功能
- 新增拟人化输入状态延迟功能
- 工具注册表增加关键词匹配，提升LLM搜索准确度

### v2.1.0
- 新增大量群管工具和群文件管理功能
- 新增设置输入状态功能

### v2.0.0
- 新增16个群管功能
- 新增AI声聊功能
- 修复已知问题

### v1.4.0
- 新增大量群管功能
- 修复已知问题

### v1.3.0
- 新增群成员关系获取/注入功能
- 修复已知问题

### v1.2.1
- 新增群聊列表/好友列表搜索功能，支持模糊搜索
- 优化定时任务与定时消息的区分
- 修复QQ空间Cookie过期问题，改为每次发空间都获取最新Cookie

### v1.2.0
- 新增QQ邮箱发送功能，支持纯文本和HTML邮件
- 完善系统提示词

### v1.1.0
- 新增QQ状态管理功能
- 新增定时指令功能（持久化存储）
- 新增群聊消息撤回功能
- 优化搜索联系人功能

### v1.0.0
- 初始版本发布，支持发表说说、戳一戳、搜索联系人、发送消息、定时消息

## 许可证
MIT License

---

Enjoy it! 🎉
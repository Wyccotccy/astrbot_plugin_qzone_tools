## [3.0.0] - 2026-04-11

### ⚡ 重大性能优化
- **大幅降低 LLM Token 消耗**：将原有的 40+ 个独立工具整合为三个核心工具（`search_wyc_tools`、`call_wyc_tools`、`run_wyc_tool`），LLM 不再需要加载全部工具描述，仅按需搜索匹配的工具。实测上下文 token 占用减少 **90% 以上**。
- **强制关键词搜索机制**：LLM 必须优先使用 `search_wyc_tools` 并传入简短关键词（如“邮箱”、“禁言”），禁止直接猜测工具名，进一步减少无效调用和 token 浪费。

### 新增
- **工具 `set_qq_profile`**：调用 NapCat `set_qq_profile` 接口，支持机器人修改自身 QQ 个人资料（昵称、个性签名）。
- **管理员指令 `/set_profile`**：用法 `/set_profile nickname=新昵称 personal_note=新签名`，便于管理员快速修改机器人资料。
- **工具独立启用开关**：在配置文件中为每个工具新增 `enable_xxx` 布尔选项（默认全部启用），可在 WebUI 中单独禁用任意工具，禁用后 LLM 将无法搜索到该工具。

### 变更
- **工具调用架构重构**：
  - 新增 `search_wyc_tools`：根据关键词模糊匹配工具（支持中英文口语化描述）。
  - 新增 `call_wyc_tools`：返回当前已启用的全部工具列表（仅名称+简述）。
  - 新增 `run_wyc_tool`：执行指定工具，需传入工具名称和 JSON 参数。
  - 原有所有工具（如 `add_memory`、`send_message` 等）不再直接暴露给 LLM，仅作为内部处理函数。
- **配置系统简化**：移除基于用户角色的权限控制（如“管理员”、“群主”），统一使用工具独立开关控制可见性。
- **优化系统提示词注入**：在 LLM 请求时强制注入工具使用规范，明确要求优先搜索、使用简短关键词。

### 修复
- 修复 `call_wyc_tools` 和 `run_wyc_tool` 因 LLM 传入多余参数（如 `tool_name`、`tool_args` 错误传递）导致的日志警告问题。

### 文档
- 更新 `_conf_schema.json`，补充所有 `enable_xxx` 配置项及默认值说明。


## [v2.1.0] - 2026-04-10  

*** 本次更新包含了一个我自己认为非常好的功能，不过默认是关闭的，需要自己去配置文件打开，打开之后在私聊中发送消息就能看到“对方正在输入中…”的提示啦！***

### ✨ 新增功能

#### 个人资料与互动
- **设置QQ头像**：新增 `set_qq_avatar` 工具及 `/set_qq_avatar` 指令，支持通过引用图片消息、本地路径或URL设置机器人头像
- **用户点赞**：新增 `send_like` 工具及 `/send_like` 指令，可给指定QQ用户发送名片赞
- **获取自定义表情**：新增 `fetch_custom_face` 工具及 `/fetch_custom_face` 指令，获取机器人账号下的自定义表情列表

#### 群文件管理增强
- **移动群文件**：新增 `move_group_file` 工具及 `/move_group_file` 指令，支持将群文件移动到指定目录
- **重命名群文件**：新增 `rename_group_file` 工具及 `/rename_group_file` 指令，支持修改群文件名称
- **传输群文件**：新增 `trans_group_file` 工具及 `/trans_group_file` 指令，用于获取群文件的传输链接

#### 历史消息获取
- **获取群历史消息**：新增 `get_group_msg_history` 工具及 `/get_group_msg_history` 指令，可按序号和数量拉取群聊历史记录
- **获取好友历史消息**：新增 `get_friend_msg_history` 工具及 `/get_friend_msg_history` 指令，可按序号和数量拉取私聊历史记录

#### 群资料设置
- **设置群头像**：新增 `set_group_portrait` 工具及 `/set_group_portrait` 指令，支持通过引用图片或本地路径修改群头像

#### 用户体验优化
- **自动输入状态**：新增配置项 `auto_input_status_enabled` 和 `auto_input_status_timeout`，开启后机器人在私聊中自动显示"正在输入"状态，回复完成后自动取消
- **手动设置输入状态**：新增 `set_input_status` 工具及 `/set_input_status` 指令，可手动控制输入状态的显示与取消

#### 配置项新增
- `auto_input_status_enabled`：是否启用自动输入状态（默认关闭）
- `auto_input_status_timeout`：自动输入状态超时时间（默认10秒）



## [2.0.0] - 2026-04-09 

### ✨ 新增

- **AI 声聊功能**：基于 NapCat AI 扩展接口实现在群内发送 AI 语音消息
  - 新增 `get_ai_characters` LLM 工具，用于获取当前可用的 AI 语音角色列表
  - 新增 `send_ai_voice` LLM 工具，支持在群聊中指定角色朗读文本
  - 新增 `/ai_characters` 管理员指令，查看所有可用角色及 ID
  - 新增 `/ai_voice` 管理员指令，手动发送 AI 语音消息
  - 配置文件中新增 `ai_voice_default_character` 选项，可预设默认音色
  - 配置文件中新增 `ai_voice_max_text_length` 选项，限制单次文本长度（默认500字符）
  - 内置角色列表缓存机制，有效期10分钟，减少重复 API 调用

- **群管理功能大幅扩展**：补全 NapCat 协议中常用群管接口
  - 新增 `set_group_admin` 工具，用于设置或取消群管理员
  - 新增 `set_group_name` 工具，修改群名称（需机器人有对应权限）
  - 新增 `get_group_notice_list` 工具，获取群公告列表
  - 新增 `upload_group_file` 工具，上传本地文件到群文件
  - 新增 `create_group_file_folder` 工具，在群文件根目录创建文件夹
  - 新增 `delete_group_folder` 工具，删除群文件夹（含内部所有文件）
  - 新增 `get_group_honor_info` 工具，查询群荣誉（龙王、群聊之火等）
  - 新增 `get_group_at_all_remain` 工具，查询 @全体成员 剩余次数
  - 新增 `set_group_special_title` 工具，设置群成员专属头衔（群主权限）
  - 新增 `get_group_shut_list` 工具，获取当前被禁言的成员列表
  - 新增 `get_group_ignore_add_request` 工具，查看被忽略的加群请求
  - 新增 `set_group_add_option` 工具，修改加群方式（允许/需验证/禁止）
  - 新增 `send_group_sign` 工具，执行群打卡操作
  - 对应管理员指令同步添加（`/set_admin`、`/set_group_name`、`/list_notices` 等13个新指令）

- **智能交互增强**
  - 新增 `get_user_group_role` 工具，查询指定用户在群内的身份（群主/管理员/成员）
  - 新增 `list_contacts` 工具，直接列出好友或群聊列表，无需关键词搜索
  - 新增 `search_contacts` 工具，支持按 QQ 号、昵称、群名模糊搜索联系人

- **定时任务系统**
  - 新增 `create_scheduled_command` 高级定时指令，持久化存储并支持重启恢复
  - 支持三种操作类型：发空间说说、修改在线状态、LLM 提醒
  - 新增 `list_scheduled_commands`、`cancel_scheduled_command`、`delete_scheduled_command` 配套工具

- **记忆系统**
  - 新增 `add_memory`、`search_memories`、`update_memory`、`delete_memory`、`get_memory_detail` 五个 LLM 工具
  - 支持为记忆添加标签、设置重要度，并自动清理超量记忆

- **邮件发送**
  - 新增 `send_qq_email` 工具，通过 QQ 邮箱 SMTP 发送邮件
  - 配置项支持发件人、授权码、SMTP 服务器和端口

- **QQ 空间功能**
  - 新增 `publish_qzone` 工具，发布 QQ 空间说说
  - 自动获取并维护 cookie 和 g_tk，支持定时发布

### 🔧 优化

- **客户端获取逻辑重构**：优先从事件中获取 `bot` 实例，确保群管操作使用正确的会话权限，解决因缓存客户端导致的 `1010` 权限不足错误
- **输出内容自动截断**：所有可能返回大量数据的工具（如成员列表、文件列表）均已加入 `max_output_chars` 限制，避免超出 LLM 上下文窗口
- **群角色自动注入**：在群聊中自动将用户身份（成员/管理员/群主）注入 LLM 系统提示词，提升 AI 对权限情境的感知
- **配置文件完善**：新增 `_conf_schema.json` 完整配置项，支持在 WebUI 中可视化编辑所有插件设置

### 🐛 修复

- 修复 AI 语音接口调用失败的问题：参照正常工作的插件，增加了 `chat_type=1` 参数、文本长度限制和超时设置
- 修复 `set_group_name` 等群管接口因客户端实例错误导致的权限异常
- 修复联系人缓存过期后无法自动刷新的问题

### ⚠️ 破坏性变更

- 插件数据目录更名为 `astrbot_plugin_qzone_tools`（如需保留旧数据，请手动迁移）
- 部分 LLM 工具的参数名称与旧版本可能不一致，请重新配置 LLM 调用

### 📚 文档

- 新增 `/tool_all_help` 管理员总帮助指令，分类展示所有可用命令
- 各 LLM 工具和指令均添加了详细的参数说明和用法示例

## [1.4.0] - 2026-04-08

### ✨ 新增

- 完整群管理工具集：新增 8 个 LLM 可调用的群管理工具，支持禁言/解禁、踢人、全体禁言、修改群名片、发送/撤回群公告、设置/取消精华消息、查询群文件列表、删除群文件、处理加群申请。所有工具均通过引用消息或参数调用，群号自动从事件获取，使用更便捷。

- 删除群文件：新增 delete_group_file 工具，支持通过 file_id 删除指定群文件（需机器人有管理文件权限）。

- 输出长度限制：新增配置项 max_output_chars（默认 2000），对群成员列表、好友列表、群文件列表等大段返回内容进行截断，避免超出模型上下文限制。

- 群管理功能总开关：新增 group_manage_enabled（默认 true），可一键禁用所有群管理相关工具和指令。
- 踢人功能独立开关：新增 kick_enabled（默认 true），可单独控制踢人操作，防止误操作。
- 管理员指令全面恢复：修复了 1.3.0 版本中管理员指令仅剩 /tool_all_help 的问题，现已恢复全部 10+ 条管理指令（记忆管理、发送消息、定时任务、空间说说、状态管理、戳一戳、撤回、邮件、定时指令、联系人搜索等）。
- 群成员列表查询工具：新增 get_group_members_info 工具，返回群成员完整信息（包含 user_id、display_name、username、role），支持输出长度自动截断。

### 🔧 修复

- 设置精华消息失败：改用引用消息方式获取消息 ID，避免手动输入消息 ID 导致的 msg not found 错误（完全参照示例插件实现）。

- 管理员指令缺失：补全了所有因篇幅被省略的管理员指令，现在 /tool_send_message、/tool_schedule、/tool_publish_qzone 等命令均可正常使用。

- 群管理工具返回格式统一：所有群管理工具现在返回 {"status": "success/error", "message": "..."} 格式，与插件内其他工具保持一致。

- 定时任务检查逻辑优化：修复了周期性扫描可能漏掉刚好到期的任务的问题，现在每分钟扫描一次，精度满足大多数场景。

### ⚡ 优化

- 联系人搜索与列表输出截断：search_contacts、list_contacts、list_group_files、get_group_members_info 等工具的输出内容现在受 max_output_chars 限制，自动截断并提示，避免 LLM 上下文溢出。

- 群文件列表显示文件 ID：list_group_files 现在会同时显示 file_id，方便后续调用 delete_group_file 删除文件。

- 删除群文件支持引用（预留）：工具函数预留了从引用消息中提取 file_id 的能力，但当前要求用户显式提供 file_id（可通过 list_group_files 获取）。

### 📦 配置更新

- 新增 group_manage_enabled：群管理功能总开关，默认 true。

- 新增 kick_enabled：踢人功能独立开关，默认 true。

- 新增 max_output_chars：限制工具返回内容的最大字符数，默认 2000。

- 原有配置项（记忆上限、角色注入、邮箱设置等）保持不变，升级时自动合并。

### 🗑️ 废弃

- 移除 set_essence / del_essence 工具（旧版要求手动输入消息 ID），请使用新版 set_essence_msg / delete_essence_msg（引用消息方式）。

###📝 计划

- 后续版本将增加更多自动化管理能力（如定时清理群文件、自动审批申请等）。

## 欢迎通过 GitHub Issues 或联系作者 QQ: 1449783068（中午 12:00～凌晨 3:00）反馈建议。


## [1.3.0] - 2026-04-07 

### ✨ 新增
- **群成员身份自动注入**：在群聊中，LLM 对话时会自动注入当前用户在群内的身份（群主/管理员/成员），帮助 AI 更好地理解上下文。可通过配置项 `inject_group_role_enabled` 开关。
- **查询群成员身份工具**：新增函数工具 `get_user_group_role`，LLM 可主动查询任意用户在任意群的身份，返回“群主/管理员/成员”。
- **总帮助命令**：新增管理员指令 `/tool_all_help`，一次性展示所有可用命令及用法。

### 🔧 修复
- **定时任务重复执行**：移除独立的延迟任务，统一由周期扫描执行，并添加执行状态锁，彻底解决同一任务被多次触发的问题。
- **`recall_by_reply` 平台兼容性**：移除了对 `PlatformAdapterType` 的依赖（因旧版 AstrBot 无此导出），现在直接使用 `AiocqhttpMessageEvent` 类型，兼容性更强。
- **过去时间创建定时指令**：增加时间校验，若执行时间早于当前时间会直接返回错误，避免任务永久挂起。
- **记忆配置无法持久化**：记忆存储改用独立 JSON 文件（`memories.json`），不再依赖 `AstrBotConfig` 不可靠的保存机制，重启后数据不丢失。
- **群聊戳一戳群号获取失败**：增加群号有效性检查，若无法获取群号则返回明确错误提示。
- **QQ 空间 Cookie 解析**：改用字典解析 Cookie，优先获取 `p_skey` 再获取 `skey`，提升健壮性。
- **联系人缓存并发写入**：添加 `asyncio.Lock` 保护缓存更新，避免多协程同时修改导致数据错乱。
- **周期扫描重复添加任务**：执行前检查任务是否已在 `running_tasks` 中，防止重复创建。

### ⚡ 优化
- **记忆自动清理**：新增配置项 `max_memories_per_user`（默认 100），每个用户的记忆超过上限时自动删除最旧的记忆（按更新时间）。
- **搜索/列表支持单独类型**：`search_contacts` 和 `list_contacts` 的 `search_type` / `contact_type` 参数现支持 `all`（全部）、`friend`（仅好友）、`group`（仅群聊），LLM 和管理员指令均可使用。
- **定时任务调度统一**：所有持久化定时指令（`create_scheduled_command`）统一由后台周期扫描执行，不再混合使用延迟任务，逻辑更清晰。
- **联系人缓存更新策略**：缓存有效期延长至 5 分钟，减少 API 调用频率。

### 📦 配置更新
- 新增 `max_memories_per_user`：控制每个用户最大记忆条数，默认 100。
- 新增 `inject_group_role_enabled`：控制是否自动注入群成员身份，默认 `true`。
- 原有配置项保持不变，现有用户升级后自动合并新配置项。

## 都给我去死吧，啥玩意啊这辈子不碰py了

## [1.2.1] - 2026-04-06

### ✨ 新增
- 群聊列表/好友列表的搜索功能，支持模糊搜索（可通过 `/tool_search` 和 `/tool_list` 指令使用）。
- 完善“定时任务”与“定时消息”的区分，避免 LLM 混用两种工具。

### 🔧 修复
- 修复了插件长时间运行时 QQ 空间 Cookie 过期的问题，现在每次发空间前都会重新获取最新 Cookie。

### 📝 计划
- 下个版本添加更多工具（有建议可联系作者 QQ: 1449783068，中午 12:00～凌晨 3:00 在线）。
- 作者状态：力竭了，爱咋咋吧。

## [1.2.0] - 2026-04-01

### 🔧 修复
- 修复了部分情况下部分工具可能出现“初始化失败: 'BotAPI' object has no attribute 'call_action'”的问题。
- 修复了 `metadata.yaml` 中多余空格导致插件无法加载的问题（向受影响用户致歉，可联系作者领取 0 元补贴）。

### 📝 计划（4.1～4.20）
- 计划 5 天内完成下一个工具的开发。
- 完善“A 让 Bot 对 B 说……，结果 B 在回应时并不知道 A 让 Bot 说的话”的上下文连贯性问题。
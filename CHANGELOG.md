## [5.0.4] - 2026-06-10

### 🐛 修复
- **`send_file` 图片发送修复**：NapCat CQ 码不支持本地绝对路径，改为 base64 编码发送（`CQ:image,file=base64://...`）。文件发送优先使用 NapCat 原生接口，失败时 fallback 到 base64 CQ 码。发送过程中 base64 数据不会返回给 LLM，避免上下文膨胀。


## [5.0.3] - 2026-06-10

### ✨ 新增功能

#### 图片读取与发送
- **新增 `read_image` 工具**：读取工作区图片文件，返回 base64 编码内容，LLM（多模态模型）可直接查看 Python 代码生成的图表、截图等
- **新增 `send_file` 工具**：将工作区文件发送到 QQ 群或私聊。支持两种模式：
  - 默认以 QQ 文件形式发送（群聊用 `upload_group_file`，私聊用 `send_online_file`）
  - `as_image=true` 时以图片消息形式发送（CQ:image）
- **`run_python_code` 图片自动检测**：执行完毕后自动扫描工作区新增的图片文件，提示 LLM 使用 `read_image` 查看
  - 通过 `python_run_auto_image_enabled` 配置项控制开关（默认开启）
  - 检测最近 35 秒内修改的图片文件，避免误报旧文件

---

## [5.0.2] - 2026-06-10

### 🐛 修复
- **Python 代码执行字体注入修复**：`shlex.quote()` 在仅包含安全字符的路径（如 `/AstrBot/...`）上不会添加引号，导致生成的 `_FONT_PATH = /path/to/font` 成为语法错误。改用 raw string 直接引用路径。

---

## [5.0.1] - 2026-06-08

### 📦 仓库瘦身
- **移除内置字体文件** `fonts/NotoSansCJK-Regular.ttc`（19.5MB），改为运行时按需从 GitHub 下载
- 修正字体路径（之前错误指向 `plugins/fonts/`，实际应为插件内 `fonts/`）
- 仓库体积从 16.39MB 降至 1.62MB

## [5.0.0] - 2026-06-02

### 🔒 安全修复（重大更新）

#### SSRF 防护
- **新增 `_check_ssrf()`**：所有 HTTP 请求（`fetch_url`、`browser_visit`、`open_page`）自动检查目标地址
- **内置黑名单**：默认阻止 127.0.0.0/8、10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、169.254.0.0/16、metadata.google.internal 等内网/元数据地址
- **WebUI 可配置**：支持自定义阻止 IP/URL 和额外 CIDR 范围

#### 图片路径安全
- **新增 `_resolve_image_file()` 路径限制**：仅允许工作区目录、/tmp、闪传中转目录
- **WebUI 开关**：`resolve_image_restricted` 可关闭限制

#### Python 沙箱
- **新增 `run_python_sandbox_enabled`**：可一键禁用 Python 代码执行工具
- **默认危险模式拦截**：内置 8 个危险代码模式（subprocess、os、sys、shutil、ctypes、__import__、eval、exec），即使用户清空配置也生效
- **字体路径注入修复**：`shlex.quote()` 防止命令注入

#### 异常信息泄露修复
- **全局 `_safe_error_msg()`**：替换全部 85+ 处用户可见的 `str(e)`，自动剥离文件路径、IP 地址，截断到 200 字符

#### 截图路径校验
- `screenshot_page_tool` 新增 `save_path` 校验，仅允许保存到工作区目录

#### Docker 容器名可配置
- 新增 `docker_container_name` 配置项（默认 `napcat`），不再硬编码

#### 浏览器搜索安全
- `browser_search_tool` 使用 `url_quote()` 编码关键词，防止 URL 注入

#### 配置端点安全
- `handle_get_config` 脱敏处理 `email_authorization_code` 字段
- `handle_save_config` 白名单校验，拒绝未知配置键，防止覆盖敏感数据

#### 工具权限硬拦截
- `_get_available_tools()` 在 Python 代码层面强制执行权限检查，LLM 无法绕过

### 📝 文档修复

#### tool_all_help 命令帮助重构
- **移除 26 个幻影斜杠命令**：闪传、在线文件、工作区、浏览器工具是 LLM 工具而非斜杠命令，已改为明确标注
- **补全全部 103 个 LLM 工具列表**：按功能分类列出所有可用工具

#### README 更新
- **新增 52 个工具文档**：闪传（8 个）、在线文件（6 个）、好友管理（1 个）、工作区（4 个）、浏览器基础（6 个）、浏览器高级（14 个）、收藏夹（3 个）、浏览器安装（1 个）
- **管理员命令表**：从 23 行扩展到 51 行，与代码完全对齐
- **修复幻影引用**：`download_flash_file` → `download_fileset`，`send_message_to_user` → `send_message`

#### WebUI 修复
- 移除不存在的 `send_file_to_user` 权限配置项

### 🐛 修复
- **插件载入崩溃修复**：`_conf_schema.json` 中 `viewport_size` 和 `tool_permissions` 的 type 从 `dict` 改为 `object`（AstrBotConfig 不支持 dict 类型）
- **授权码脱敏修复**：移除 `email_authorization_code` 的 `***` 脱敏，本地 WebUI 用户需要看到真实值
- **配置持久化修复**：`_conf_schema.json` 缺少所有 v5.0.0 新增的配置 key，导致工作区设置、安全设置、浏览器设置等无法持久化
  - 根因：AstrBotConfig 通过 schema 决定哪些 key 需要持久化，没有 schema 定义的 key 在 `save_config()` 时被忽略
  - 修复：`_conf_schema.json` 新增 23 个 key，`CONFIG_SAVE_WHITELIST` 新增 17 个浏览器相关 key
- **CONFIG_SAVE_WHITELIST 补全**：新增 `browser_type`, `browser_mode`, `cdp_url`, `viewport_size`, `max_pages`, `timeout`, `zoom_factor`, `max_memory_percent`, `idle_timeout`, `monitor_interval` 等浏览器配置项

### 🔧 改进
- **WebUI 浏览器引擎设置面板**：新增可视化配置浏览器类型、模式、CDP 地址、代理、视口大小、缩放、标签页数、超时等
- **WebUI 浏览器性能设置面板**：内存使用上限、空闲超时、监控间隔，带滑块和直观说明
- WebUI 安全设置面板：可视化配置 SSRF 黑名单、图片路径限制、Python 沙箱、Docker 容器名
- 所有配置变更通过 `self.config.update()` + `self.config.save_config()` 持久化到插件配置文件

---

## [4.6.0] - 2026-06-01

### ✨ 新增功能

#### 图片输出格式转换
- **新增 `image_output_format` 配置项**：支持 `webp`（默认）、`png`、`jpg` 三种格式
- **统一转换**：所有插件生成的图片（浏览器截图、刻度叠加图、下载图片等）发送给 AI 前自动转换为目标格式
- **兼容性优化**：webp 格式体积最小，适合大多数场景；jpg 通用性最好；png 无损保真

#### 浏览器渲染模式
- **新增 `browser_render_mode` 配置项**：四种渲染模式可选
  - `完全`（默认）：完整渲染网页，适合性能中上的设备
  - `简略`：禁用毛玻璃效果和滤镜，适合普通设备
  - `极简`：不渲染动画/毛玻璃/自定义字体，仅保留布局和文字，适合 2C2G 服务器
  - `纯文本`：仅渲染文字，不加载图片/视频/Canvas 等，适合超低性能主机
- **CSS 注入机制**：截图前自动注入对应模式的 CSS 样式，不影响页面实际渲染

#### LLM 截图纯文本模式
- **新增 `llm_screenshot_text_only` 配置项**：开启后截图工具只返回页面文本，不返回图片
- **适合非多模态模型**：当 LLM 不支持图片输入时，自动提取页面 `innerText` 返回
- **支持所有截图工具**：`browser_screenshot`、`screenshot_page` 均支持

### 🔧 改进
- **WebUI 新增「浏览器 & 图片设置」面板**：可视化配置图片格式、渲染模式、纯文本模式
- **`TickOverlay` 支持配置**：刻度叠加图输出格式跟随 `image_output_format` 配置

---

## [4.2.0] - 2026-05-31

### ✨ 新增功能

#### 工具权限控制
- **新增 WebUI 权限控制页面**：可视化管理每个工具的访问权限
- **三级权限**：全局（所有人可用）、超管（仅 AstrBot 管理员可用）、禁用（任何人都不能使用）
- **按分类批量设置**：一键将整个分类的工具设为同一权限级别
- **代码层面硬拦截**：权限检查在 Python 代码中强制执行，LLM 无法绕过

#### 隐私控制
- **新增隐私模式**：开启后 LLM 只能看到群名字，无法看到群号和 QQ 号
- **聊天记录过滤**：隐私模式下自动隐藏消息中的 QQ 号（替换为 [用户]）
- **联系人搜索过滤**：搜索结果中隐藏群号和 QQ 号，只显示名字
- **群成员列表过滤**：隐私模式下隐藏成员的 QQ 号
- **群名自动解析**：隐私模式下传入群名字可自动解析为群 ID

### 🔧 改进
- **`_get_available_tools` 支持事件过滤**：根据用户身份动态过滤可用工具
- **`search_wyc_tools` / `call_wyc_tools` 权限感知**：非管理员搜不到超管工具

## [4.1.0] - 2026-05-27

### ✨ 新增功能

#### 高级浏览器自动化
- **搜索引擎支持**：百度、必应、谷歌搜索，自动打开搜索结果
- **页面交互**：点击坐标、输入文字、滚动、滑动、缩放
- **标签页管理**：查看所有标签、切换标签、关闭标签
- **收藏夹功能**：添加、查看、删除收藏，支持 URL 模板
- **对话功能**：向当前页面输入框发送对话内容
- **浏览器监控**：内存监控自动重启、闲置自动关闭
- **截图刻度**：可选在截图上叠加坐标刻度
- **多引擎支持**：chromium、firefox、webkit 可选

### 🔧 改进
- **WebUI 能力控制**：新增所有浏览器工具的开关控制
- **工具注册优化**：浏览器工具分为高级版和简化版，LLM 可根据场景选择
- **自动依赖安装**：插件加载时自动检查并安装 Playwright 和系统依赖

## [4.0.0] - 2026-05-27

### ✨ 新增功能

#### 浏览器自动化
- **新增 `open_page` 工具**：打开网页，支持 CSS 选择器和文字点击
- **新增 `click_element` 工具**：点击网页元素（按钮、链接等）
- **新增 `type_text` 工具**：在网页输入框中输入文字，可选按回车
- **新增 `screenshot_page` 工具**：对当前网页截图，用于验证码识别等场景
- **新增 `close_page` 工具**：关闭浏览器，释放资源
- **自动安装依赖**：插件加载时自动检查并安装 Playwright 和 Chromium 浏览器
- **会话复用**：同一会话内浏览器保持打开，无需重复启动

#### 网页内容获取
- **新增 `fetch_url` 工具**：获取网页文本内容，支持自定义最大字数（默认500）

#### 闪传功能优化
- **Docker 环境支持**：自动使用 `docker cp` 将文件复制到 NapCat 容器，无需手动配置共享目录
- **智能检测**：自动判断 Docker/非 Docker 环境，选择最佳文件传输方式

### 🐛 修复
- **配置保存问题**：修复保存配置时会清空其他配置项（如工具开关）的问题
- **工具开关失效**：修复关闭工具开关后 LLM 仍能调用的问题

### 🔧 改进
- **WebUI 能力控制**：新增浏览器自动化工具的开关控制
- **错误提示优化**：闪传功能在 Docker 环境下给出更清晰的配置指引
- **日志增强**：Playwright 安装过程记录详细日志

### 📝 依赖更新
- 新增可选依赖：playwright（浏览器自动化）
- 新增系统依赖：libnss3, libatk1.0-0 等（Playwright 运行所需）

## [3.6.0] - 2026-05-22

### ✨ WebUI 优化
- **WebUI 面板重写**：全新的配置、记忆与定时消息管理面板，支持可视化编辑插件配置、管理用户记忆、查看和取消定时消息。
- **Bridge SDK 内联化**：将 AstrBot Plugin Page Bridge SDK 直接内联到 HTML 中，避免沙箱环境下外部脚本加载失败导致页面卡死。
- **超时容错**：添加 `bridge.ready()` 5 秒超时回落机制，即使父窗口上下文未及时返回也能正常加载配置。
- **错误可见化**：配置加载失败时页面顶部显示红色错误横幅，不再静默失败。
- **WebUI 后端 API 完善**：新增 `add_memory` 和 `update_memory` Web API 端点，WebUI 记忆管理功能完整可用。

### 🐛 修复

#### 获取历史记录工具
- **重写消息获取逻辑**：`get_group_msg_history` 和 `get_friend_msg_history` 移除已废弃的 `message_seq` 参数，改用 `_call_history_api_with_seq` 分页拉取机制，避免 NapCat 接口变更导致无法获取消息。
- **消息内容可读性增强**：新增 `_format_message_content` 方法，将 OneBot v11 消息段（图片、表情、@提及、回复、文件、语音等）转换为可读文本，LLM 能理解消息中的媒体内容。
- **搜索关键词扩充**：历史记录工具的搜索标签增加 30+ 中文口语化关键词（"群里说了什么"、"看看群消息"、"查群记录"等），LLM 更容易找到匹配工具。

#### 设置 QQ 头像 / 群头像
- **跨容器图片传递**：新增 `_resolve_image_file` 方法，自动将本地文件路径转为 `base64://` 格式，解决 Docker 容器内文件路径无法直接传递给 NapCat 的问题。
- **参数合理性调整**：`set_qq_avatar` 和 `set_group_portrait` 的 `file` 参数改为必填，LLM 必须提供图片路径/URL/Base64，不再依赖引用消息（NapCat 下引用消息获取图片不可靠）。
- **错误提示友好化**：设置失败时返回 "❌ 设置头像失败，请检查图片是否有效" 而非原始异常信息，用户端体验更好。
- **文件有效性检查**：添加前置检查，文件不存在时直接返回明确错误提示，避免 NapCat 接口调用失败后吞异常。

#### 其他
- 设置头像/群头像异常日志优化（`exc_info=False`），减少非必要堆栈输出。

### ⚡ 优化
- WebUI 底层的 Bridge 通信容错增强


## [3.5.1] - 2026.5.4
### 同步更新了WebUI，可以更方便直观的查看插件信息（**额现在还不能编辑信息，Astrbou的这玩意还有点没搞明白.....等等我**）

### 部分工具NAPCAT似乎不太兼容......我直接测试API接口是可用的，但是换成LLM调用函数工具就用不了了，我还在研究当中

## [3.0.1] - 2026-04-21

## 没啥更新的，加了个"输入状态拟人"，私信时如果一定时间内没有找bot，bot会进入"休息"状态，在这个状态下给bot发消息，会随机延迟一段时间再回复。回复之后，后续一定时间内的回复都是实时回复。


## [3.0.0] - 2026-04-11

### ⚡ 重大性能优化
- **大幅降低 LLM Token 消耗**：将原有的 40+ 个独立工具整合为三个核心工具（`search_wyc_tools`、`call_wyc_tools`、`run_wyc_tool`），LLM 不再需要加载全部工具描述，仅按需搜索匹配的工具。实测上下文 token 占用减少 **90% 以上**。
- **强制关键词搜索机制**：LLM 必须优先使用 `search_wyc_tools` 并传入简短关键词（如"邮箱"、"禁言"），禁止直接猜测工具名，进一步减少无效调用和 token 浪费。

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
- **配置系统简化**：移除基于用户角色的权限控制（如"管理员"、"群主"），统一使用工具独立开关控制可见性。
- **优化系统提示词注入**：在 LLM 请求时强制注入工具使用规范，明确要求优先搜索、使用简短关键词。

### 修复
- 修复 `call_wyc_tools` 和 `run_wyc_tool` 因 LLM 传入多余参数（如 `tool_name`、`tool_args` 错误传递）导致的日志警告问题。

### 文档
- 更新 `_conf_schema.json`，补充所有 `enable_xxx` 配置项及默认值说明。


## [v2.1.0] - 2026-04-10  

*** 本次更新包含了一个我自己认为非常好的功能，不过默认是关闭的，需要自己去配置文件打开，打开之后在私聊中发送消息就能看到"对方正在输入中…"的提示啦！***

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
- **查询群成员身份工具**：新增函数工具 `get_user_group_role`，LLM 可主动查询任意用户在任意群的身份，返回"群主/管理员/成员"。
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
- 完善"定时任务"与"定时消息"的区分，避免 LLM 混用两种工具。

### 🔧 修复
- 修复了插件长时间运行时 QQ 空间 Cookie 过期的问题，现在每次发空间前都会重新获取最新 Cookie。

### 📝 计划
- 下个版本添加更多工具（有建议可联系作者 QQ: 1449783068，中午 12:00～凌晨 3:00 在线）。
- 作者状态：力竭了，爱咋咋吧。

## [1.2.0] - 2026-04-01

### 🔧 修复
- 修复了部分情况下部分工具可能出现"初始化失败: 'BotAPI' object has no attribute 'call_action'"的问题。
- 修复了 `metadata.yaml` 中多余空格导致插件无法加载的问题（向受影响用户致歉，可联系作者领取 0 元补贴）。

### 📝 计划（4.1～4.20）
- 计划 5 天内完成下一个工具的开发。
- 完善"A 让 Bot 对 B 说……，结果 B 在回应时并不知道 A 让 Bot 说的话"的上下文连贯性问题。

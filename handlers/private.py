# handlers/private.py
"""
私聊处理模块
包含: /start, /help, /myid 命令，以及 @teacher_name 群组处理
"""

import asyncio
import logging
import re
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import (
    get_start_message,
    get_start_buttons,
    get_all_required_channels,
    get_teacher_stats,
    get_leaderboard,
    record_user,
    get_teacher_info,
    get_delete_user_messages,
    search_teachers,
    get_teacher_score_averages,
)
from states import RatingStates
from bot_instance import bot, get_channel_invite_link, get_bot_start_url
from utils.helpers import (
    format_leaderboard_text,
    fetch_tg_teacher_info,
    auto_delete_message,
    format_score_line,
    build_rating_nav_keyboard,
    get_rating_forward_prompt,
)

logger = logging.getLogger(__name__)
router = Router()

MAX_INLINE_REVIEWS = 3  # 卡片内最多显示的评价条数
DEFAULT_WELCOME_MESSAGE = (
    "👋 欢迎来到「狼评」教师评价\n\n"
    "这里是一个更高效的教师口碑入口，帮你在联系前先看清老师的真实反馈。\n\n"
    "🎯 你可以在这里：\n"
    "• 查看老师的推荐率、综合印象与最新评价\n"
    "• 提交一条客观评价，帮助更多同学快速决策\n"
    "• 先逛教师榜单，再决定要不要深入了解\n\n"
    "🔎 开始方式：\n"
    "在群组或私聊直接发送 @teacher_name\n"
    "例如：@李老师 / @王教授 / @张老师\n\n"
    "💡 如果你是第一次使用，建议先看「评价流程」。"
)


def _build_welcome_keyboard(start_buttons: list):
    """构建欢迎页键盘，固定包含三个快捷按钮，并追加自定义按钮"""
    kb_rows = [
        [
            InlineKeyboardButton(text="🚀 快速上手", callback_data="show_help"),
            InlineKeyboardButton(text="📝 评价流程", callback_data="how_to_rate"),
            InlineKeyboardButton(text="🏆 排行榜", callback_data="leaderboard_quick"),
        ]
    ]
    for btn in start_buttons:
        kb_rows.append([InlineKeyboardButton(text=btn["text"], url=btn["url"])])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def _extract_start_payload(text: str) -> str:
    """从 /start 文本中提取 payload"""
    if not text:
        return ""
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


async def _start_rating_flow(message: Message, state: FSMContext, teacher_name: str) -> None:
    """在私聊中初始化评价流程"""
    await state.update_data(
        teacher=teacher_name,
        user_id=message.from_user.id,
        forward_checked=False,
        forwarded_teacher_id="",
        forwarded_teacher_username="",
        forwarded_teacher_nickname=""
    )
    await state.set_state(RatingStates.waiting_forwarded_message)
    await message.reply(
        get_rating_forward_prompt(teacher_name),
        reply_markup=build_rating_nav_keyboard(teacher_name, back_target="card")
    )


async def _build_mention_action_keyboard(teacher_name: str, is_private: bool) -> InlineKeyboardMarkup:
    """构建 @提及时的操作选择按钮"""
    if is_private:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 查看评价", callback_data=f"mention_action|view|{teacher_name}")],
            [InlineKeyboardButton(text="📝 提交评价", callback_data=f"mention_action|rate|{teacher_name}")]
        ])

    view_url = await get_bot_start_url(f"view_{teacher_name}")
    rate_url = await get_bot_start_url(f"rate_{teacher_name}")
    if view_url and rate_url:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 查看评价", url=view_url)],
            [InlineKeyboardButton(text="📝 提交评价", url=rate_url)]
        ])

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 查看评价", callback_data=f"mention_action|view|{teacher_name}")],
        [InlineKeyboardButton(text="📝 提交评价", callback_data=f"mention_action|rate|{teacher_name}")]
    ])


@router.message(Command("start", "开始"))
async def cmd_start(message: Message, state: FSMContext):
    """处理 /start 或 /开始 命令"""
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    channels = get_all_required_channels()

    # 记录用户（用于广播功能）
    try:
        record_user(
            user_id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or ""
        )
    except Exception as e:
        logger.warning(f"记录用户失败: {e}")

    logger.info(f"👤 用户 {user_id} 启动机器人，频道数: {len(channels)}")
    
    if channels:
        try:
            # 检查用户是否在所有频道中
            not_subscribed = []
            
            for channel_id in channels:
                try:
                    member = await bot.get_chat_member(channel_id, user_id)
                    if member.status in ('left', 'kicked', 'restricted'):
                        not_subscribed.append(channel_id)
                except Exception:
                    not_subscribed.append(channel_id)
            
            if not_subscribed:
                logger.warning(f"⚠️ 用户 {user_id} 未订阅 {len(not_subscribed)} 个频道")
                
                # 获取频道信息并创建按钮
                kb_buttons = []
                for channel_id in not_subscribed:
                    try:
                        channel = await bot.get_chat(channel_id)
                        channel_link = await get_channel_invite_link(channel_id)
                        if channel_link:
                            kb_buttons.append([
                                InlineKeyboardButton(
                                    text=f"📢 加入 {channel.title}",
                                    url=channel_link
                                )
                            ])
                    except Exception as e:
                        logger.error(f"获取频道信息失败: {e}")
                
                kb_buttons.append([
                    InlineKeyboardButton(
                        text="✅ 我已全部加入，验证",
                        callback_data="check_all_subscriptions"
                    )
                ])
                
                kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
                
                await message.reply(
                    f"⚠️ 您需要加入以下频道才能使用机器人\n\n"
                    f"━━━━━━━━━━━━━\n"
                    f"📊 需要加入 {len(not_subscribed)} 个频道\n"
                    f"━━━━━━━━━━━━━\n\n"
                    f"🔗 请点击下方按钮加入，加入后点击验证",
                    reply_markup=kb
                )
                return
            
            logger.info(f"✅ 用户 {user_id} 已订阅所有频道")
        
        except Exception as e:
            logger.error(f"检查频道成员时出错: {e}")
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔄 重新验证",
                    callback_data="retry_verify"
                )]
            ])
            
            await message.reply(
                "⚠️ 无法验证您的订阅状态\n\n"
                "🔗 请确保已加入所有频道后重新验证",
                reply_markup=kb
            )
            return

    # 用户已订阅或未设置频道要求
    welcome = get_start_message(DEFAULT_WELCOME_MESSAGE)
    start_buttons = get_start_buttons()
    kb = _build_welcome_keyboard(start_buttons)
    payload = _extract_start_payload(message.text or "")

    if payload.startswith("view_"):
        teacher_name = payload[5:].strip().lstrip("@")
        if teacher_name:
            card_text, card_kb = await _build_teacher_card(teacher_name)
            await message.reply(card_text, reply_markup=card_kb)
            return

    if payload.startswith("rate_"):
        teacher_name = payload[5:].strip().lstrip("@")
        if teacher_name:
            await _start_rating_flow(message, state, teacher_name)
            return

    await message.reply(welcome, reply_markup=kb)


# ==================== 键盘按钮文字处理 ====================

@router.message(F.text.in_(["📖 查看帮助", "📘 帮助中心", "帮助"]), StateFilter(None))
async def kb_show_help(message: Message):
    """处理键盘按钮：查看帮助"""
    if message.chat.type != "private":
        return
    await cmd_help(message)


@router.message(F.text.regexp(r"^/帮助(?:@[A-Za-z0-9_]+)?$"), StateFilter(None))
async def text_cmd_help(message: Message):
    """兼容 /帮助 被当作普通文本发送的情况"""
    await cmd_help(message)


@router.message(F.text.in_(["⭐ 如何评价", "📝 评价流程"]), StateFilter(None))
async def kb_how_to_rate(message: Message):
    """处理键盘按钮：如何评价"""
    if message.chat.type != "private":
        return
    await message.reply("""⭐ 如何评价教师

步骤 1️⃣：输入教师名称
在群组或私聊中输入: @李老师

步骤 2️⃣：选择操作
机器人会先询问您：
• 📖 查看评价
• 📝 提交评价

步骤 3️⃣：转发教师消息
向机器人转发一条该教师的 Telegram 消息

步骤 4️⃣：选择态度
• 👍 推荐
• 👎 不推荐

步骤 5️⃣：完成评分
依次填写：
• 🤝 服务质量
• ✨ 外貌形象
• 🌟 推荐指数

步骤 6️⃣：填写理由
在私聊中输入评价理由
至少 12 个字

步骤 7️⃣：提交
评价成功后机器人会显示确认

💡 小贴士：
• 一个教师只能评价一次
• 评价要真实客观
• 具体说明优缺点""")


@router.message(F.text == "🏆 教师排行榜", StateFilter(None))
async def kb_leaderboard(message: Message):
    """处理键盘按钮：教师排行榜"""
    if message.chat.type != "private":
        return
    leaderboard = get_leaderboard(10)
    text = format_leaderboard_text(leaderboard)
    await message.reply(text)


@router.message(F.text == "❓ 常见问题", StateFilter(None))
async def kb_faq(message: Message):
    """处理键盘按钮：常见问题"""
    if message.chat.type != "private":
        return
    await message.reply("""❓ 常见问题

Q: 如何查询教师评价？
A: 输入 @teacher_name

Q: 可以评价多少次？
A: 每个教师只能一次，不同教师可多次

Q: 评价立即显示吗？
A: 是的，立即保存和显示

Q: 可以修改评价吗？
A: 不支持修改

Q: 评价公开吗？
A: 是的，所有用户都能看到

Q: 如何举报不当评价？
A: 联系管理员

Q: 可以匿名评价吗？
A: 可以用别账号""")


@router.message(Command("help", "帮助"))
async def cmd_help(message: Message):
    """处理 /help 或 /帮助 命令，以及键盘按钮"📖 查看帮助"触发"""
    help_text = """📖 完整帮助文档

👥 用户命令：
• /开始 - 启动机器人
• /查询 <教师名> - 搜索教师评价（支持中文名模糊搜索）
• /我的ID - 获取您的用户ID

🌟 核心功能：
查询教师评价 - 在群组或私聊中输入 @teacher_name，或使用 /查询 命令

⭐ 如何评价教师：

1️⃣ 输入教师名称
   在群组或私聊中输入 @teacher_name
   或发送 /查询 李老师

2️⃣ 选择操作
   机器人会先询问您要：
   • 📖 查看评价
   • 📝 提交评价

3️⃣ 查看评价卡片 / 开始评价
   如果选择查看评价，机器人会显示该教师的：
   • 推荐人数 (👍)
   • 不推荐人数 (👎)
   • 综合评分（服务/形象/推荐）
   • 评价详情和历史记录

4️⃣ 转发教师消息
   如果选择提交评价，先向机器人转发一条该教师的 Telegram 消息

5️⃣ 选择态度
   点击下方按钮：
   • 👍 推荐 - 推荐这位教师
   • 👎 不推荐 - 不推荐这位教师

6️⃣ 多维度打分（可跳过）
   依次为以下三项打 1-5 分：
   • 🤝 服务质量（沟通、回应、负责程度）
   • ✨ 外貌形象（气质、形象、状态观感）
   • 🌟 推荐指数（你整体有多愿意推荐 TA）

7️⃣ 填写评价理由
   机器人在您的私聊中会发送消息
   要求您填写评价理由
   • 至少需要 12 个字
   • 请真实、客观、具体
   
   评价示例：
   ✅ "讲课很生动，逻辑清晰，认真负责，强烈推荐"
   ✅ "课程进度快，不太照顾基础差的同学"
   ❌ "很好" (太短了)

8️⃣ 提交评价
   评价将被保存到数据库，其他用户可以看到

📊 查看评价统计：
输入 @teacher_name 或 /查询 即可看到该教师的：
• 总评价数
• 推荐/不推荐比例
• 综合评分（服务/形象/推荐均值）
• 最新的评价内容

💡 使用建议：
✅ 真实评价 - 帮助其他同学
✅ 具体内容 - 说明优缺点
✅ 尊重他人 - 文明评价
✅ 客观态度 - 不夸大不贬低

⚠️ 注意事项：
• 每个用户对同一个教师只能评价一次
• 评价内容应该基于真实体验
• 避免人身攻击或侮辱性语言

❓ 常见问题：

Q: 可以修改已经提交的评价吗？
A: 当前版本不支持修改，但可以联系管理员。

Q: 为什么看不到我的评价？
A: 评价提交后会立即显示，检查是否输入了正确的教师名称。

Q: 如何举报不文明的评价？
A: 联系管理员，提供评价的教师名称和时间。

📞 获取帮助：
• 联系管理员获取更多帮助
• 在群组中使用 @teacher_name 测试
• 私聊中使用 /查询 李老师 测试"""
    
    await message.reply(help_text)


@router.message(Command("leaderboard", "排行榜"))
async def cmd_leaderboard(message: Message):
    """处理 /leaderboard 或 /排行榜 命令"""
    leaderboard = get_leaderboard(10)
    text = format_leaderboard_text(leaderboard)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="back_to_start")]
    ])
    await message.reply(text, reply_markup=kb)


@router.message(Command("myid", "我的ID"))
async def get_my_id(message: Message):
    """获取用户ID"""
    user_id = message.from_user.id
    username = message.from_user.username or "无"
    first_name = message.from_user.first_name or "用户"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 查看帮助", callback_data="show_help")],
        [InlineKeyboardButton(text="🔙 返回主菜单", callback_data="back_to_start")]
    ])
    
    await message.reply(f"""📋 您的 Telegram 信息

👤 基本信息：
• 用户ID: <code>{user_id}</code>
• 用户名: @{username}
• 名字: {first_name}

🛠️ 管理员设置：
如果您想成为管理员，请：

1️⃣ 复制您的用户ID:
   <code>{user_id}</code>

2️⃣ 进入 Railway Dashboard
   → fuyao 项目
   → Settings → Variables

3️⃣ 编辑或添加 ADMIN_IDS:
   键: ADMIN_IDS
   值: {user_id}
   (多个管理员用逗号分隔)

4️⃣ 保存并重新部署机器人
   点击 "Redeploy"

5️⃣ 部署完成后，您就可以使用:
   • /管理 - 管理后台
   • /添加频道 - 添加频道
   • /频道列表 - 查看频道
   • 等更多管理员命令

💡 管理员权限:
✅ 查看统计数据
✅ 添加/删除频道
✅ 自定义欢迎语
✅ 诊断系统问题
✅ 查看数据库信息""", reply_markup=kb)

# ==================== 处理 @teacher_name 提及 ====================

def _format_score_line(scores: dict) -> str:
    """将评分均值格式化为一行文字，若无数据则返回空字符串"""
    return format_score_line(scores)


@router.message(Command("查询", "search"))
async def cmd_search_teacher(message: Message):
    """处理 /查询 <教师名> 命令，支持私聊按中文名模糊搜索教师"""
    if message.chat.type != "private":
        return

    text = message.text or ""
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.reply(
            "🔍 使用方法：/查询 <教师名>\n\n"
            "示例：\n"
            "/查询 李老师\n"
            "/查询 王教授\n\n"
            "也可在群组或私聊中输入 @teacher_name 直接查询"
        )
        return

    keyword = parts[1].strip().lstrip("@")

    results = search_teachers(keyword)

    if not results:
        await message.reply(
            f"🔍 未找到与「{keyword}」相关的教师\n\n"
            f"💡 提示：\n"
            f"• 尝试更简短的关键词\n"
            f"• 也可以直接输入 @teacher_name 查询"
        )
        return

    if len(results) == 1:
        # 精确或唯一匹配，直接显示教师卡片
        from handlers.private import _build_teacher_card
        card_text, kb = await _build_teacher_card(results[0])
        await message.reply(card_text, reply_markup=kb)
        return

    # 多个匹配，让用户选择
    kb_rows = []
    for name in results[:10]:
        stats = get_teacher_stats(name)
        label = f"@{name}（{stats['total']} 条评价）"
        kb_rows.append([InlineKeyboardButton(text=label, callback_data=f"more_reviews|{name}|0")])

    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    await message.reply(
        f"🔍 找到 {len(results)} 位相关教师，请选择：",
        reply_markup=kb
    )


async def _build_teacher_card(teacher_name: str):
    """构建教师评价卡片文字和按钮，供私聊查询和 @mention 共用"""
    stats = get_teacher_stats(teacher_name)
    teacher_info = get_teacher_info(teacher_name)

    nickname = teacher_info.get("nickname", "")
    tid = teacher_info.get("teacher_id", "")
    nickname, tid = await fetch_tg_teacher_info(bot, teacher_name, nickname, tid)

    header = f"👨‍🏫 教师名片｜@{teacher_name}"
    if nickname:
        header += f"\n📛 昵称：{nickname}"
    if tid:
        header += f"\n🪪 Telegram ID：{tid}"

    scores = get_teacher_score_averages(teacher_name)
    score_line = _format_score_line(scores)

    if stats["total"] == 0:
        display_text = (
            f"┏━━━━━━━━━━━━━━\n"
            f"{header}\n"
            f"┗━━━━━━━━━━━━━━\n\n"
            f"📭 暂无公开评价\n"
            f"这位老师还没有留下可参考的反馈。\n\n"
            f"✨ 你可以成为第一位提交评价的人。"
        )
    else:
        recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
        not_rec_pct = 100 - recommend_percentage

        display_text = (
            f"┏━━━━━━━━━━━━━━\n"
            f"{header}\n"
            f"┗━━━━━━━━━━━━━━\n\n"
            f"📌 当前概览\n"
            f"• 评价样本：{stats['total']} 条\n"
            f"• 推荐人数：{stats['recommend']} 人（{recommend_percentage}%）\n"
            f"• 不推荐：{stats['not_recommend']} 人（{not_rec_pct}%）\n"
        )
        if score_line:
            display_text += f"\n⭐ 综合印象\n{score_line}\n"

        if stats["latest"]:
            display_text += f"\n📝 最新反馈\n"
            for i, review in enumerate(stats["latest"][:MAX_INLINE_REVIEWS], 1):
                rec_emoji = "👍" if review[2] else "👎"
                reason = review[3]
                display_text += f"{i}. {rec_emoji} 评价 #{review[0]}\n"
                display_text += f"   💬 {reason[:50]}{'...' if len(reason) > 50 else ''}\n\n"
            display_text = display_text.rstrip()

    kb_rows = [[
        InlineKeyboardButton(text="📝 提交评价", callback_data=f"mention_action|rate|{teacher_name}"),
        InlineKeyboardButton(text="🏆 教师榜单", callback_data="leaderboard_quick")
    ]]

    if stats["total"] > MAX_INLINE_REVIEWS:
        remaining = stats["total"] - MAX_INLINE_REVIEWS
        kb_rows.append([
            InlineKeyboardButton(
                text=f"📋 查看全部评价（还有 {remaining} 条）",
                callback_data=f"more_reviews|{teacher_name}|0"
            )
        ])

    return display_text, InlineKeyboardMarkup(inline_keyboard=kb_rows)


# ==================== 处理 @teacher_name 提及 ====================

@router.message(StateFilter(None))
async def handle_teacher_mention(message: Message, state: FSMContext):
    """
    处理 @teacher_name 提及
    支持群组和私聊
    """
    # 忽略没有文本的消息（图片、贴纸等）
    if not message.text:
        return
    
    # 忽略命令
    if message.text.startswith("/"):
        return
    
    # 处理群组中发送的"排行榜"关键词
    if message.chat.type != "private" and "排行榜" in message.text:
        leaderboard = get_leaderboard(10)
        text = format_leaderboard_text(leaderboard)
        await message.reply(text)
        return

    # 只处理包含 @ 符号的消息
    if "@" not in message.text:
        return
    
    # 提取 @username（仅匹配英文字母、数字和下划线，即 Telegram 用户名格式）
    pattern = r'@([a-zA-Z0-9_]+)'
    matches = re.findall(pattern, message.text)
    
    if not matches:
        return
    
    teacher_name = matches[0]
    user_id = message.from_user.id
    
    logger.info(f"👤 用户 {user_id} 查询教师 @{teacher_name}")
    
    try:
        sent = await message.reply(
            f"👋 已识别教师 @{teacher_name}\n\n请选择接下来要执行的操作：",
            reply_markup=await _build_mention_action_keyboard(
                teacher_name,
                is_private=message.chat.type == "private"
            )
        )
        logger.info(f"✅ 已向用户询问 @{teacher_name} 的操作类型")

        # 在群组中自动删除机器人回复和原始消息
        if message.chat.type != "private":
            asyncio.create_task(auto_delete_message(sent))
            if get_delete_user_messages():
                asyncio.create_task(auto_delete_message(message))
        
    except Exception as e:
        logger.error(f"处理教师提及时出错: {e}", exc_info=True)
        await message.reply(f"❌ 出错: {str(e)}")

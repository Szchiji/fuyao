# handlers/private.py
"""
私聊处理模块
包含: /start, /help, /myid 命令，以及 @teacher_name 群组处理
"""

import logging
import re
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from database import (
    get_start_message,
    get_start_buttons,
    get_all_required_channels,
    get_teacher_stats,
    get_leaderboard,
    record_user,
    get_teacher_info
)
from states import RatingStates
from bot_instance import bot, get_channel_invite_link
from utils.helpers import format_leaderboard_text

logger = logging.getLogger(__name__)
router = Router()

MAX_INLINE_REVIEWS = 3  # 卡片内最多显示的评价条数


def _build_welcome_keyboard(start_buttons: list) -> InlineKeyboardMarkup | ReplyKeyboardMarkup:
    """根据是否有自定义按钮决定键盘类型"""
    if start_buttons:
        kb_rows = []
        for btn in start_buttons:
            kb_rows.append([InlineKeyboardButton(text=btn["text"], url=btn["url"])])
        return InlineKeyboardMarkup(inline_keyboard=kb_rows)
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📖 查看帮助"), KeyboardButton(text="⭐ 如何评价")],
                [KeyboardButton(text="🏆 教师排行榜"), KeyboardButton(text="❓ 常见问题")]
            ],
            resize_keyboard=True
        )


@router.message(Command("start", "开始"))
async def cmd_start(message: Message):
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
                except:
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
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"📊 需要加入 {len(not_subscribed)} 个频道\n"
                    f"━━━━━━━━━━━━━━━━━━━\n\n"
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
    default_welcome = (
        "👋 欢迎使用狼评机器人！🎓\n\n"
        "这是一个教师评价平台，帮助同学们了解教师的教学情况。\n\n"
        "📝 使用方法：\n"
        "在群组中输入 @teacher_name 来查询或评价教师\n\n"
        "例如：@李老师、@王教授、@张老师\n\n"
        "💡 更多帮助请输入 /帮助"
    )
    welcome = get_start_message(default_welcome)
    start_buttons = get_start_buttons()
    kb = _build_welcome_keyboard(start_buttons)
    
    await message.reply(welcome, reply_markup=kb)


# ==================== 键盘按钮文字处理 ====================

@router.message(F.text == "📖 查看帮助", StateFilter(None))
async def kb_show_help(message: Message):
    """处理键盘按钮：查看帮助"""
    if message.chat.type != "private":
        return
    await cmd_help(message)


@router.message(F.text == "⭐ 如何评价", StateFilter(None))
async def kb_how_to_rate(message: Message):
    """处理键盘按钮：如何评价"""
    if message.chat.type != "private":
        return
    await message.reply("""⭐ 如何评价教师

步骤 1️⃣：输入教师名称
在群组中输入: @李老师

步骤 2️⃣：查看评价卡片
机器人显示该教师的：
• 推荐人数: 👍 5
• 不推荐人数: 👎 2
• 最新评价（含 ID）

步骤 3️⃣：选择态度
• 👍 推荐
• 👎 不推荐

步骤 4️⃣：填写理由
在私聊中输入评价理由
至少 12 个字

步骤 5️⃣：提交
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
• /帮助 - 获取帮助
• /我的ID - 获取您的用户ID

🌟 核心功能：
查询教师评价 - 输入 @teacher_name

⭐ 如何评价教师：

1️⃣ 输入教师名称
   在群组或私聊中输入 @teacher_name
   例如: @李老师、@王教授、@数学老师

2️⃣ 查看评价卡片
   机器人会显示该教师的：
   • 推荐人数 (👍)
   • 不推荐人数 (👎)
   • 评价详情和历史记录

3️⃣ 选择态度
   点击下方按钮：
   • 👍 推荐 - 推荐这位教师
   • 👎 不推荐 - 不推荐这位教师

4️⃣ 填写评价理由
   机器人在您的私聊中会发送消息
   要求您填写评价理由
   • 至少需要 12 个字
   • 请真实、客观、具体
   
   评价示例：
   ✅ "讲课很生动，逻辑清晰，认真负责，强烈推荐"
   ✅ "课程进度快，不太照顾基础差的同学"
   ❌ "很好" (太短了)

5️⃣ 提交评价
   检查内容后提交
   • 评价将被保存到数据库
   • 其他用户可以看到您的评价
   • 每个教师只能评价一次

📊 查看评价统计：
输入 @teacher_name 即可看到该教师的：
• 总评价数
• 推荐/不推荐比例
• 最新的评价内容
• 评价时间

💡 使用建议：
✅ 真实评价 - 帮助其他同学
✅ 具体内容 - 说明优缺点
✅ 尊重他人 - 文明评价
✅ 客观态度 - 不夸大不贬低

⚠️ 注意事项：
• 每个用户对同一个教师只能评价一次
• 评价内容应该基于真实体验
• 避免人身攻击或侮辱性语言
• 机器人会记录所有评价

❓ 常见问题：

Q: 可以修改已经提交的评价吗？
A: 当前版本不支持修改，但可以联系管理员。

Q: 为什么看不到我的评价？
A: 评价提交后会立即显示，检查是否输入了正确的教师名称。

Q: 如何举报不文明的评价？
A: 联系管理员，提供评价的教师名称和时间。

Q: 可以用匿名账号评价吗？
A: 可以的，但机器人会记录用户ID用于反作弊。

Q: 评价会被删除吗？
A: 管理员有权删除违规评价。

📞 获取帮助：
• 查看这个帮助文档: /帮助
• 联系管理员获取更多帮助
• 在群组中使用 @teacher_name 测试"""
    
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
    
    # 提取 @username
    pattern = r'@([a-zA-Z0-9_\u4e00-\u9fff]+)'
    matches = re.findall(pattern, message.text)
    
    if not matches:
        return
    
    teacher_name = matches[0]
    user_id = message.from_user.id
    
    logger.info(f"👤 用户 {user_id} 查询教师 @{teacher_name}")
    
    try:
        stats = get_teacher_stats(teacher_name)
        teacher_info = get_teacher_info(teacher_name)
        
        nickname = teacher_info.get("nickname", "")
        tid = teacher_info.get("teacher_id", "")
        
        # 构建教师信息头部
        header = f"👨‍🏫 @{teacher_name}"
        if nickname:
            header += f"\n📛 昵称：{nickname}"
        if tid:
            header += f"\n🆔 ID：{tid}"
        
        if stats["total"] == 0:
            display_text = (
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{header}\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"📭 暂无评价记录\n\n"
                f"快来成为第一个评价的人吧！"
            )
        else:
            recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
            not_rec_pct = 100 - recommend_percentage
            
            display_text = (
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{header}\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 评价统计：\n"
                f"👍 推荐：{stats['recommend']} 人（{recommend_percentage}%）\n"
                f"👎 不推荐：{stats['not_recommend']} 人（{not_rec_pct}%）\n"
                f"📈 共 {stats['total']} 条评价\n"
            )
            
            # latest 字段顺序: id(0), user_id(1), recommend(2), reason(3), time(4)
            if stats["latest"]:
                display_text += f"\n━━━━━━━━━━━━━━━━━━━\n📝 最新评价（最多显示 {MAX_INLINE_REVIEWS} 条）：\n\n"
                for i, review in enumerate(stats["latest"][:MAX_INLINE_REVIEWS], 1):
                    rec_emoji = "👍" if review[2] else "👎"
                    reason = review[3]
                    display_text += f"{i}. {rec_emoji} [#{review[0]}]\n"
                    display_text += f"   💬 {reason[:50]}{'...' if len(reason) > 50 else ''}\n\n"
                display_text += "━━━━━━━━━━━━━━━━━━━"
        
        # 构建按钮
        action_row = [
            InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher_name}"),
            InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher_name}")
        ]
        kb_rows = [action_row]
        
        # 如果评价数超过 MAX_INLINE_REVIEWS 条，添加"更多评价"按钮
        if stats["total"] > MAX_INLINE_REVIEWS:
            remaining = stats["total"] - MAX_INLINE_REVIEWS
            kb_rows.append([
                InlineKeyboardButton(
                    text=f"📋 查看更多评价（{remaining} 条）",
                    callback_data=f"more_reviews|{teacher_name}|0"
                )
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        
        await message.reply(display_text, reply_markup=kb)
        logger.info(f"✅ 显示 @{teacher_name} 的评价信息")
        
    except Exception as e:
        logger.error(f"处理教师提及时出错: {e}", exc_info=True)
        await message.reply(f"❌ 出错: {str(e)}")

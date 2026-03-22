# handlers/private.py
"""
私聊处理模块
包含: /start, /help, /myid 命令，以及 @teacher_name 群组处理
"""

import logging
import re
from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import (
    get_start_message,
    get_all_required_channels,
    get_teacher_stats,
    get_leaderboard
)
from states import RatingStates
from bot_instance import bot, get_channel_invite_link
from utils.helpers import format_leaderboard_text

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start", "开始"))
async def cmd_start(message: Message):
    """处理 /start 或 /开始 命令"""
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    channels = get_all_required_channels()
    
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
                    f"""⚠️ 您需要加入所有频道才能使用此机器人

📊 需要加入 {len(not_subscribed)} 个频道

🔗 请点击下方按钮加入""",
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
                "🔗 请确保��加入所有频道后重新验证",
                reply_markup=kb
            )
            return

    # 用户已订阅或未设置频道要求
    welcome = get_start_message(
        """👋 欢迎使用狼评机器人！🎓

这是一个教师评价平台，帮助同学们了解教师的教学情况。

📝 使用方法:
在群组中输入 @teacher_name 来查询或评价教师

例如: @李老师、@王教授、@张老师

💡 更多帮助请输入 /帮助"""
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 查看帮助", callback_data="show_help")],
        [InlineKeyboardButton(text="⭐ 如何评价", callback_data="how_to_rate")],
        [InlineKeyboardButton(text="🏆 教师排行榜", callback_data="show_leaderboard")],
        [InlineKeyboardButton(text="❓ 常见问题", callback_data="faq")]
    ])
    
    await message.reply(welcome, reply_markup=kb)


@router.message(Command("help", "帮助"))
async def cmd_help(message: Message):
    """处理 /help 或 /帮助 命令"""
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
        
        if stats["total"] == 0:
            display_text = f"""【@{teacher_name}】
暂无评价记录
快来成为第一个评价的人吧！"""
        else:
            recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
            
            display_text = f"""【@{teacher_name}】
📊 评价统计：
👍 推荐: {stats['recommend']} 人 ({recommend_percentage}%)
👎 不推荐: {stats['not_recommend']} 人 ({100-recommend_percentage}%)

📈 总评价数: {stats['total']}"""
            
            # latest 字段顺序: id(0), user_id(1), recommend(2), reason(3), time(4)
            if stats["latest"]:
                display_text += "\n\n📝 最新评价："
                for i, review in enumerate(stats["latest"][:2], 1):
                    rec_emoji = "👍" if review[2] else "👎"
                    display_text += f"\n{i}. {rec_emoji} [#{review[0]}] {review[3][:40]}..."
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher_name}"),
                InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher_name}")
            ]
        ])
        
        await message.reply(display_text, reply_markup=kb)
        logger.info(f"✅ 显示 @{teacher_name} 的评价信息")
        
    except Exception as e:
        logger.error(f"处理教师提及时出错: {e}", exc_info=True)
        await message.reply(f"❌ 出错: {str(e)}")
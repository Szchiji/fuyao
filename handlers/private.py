# handlers/private.py
"""
私聊处理模块
包含: /start, /help, /myid 命令
"""

import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_LINK
from database import get_start_message, get_required_channel
from bot_instance import bot

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """处理 /start 命令"""
    if message.chat.type != "private":
        return

    required = get_required_channel()
    user_id = message.from_user.id
    
    logger.info(f"用户 {user_id} 启动机器人，频道要求: {required}")
    
    if required:
        try:
            # 检查用户是否是频道成员
            member = await bot.get_chat_member(required, user_id)
            logger.info(f"用户 {user_id} 在频道 {required} 的状态: {member.status}")
            
            # 检查成员状态
            if member.status in ('left', 'kicked', 'restricted'):
                logger.warning(f"用户 {user_id} 未订阅频道 {required}")
                
                # 创建多个按钮
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📢 加入频道",
                        url=CHANNEL_LINK
                    )],
                    [InlineKeyboardButton(
                        text="❓ 频道介绍",
                        callback_data="channel_info"
                    )],
                    [InlineKeyboardButton(
                        text="💬 联系管理员",
                        callback_data="contact_admin"
                    )]
                ])
                
                await message.reply(
                    "⚠️ 您需要先加入我们的频道才能使用此机器人\n\n"
                    "🔗 请点击下方按钮加入频道，加入后就可以使用所有功能了！",
                    reply_markup=kb
                )
                return
            
            logger.info(f"用户 {user_id} 已订阅频道")
        
        except Exception as e:
            logger.error(f"检查频道成员时出错: {e}")
            
            # 如果检查失败，拒绝访问
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📢 加入频道",
                    url=CHANNEL_LINK
                )],
                [InlineKeyboardButton(
                    text="🔄 重新验证",
                    callback_data="retry_verify"
                )]
            ])
            
            await message.reply(
                "⚠️ 无法验证您的订阅状态\n\n"
                "🔗 请确保已加入频道后再使用此机器人",
                reply_markup=kb
            )
            return

    # 用户已订阅或未设置频道要求
    welcome = get_start_message(
        "👋 欢迎使用狼评机器人！🎓\n\n"
        "这是一个教师评价平台，帮助同学们了解教师的教学情况。\n\n"
        "📝 使用方法:\n"
        "在群组中输入 @teacher_name 来查询或评价教师\n\n"
        "例如: @李老师、@王教授、@张老师\n\n"
        "💡 更多帮助请输入 /help"
    )
    
    # 添加快捷按钮
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📖 查看帮助",
            callback_data="show_help"
        )],
        [InlineKeyboardButton(
            text="⭐ 如何评价",
            callback_data="how_to_rate"
        )],
        [InlineKeyboardButton(
            text="❓ 常见问题",
            callback_data="faq"
        )]
    ])
    
    await message.reply(welcome, reply_markup=kb)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """处理 /help 命令"""
    help_text = """📖 完整帮助文档

👥 用户命令：
• /start - 启动机器人
• /help - 获取帮助
• /myid - 获取您的用户ID

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
• 查看这个帮助文档: /help
• 联系管理员获取更多帮助
• 在群组中使用 @teacher_name 测试"""
    
    await message.reply(help_text)


@router.message(Command("myid"))
async def get_my_id(message: Message):
    """获取用户ID - 任何人都可以使用"""
    user_id = message.from_user.id
    username = message.from_user.username or "无"
    first_name = message.from_user.first_name or "用户"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📖 查看帮助",
            callback_data="show_help"
        )],
        [InlineKeyboardButton(
            text="🔙 返回主菜单",
            callback_data="back_to_start"
        )]
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
   • /admin - 管理后台
   • /setchannel - 设置频道
   • /stats - 查看统计
   • 等更多管理员命令

💡 管理员权限:
✅ 查看统计数据
✅ 设置频道验证
✅ 自定义欢迎语
✅ 诊断系统问题
✅ 查看数据库信息""", reply_markup=kb)
# 在 handlers/private.py 中添加

from aiogram.filters import Regexp
from states import RatingStates

# 群组消息处理 - 检测 @teacher_name 并启动评价流程
@router.message(Regexp(r'^@(\w+)$'))
async def handle_teacher_mention(message: Message, state: FSMContext):
    """处理 @teacher_name 提及"""
    if message.chat.type == "private":
        # 私聊中也支持直接输入
        pass
    
    # 提取教师名称
    teacher_name = message.text[1:]  # 去掉 @
    
    # 获取教师统计
    stats = get_teacher_stats(teacher_name)
    
    if stats["total"] == 0:
        # 暂无评价
        display_text = f"""【@{teacher_name}】
暂无评价记录
快来成为第一个评价的人吧！"""
    else:
        # 显示现有评价
        recommend_percentage = int((stats["recommend"] / stats["total"]) * 100) if stats["total"] > 0 else 0
        
        display_text = f"""【@{teacher_name}】
评价统计：
👍 推荐: {stats['recommend']} 人 ({recommend_percentage}%)
👎 不推荐: {stats['not_recommend']} 人 ({100-recommend_percentage}%)
总评价数: {stats['total']}"""
    
    # 创建评价按钮
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 推荐", callback_data=f"rec|1|{teacher_name}")],
        [InlineKeyboardButton(text="👎 不推荐", callback_data=f"rec|0|{teacher_name}")]
    ])
    
    await message.reply(display_text, reply_markup=kb)
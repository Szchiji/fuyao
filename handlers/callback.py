# 在 handlers/callback.py 中修改频道介绍部分

# 处理频道介绍
if data == "channel_info":
    from bot_instance import get_channel_invite_link
    from database import get_required_channel
    
    channel_id = get_required_channel()
    
    info_text = """📢 频道介绍

这是一个教师评价平台，帮助同学们：
✅ 了解教师的教学风格
✅ 参考其他同学的评价
✅ 做出选课决定
✅ 互相分享学习体验

🎯 频道内容：
• 热门教师排行榜
• 评价统计分析
• 用户反馈和建议

🔗 加入频道获得：
• 实时评价更新
• 教师排行榜
• 社区讨论

点击下方按钮加入频道："""
    
    # 自动获取频道链接
    channel_link = await get_channel_invite_link(channel_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 立即加入频道",
            url=channel_link if channel_link else "https://t.me"
        )],
        [InlineKeyboardButton(
            text="🔙 返回",
            callback_data="back_to_start"
        )]
    ])
    
    await callback.answer()
    await bot.send_message(callback.from_user.id, info_text, reply_markup=kb)
    return
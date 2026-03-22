# handlers/callback.py - 评价部分完整修复

@router.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    """处理所有回调查询"""
    try:
        data = callback.data
        
        # 处理推荐/不推荐
        if data.startswith("rec|"):
            parts = data.split("|")
            if len(parts) < 3:
                await callback.answer("❌ 数据错误")
                return
            
            rec_str = parts[1]
            teacher = "|".join(parts[2:])  # 教师名称可能包含 |
            
            try:
                recommend = int(rec_str)
            except ValueError:
                await callback.answer("❌ 数据错误")
                return
            
            user_id = callback.from_user.id
            
            # 检查是否已评价
            from database import check_user_rated_teacher
            if check_user_rated_teacher(teacher, user_id):
                await callback.answer("❌ 您已经评价过这位教师了", show_alert=True)
                return
            
            # 保存状态
            await state.update_data(
                teacher=teacher,
                recommend=recommend,
                user_id=user_id
            )
            await state.set_state(RatingStates.waiting_reason)
            
            # 发送提示
            await callback.answer()
            await bot.send_message(
                callback.from_user.id,
                f"您选择了 {'👍 推荐' if recommend else '👎 不推荐'} @{teacher}\n\n"
                f"请在下方填写您的评价理由（至少 12 字）："
            )
            return
        
        # ... 其他回调处理 ...

    except Exception as e:
        logger.error(f"处理回调时出错: {e}")
        await callback.answer(f"❌ 出错: {str(e)}", show_alert=True)
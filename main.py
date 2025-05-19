import re
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.platform import AstrBotMessage
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.provider import LLMResponse
from openai.types.chat.chat_completion import ChatCompletion
import traceback

@register("error_notice", "DragonEmpery", "屏蔽机器人的错误信息回复，并发送给管理员。", "1.0.3")
class ErrorFilter(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.Iserror_notice = self.config.get('Iserror_notice', True)
        # 管理员列表
        self.admins_id: list = context.get_config().get("admins_id", [])

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        result = event.get_result()
        if not result:  # 检查结果是否存在
            return

        message_str = result.get_plain_text()
        if self.Iserror_notice and message_str:  # 确保message_str不为空
            # 错误关键词检测
            error_keywords = ['请求失败', '错误类型', '错误信息', '调用失败', '处理失败', '描述失败', '获取模型列表失败']
            if any(keyword in message_str for keyword in error_keywords):
                # 获取事件信息
                chat_type = "未知类型"
                chat_id = "未知ID"
                user_name = "未知用户"
                platform_name = "未知平台"
                group_name = "未知群聊"  # 初始化群聊名称

                try:  # Catch potential exceptions during event object processing
                    if event.message_obj:
                        if event.message_obj.group_id:
                            chat_type = "群聊"
                            chat_id = event.message_obj.group_id

                            # 尝试获取群聊名称
                            try:
                                # 使用 event.bot.get_group_info 获取群组信息
                                group_info = await event.bot.get_group_info(group_id=chat_id)

                                # 假设群信息对象里有 group_name 属性
                                group_name = group_info.get('group_name', "获取群名失败") if group_info else "获取群名失败"

                            except Exception as e:
                                logger.error(f"获取群名失败: {e}")
                                logger.error(traceback.format_exc()) # 打印完整的 traceback
                                group_name = "获取群名失败"  # 设置为错误提示
                        else:
                            chat_type = "私聊"
                            chat_id = event.message_obj.sender.user_id

                        user_name = event.get_sender_name()
                        platform_name = event.get_platform_name()  # 获取平台名称
                    else:
                        logger.warning("event.message_obj is None. Could not get chat details")

                except Exception as e:
                    logger.error(f"Error while processing event information: {e}")
                    formatted_traceback = traceback.format_exc()  # Capture traceback locally if any error occurs

                # 给管理员发通知
                try: #Catch exceptions while sending message to admin.
                    for admin_id in self.admins_id:
                        if str(admin_id).isdigit():  # 管理员QQ号
                            # Capture traceback information
                            formatted_traceback = traceback.format_exc()

                            # Limit traceback length to prevent message from being too long. You can adjust the limit as needed.
                            max_traceback_length = 2000
                            if len(formatted_traceback) > max_traceback_length:
                                formatted_traceback = formatted_traceback[:max_traceback_length] + "\n... (Traceback truncated)"

                            # Include group_name in the message
                            await event.bot.send_private_msg(
                                user_id=int(admin_id),
                                message=f"主人，我在群聊 {group_name}（{chat_id}） 中和 [{user_name}] 聊天出现错误了: {message_str}" if chat_type == "群聊" else f"主人，我在和 {user_name}（{chat_id}） 私聊时出现错误了: {message_str}"
                            )
                except Exception as e:
                     logger.error(f"Error while sending message to admin: {e}")

                logger.info(f"拦截错误消息: {message_str}")
                event.stop_event()  # 停止事件传播
                event.set_result(None)  # 清除结果
                return  # 确保后续处理不会执行

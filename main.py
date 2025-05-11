import re
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.platform import AstrBotMessage
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.provider import LLMResponse
from openai.types.chat.chat_completion import ChatCompletion

@register("error_notice", "DragonEmpery", "屏蔽机器人的错误信息回复，并发送给管理员。", "1.0.0")
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
            error_keywords = ['请求失败', '错误类型', '错误信息']
            if any(keyword in message_str for keyword in error_keywords):
                # 给管理员发通知
                for admin_id in self.admins_id:
                    if str(admin_id).isdigit():  # 管理员QQ号
                        await event.bot.send_private_msg(
                            user_id=int(admin_id),
                            message=f"主人，我出现错误了：{message_str}"  # 发送原始错误内容
                        )

                logger.info(f"拦截错误消息: {message_str}")
                event.stop_event()  # 停止事件传播
                event.set_result(None)  # 清除结果
                return  # 确保后续处理不会执行

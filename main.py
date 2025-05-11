import re
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.platform import AstrBotMessage
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.provider import LLMResponse
from openai.types.chat.chat_completion import ChatCompletion

@register("error_filter", "LuffyLSX", "屏蔽机器人的错误信息回复。", "1.0.0")
class ErrorFilter(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
        self.IsError_filter = self.config.get('IsError_filter', True)
        # 管理员列表
        self.admins_id: list = context.get_config().get("admins_id", [])

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        result = event.get_result()
        if not result:  # 检查结果是否存在
            return

        message_str = result.get_plain_text()
        if self.IsError_filter and message_str:  # 确保message_str不为空
            # 扩展错误关键词检测
            error_keywords = ['请求失败', '出错', '错误', '失败', '无法完成']
            if any(keyword in message_str for keyword in error_keywords):
                # 给管理员发通知（新增的核心代码）
                for admin_id in self.admins_id:
                    if str(admin_id).isdigit():  # 确保是合法QQ号
                        await event.bot.send_private_msg(
                            user_id=int(admin_id),
                            message=f"机器人出现错误：{message_str}"  # 发送原始                                                                       错误内容
                        )

                logger.info(f"拦截错误消息: {message_str}")
                event.stop_event()  # 停止事件传播
                event.set_result(None)  # 清除结果
                return  # 确保后续处理不会执行

import re
import astrbot.core.message.components as Comp
from astrbot.core.message.message_event_result import MessageChain
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
        # 通知目标列表
        self.target_umos: list[str] = []
        target_umo_config = self.config.get("target_umo")
        if isinstance(target_umo_config, list) and target_umo_config:
            self.target_umos = target_umo_config
        else:
            logger.error("Error Notice: 配置中的 'target_umo' 不是一个有效的列表或为空，插件将无法发送错误通知。")

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
                if not self.target_umos:
                    logger.warning("Error Notice: 未配置 'target_umo'，无法发送错误通知。")
                    return
                
                try:
                    # 捕获并格式化 traceback
                    formatted_traceback = traceback.format_exc()
                    max_traceback_length = 2000
                    if len(formatted_traceback) > max_traceback_length:
                        formatted_traceback = formatted_traceback[:max_traceback_length] + "\n... (Traceback truncated)"

                    # 构建消息
                    base_message = f"主人，我在群聊 {group_name}（{chat_id}） 中和 [{user_name}] 聊天出现错误了: {message_str}" if chat_type == "群聊" else f"主人，我在和 {user_name}（{chat_id}） 私聊时出现错误了: {message_str}"
                    full_message = f"{base_message}\n\n{formatted_traceback}"
                    
                    chain = MessageChain(chain=[Comp.Plain(full_message)])

                    # 发送给所有目标
                    for umo in self.target_umos:
                        try:
                            await self.context.send_message(umo, chain)
                            logger.info(f"Error Notice: 错误通知已发送至 {umo}")
                        except Exception as send_error:
                            logger.error(f"Error Notice: 错误通知发送至 {umo} 失败: {send_error}", exc_info=True)
                except Exception as e:
                     logger.error(f"Error Notice: 发送错误通知时发生未知错误: {e}", exc_info=True)

                logger.info(f"拦截错误消息: {message_str}")
                event.stop_event()  # 停止事件传播
                event.set_result(None)  # 清除结果
                return  # 确保后续处理不会执行

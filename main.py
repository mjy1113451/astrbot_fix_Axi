# main.py
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.message_components import Reply
from astrbot.api import logger

class FixQuoteTimestampPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.on_decorating_result()
    async def fix_quote_id(self, event: AstrMessageEvent):
        """
        在消息发送前修正引用组件的 id。
        将 LLM 生成的 "msg<正数ID>" 格式还原为原始的负数字符串。
        """
        result = event.get_result()
        if not result or not result.chain:
            return

        for comp in result.chain:
            if not isinstance(comp, Reply):
                continue

            original_id = comp.id
            # 匹配 "msg" 后跟数字的格式，例如 "msg688014524"
            if isinstance(original_id, str) and original_id.startswith("msg"):
                try:
                    numeric_part = original_id[3:]  # 去掉 "msg"
                    # 还原为负数 ID
                    fixed_id = f"-{numeric_part}"
                    comp.id = fixed_id
                    logger.debug(
                        f"[FixQuote] 修正引用 ID: {original_id} -> {fixed_id}"
                    )
                except (ValueError, IndexError):
                    logger.warning(
                        f"[FixQuote] 无法解析引用 ID: {original_id}，将移除该引用"
                    )
                    result.chain.remove(comp)
# main.py
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.message_components import Reply, At
from astrbot.api import logger


class FixQuoteAndMentionPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # ============ 功能一：@ 非 bot 不回复（仅在 on_llm_request 兜底） ============

    def _is_at_only_others(self, event: AstrMessageEvent) -> bool:
        """
        判断消息是否「只 @ 了别人（不是 bot / 不是 @all）」。
        若消息中没有 @ 组件，返回 False（不属于"@别人"场景）。
        """
        message_obj = getattr(event, "message_obj", None)
        if not message_obj:
            return False

        chain = getattr(message_obj, "message", None) or []
        at_list = [c for c in chain if isinstance(c, At)]
        if not at_list:
            return False  # 没有 @ 任何人

        self_id = str(getattr(message_obj, "self_id", "") or "")

        for at in at_list:
            at_qq = str(getattr(at, "qq", "") or "").lower()
            # @全体成员 或 @bot 自身 => 视为正常需要回复
            if at_qq == "all" or (self_id and at_qq == self_id):
                return False
        # 存在 @ 组件，且没有任何一个指向 bot / all
        return True

    @filter.on_llm_request()
    async def block_at_others_llm(self, event: AstrMessageEvent):
        """
        在 LLM 请求前兜底拦截：仅 @ 非 bot 用户时停止事件，
        防止 enhance_mode 等主动回复插件绕过前端唤醒检查。
        """
        if self._is_at_only_others(event):
            logger.debug(
                "[FixQuote] on_llm_request: 仅 @ 非 bot 用户，停止事件"
            )
            event.stop_event()

    # ============ 功能二：修复 1970 引用 ============

    @filter.on_decorating_result()
    async def fix_quote_id(self, event: AstrMessageEvent):
        """
        在消息发送前修正引用组件的 id。
        将 LLM 生成的 "msg<正数ID>" 格式还原为原始的负数字符串。
        """
        result = event.get_result()
        if not result or not result.chain:
            return

        for comp in list(result.chain):
            if not isinstance(comp, Reply):
                continue

            original_id = comp.id
            if isinstance(original_id, str) and original_id.startswith("msg"):
                try:
                    fixed_id = f"-{original_id[3:]}"
                    comp.id = fixed_id
                    logger.debug(
                        f"[FixQuote] 修正引用 ID: {original_id} -> {fixed_id}"
                    )
                except Exception:
                    logger.warning(
                        f"[FixQuote] 无法解析引用 ID: {original_id}，移除该引用"
                    )
                    result.chain.remove(comp)
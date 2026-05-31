from aiogram.filters import BaseFilter, Filter
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.repositories import get_user_by_id

class I18nTextFilter(BaseFilter):
    def __init__(self, key: str):
        self.key = key

    async def __call__(self, message: Message) -> bool:
        return message.text == _(self.key)


class IsProUserFilter(Filter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        user = await get_user_by_id(session, message.from_user.id)
        return user is not None and user.subscription_type == "pro"
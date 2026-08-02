from aiogram.filters import BaseFilter, Filter
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession

from financial_bot.repositories import get_user_by_id


# class I18nTextFilter(BaseFilter):
#     def __init__(self, key: str):
#         self.key = key
#
#     async def __call__(self, message: Message) -> bool:
#         return message.text == _(self.key)


class IsProUserFilter(Filter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:

        if not message.from_user:
            return False

        user = await get_user_by_id(session, message.from_user.id)
        return user is not None and user.subscription_type == "pro"


class DeleteTransactionCallback(CallbackData, prefix="del_tx"):
    batch_id: str


class I18nTextFilter(BaseFilter):
    def __init__(self, *keys: str):

        self.keys = keys

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False


        translated_values = {_(key) for key in self.keys}
        return message.text in translated_values
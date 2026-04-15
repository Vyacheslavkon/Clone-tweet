from aiogram.types import Message
from aiogram_i18n import I18nContext
from aiogram.filters import BaseFilter
from aiogram.utils.i18n import gettext as _


class I18nTextFilter(BaseFilter):
    def __init__(self, key: str):
        self.key = key


    async def __call__(self, message: Message) -> bool:
        return message.text == _(self.key)
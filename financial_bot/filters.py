from aiogram.types import Message
from aiogram_i18n import I18nContext
from aiogram.filters import BaseFilter



class I18nTextFilter(BaseFilter):
    def __init__(self, key: str):
        self.key = key

    async def __call__(self, message: Message, i18n: I18nContext) -> bool:

        return message.text == i18n.gettext(self.key)
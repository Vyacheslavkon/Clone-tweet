from aiogram import Router
from aiogram.types import Message

router_fallback = Router()

@router_fallback.message()
async def any_unhandled_event(message: Message):
    await message.reply("Sorry, I didn't understand you, please use the suggested choice!")

# import asyncio
#
# from core.celery_app import app
# from core.database import async_session
#
# from .repositories import create_user

# @app.task
# def top_up_balance_task(user_id: int, amount: float):
# Celery обычно синхронный, для Async SQLAlchemy нужен мост:
# loop = asyncio.get_event_loop()
#
# async def run():
#     async with async_session() as session:
#         await update_balance(session, user_id, amount)
#
# loop.run_until_complete(run())

import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import CallbackQuery, Chat, Message, TelegramObject, Update, User
from aiogram.utils.i18n import I18n, I18nMiddleware

from financial_bot.handlers.adding_data import router_data
from financial_bot.handlers.common import router
from financial_bot.handlers.history import history_rout
from financial_bot.handlers.reports import report_rout
from financial_bot.handlers.transactions import router_tr
from financial_bot.middlewares import SessionMiddleware
from financial_bot.repositories import (
    add_data_for_user,
    add_transaction,
    create_user,
)
from financial_bot.schemas import AddData, CreateUser
from services.analysis_cache import FinancialCacheService
from services.client import ai_service
from services.schemas import (
    ReceiptAnalysisSchema,
    ReceiptItemSchema,
    ReceiptListAnalysisSchema,
)
from services.celery_app import app as celery_app

current_file_path = Path(__file__).resolve()
base_dir = current_file_path.parent.parent.parent
locales_path = base_dir / "financial_bot" / "locales"


@pytest.fixture
def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.id = 12345678

    bot.get_me = AsyncMock(
        return_value=User(
            id=12345678, is_bot=True, first_name="TestBot", username="test_bot"
        )
    )
    return bot


@pytest.fixture
async def test_user(test_session):
    data = {"tg_id": 12345, "language_code": "ru", "first_name": "TestUser"}

    new_user = CreateUser(**data)

    user_db_obj = await create_user(test_session, new_user)
    await test_session.flush()
    await test_session.refresh(user_db_obj)

    return user_db_obj


@pytest.fixture
async def user_for_pipeline(test_session_for_pipeline):

    user_data = CreateUser(tg_id=12345, language_code="ru", first_name="TestUser")
    db_user = await create_user(test_session_for_pipeline, user_data)
    await test_session_for_pipeline.flush()

    return db_user


@pytest.fixture
async def fake_analysis():
    fake_item = ReceiptItemSchema(name="Кофе", price=250.0)
    fake_tx = ReceiptAnalysisSchema(
        amount=250.0,
        category="food",
        type="expense",
        description="кофейня",
        items=[fake_item],
    )

    return ReceiptListAnalysisSchema(
        is_shopping_related=True, transactions=[fake_tx], error_message=None
    )


@pytest.fixture
async def test_data(test_session, test_user):
    add_data = {
        "savings_goal": 10000,
        "monthly_budget": 30000,
        "budget_remind_percent": 20,
    }

    new_obg = AddData(**add_data)

    await add_data_for_user(test_session, new_obg, test_user.tg_id)
    await test_session.flush()
    return new_obg


@pytest.fixture
async def test_transaction(test_session, test_user):

    data = {
        "user_id": test_user.id,
        "amount": 300,
        "type": "expense",
        "category": "food",
        "description": "coffee",
    }

    await add_transaction(test_session, data)


class MyI18nMiddleware(I18nMiddleware):
    async def get_locale(self, event: TelegramObject, data: Dict[str, Any]) -> str:
        # В тестах проще всего возвращать дефолтную локаль
        # Или можно достать из event.from_user.language_code
        return self.i18n.default_locale


@pytest.fixture
def test_i18n():
    """Отдельная фикстура для объекта I18n"""
    return I18n(path="financial_bot/locales", default_locale="en", domain="messages")


@pytest.fixture
async def test_dp(test_session, test_redis, test_i18n, cache_service):
    # add cache_service
    storage = RedisStorage(redis=test_redis)
    dp = Dispatcher(storage=storage)
    dp["cache_service"] = cache_service
    i18n_middleware = MyI18nMiddleware(i18n=test_i18n)
    dp.update.outer_middleware(i18n_middleware)

    dp.update.middleware(SessionMiddleware(session_pool=test_session))

    for r in [router, router_tr, router_data, report_rout, history_rout]:
        if r is not None:

            new_router = copy.deepcopy(r)
            dp.include_router(new_router)
        else:
            raise ValueError(
                "One of the routers (router или router_tr) "
                "is not imported or is equal None"
            )

    return dp


@pytest.fixture
def create_mock_update(mock_bot):
    def _create_message(text: str, user_id: int, update_id: int):

        message = Message(
            message_id=1,
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=User(
                id=user_id, is_bot=False, first_name="TestUser", language_code="ru"
            ),
            text=text,
            bot=mock_bot,
        )
        return Update(update_id=update_id, message=message)

    def _create_callback(data: str, user_id: int, update_id: int):
        message = Message(
            message_id=2,
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            text="Кнопки",
            bot=mock_bot,
        )
        callback_query = CallbackQuery(
            id="123",
            from_user=User(
                id=user_id, is_bot=False, first_name="TestUser", language_code="ru"
            ),
            data=data,
            chat_instance="abc",
            message=message,
            bot=mock_bot,
        )
        return Update(update_id=update_id, callback_query=callback_query)

    return _create_message, _create_callback


@pytest.fixture
async def budget(test_session, test_user):

    new_obg = AddData(monthly_budget="2000")

    await add_data_for_user(test_session, new_obg, test_user.tg_id)

    return new_obg


@pytest.fixture
def mock_ai_service(mocker):
    mock_method = AsyncMock()

    mocker.patch.object(ai_service, "process_voice_message", mock_method)

    # Возвращаем сам мок-метод в тест
    return mock_method


@pytest.fixture(autouse=True)
def patch_pipeline_dependencies(mocker, test_session_for_pipeline, mock_bot):

    original_close = test_session_for_pipeline.close
    original_rollback = test_session_for_pipeline.rollback

    test_session_for_pipeline.close = AsyncMock()
    test_session_for_pipeline.rollback = AsyncMock()

    mocker.patch(
        "services.pipelines.get_isolated_session",
        return_value=test_session_for_pipeline,
    )

    mocker.patch("financial_bot.highload_bot.get_shared_bot", return_value=mock_bot)  # maybe bot

    yield test_session_for_pipeline

    test_session_for_pipeline.close = original_close
    test_session_for_pipeline.rollback = original_rollback


@pytest.fixture
async def data_transaction_ai(test_session_for_pipeline):

    return ReceiptListAnalysisSchema(
        is_shopping_related=True,
        error_message=None,
        transactions=[
            ReceiptAnalysisSchema(
                type="expense",
                category="food",
                amount=250.0,
                description="food",
                items=[
                    ReceiptItemSchema(name="Молоко", price=150.0),
                    ReceiptItemSchema(name="Хлеб", price=100.0),
                ],
            )
        ],
    )


@pytest.fixture
async def data_for_merge_by_cat():
    return ReceiptListAnalysisSchema(
        is_shopping_related=True,
        error_message=None,
        transactions=[
            ReceiptAnalysisSchema(
                type="expense",
                category="food",
                amount=150.0,
                description="Супермаркет",
                items=[ReceiptItemSchema(name="Молоко", price=150.0)],
            ),
            ReceiptAnalysisSchema(
                type="expense",
                category="food",
                amount=50.0,
                description="Рынок",
                items=[ReceiptItemSchema(name="Хлеб", price=50.0)],
            ),
            ReceiptAnalysisSchema(
                type="expense",
                category="transport",
                amount=300.0,
                description="Такси",
                items=[],
            ),
        ],
    )


@pytest.fixture
def mock_redis_client():

    client = AsyncMock()
    pipeline_mock = AsyncMock()
    client.pipeline.return_value.__aenter__.return_value = pipeline_mock
    return client

@pytest.fixture
def cache_service(mock_redis_client):

    return FinancialCacheService(redis_client=mock_redis_client)


@pytest.fixture
def celery_eager():
    original = (celery_app.conf.task_always_eager, celery_app.conf.task_eager_propagates)
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager, celery_app.conf.task_eager_propagates = original
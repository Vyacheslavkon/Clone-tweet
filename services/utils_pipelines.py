import base64
import gettext
import io
import os
import re
from collections import defaultdict, Counter
from pathlib import Path
from typing import Callable, List

from aiogram import Bot
from loguru import logger

from dotenv import load_dotenv
from PIL import Image, ImageEnhance, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from services.schemas import ReceiptAnalysisSchema
from typing import List, Dict, Tuple
from services.schemas import ReceiptListAnalysisSchema

load_dotenv()

POSTGRES_ASYNC_URL = os.getenv("DATABASE_URL_DOCKER")



def merge_transactions_by_category(
    analysis_result: ReceiptListAnalysisSchema,
) -> ReceiptListAnalysisSchema:

    merged_map: dict[tuple[str, str], ReceiptAnalysisSchema] = {}

    for tx in analysis_result.transactions:
        key = (tx.type, tx.category)

        if key not in merged_map:

            merged_map[key] = ReceiptAnalysisSchema(
                type=tx.type,
                category=tx.category,
                amount=tx.amount,
                description=tx.description,
                items=list(tx.items),
            )
        else:

            merged_map[key].amount += tx.amount
            merged_map[key].items.extend(tx.items)

            if tx.description and tx.description != merged_map[key].description:
                current_desc = merged_map[key].description
                if current_desc:
                    merged_map[key].description = f"{current_desc}, {tx.description}"
                else:
                    merged_map[key].description = tx.description

    new_result = analysis_result.model_copy(deep=True)
    new_result.transactions = list(merged_map.values())
    return new_result

CATEGORY_TITLES: Dict[str, str] = {
        "food": "🍎 Еда",
        "home": "🏠 Дом/Аренда",
        "entertainment": "🎉 Развлечения",
        "transport": "🚗 Транспорт",
        "health": "💊 Здоровье",
        "other": "📦 Другое"
    }



def render_category_tree(
        cat_key: str,
        data: dict,
        _: Callable[[str], str],
        max_visible_items: int = 5
) -> List[str]:

    tree_lines = []

    system_keys_transactions = {
        "food": _("Food"),
        "health": _("Health"),
        "transport": _("Transport"),
        "entertainment": _("Entertainment"),
        "home": _("Home"),
        "other": _("Other")
    }

    category_items = []
    for item in data.get("top_items", []):
        if item["category"] == cat_key:
            name_raw = item["name"].strip()
            name_lower = name_raw.lower()

            if name_lower in system_keys_transactions:

                category_items.append(system_keys_transactions[name_lower])

            elif "system_category_" in name_lower:
                clean_key = name_lower.replace("system_category_", "")
                category_items.append(system_keys_transactions.get(clean_key, clean_key))

            else:

                category_items.append(name_raw)

    if not category_items:
        return tree_lines

    item_counts = Counter(category_items)
    all_unique_items = item_counts.most_common()

    visible_items = all_unique_items[:max_visible_items]
    for item_name, item_freq in visible_items:
        tree_lines.append(f"     └ {item_name} — {item_freq}")

    total_items_count = len(category_items)
    visible_items_count = sum(freq for _, freq in visible_items)
    hidden_items_count = total_items_count - visible_items_count

    if hidden_items_count > 0:
        tree_lines.append(_("     └ Other operations — {count}").format(count=hidden_items_count))

    return tree_lines


def render_monthly_tree(data: dict, _: Callable[[str], str]) -> List[str]:
    category_titles = {
        "food": _("Groceries and food"),
        "health": _("Health and Medicine"),
        "transport": _("Transport and Automotive"),
        "entertainment": _("Entertainment and leisure"),
        "home": _("Home and Household"),
        "other": _("Other expenses")
    }

    essential_categories = ["food", "health", "home"]
    discretionary_categories = ["transport", "entertainment", "other"]

    tree_lines = [_("\n🟢 <u>Necessary :</u>")]

    for cat_data in data.get("categories", []):
        cat_key = cat_data["category"]

        if cat_key in essential_categories:
            tree_lines.append(_(" • <b>{cat_name}</b> — <b>{count} transactions per month</b>").format(
                cat_name=category_titles.get(cat_key, cat_key).upper(),
                count=cat_data["count"]
            ))
            tree_lines.extend(render_category_tree(cat_key, data, _))

    tree_lines.append(_("\n🟡 <u>Secondary :</u>"))

    for cat_data in data.get("categories", []):
        cat_key = cat_data["category"]
        if cat_key in discretionary_categories:
            tree_lines.append(_(" • <b>{cat_name}</b> — <b>{count} transactions per month</b>").format(
                cat_name=category_titles.get(cat_key, cat_key).upper(),
                count=cat_data["count"]
            ))

            tree_lines.extend(render_category_tree(cat_key, data, _))

    return tree_lines


def format_weekly_block(
        items_list: list,
        _: Callable[[str], str],
        max_items: int
) -> List[str]:

    block_lines = []
    if not items_list:
        block_lines.append(_("   • No expenses for the period"))
        return block_lines

    counts = Counter(items_list)

    for name, freq in counts.most_common(max_items):
        block_lines.append(f"   • <b>{name}</b> — {freq} " + _("transaction(s)"))

    return block_lines


def render_weekly_top(
        data: dict,
        _: Callable[[str], str],
        max_items: int = 10
) -> List[str]:

    tree_lines = []


    essential_categories = {"food", "health", "home"}

    system_keys_transactions = {
        "food": _("Food"),
        "health": _("Health"),
        "transport": _("Transport"),
        "entertainment": _("Entertainment"),
        "home": _("Home"),
        "other": _("Other")
    }

    essential_items = []
    discretionary_items = []

    for item in data.get("top_items", []):
        cat_key = item.get("category", "other")
        name_raw = item["name"].strip()
        name_lower = name_raw.lower()


        if name_lower in system_keys_transactions:
            display_name = system_keys_transactions[name_lower]
        elif "system_category_" in name_lower:
            clean_key = name_lower.replace("system_category_", "")
            display_name = system_keys_transactions.get(clean_key, clean_key)
        else:
            display_name = name_raw


        if cat_key in essential_categories:
            essential_items.append(display_name)
        else:
            discretionary_items.append(display_name)


    tree_lines.append(_("\n🟢 <u>Necessary :</u>"))
    tree_lines.extend(format_weekly_block(essential_items, _, max_items))

    tree_lines.append(_("\n🟡 <u>Secondary :</u>"))
    tree_lines.extend(format_weekly_block(discretionary_items, _, max_items))

    return tree_lines


def render_detailed_transactions(data: dict, _: Callable[[str], str]) -> str:

    category_titles = {
        "food": _("Food"),
        "health": _("Health"),
        "transport": _("Transport"),
        "entertainment": _("Entertainment"),
        "home": _("Home"),
        "other": _("Other")
    }

    report_lines = [
        _("🧾 <b>Detailed Transaction History</b>\n"),
    ]


    raw_items = data.get("top_items", [])
    try:
        sorted_items = sorted(raw_items, key=lambda x: x.get("date", ""), reverse=True)
    except TypeError as type_err:

        logger.warning(
            "Failed to sort transactions by date due to mismatched types. "
            "Using fallback unsorted data. Error: %s", type_err
        )

        sorted_items = raw_items

    current_group_date = None
    currency = data.get("user_config", {}).get("currency", "RUB")

    for item in sorted_items:
        item_date = item.get("date", "")

        if item_date != current_group_date:
            current_group_date = item_date
            report_lines.append(f"\n📅 <b>{item_date}</b>")

        cat_key = item.get("category", "other")
        cat_title = category_titles.get(cat_key, cat_key)
        name_raw = item.get("name", "").strip()
        name_lower = name_raw.lower()


        if name_lower in category_titles or "system_category" in name_lower or "operation" in name_lower:

            display_name = f"✍️ {cat_title}"
        else:

            display_name = f"🛒 {name_raw} ({cat_title})"

        amount = item.get("total_amount", 0.0)

        report_lines.append(f"  • {display_name} — <b>{round(amount, 2)} {currency}</b>")

    if not sorted_items:
        report_lines.append(_("No transactions found for this period."))

    return "\n".join(report_lines)



def render_receipt_report(
        analysis_result: ReceiptListAnalysisSchema,
        _
) -> Tuple[str, str]:

    income_txs = [t for t in analysis_result.transactions if t.type == "income"]
    expense_txs = [t for t in analysis_result.transactions if t.type == "expense"]

    total_income = sum(t.amount for t in income_txs)
    total_expense = sum(t.amount for t in expense_txs)

    icons = {
        "food": "🍏",
        "transport": "🚗",
        "home": "🏠",
        "entertainment": "🎉",
        "health": "💊",
        "other": "📦",
        "salary": "💼",
        "bonus": "📈",
        "gift": "🎁",
        "deal": "🤝"
    }

    report_chunks = [_("✅ <b>Operations successfully recorded!</b>\n")]


    if income_txs:
        report_chunks.append(_("💰 <b>Received Income:</b>"))
        income_details = []
        for tx in income_txs:
            icon = icons.get(tx.category, "💵")
            localized_category = _(tx.description.capitalize() if tx.description else "Other")
            items_lines = [f"  • {item.name}: <b>{item.price}</b>" for item in tx.items]
            items_str = "\n" + "\n".join(items_lines) if items_lines else ""
            income_details.append(f"{icon} {localized_category}: <b>+{tx.amount}</b>{items_str}")
        report_chunks.append("\n".join(income_details))

    if income_txs and expense_txs:
        report_chunks.append(" ")


    if expense_txs:
        report_chunks.append(_("📉 <b>Spent Expenses:</b>"))
        expense_details = []
        for tx in expense_txs:
            icon = icons.get(tx.category, "📦")
            localized_category = _(tx.category.capitalize())
            items_lines = [
                f"  • {item.name}: <b>{item.price}</b>" if item.price > 0 else f"  • {item.name}"
                for item in tx.items
            ]
            items_str = "\n".join(items_lines)
            expense_details.append(_("{icon} {category}: <b>-{amount}</b>\n{items}").format(
                icon=icon, category=localized_category, amount=tx.amount, items=items_str
            ))
        report_chunks.append("\n".join(expense_details))


    report_chunks.append("\n" + "─" * 20)
    meta_lines = []
    if total_income > 0:
        meta_lines.append(_("Total Income: <b>+{total_amount}</b>").format(total_amount=total_income))
    if total_expense > 0:
        meta_lines.append(_("Total Expenses: <b>-{total_amount}</b>").format(total_amount=total_expense))
    report_chunks.append("\n".join(meta_lines))

    msg_text = "\n".join(report_chunks)


    if income_txs and not expense_txs:
        localized_button_label = _("❌ cancel income")
    elif expense_txs and not income_txs:
        localized_button_label = _("❌ cancel expense")
    else:
        localized_button_label = _("❌ cancel operation")

    return msg_text, localized_button_label



def get_translator(locale: str):
    locales_dir = Path(__file__).resolve().parent.parent / "financial_bot" / "locales"
    try:
        return gettext.translation(
            domain="messages", localedir=str(locales_dir),
            languages=[locale], fallback=True,
        ).gettext
    except Exception as e:
        logger.error("Failed to load localization: {error}", error=e)
        return gettext.NullTranslations().gettext


async def _reply(
    bot: Bot, chat_id: int, status_message_id: int | None,
    text: str, reply_markup=None,
) -> None:

    if status_message_id:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=status_message_id,
            text=text, reply_markup=reply_markup,
        )
    else:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def render_analysis_report(data: dict, analysis_result, days: int, _) -> str:
    currency = data.get("user_config", {}).get("currency", "руб.")

    lines = [
        _("📊 <b>Comprehensive financial analysis</b>\n"),
        _("💰 <b>Total Income:</b> {income} {curr}").format(income=data.get('total_income', 0.0), curr=currency),
        _("🛒 <b>Total Expense:</b> {expense} {curr}").format(expense=data.get('total_amount', 0.0), curr=currency),
        _("⚖️ <b>Net Balance:</b> {balance} {curr}\n").format(balance=data.get('net_balance', 0.0), curr=currency),
    ]

    budget_status = getattr(analysis_result, "budget_status", None) or getattr(analysis_result, "weekly_balance_status",
                                                                               None)
    if budget_status:
        lines.append(_("📈 <b>Budget status:</b> {status}").format(status=budget_status))

    budget_usage_percent = getattr(analysis_result, "budget_usage_percent", None)
    if budget_usage_percent is not None:
        lines.append(_("📊 <b>Budget used:</b> {percent}%\n").format(percent=round(budget_usage_percent, 1)))

    lines.append(f"{analysis_result.summary}\n")
    lines.append(_("🎯 <b>Categorizing top expenses by importance:</b>"))

    if days == 7:
        lines.extend(render_weekly_top(data, _))
    else:
        lines.extend(render_monthly_tree(data, _))

    if analysis_result.recommendations:
        lines.append(_("\n💡 <b>Optimization recommendations:</b>"))
        for i, rec in enumerate(analysis_result.recommendations, 1):
            if days == 7:
                lines.append(_("\n{num}. <b>{target}</b>\n└ {reason}\n└ <i>Possible savings: {saving}</i>").format(
                    num=i, target=getattr(rec, "target_item", _("Optimization")), reason=rec.reason,
                    saving=rec.potential_saving
                ))
            else:
                lines.append(
                    _("\n{num}. <b>{target}</b> — <b>{freq}</b>\n└ {reason}\n└ <i>Possible savings: {saving}</i>").format(
                        num=i, target=getattr(rec, "target_habit_pattern", _("Optimization")),
                        freq=getattr(rec, "frequency_metric", ""), reason=rec.reason, saving=rec.potential_saving
                    ))

    return "\n".join(lines)
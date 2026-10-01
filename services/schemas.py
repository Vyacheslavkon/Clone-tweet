from decimal import Decimal
from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReceiptItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(
        description="The cleaned name of the product or service (e.g., 'Milk 3.2% 1L')."
    )
    price: Decimal = Field(
        description="The final total cost of this specific position/item, taking all discounts into account."
    )


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    HOME = "home"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    OTHER = "other"


class IncomeCategory(str, Enum):
    SALARY = "salary"
    BONUS = "bonus"
    GIFT = "gift"
    DEAL = "deal"
    OTHER = "other"


class ReceiptAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: Optional[str] = Field(
        default=None,
        description="The name of the store, brand, or organization (e.g., 'Walmart', 'Uber')."
    )

    amount: Decimal = Field(
        description="The total monetary amount for the entire receipt."
    )

    category: str = Field(
        description="The category of the transaction. For 'expense', it must strictly be from the expense list; for 'income', strictly from the income list."
    )

    items: List[ReceiptItemSchema] = Field(
        default=[],
        description="A list of specific items/products. For generalized scenarios or income transactions, it contains exactly one element."
    )

    type: TransactionType = Field(
        description="The type of transaction: 'income' for earnings, 'expense' for expenditures."
    )

    @model_validator(mode="before")
    @classmethod
    def fix_and_validate_categories(cls, data: dict) -> dict:

        if not isinstance(data, dict):
            return data

        valid_expenses = {
            "food",
            "transport",
            "home",
            "entertainment",
            "health",
            "other",
        }
        valid_income = {"salary", "bonus", "gift", "deal", "other"}

        category = data.get("category")
        tx_type = data.get("type")

        if isinstance(category, str):
            cleaned_category = category.strip().lower()

            if tx_type == "income":
                if cleaned_category not in valid_income:
                    cleaned_category = "other"
            elif tx_type == "expense":
                if cleaned_category not in valid_expenses:
                    cleaned_category = "other"
            else:

                cleaned_category = "other"

            data["category"] = cleaned_category

        return data


class ReceiptListAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_shopping_related: bool = Field(
        description="True if the text contains at least one valid financial transaction (income or expense) with a specified amount/price. False in all other cases."
    )
    error_message: str | None = Field(
        default=None,
        description="If is_shopping_related=False or amount=0, write a short, ironic, or humorous response to the user in the user's native language.",
    )
    transactions: List[ReceiptAnalysisSchema] = Field(
        default=[],
        description="A list of financial transactions, strictly separated by their respective categories."
    )


class MonthlyAnalyzedCategory(BaseModel):
    name: str = Field(
        min_length=3,
        description=(
            "The high-level category name generated strictly in the user's language. "
            "INSTRUCTION: Scan the 'name' and 'category' fields in the raw data. "
            "If you see specific product tokens (like 'Toothpaste', 'T-shirt'), cluster them into narrow, "
            "accurate sub-categories (e.g., 'Hygiene & Cosmetics', 'Clothing & Shopping'). "
            "If you see only broad category tokens (like 'food', 'transport'), expand them into beautiful "
            "human-readable names (e.g., 'Groceries & Supermarkets', 'Transport & Auto'). "
            "Never use raw single product names as titles. Aim for a detailed layout."
        )
    )

    frequency_metric: str = Field(
        description="The aggregated indicator: 'X transactions per month' or 'Regularly (X times a week)' in the user's language."
    )
    expense_type: Literal["essential", "discretionary"] = Field(
        description="Strictly classify this specific category into 'essential' or 'discretionary' based on its current context."
    )

    items_breakdown: List[str] = Field(
        description="A list of specific transaction names or item descriptors from 'top_items' that formed this category. "
                    "For example, if name is 'Cafes & Fastfood', this list must contain items like ['McDonalds', 'KFC', 'Coffee']. "
                    "If the category was formed by manual entries without details, put the base category name here: ['Manual Entry Expenses']."
    )



class MonthlyCategoryRecommendation(BaseModel):
    target_habit_pattern: str = Field(
        description="The identified systemic behavioral ritual or recurring user spending habit based on transaction frequency over the month. "
                    "Examples formatted strictly in the user's language: 'Frequent snacks and coffee to go', 'Regular fast food purchases'. "
                    "FORBIDDEN: Never write the name of a specific single purchase (e.g., do NOT write 'Toy bus'). "
                    "The title MUST describe a recurring behavioral pattern in the plural form."
    )

    frequency_metric: str = Field(
        description="The exact frequency of this specific ritual counted across the raw monthly data. "
                    "Examples formatted strictly in the user's language: 'Purchased 14 times this month', '7 rides in 3 weeks', 'Nearly every day'."
    )

    reason: str = Field(
        description="A deep macro-analysis of this specific habit over the month. Explain to the user how this pattern "
                    "compounds and affects their long-term budget in the future. "
                    "STRICTLY FORBIDDEN: Do not mention specific personal names, brands, or unique single events from the raw data "
                    "(e.g., instead of 'Gift for Victoria' write 'unplanned expenses on gifts and holidays'; "
                    "instead of 'Toy bus' write 'spontaneous purchases for children'). "
                    "Provide actionable financial advice on how to control and track this expense category. Written strictly in the user's language."
    )

    potential_saving: str = Field(
        description="An estimate of the monthly savings potential within this behavioral pattern. "
                    "Format as a free-form encouraging text in the user's language (e.g., 'Up to 3,000 RUB per month if...')."
    )



class MonthlyAnalysisResponse(BaseModel):

    summary: str = Field(
        description="A deep, strategic verbal audit of the user's monthly financial behavior (max 4 sentences). "
                    "CRITICAL: You are STRICTLY FORBIDDEN from generating or writing any percentage values (do NOT use the '%' symbol at all) "
                    "or calculating new balance numbers. Focus entirely on behavioral trends, lifestyle coaching, "
                    "and conceptual budget evaluation using ONLY the raw numbers passed in the context. "
                    "Written in the response language."
    )

    budget_status: str = Field(
        description="The final verdict on the monthly budget status and savings targets. "
                    "Examples formatted strictly in the user's language: 'Perfectly within limits', 'Limit exceeded', "
                    "'Savings goal at risk', 'Budget not set'."
    )
    budget_usage_percent: Optional[float] = Field(
        default=None,
        description="The calculated percentage of the consumed 'monthly_budget'. Calculate this value mathematically "
                    "based on the passed limit. If the monthly budget limit is not provided, strictly return null."
    )


    recommendations: List[MonthlyCategoryRecommendation] = Field(
        description="A list of 2-3 expert strategic optimization recommendations regarding systemic habits and behavioral rituals."
    )


    classified_items: List[MonthlyAnalyzedCategory] = Field(
        description="A complete classification of all expense categories present in the user's data for the month, "
                    "sorted by total spending volume from highest to lowest."
    )


class AnalyzedItem(BaseModel):
    name: str = Field(
        description="The name of a specific item from the receipt (e.g., 'Toothpaste') "
                    "OR the name of the expense category if itemized details are missing (e.g., 'Transport', 'Groceries')."
    )

    expense_type: str = Field(
        description="Strictly one of two options:\n"
                    "1. 'essential' (Vital expenses: medications, basic healthcare, rent, children's and school items including stationery, utilities, repairs of critical breakdowns).\n"
                    "2. 'discretionary' (Flexible spending: takeout coffee, restaurants, premium-class taxis, games, subscriptions, hobbies, home decor, impulse purchases)."
    )

    frequency_metric: str = Field(
        description="The transaction frequency metric for each item or expense category over the past days of the week. "
                    "Strict format: 'X transactions over the past days of the week'."
    )


class TargetRecommendation(BaseModel):
    target_item: str = Field(
        description="The name of the specific item, service, habit, or expense category (from the 'name' field in 'top_items') that is being optimized."
    )
    reason: str = Field(
        description="A well-argued advice explaining why and how spending on this item or category can be optimized."
    )
    potential_saving: str = Field(
        description="An estimate of the potential savings in a free-text format."
    )


class WeeklyAnalysisResponse(BaseModel):
    summary: str = Field(
        description="Short operational audit of the user's financial behavior for the current week "
                    "(up to 4 sentences). Evaluate the week's net balance ('net_balance') relative to income "
                    "and say whether the user keeps the balance positive. "
                    "IMPORTANT: copy numeric aggregates from 'user_context' exactly, without changes or rounding. "
                    "Written in the response language."
    )
    weekly_balance_status: str = Field(
        description="Short verdict on the week so far, written in the response language. "
                    "Examples: 'Expenses exceeded income', 'Great discipline! 🔥'."
    )
    classified_items: List[AnalyzedItem] = Field(
        description="Classification of the user's top items this week by importance"
    )
    recommendations: List[TargetRecommendation] = Field(
        description="2-3 targeted tips STRICTLY about specific spending items (labels)"
    )
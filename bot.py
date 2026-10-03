from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import BOT_TOKEN
from services.nobitex import get_usdt_price


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "ربات قیمت دلار نوبیتکس فعال است.\n\n"
        "برای دریافت قیمت:\n"
        "/price"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prices = get_usdt_price()

        buy = prices["buy"]
        sell = prices["sell"]

        message = (
            "💵 قیمت تتر در نوبیتکس\n\n"
            f"🟢 خرید: {buy:,.0f} ریال\n"
            f"🔴 فروش: {sell:,.0f} ریال"
        )

        await update.message.reply_text(message)

    except Exception as error:
        print(f"Nobitex error: {error}")

        await update.message.reply_text(
            "❌ در دریافت قیمت مشکلی پیش آمد.\n"
            "لطفاً چند لحظه بعد دوباره تلاش کنید."
        )


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))

    print("🤖 Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()

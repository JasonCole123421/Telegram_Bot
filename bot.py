from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import BOT_TOKEN
from database import (
    init_db,
    get_group_settings,
    save_group_settings,
)
from services.nobitex import get_usdt_price


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "💵 ربات قیمت دلار نوبیتکس\n\n"
        "/price - دریافت قیمت\n"
        "/setinterval 15 - تنظیم فاصله ارسال\n"
        "/autoprice on - فعال کردن ارسال خودکار\n"
        "/autoprice off - غیرفعال کردن ارسال خودکار\n"
        "/settings - مشاهده تنظیمات"
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
            "❌ در دریافت قیمت مشکلی پیش آمد."
        )


async def set_interval(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "این دستور فقط داخل گروه قابل استفاده است."
        )
        return

    if not await is_admin(update):
        return

    if not context.args:
        await update.message.reply_text(
            "مثال:\n/setinterval 15"
        )
        return

    try:
        minutes = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ مقدار باید عدد باشد.\n"
            "مثال: /setinterval 15"
        )
        return

    if minutes < 1:
        await update.message.reply_text(
            "❌ فاصله ارسال باید حداقل ۱ دقیقه باشد."
        )
        return

    settings = get_group_settings(update.effective_chat.id)

    save_group_settings(
        update.effective_chat.id,
        minutes,
        settings["auto_price_enabled"]
    )

    await update.message.reply_text(
        f"✅ فاصله ارسال روی {minutes} دقیقه تنظیم شد."
    )


async def autoprice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "این دستور فقط داخل گروه قابل استفاده است."
        )
        return

    if not await is_admin(update):
        return

    if not context.args or context.args[0].lower() not in ("on", "off"):
        await update.message.reply_text(
            "مثال:\n"
            "/autoprice on\n"
            "/autoprice off"
        )
        return

    enabled = context.args[0].lower() == "on"

    settings = get_group_settings(update.effective_chat.id)

    save_group_settings(
        update.effective_chat.id,
        settings["interval_minutes"],
        enabled
    )

    if enabled:
        await update.message.reply_text(
            f"✅ ارسال خودکار فعال شد.\n"
            f"⏱ هر {settings['interval_minutes']} دقیقه"
        )
    else:
        await update.message.reply_text(
            "⛔ ارسال خودکار غیرفعال شد."
        )


async def settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "این دستور فقط داخل گروه قابل استفاده است."
        )
        return

    if not await is_admin(update):
        return

    group_settings = get_group_settings(
        update.effective_chat.id
    )

    status = (
        "فعال ✅"
        if group_settings["auto_price_enabled"]
        else "غیرفعال ⛔"
    )

    await update.message.reply_text(
        "⚙️ تنظیمات ربات\n\n"
        f"📢 ارسال خودکار: {status}\n"
        f"⏱ فاصله ارسال: "
        f"{group_settings['interval_minutes']} دقیقه"
    )


async def is_admin(update: Update):
    member = await update.effective_chat.get_member(
        update.effective_user.id
    )

    if member.status not in ("administrator", "creator"):
        await update.message.reply_text(
            "⛔ فقط ادمین‌های گروه می‌توانند این تنظیم را تغییر دهند."
        )
        return False

    return True


async def send_scheduled_price(
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = context.job.chat_id

    try:
        group_settings = get_group_settings(chat_id)

        if not group_settings["auto_price_enabled"]:
            return

        prices = get_usdt_price()

        buy = prices["buy"]
        sell = prices["sell"]

        message = (
            "💵 قیمت تتر در نوبیتکس\n\n"
            f"🟢 خرید: {buy:,.0f} ریال\n"
            f"🔴 فروش: {sell:,.0f} ریال"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=message
        )

    except Exception as error:
        print(
            f"Scheduled price error for {chat_id}: {error}"
        )


async def schedule_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    settings = get_group_settings(chat_id)

    remove_existing_job(context, chat_id)

    if settings["auto_price_enabled"]:
        context.job_queue.run_repeating(
            send_scheduled_price,
            interval=settings["interval_minutes"] * 60,
            first=settings["interval_minutes"] * 60,
            chat_id=chat_id,
            name=str(chat_id)
        )


def remove_existing_job(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int
):
    jobs = context.job_queue.get_jobs_by_name(
        str(chat_id)
    )

    for job in jobs:
        job.schedule_removal()


async def post_init(application):
    init_db()


def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("price", price)
    )

    application.add_handler(
        CommandHandler("setinterval", set_interval)
    )

    application.add_handler(
        CommandHandler("autoprice", autoprice)
    )

    application.add_handler(
        CommandHandler("settings", settings)
    )

    print("🤖 Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()

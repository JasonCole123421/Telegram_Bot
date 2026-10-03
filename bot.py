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
    get_active_groups,
)
from services.nobitex import get_usdt_price


# ----------------------------------------
# Price
# ----------------------------------------

def build_price_message():
    prices = get_usdt_price()

    buy = prices["buy"]
    sell = prices["sell"]

    return (
        "💵 قیمت تتر در نوبیتکس\n\n"
        f"🟢 خرید: {buy:,.0f} ریال\n"
        f"🔴 فروش: {sell:,.0f} ریال"
    )


async def price(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    try:
        message = build_price_message()

        await update.message.reply_text(message)

    except Exception as error:
        print(f"Nobitex error: {error}")

        await update.message.reply_text(
            "❌ در دریافت قیمت مشکلی پیش آمد."
        )


# ----------------------------------------
# Start
# ----------------------------------------

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "💵 ربات قیمت دلار نوبیتکس\n\n"
        "دستورات:\n\n"
        "/price - دریافت قیمت\n"
        "/setinterval 15 - تنظیم فاصله ارسال\n"
        "/autoprice on - فعال کردن ارسال خودکار\n"
        "/autoprice off - غیرفعال کردن ارسال خودکار\n"
        "/settings - مشاهده تنظیمات"
    )


# ----------------------------------------
# Admin Check
# ----------------------------------------

async def is_admin(update: Update):
    member = await update.effective_chat.get_member(
        update.effective_user.id
    )

    if member.status not in (
        "administrator",
        "creator"
    ):
        await update.message.reply_text(
            "⛔ فقط ادمین‌های گروه می‌توانند "
            "تنظیمات ربات را تغییر دهند."
        )

        return False

    return True


# ----------------------------------------
# Scheduler
# ----------------------------------------

def remove_existing_job(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int
):
    jobs = context.job_queue.get_jobs_by_name(
        str(chat_id)
    )

    for job in jobs:
        job.schedule_removal()


def create_group_job(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    interval_minutes: int
):
    remove_existing_job(context, chat_id)

    context.job_queue.run_repeating(
        send_scheduled_price,
        interval=interval_minutes * 60,
        first=interval_minutes * 60,
        chat_id=chat_id,
        name=str(chat_id)
    )


async def send_scheduled_price(
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = context.job.chat_id

    try:
        settings = get_group_settings(chat_id)

        if not settings["auto_price_enabled"]:
            return

        message = build_price_message()

        await context.bot.send_message(
            chat_id=chat_id,
            text=message
        )

    except Exception as error:
        print(
            f"Scheduled price error "
            f"for {chat_id}: {error}"
        )


# ----------------------------------------
# Set Interval
# ----------------------------------------

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
            "مثال:\n"
            "/setinterval 15"
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

    chat_id = update.effective_chat.id

    settings = get_group_settings(chat_id)

    save_group_settings(
        chat_id,
        minutes,
        settings["auto_price_enabled"]
    )

    # اگر ارسال خودکار فعال است،
    # Scheduler را با فاصله جدید بازسازی کن.
    if settings["auto_price_enabled"]:
        create_group_job(
            context,
            chat_id,
            minutes
        )

    await update.message.reply_text(
        f"✅ فاصله ارسال روی "
        f"{minutes} دقیقه تنظیم شد."
    )


# ----------------------------------------
# Auto Price
# ----------------------------------------

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

    if (
        not context.args
        or context.args[0].lower()
        not in ("on", "off")
    ):
        await update.message.reply_text(
            "مثال:\n\n"
            "/autoprice on\n"
            "/autoprice off"
        )
        return

    chat_id = update.effective_chat.id

    enabled = (
        context.args[0].lower() == "on"
    )

    settings = get_group_settings(chat_id)

    save_group_settings(
        chat_id,
        settings["interval_minutes"],
        enabled
    )

    if enabled:
        create_group_job(
            context,
            chat_id,
            settings["interval_minutes"]
        )

        await update.message.reply_text(
            "✅ ارسال خودکار فعال شد.\n\n"
            f"⏱ هر "
            f"{settings['interval_minutes']} دقیقه"
        )

    else:
        remove_existing_job(
            context,
            chat_id
        )

        await update.message.reply_text(
            "⛔ ارسال خودکار غیرفعال شد."
        )


# ----------------------------------------
# Settings
# ----------------------------------------

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

    chat_id = update.effective_chat.id

    group_settings = get_group_settings(
        chat_id
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


# ----------------------------------------
# Restore Jobs After Restart
# ----------------------------------------

async def post_init(
    application: Application
):
    init_db()

    active_groups = get_active_groups()

    print(
        f"🔄 Restoring "
        f"{len(active_groups)} active group(s)..."
    )

    for chat_id, interval_minutes in active_groups:
        create_group_job(
            application,
            chat_id,
            interval_minutes
        )


# ----------------------------------------
# Main
# ----------------------------------------

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
        CommandHandler(
            "setinterval",
            set_interval
        )
    )

    application.add_handler(
        CommandHandler(
            "autoprice",
            autoprice
        )
    )

    application.add_handler(
        CommandHandler(
            "settings",
            settings
        )
    )

    print("🤖 Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()

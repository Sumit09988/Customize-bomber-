import logging
import aiohttp
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8669433267:AAE4SQAPoSw_nsbAqJRHJ-emYS7IXIiHRho"
OWNER_ID  = 7515864015
API_BASE  = "https://rootx-osint.in/"
API_KEY   = "Billaa"

users_db: set[int] = set()
channels_db: list[dict] = []

logging.basicConfig(level=logging.INFO)

# Telegram built-in animated emoji — yeh sab animated hain Telegram client mein
# Sirf single emoji as message text bhejne pe animate hote hain
# Message mein text ke saath bhi dikhte hain (static form mein)
E = {
    "crown":  "👑",
    "rocket": "🚀",
    "search": "🔍",
    "globe":  "🌍",
    "phone":  "📞",
    "id":     "🆔",
    "check":  "✅",
    "cross":  "❌",
    "spin":   "⏳",
    "mega":   "📣",
    "users":  "👥",
    "dev":    "👨‍💻",
    "lock":   "🔒",
    "zap":    "⚡",
    "help":   "❓",
    "new":    "🆕",
    "link":   "🔗",
    "fire":   "🔥",
    "star":   "⭐",
    "shield": "🛡",
    "tick":   "☑️",
    "key":    "🔑",
    "eye":    "👁",
    "bolt":   "🌩",
    "scan":   "📡",
    "warn":   "⚠️",
    "gem":    "💎",
    "pin":    "📌",
    "chart":  "📊",
    "target": "🎯",
}

def e(k: str) -> str:
    return E.get(k, "")

def kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🚀 Lookup Now"],
            ["❓ Help", "👨‍💻 Developer"],
            ["👥 Total Users", "📣 Broadcast"],
            ["➕ Add Channel", "➖ Remove Channel"],
        ],
        resize_keyboard=True,
        input_field_placeholder="@username ya User ID bhejo..."
    )

def result_inline(query: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Search Again", callback_data=f"s:{query}"),
            InlineKeyboardButton("🏠 Home", callback_data="home"),
        ],
        [InlineKeyboardButton("📤 Share", switch_inline_query=query)],
        [InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/T4HKR")],
    ])

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not channels_db:
        return True
    uid = update.effective_user.id
    not_joined = []
    for ch in channels_db:
        try:
            member = await context.bot.get_chat_member(ch["id"], uid)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    if not_joined:
        btns = [
            [InlineKeyboardButton(f"⚡ Join Channel {i+1}", url=ch["link"])]
            for i, ch in enumerate(not_joined)
        ]
        btns.append([InlineKeyboardButton("✅ Joined — Check Again", callback_data="recheck")])
        await update.effective_message.reply_text(
            f"{e('lock')} <b>Force Join Required</b>\n\n"
            f"{e('zap')} Pehle join karo, phir use karo:",
            reply_markup=InlineKeyboardMarkup(btns),
            parse_mode="HTML"
        )
        return False
    return True

def msg_welcome(name: str) -> str:
    return (
        f"{e('crown')} <b>Welcome, {name}!</b>\n\n"
        f"{e('rocket')} <b>Username → Number Lookup Bot</b>\n\n"
        f"{e('zap')} Fast & Free — No limits!\n"
        f"{e('shield')} Secure & Anonymous\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"{e('dev')} Dev: @T4HKR"
    )

def msg_searching(query: str) -> str:
    return (
        f"{e('spin')} <b>Searching...</b>\n\n"
        f"{e('scan')} Query: <code>{query}</code>\n\n"
        f"{e('fire')} Processing your request..."
    )

def msg_result(data: dict, query: str) -> str:
    return (
        f"{e('check')} <b>RESULT FOUND</b>\n\n"
        f"╔══════════════════╗\n"
        f"{e('globe')} <b>Country:</b>  <code>{data.get('country','Unknown')}</code>\n"
        f"{e('phone')} <b>Number:</b>   <code>{data.get('number','N/A')}</code>\n"
        f"{e('id')}    <b>User ID:</b>  <code>{data.get('user_id','N/A')}</code>\n"
        f"╚══════════════════╝\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"{e('search')} <b>Query:</b> <code>{query}</code>\n"
        f"{e('dev')} Dev: @T4HKR"
    )

def msg_noresult(query: str) -> str:
    return (
        f"{e('cross')} <b>No Result Found</b>\n\n"
        f"{e('warn')} No data available for:\n"
        f"<code>{query}</code>\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"{e('dev')} Dev: @T4HKR"
    )

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, user) -> None:
    try:
        await context.bot.send_message(
            OWNER_ID,
            f"{e('new')} <b>New User Joined!</b>\n\n"
            f"{e('id')} ID: <code>{user.id}</code>\n"
            f"👤 Name: {user.first_name}\n"
            f"{e('link')} Username: @{user.username or 'N/A'}",
            parse_mode="HTML"
        )
    except Exception:
        pass

async def osint_query(query: str) -> dict | None:
    url = f"{API_BASE}?type=tg_num&key={API_KEY}&query={query}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return await r.json()
    except Exception:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_new = user.id not in users_db
    users_db.add(user.id)
    if is_new:
        await notify_owner(context, user)
    if not await check_force_join(update, context):
        return
    await update.message.reply_text(
        msg_welcome(user.first_name),
        reply_markup=kb(),
        parse_mode="HTML"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    users_db.add(user.id)

    if context.user_data.get("await_broadcast") and user.id == OWNER_ID:
        context.user_data.pop("await_broadcast")
        sent = failed = 0
        for uid in list(users_db):
            try:
                await context.bot.send_message(uid, text, parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"{e('mega')} <b>Broadcast Done</b>\n\n"
            f"{e('check')} Sent: <code>{sent}</code>\n"
            f"{e('cross')} Failed: <code>{failed}</code>",
            parse_mode="HTML"
        )
        return

    if context.user_data.get("await_ch_id") and user.id == OWNER_ID:
        try:
            ch_id = int(text.strip())
            context.user_data["temp_ch_id"] = ch_id
            context.user_data.pop("await_ch_id")
            context.user_data["await_ch_link"] = True
            await update.message.reply_text(
                f"{e('check')} Channel ID saved: <code>{ch_id}</code>\n\n"
                f"{e('link')} Ab invite link bhejo:\n"
                f"Private: <code>https://t.me/+xxxxx</code>\n"
                f"Public: <code>https://t.me/username</code>",
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text(
                f"{e('cross')} Invalid ID. Example: <code>-1001234567890</code>",
                parse_mode="HTML"
            )
        return

    if context.user_data.get("await_ch_link") and user.id == OWNER_ID:
        link = text.strip()
        ch_id = context.user_data.pop("temp_ch_id", None)
        context.user_data.pop("await_ch_link")
        if ch_id:
            channels_db.append({"id": ch_id, "link": link})
            await update.message.reply_text(
                f"{e('check')} <b>Channel Added!</b>\n\n"
                f"{e('id')} ID: <code>{ch_id}</code>\n"
                f"{e('link')} Link: {link}\n\n"
                f"Total channels: <code>{len(channels_db)}</code>",
                parse_mode="HTML"
            )
        return

    if context.user_data.get("await_rm_ch") and user.id == OWNER_ID:
        context.user_data.pop("await_rm_ch")
        try:
            ch_id = int(text.strip())
            before = len(channels_db)
            channels_db[:] = [c for c in channels_db if c["id"] != ch_id]
            if len(channels_db) < before:
                await update.message.reply_text(
                    f"{e('check')} Removed: <code>{ch_id}</code>", parse_mode="HTML"
                )
            else:
                await update.message.reply_text(
                    f"{e('cross')} Not found: <code>{ch_id}</code>", parse_mode="HTML"
                )
        except ValueError:
            await update.message.reply_text("❌ Sirf channel ID number bhejo.", parse_mode="HTML")
        return

    match text:
        case "🚀 Lookup Now":
            await update.message.reply_text(
                f"{e('search')} <b>Send @username or User ID:</b>\n\n"
                f"{e('target')} Example: <code>@username</code> or <code>123456789</code>",
                parse_mode="HTML"
            )

        case "❓ Help":
            await update.message.reply_text(
                f"{e('help')} <b>Help & Guide</b>\n\n"
                f"{e('rocket')} <b>Lookup Now</b> — @username ya ID bhejo\n"
                f"{e('zap')} Fast & Free — Koi limit nahi\n"
                f"{e('shield')} Anonymous lookup\n\n"
                f"━━━━━━━━━━━━━━\n"
                f"{e('dev')} Dev: @T4HKR",
                parse_mode="HTML"
            )

        case "👨‍💻 Developer":
            await update.message.reply_text(
                f"{e('dev')} <b>Developer</b>\n\n"
                f"{e('star')} @T4HKR\n\n"
                f"{e('gem')} Premium Bot Builder",
                parse_mode="HTML"
            )

        case "👥 Total Users":
            if user.id != OWNER_ID:
                await update.message.reply_text(f"{e('lock')} Owner only!")
                return
            await update.message.reply_text(
                f"{e('users')} <b>Total Users</b>\n\n"
                f"{e('chart')} Count: <code>{len(users_db)}</code>",
                parse_mode="HTML"
            )

        case "📣 Broadcast":
            if user.id != OWNER_ID:
                await update.message.reply_text(f"{e('lock')} Owner only!")
                return
            context.user_data["await_broadcast"] = True
            await update.message.reply_text(
                f"{e('mega')} <b>Broadcast Mode</b>\n\n"
                f"{e('pin')} Message bhejo — sab users ko jayega:",
                parse_mode="HTML"
            )

        case "➕ Add Channel":
            if user.id != OWNER_ID:
                await update.message.reply_text(f"{e('lock')} Owner only!")
                return
            context.user_data["await_ch_id"] = True
            await update.message.reply_text(
                f"➕ <b>Add Channel — Step 1/2</b>\n\n"
                f"{e('id')} Channel ID bhejo:\n\n"
                f"{e('warn')} @userinfobot pe forward karo ID lene ke liye\n\n"
                f"Example: <code>-1001234567890</code>",
                parse_mode="HTML"
            )

        case "➖ Remove Channel":
            if user.id != OWNER_ID:
                await update.message.reply_text(f"{e('lock')} Owner only!")
                return
            if not channels_db:
                await update.message.reply_text(
                    f"{e('cross')} Koi channel add nahi hai.", parse_mode="HTML"
                )
                return
            ch_list = "\n".join([f"<code>{c['id']}</code> — {c['link']}" for c in channels_db])
            context.user_data["await_rm_ch"] = True
            await update.message.reply_text(
                f"➖ <b>Remove Channel</b>\n\nCurrent channels:\n{ch_list}\n\n"
                f"{e('id')} Remove karne wala Channel ID bhejo:",
                parse_mode="HTML"
            )

        case _:
            if not await check_force_join(update, context):
                return
            msg = await update.message.reply_text(msg_searching(text), parse_mode="HTML")
            data = await osint_query(text)
            if data and data.get("number"):
                await msg.edit_text(
                    msg_result(data, text),
                    reply_markup=result_inline(text),
                    parse_mode="HTML"
                )
            else:
                await msg.edit_text(msg_noresult(text), parse_mode="HTML")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "home":
        await q.edit_message_text(
            msg_welcome(q.from_user.first_name), parse_mode="HTML"
        )
    elif q.data == "recheck":
        if await check_force_join(update, context):
            await q.edit_message_text(
                f"{e('check')} <b>Verified!</b>\n\n@username ya User ID bhejo",
                parse_mode="HTML"
            )
    elif q.data.startswith("s:"):
        raw = q.data[2:]
        await q.edit_message_text(msg_searching(raw), parse_mode="HTML")
        data = await osint_query(raw)
        if data and data.get("number"):
            await q.edit_message_text(
                msg_result(data, raw),
                reply_markup=result_inline(raw),
                parse_mode="HTML"
            )
        else:
            await q.edit_message_text(msg_noresult(raw), parse_mode="HTML")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

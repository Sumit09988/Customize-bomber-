# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INSTALL: pip install pyrogram tgcrypto anthropic yt-dlp
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import asyncio
import json
import os
import anthropic
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MessageEntity
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   ⚡ SUMIT BOTS @T4HKR
#   Owner: 7515864015
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN     = "8803693096:AAHrFlrc5Bsg2s4nQIUaM7Wr_VMX9p0ucaU"
OWNER_ID      = 7515864015
ANTHROPIC_KEY = "your_anthropic_api_key"
BRAND         = "⚡ **SUMIT BOTS** | @T4HKR"
CONFIG_FILE   = "config.json"
DB_FILE       = "groups.json"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PREMIUM ANIMATED EMOJI IDs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMOJI_IDS = [
    6147565374289220368,
    6147460667281511517,
    6147868521670907133,
    6147902731085420231,
    6235475653961979149,
    6237864166879663987,
    6147637448135414816,
    6120436698695338614,
    6158743460468757612,
    6125127017730938358,
    6174970628597094685,
    6228803984908358340,
    6228682720801723876,
    6244425785986257276,
    6235474107773752889,
]

PLACEHOLDER = "\U000E0020"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"api_id": None, "api_hash": None, "sessions": []}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_session(session: str):
    cfg = load_config()
    if session not in cfg["sessions"]:
        cfg["sessions"].append(session)
        save_config(cfg)

def remove_session(index: int):
    cfg = load_config()
    if 0 <= index < len(cfg["sessions"]):
        cfg["sessions"].pop(index)
        save_config(cfg)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATABASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_groups():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_group(chat_id, title):
    db = load_groups()
    db[str(chat_id)] = title
    with open(DB_FILE, "w") as f:
        json.dump(db, f, ensure_ascii=False)

def remove_group(chat_id):
    db = load_groups()
    db.pop(str(chat_id), None)
    with open(DB_FILE, "w") as f:
        json.dump(db, f, ensure_ascii=False)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PREMIUM EMOJI SENDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def send_premium(
    client,
    chat_id: int,
    text: str,
    emoji_ids: list = None,
    reply_markup=None,
    reply_to_message_id: int = None
):
    if not emoji_ids:
        emoji_ids = EMOJI_IDS[:4]

    placeholders = ""
    entities     = []
    offset       = 0

    for eid in emoji_ids:
        ph = PLACEHOLDER * 2
        placeholders += ph
        entities.append(MessageEntity(
            type="custom_emoji",
            offset=offset,
            length=len(ph),
            custom_emoji_id=eid
        ))
        offset += len(ph)

    full_text = placeholders + "\n" + text

    try:
        await client.send_message(
            chat_id=chat_id,
            text=full_text,
            entities=entities,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
            disable_web_page_preview=True
        )
    except Exception:
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            reply_to_message_id=reply_to_message_id,
            disable_web_page_preview=True
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI CLIENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ai           = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
CHAT_HISTORY = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BOT CLIENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bot = Client(
    "sumit_main_bot",
    bot_token=BOT_TOKEN,
    api_id=2040,
    api_hash="b18441a1ff607e10a989891a5462e627"
)

setup_state = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTO GROUP SAVE / REMOVE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.new_chat_members)
async def on_join(client: Client, message: Message):
    for m in message.new_chat_members:
        if m.is_self:
            save_group(message.chat.id, message.chat.title)
            try:
                await send_premium(
                    client, message.chat.id,
                    f"**Hii bc sab log!**\nAa gaya main group mein\n\n{BRAND}",
                    emoji_ids=EMOJI_IDS[:4]
                )
            except:
                pass

@bot.on_message(filters.left_chat_member)
async def on_leave(client: Client, message: Message):
    if message.left_chat_member.is_self:
        remove_group(message.chat.id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DM — UNKNOWN IGNORE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.private & ~filters.user(OWNER_ID))
async def ignore_dm(client: Client, message: Message):
    pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# START
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("start") & filters.private & filters.user(OWNER_ID))
async def start(client: Client, message: Message):
    cfg      = load_config()
    api_set  = "✅" if cfg.get("api_id") else "❌"
    hash_set = "✅" if cfg.get("api_hash") else "❌"
    ub_count = len(cfg.get("sessions", []))

    await send_premium(
        client, message.chat.id,
        f"{BRAND}\n\n"
        f"**Hii Sumit bhai!**\n\n"
        f"**Setup Status:**\n"
        f"API ID: {api_set}\n"
        f"API HASH: {hash_set}\n"
        f"Sessions: {ub_count}\n\n"
        f"**Setup Commands:**\n"
        f"/setapi — API ID set karo\n"
        f"/sethash — API HASH set karo\n"
        f"/addsession — Session add karo\n"
        f"/delsession 1 — Session hatao\n"
        f"/sessions — Sessions list\n\n"
        f"**Broadcast:**\n"
        f"/broadcast — Turant sabko bhejo\n"
        f"/tbroadcast 30m msg — Timer ke saath\n\n"
        f"**Admin:**\n"
        f"/admincheck — Kahan admin hoon\n"
        f"/groups — Total groups list\n\n"
        f"**Group mein @mention karke baat karo!**",
        emoji_ids=EMOJI_IDS[:6],
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚙️ Setup", callback_data="setup"),
                InlineKeyboardButton("👥 Groups", callback_data="groups")
            ],
            [
                InlineKeyboardButton("📢 Channel", url="https://t.me/T4HKR"),
                InlineKeyboardButton("👤 Owner", url="tg://user?id=7515864015")
            ]
        ])
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SET API ID
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("setapi") & filters.private & filters.user(OWNER_ID))
async def set_api(client: Client, message: Message):
    setup_state[OWNER_ID] = "waiting_api_id"
    await message.reply(
        f"**API ID bhej bhai:**\n\n"
        f"my.telegram.org → Login\n"
        f"→ API Development Tools\n"
        f"→ App ID copy karo yahan bhejo\n\n"
        f"Cancel: /cancel"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SET API HASH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("sethash") & filters.private & filters.user(OWNER_ID))
async def set_hash(client: Client, message: Message):
    setup_state[OWNER_ID] = "waiting_api_hash"
    await message.reply(
        f"**API HASH bhej bhai:**\n\n"
        f"my.telegram.org → Login\n"
        f"→ API Development Tools\n"
        f"→ App hash copy karo yahan bhejo\n\n"
        f"Cancel: /cancel"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADD SESSION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("addsession") & filters.private & filters.user(OWNER_ID))
async def add_session_cmd(client: Client, message: Message):
    cfg = load_config()
    if not cfg.get("api_id") or not cfg.get("api_hash"):
        await message.reply(
            f"Pehle API ID aur HASH set kar!\n"
            f"/setapi → /sethash → phir /addsession"
        )
        return
    setup_state[OWNER_ID] = "waiting_session"
    await message.reply(
        f"**Session String bhej bhai**\n\n"
        f"Apne PC pe yeh chala:\n\n"
        f"```\npip install pyrogram tgcrypto\n```\n\n"
        f"Phir yeh Python script:\n\n"
        f"```python\n"
        f"from pyrogram import Client\n"
        f"import asyncio\n\n"
        f"async def main():\n"
        f"    async with Client(\n"
        f"        'mysession',\n"
        f"        api_id={cfg['api_id']},\n"
        f"        api_hash='{cfg['api_hash']}'\n"
        f"    ) as app:\n"
        f"        print(await app.export_session_string())\n\n"
        f"asyncio.run(main())\n"
        f"```\n\n"
        f"BQA... se start hone wali string yahan bhej\n\n"
        f"Cancel: /cancel"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DELETE SESSION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("delsession") & filters.private & filters.user(OWNER_ID))
async def del_session_cmd(client: Client, message: Message):
    cfg      = load_config()
    sessions = cfg.get("sessions", [])

    if not sessions:
        await message.reply("Koi session nahi hai abhi.")
        return

    args = message.command
    if len(args) > 1:
        try:
            idx = int(args[1]) - 1
            remove_session(idx)
            await message.reply(f"Session {args[1]} hata diya!")
        except:
            await message.reply("Number sahi nahi bhai.")
    else:
        text = "**Konsa hatana hai?**\n\n"
        for i, s in enumerate(sessions, 1):
            text += f"{i}. `{s[:35]}...`\n"
        text += f"\n`/delsession 1` — pehla hatao"
        await message.reply(text)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSIONS LIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("sessions") & filters.private & filters.user(OWNER_ID))
async def sessions_list(client: Client, message: Message):
    cfg      = load_config()
    sessions = cfg.get("sessions", [])
    if not sessions:
        await message.reply("Koi session nahi. /addsession se add kar.")
        return
    text = f"**Total Sessions: {len(sessions)}**\n\n"
    for i, s in enumerate(sessions, 1):
        text += f"{i}. `{s[:40]}...`\n"
    await send_premium(client, message.chat.id, text, emoji_ids=EMOJI_IDS[:3])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CANCEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("cancel") & filters.private & filters.user(OWNER_ID))
async def cancel(client: Client, message: Message):
    setup_state.pop(OWNER_ID, None)
    await message.reply("Cancel. /start maar.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OWNER DM INPUT HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(
    filters.private &
    filters.user(OWNER_ID) &
    ~filters.command([
        "start","setapi","sethash","addsession",
        "delsession","sessions","cancel",
        "broadcast","tbroadcast","admincheck","groups"
    ])
)
async def owner_input_handler(client: Client, message: Message):
    user_text = message.text or ""
    state     = setup_state.get(OWNER_ID)

    # API ID
    if state == "waiting_api_id":
        try:
            api_id = int(user_text.strip())
            cfg    = load_config()
            cfg["api_id"] = api_id
            save_config(cfg)
            setup_state.pop(OWNER_ID, None)
            await message.reply(
                f"API ID set!\nID: `{api_id}`\n\nAb /sethash maar."
            )
        except ValueError:
            await message.reply("Sirf number bhej bc! API ID number hota hai.")
        return

    # API HASH
    if state == "waiting_api_hash":
        api_hash = user_text.strip()
        if len(api_hash) < 10:
            await message.reply("Yeh sahi nahi lagta bhai. Dobara check kar.")
            return
        cfg = load_config()
        cfg["api_hash"] = api_hash
        save_config(cfg)
        setup_state.pop(OWNER_ID, None)
        await message.reply(f"API HASH set!\n\nAb /addsession maar.")
        return

    # SESSION
    if state == "waiting_session":
        session = user_text.strip()
        if not session.startswith("BQA"):
            await message.reply(
                "Session string sahi nahi!\n"
                "BQA se start honi chahiye.\n"
                "Dobara try kar ya /cancel maar."
            )
            return
        add_session(session)
        setup_state.pop(OWNER_ID, None)
        cfg = load_config()
        await message.reply(
            f"Session add!\nTotal: {len(cfg['sessions'])}\n\n"
            f"Aur add: /addsession"
        )
        return

    # FRIENDLY CHAT
    if not user_text:
        await message.reply("bc kuch toh bol")
        return

    if OWNER_ID not in CHAT_HISTORY:
        CHAT_HISTORY[OWNER_ID] = []

    CHAT_HISTORY[OWNER_ID].append({"role": "user", "content": user_text})

    if len(CHAT_HISTORY[OWNER_ID]) > 20:
        CHAT_HISTORY[OWNER_ID] = CHAT_HISTORY[OWNER_ID][-20:]

    await client.send_chat_action(message.chat.id, "typing")

    try:
        response = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=(
                "Tu SUMIT BOT hai — Sumit ka pakka yaar. "
                "Hinglish mein baat kar. Gali deta hai pyaar se — "
                "mc, bc, bhosdike, chutiye, haraami — "
                "normal dost jaisi baat mein. "
                "2-3 line mein reply kar. "
                "Kabhi mat bol Main AI hoon. "
                "Funny reh, dost ban."
            ),
            messages=CHAT_HISTORY[OWNER_ID]
        )
        reply_text = response.content[0].text
        CHAT_HISTORY[OWNER_ID].append({"role": "assistant", "content": reply_text})
        await message.reply(reply_text)
    except Exception as e:
        await message.reply(f"bc kuch toot gaya\n`{e}`")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUP CHAT — GALI WALA DOST
# Sirf @mention ya reply pe
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(
    filters.group &
    ~filters.command([
        "broadcast","tbroadcast","admincheck","groups"
    ])
)
async def group_chat(client: Client, message: Message):
    me = await client.get_me()

    is_mentioned = False
    if message.mentioned:
        is_mentioned = True
    elif message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id == me.id:
            is_mentioned = True

    if not is_mentioned:
        return

    user_name = message.from_user.first_name
    user_id   = message.from_user.id
    user_text = (message.text or "").replace(f"@{me.username}", "").strip()

    if not user_text:
        await message.reply("haan bc bol kya hai")
        return

    chat_key = f"{message.chat.id}_{user_id}"
    if chat_key not in CHAT_HISTORY:
        CHAT_HISTORY[chat_key] = []

    CHAT_HISTORY[chat_key].append({"role": "user", "content": user_text})

    if len(CHAT_HISTORY[chat_key]) > 15:
        CHAT_HISTORY[chat_key] = CHAT_HISTORY[chat_key][-15:]

    await client.send_chat_action(message.chat.id, "typing")

    try:
        response = ai.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=250,
            system=(
                f"Tu SUMIT BOT hai — @T4HKR ka banda. "
                f"Tu {user_name} ka yaar hai is group mein. "
                f"Hinglish mein baat kar bilkul natural. "
                f"Gali deta hai pyaar se — mc, bc, bhosdike, chutiye. "
                f"2-3 line max. Kabhi mat bol Main AI hoon. "
                f"Funny reh. Sad ho toh gali deke motivate kar."
            ),
            messages=CHAT_HISTORY[chat_key]
        )
        reply_text = response.content[0].text
        CHAT_HISTORY[chat_key].append({"role": "assistant", "content": reply_text})
        await message.reply(reply_text)
    except:
        await message.reply("bc error aa gaya")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BROADCAST — TURANT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply(
            f"Jo message bhejni ho usse reply karke /broadcast maar\n\n{BRAND}"
        )
        return

    text    = message.reply_to_message.text or message.reply_to_message.caption
    groups  = load_groups()

    if not groups:
        await message.reply(f"Koi group nahi.\n\n{BRAND}")
        return

    msg     = await message.reply(f"Broadcast shuru...\nGroups: {len(groups)}")
    success = failed = 0

    for chat_id in groups:
        try:
            await send_premium(
                client, int(chat_id),
                f"{text}\n\n{BRAND}",
                emoji_ids=EMOJI_IDS[:3]
            )
            success += 1
            await asyncio.sleep(0.4)
        except:
            failed += 1

    await msg.edit(f"Done!\nSuccess: {success}\nFailed: {failed}\n\n{BRAND}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BROADCAST — TIMER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def do_tbroadcast(client, text, delay):
    await asyncio.sleep(delay)
    groups = load_groups()
    for chat_id in groups:
        try:
            await send_premium(
                client, int(chat_id),
                f"{text}\n\n{BRAND}",
                emoji_ids=EMOJI_IDS[:3]
            )
            await asyncio.sleep(0.4)
        except:
            pass

@bot.on_message(filters.command("tbroadcast") & filters.user(OWNER_ID))
async def tbroadcast(client: Client, message: Message):
    args = message.command
    if len(args) < 3:
        await message.reply(
            f"Format: /tbroadcast time message\n\n"
            f"/tbroadcast 30m Aaj offer!\n"
            f"/tbroadcast 2h Event!\n"
            f"/tbroadcast 1d Kal milte!\n\n{BRAND}"
        )
        return

    time_str  = args[1].lower()
    bcast_msg = " ".join(args[2:])

    if time_str.endswith("m"):
        delay    = int(time_str[:-1]) * 60
        readable = f"{time_str[:-1]} minute baad"
    elif time_str.endswith("h"):
        delay    = int(time_str[:-1]) * 3600
        readable = f"{time_str[:-1]} ghante baad"
    elif time_str.endswith("d"):
        delay    = int(time_str[:-1]) * 86400
        readable = f"{time_str[:-1]} din baad"
    else:
        await message.reply(f"Format galat! 30m 2h 1d use kar\n\n{BRAND}")
        return

    await send_premium(
        client, message.chat.id,
        f"**Timer Set!**\n"
        f"Message: {bcast_msg}\n"
        f"Kab: {readable}\n"
        f"Groups: {len(load_groups())}\n\n{BRAND}",
        emoji_ids=EMOJI_IDS[:4]
    )
    asyncio.create_task(do_tbroadcast(client, bcast_msg, delay))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADMIN CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("admincheck") & filters.user(OWNER_ID))
async def admin_check(client: Client, message: Message):
    groups         = load_groups()
    msg            = await message.reply("Check ho raha hai...")
    admin_list     = []
    not_admin_list = []

    for chat_id, title in groups.items():
        try:
            member = await client.get_chat_member(int(chat_id), "me")
            if member.status.value in ["administrator", "owner"]:
                admin_list.append(f"👑 {title}")
            else:
                not_admin_list.append(f"👤 {title}")
        except:
            not_admin_list.append(f"❓ {title}")

    text = (
        f"**Admin Report**\n\n"
        f"Jahan admin hoon ({len(admin_list)}):\n"
        + ("\n".join(admin_list) or "Koi nahi") +
        f"\n\nJahan nahi ({len(not_admin_list)}):\n"
        + ("\n".join(not_admin_list) or "Sab jagah admin!") +
        f"\n\n{BRAND}"
    )
    await msg.delete()
    await send_premium(client, message.chat.id, text, emoji_ids=EMOJI_IDS[:5])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GROUPS LIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("groups") & filters.user(OWNER_ID))
async def groups_list(client: Client, message: Message):
    groups = load_groups()
    if not groups:
        await message.reply(f"Koi group nahi.\n\n{BRAND}")
        return
    text = f"**Total Groups: {len(groups)}**\n\n"
    for i, (chat_id, title) in enumerate(groups.items(), 1):
        text += f"{i}. {title}\n`{chat_id}`\n\n"
    text += BRAND
    await send_premium(client, message.chat.id, text, emoji_ids=EMOJI_IDS[:4])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALLBACKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_callback_query()
async def callbacks(client, cq):
    data = cq.data
    if data == "setup":
        cfg = load_config()
        await cq.answer(
            f"API ID: {'Set ✅' if cfg.get('api_id') else 'Nahi ❌'}\n"
            f"API HASH: {'Set ✅' if cfg.get('api_hash') else 'Nahi ❌'}\n"
            f"Sessions: {len(cfg.get('sessions', []))}",
            show_alert=True
        )
    elif data == "groups":
        g = load_groups()
        await cq.answer(f"Total {len(g)} groups!", show_alert=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ⚡ SUMIT BOTS @T4HKR")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    await bot.start()
    me = await bot.get_me()
    print(f"Bot: @{me.username}")
    print("  Sab Chalu! 6767")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    await asyncio.get_event_loop().run_forever()

asyncio.run(main())

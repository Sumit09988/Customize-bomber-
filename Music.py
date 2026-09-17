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
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio
import yt_dlp

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
# CONFIG — API ID/HASH BOT SE CHANGE HOGA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"api_id": None, "api_hash": None, "sessions": []}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_api_id():
    return load_config().get("api_id")

def get_api_hash():
    return load_config().get("api_hash")

def get_sessions():
    return load_config().get("sessions", [])

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

    await client.send_message(
        chat_id=chat_id,
        text=full_text,
        entities=entities,
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
# BOT CLIENT — SIRF BOT TOKEN SE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bot token se directly connect — API ID/HASH baad mein add hoga
bot = Client(
    "sumit_main_bot",
    bot_token=BOT_TOKEN,
    api_id=2040,          # Telegram default test values
    api_hash="b18441a1ff607e10a989891a5462e627"
)

userbots       = []
pytgcalls_list = []
group_ub_map   = {}
music_queue    = {}
setup_state    = {}  # Owner ke setup steps track karne ke liye

def get_vc(chat_id: int):
    if not pytgcalls_list:
        return None
    if chat_id not in group_ub_map:
        idx = len(group_ub_map) % len(pytgcalls_list)
        group_ub_map[chat_id] = idx
    return pytgcalls_list[group_ub_map[chat_id]]

def get_audio(query: str):
    opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        if query.startswith("http"):
            info = ydl.extract_info(query, download=False)
        else:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            info = info["entries"][0]
        return info["url"], info.get("title", "Unknown")

async def reload_userbots():
    """Naye sessions se userbots reload karo"""
    global userbots, pytgcalls_list, group_ub_map

    api_id   = get_api_id()
    api_hash = get_api_hash()
    sessions = get_sessions()

    if not api_id or not api_hash:
        return False

    # Purane userbots band karo
    for ub in userbots:
        try:
            await ub.stop()
        except:
            pass

    userbots       = []
    pytgcalls_list = []
    group_ub_map   = {}

    for i, session in enumerate(sessions):
        try:
            ub = Client(
                f"userbot_{i+1}",
                api_id=int(api_id),
                api_hash=api_hash,
                session_string=session
            )
            vc = PyTgCalls(ub)
            await ub.start()
            await vc.start()
            userbots.append(ub)
            pytgcalls_list.append(vc)
        except Exception as e:
            print(f"Userbot {i+1} Error: {e}")

    return True

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
        f"/delsession — Session hatao\n"
        f"/sessions — Sessions dekho\n"
        f"/reloadub — Userbots reload karo\n\n"
        f"**Music:**\n"
        f"/play song — Gaana bajao\n"
        f"/skip — Next\n"
        f"/stop — Band karo\n"
        f"/queue — Queue\n"
        f"/np — Ab kya chal raha\n\n"
        f"**Broadcast:**\n"
        f"/broadcast — Turant\n"
        f"/tbroadcast 30m msg — Timer\n\n"
        f"**Admin:**\n"
        f"/admincheck — Kahan admin hoon\n"
        f"/groups — Total groups\n"
        f"/ubstatus — Userbot status",
        emoji_ids=EMOJI_IDS[:6],
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⚙️ Setup", callback_data="setup"),
                InlineKeyboardButton("👥 Groups", callback_data="groups")
            ],
            [
                InlineKeyboardButton("🤖 UB Status", callback_data="ubstatus"),
                InlineKeyboardButton("📢 Channel", url="https://t.me/T4HKR")
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
        f"my.telegram.org pe ja\n"
        f"Login karo → API Development Tools\n"
        f"App ID copy karo aur yahan bhej\n\n"
        f"Ya cancel karne ke liye /cancel maar"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SET API HASH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("sethash") & filters.private & filters.user(OWNER_ID))
async def set_hash(client: Client, message: Message):
    setup_state[OWNER_ID] = "waiting_api_hash"
    await message.reply(
        f"**API HASH bhej bhai:**\n\n"
        f"my.telegram.org pe ja\n"
        f"Login karo → API Development Tools\n"
        f"App hash copy karo aur yahan bhej\n\n"
        f"Ya cancel karne ke liye /cancel maar"
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
        f"**Session String bhej bhai:**\n\n"
        f"Session string generate karne ke liye:\n"
        f"1. Apne PC pe yeh script chala:\n\n"
        f"`pip install pyrogram tgcrypto`\n\n"
        f"Phir Python mein:\n"
        f"```python\n"
        f"from pyrogram import Client\n"
        f"import asyncio\n\n"
        f"async def main():\n"
        f"    async with Client('s', {cfg['api_id']}, '{cfg['api_hash']}') as app:\n"
        f"        print(await app.export_session_string())\n\n"
        f"asyncio.run(main())\n"
        f"```\n\n"
        f"Session string BQA... se start hogi\n"
        f"Woh yahan bhej\n\n"
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

    text = "**Konsa session hatana hai?**\n\n"
    for i, s in enumerate(sessions):
        text += f"{i+1}. `{s[:30]}...`\n"
    text += f"\n`/delsession 1` — pehla hatao\n`/delsession 2` — doosra hatao"

    args = message.command
    if len(args) > 1:
        try:
            idx = int(args[1]) - 1
            remove_session(idx)
            await message.reply(f"Session {args[1]} hata diya!")
        except:
            await message.reply("Number sahi nahi hai bhai.")
    else:
        await message.reply(text)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSIONS LIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("sessions") & filters.private & filters.user(OWNER_ID))
async def sessions_list(client: Client, message: Message):
    cfg      = load_config()
    sessions = cfg.get("sessions", [])

    if not sessions:
        await message.reply("Koi session nahi hai. /addsession se add kar.")
        return

    text = f"**Total Sessions: {len(sessions)}**\n\n"
    for i, s in enumerate(sessions, 1):
        text += f"{i}. `{s[:40]}...`\n"

    await send_premium(
        client, message.chat.id, text,
        emoji_ids=EMOJI_IDS[:3]
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RELOAD USERBOTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("reloadub") & filters.private & filters.user(OWNER_ID))
async def reload_ub(client: Client, message: Message):
    msg = await message.reply("Userbots reload ho rahe hain...")
    result = await reload_userbots()
    if result:
        await msg.edit(
            f"Userbots reload ho gaye!\n"
            f"Total: {len(userbots)} userbots active\n\n{BRAND}"
        )
    else:
        await msg.edit(
            f"Pehle API ID aur HASH set kar!\n"
            f"/setapi → /sethash → /reloadub"
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CANCEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("cancel") & filters.private & filters.user(OWNER_ID))
async def cancel(client: Client, message: Message):
    setup_state.pop(OWNER_ID, None)
    await message.reply("Cancel kar diya. /start maar.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OWNER DM CHAT — INPUT HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(
    filters.private &
    filters.user(OWNER_ID) &
    ~filters.command([
        "start","setapi","sethash","addsession",
        "delsession","sessions","reloadub","cancel",
        "broadcast","tbroadcast","admincheck",
        "groups","ubstatus"
    ])
)
async def owner_input_handler(client: Client, message: Message):
    user_text = message.text or ""
    state     = setup_state.get(OWNER_ID)

    # ─── API ID input ───
    if state == "waiting_api_id":
        try:
            api_id = int(user_text.strip())
            cfg    = load_config()
            cfg["api_id"] = api_id
            save_config(cfg)
            setup_state.pop(OWNER_ID, None)
            await message.reply(
                f"API ID set ho gaya!\n"
                f"ID: `{api_id}`\n\n"
                f"Ab /sethash maar."
            )
        except ValueError:
            await message.reply("BC sirf number bhej! API ID numbers mein hota hai.")
        return

    # ─── API HASH input ───
    if state == "waiting_api_hash":
        api_hash = user_text.strip()
        if len(api_hash) < 10:
            await message.reply("Yeh API HASH sahi nahi lagta. Dobara check kar.")
            return
        cfg = load_config()
        cfg["api_hash"] = api_hash
        save_config(cfg)
        setup_state.pop(OWNER_ID, None)
        await message.reply(
            f"API HASH set ho gaya!\n\n"
            f"Ab /addsession maar — session string add karo."
        )
        return

    # ─── Session input ───
    if state == "waiting_session":
        session = user_text.strip()
        if not session.startswith("BQA"):
            await message.reply(
                "Yeh session string sahi nahi lagti!\n"
                "BQA se start honi chahiye.\n"
                "Dobara try kar ya /cancel maar."
            )
            return
        add_session(session)
        setup_state.pop(OWNER_ID, None)
        cfg = load_config()
        await message.reply(
            f"Session add ho gaya!\n"
            f"Total sessions: {len(cfg['sessions'])}\n\n"
            f"Aur add karne ke liye /addsession maar.\n"
            f"Userbots activate karne ke liye /reloadub maar."
        )
        return

    # ─── Normal friendly chat ───
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
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(
    filters.group &
    ~filters.command([
        "play","skip","stop","queue","np",
        "broadcast","tbroadcast","admincheck",
        "groups","ubstatus"
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
                f"Gali deta hai pyaar se — mc, bc, bhosdike, chutiye — normal dosto jaisi. "
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
# MUSIC — PLAY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("play") & filters.group)
async def play(client: Client, message: Message):
    chat_id = message.chat.id

    if not pytgcalls_list:
        await message.reply(
            f"Pehle userbots setup kar!\n"
            f"DM mein /setapi → /sethash → /addsession → /reloadub maar"
        )
        return

    if len(message.command) < 2:
        await send_premium(
            client, chat_id,
            f"bc song ka naam toh de!\nExample: /play Kesariya\n\n{BRAND}",
            emoji_ids=[EMOJI_IDS[2]],
            reply_to_message_id=message.id
        )
        return

    query = " ".join(message.command[1:])
    await send_premium(
        client, chat_id,
        f"Dhundh raha hoon: {query}",
        emoji_ids=[EMOJI_IDS[7]],
        reply_to_message_id=message.id
    )

    try:
        url, title = get_audio(query)
    except Exception as e:
        await message.reply(f"Nahi mila!\nError: `{e}`")
        return

    if chat_id not in music_queue:
        music_queue[chat_id] = []
    music_queue[chat_id].append({"url": url, "title": title})

    vc = get_vc(chat_id)

    try:
        await vc.join_group_call(
            chat_id,
            AudioPiped(url, HighQualityAudio())
        )
        await send_premium(
            client, chat_id,
            f"**Ab chal raha hai:**\n{title}\n\n{BRAND}",
            emoji_ids=EMOJI_IDS[:4],
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⏭ Skip", callback_data=f"skip_{chat_id}"),
                    InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{chat_id}")
                ],
                [
                    InlineKeyboardButton("📋 Queue", callback_data=f"queue_{chat_id}")
                ]
            ])
        )
    except Exception:
        await send_premium(
            client, chat_id,
            f"**Queue mein add:**\n{title}\n\n{BRAND}",
            emoji_ids=[EMOJI_IDS[5]]
        )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MUSIC — SKIP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("skip") & filters.group)
async def skip(client: Client, message: Message):
    chat_id = message.chat.id
    vc      = get_vc(chat_id)
    if not vc:
        await message.reply("Koi userbot nahi hai! /reloadub maar DM mein.")
        return
    try:
        if music_queue.get(chat_id):
            music_queue[chat_id].pop(0)
        if music_queue.get(chat_id):
            nxt = music_queue[chat_id][0]
            await vc.change_stream(chat_id, AudioPiped(nxt["url"], HighQualityAudio()))
            await send_premium(
                client, chat_id,
                f"**Skip! Ab:**\n{nxt['title']}\n\n{BRAND}",
                emoji_ids=[EMOJI_IDS[3]],
                reply_to_message_id=message.id
            )
        else:
            await vc.leave_group_call(chat_id)
            await send_premium(
                client, chat_id,
                f"Queue khatam! Bot nikla.\n\n{BRAND}",
                emoji_ids=[EMOJI_IDS[1]],
                reply_to_message_id=message.id
            )
    except Exception as e:
        await message.reply(f"Error: `{e}`")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MUSIC — STOP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("stop") & filters.group)
async def stop(client: Client, message: Message):
    chat_id = message.chat.id
    vc      = get_vc(chat_id)
    if not vc:
        await message.reply("Koi userbot nahi hai!")
        return
    try:
        music_queue[chat_id] = []
        await vc.leave_group_call(chat_id)
        await send_premium(
            client, chat_id,
            f"**Stop! Bot VC se nikla.**\n\n{BRAND}",
            emoji_ids=[EMOJI_IDS[2]],
            reply_to_message_id=message.id
        )
    except Exception as e:
        await message.reply(f"Error: `{e}`")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MUSIC — QUEUE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("queue") & filters.group)
async def queue_list(client: Client, message: Message):
    chat_id = message.chat.id
    q       = music_queue.get(chat_id, [])
    if not q:
        await send_premium(
            client, chat_id,
            f"Queue khaali hai!\n\n{BRAND}",
            emoji_ids=[EMOJI_IDS[8]],
            reply_to_message_id=message.id
        )
        return
    text = f"**Queue ({len(q)} songs):**\n\n"
    for i, t in enumerate(q, 1):
        text += f"{i}. {t['title']}\n"
    text += f"\n{BRAND}"
    await send_premium(
        client, chat_id, text,
        emoji_ids=EMOJI_IDS[:3],
        reply_to_message_id=message.id
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MUSIC — NOW PLAYING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("np") & filters.group)
async def now_playing(client: Client, message: Message):
    chat_id = message.chat.id
    q       = music_queue.get(chat_id, [])
    if not q:
        await send_premium(
            client, chat_id,
            f"Kuch nahi chal raha!\n\n{BRAND}",
            emoji_ids=[EMOJI_IDS[4]],
            reply_to_message_id=message.id
        )
        return
    await send_premium(
        client, chat_id,
        f"**Ab chal raha hai:**\n{q[0]['title']}\n\n{BRAND}",
        emoji_ids=EMOJI_IDS[:4],
        reply_to_message_id=message.id
    )

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

    text   = message.reply_to_message.text or message.reply_to_message.caption
    groups = load_groups()

    if not groups:
        await message.reply(f"Koi group nahi database mein.\n\n{BRAND}")
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
            f"Format: /tbroadcast time message\n"
            f"Example:\n"
            f"/tbroadcast 30m Aaj offer!\n"
            f"/tbroadcast 2h Event raat ko!\n"
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
        await message.reply(f"Format galat! 30m 2h 1d\n\n{BRAND}")
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
        text += f"{i}. {title}\n{chat_id}\n\n"
    text += BRAND
    await send_premium(client, message.chat.id, text, emoji_ids=EMOJI_IDS[:4])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USERBOT STATUS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("ubstatus") & filters.user(OWNER_ID))
async def ub_status(client: Client, message: Message):
    text = f"**Userbot Status:**\n\n"
    if not userbots:
        text += "Koi userbot nahi!\n/reloadub maar setup ke baad."
    else:
        for i, ub in enumerate(userbots, 1):
            try:
                me = await ub.get_me()
                text += f"{i}. {me.first_name}"
                text += f" @{me.username}\n" if me.username else "\n"
            except:
                text += f"{i}. Offline\n"
    text += f"\n{BRAND}"
    await send_premium(client, message.chat.id, text, emoji_ids=EMOJI_IDS[:3])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALLBACKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_callback_query()
async def callbacks(client, cq):
    data = cq.data

    if data == "setup":
        cfg = load_config()
        await cq.answer(
            f"API ID: {'Set' if cfg.get('api_id') else 'Nahi'}\n"
            f"API HASH: {'Set' if cfg.get('api_hash') else 'Nahi'}\n"
            f"Sessions: {len(cfg.get('sessions', []))}",
            show_alert=True
        )
    elif data == "groups":
        g = load_groups()
        await cq.answer(f"Total {len(g)} groups!", show_alert=True)
    elif data == "ubstatus":
        await cq.answer(f"Total {len(userbots)} userbots active!", show_alert=True)
    elif data.startswith("skip_"):
        chat_id = int(data.split("_")[1])
        vc      = get_vc(chat_id)
        if not vc:
            await cq.answer("Koi userbot nahi!", show_alert=True)
            return
        try:
            if music_queue.get(chat_id):
                music_queue[chat_id].pop(0)
            if music_queue.get(chat_id):
                nxt = music_queue[chat_id][0]
                await vc.change_stream(chat_id, AudioPiped(nxt["url"], HighQualityAudio()))
                await cq.answer(f"Skip! Ab: {nxt['title'][:50]}", show_alert=True)
            else:
                await vc.leave_group_call(chat_id)
                await cq.answer("Queue khatam!", show_alert=True)
        except:
            await cq.answer("Error!", show_alert=True)
    elif data.startswith("stop_"):
        chat_id = int(data.split("_")[1])
        vc      = get_vc(chat_id)
        if not vc:
            await cq.answer("Koi userbot nahi!", show_alert=True)
            return
        try:
            music_queue[chat_id] = []
            await vc.leave_group_call(chat_id)
            await cq.answer("Stop!", show_alert=True)
        except:
            await cq.answer("Error!", show_alert=True)
    elif data.startswith("queue_"):
        chat_id = int(data.split("_")[1])
        q       = music_queue.get(chat_id, [])
        if q:
            text = "\n".join([f"{i}. {t['title'][:30]}" for i, t in enumerate(q, 1)])
            await cq.answer(f"Queue:\n{text[:200]}", show_alert=True)
        else:
            await cq.answer("Queue khaali!", show_alert=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ⚡ SUMIT BOTS @T4HKR")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Agar pehle se config hai toh userbots load karo
    cfg = load_config()
    if cfg.get("api_id") and cfg.get("api_hash") and cfg.get("sessions"):
        print("Config mili — userbots load ho rahe hain...")
        await reload_userbots()
        print(f"Total userbots: {len(userbots)}")
    else:
        print("Config nahi mili — bot se setup karo!")
        print("DM mein /start maar aur /setapi se shuru karo")

    await bot.start()
    me = await bot.get_me()
    print(f"Bot: @{me.username}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Sab Chalu! 6767")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    await asyncio.get_event_loop().run_forever()

asyncio.run(main())

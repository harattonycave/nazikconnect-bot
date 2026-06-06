import logging
import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "verifyhof")
ADMIN_CHAT_IDS = [
    os.environ.get("ADMIN_CHAT_ID_1", "8474703406"),
    os.environ.get("ADMIN_CHAT_ID_2", "8808544262"),
]
GROUP_INVITE_LINK = "https://t.me/+wZdBwJCpYpAwMTQ0"
SIGNAL_GROUP_LINK = os.environ.get("SIGNAL_GROUP_LINK", "https://t.me/+s0ACkwJ143E5Y2Y0")
PU_PRIME_LINK = "https://puvip.co/la-partners/777999"
VIDEO_1_LINK = os.environ.get("VIDEO_1_LINK", "https://www.youtube.com/watch?v=Hby1IJFZ8V0")
VIDEO_2_LINK = os.environ.get("VIDEO_2_LINK", "https://www.youtube.com/watch?v=Hby1IJFZ8V0")
BOT_USERNAME = "nazikconnect_bot"
DB_PATH = "nazikconnect.db"

LANG_FLAGS = {"tm": "🇹🇲", "ru": "🇷🇺", "en": "🇬🇧", "tr": "🇹🇷"}
LANG_NAMES = {"tm": "Türkmençe", "ru": "Русский", "en": "English", "tr": "Türkçe"}

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            language TEXT DEFAULT NULL,
            joined_at TEXT,
            bonus_selected TEXT,
            bonus_selected_at TEXT,
            account_opened INTEGER DEFAULT 0,
            account_opened_at TEXT,
            deposit_completed INTEGER DEFAULT 0,
            deposit_completed_at TEXT,
            reminder_1_sent INTEGER DEFAULT 0,
            reminder_2_sent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def migrate_db():
    """Mevcut DB'ye yeni kolonları ekle (varsa atla)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for col in ["reminder_1_sent INTEGER DEFAULT 0", "reminder_2_sent INTEGER DEFAULT 0"]:
        col_name = col.split()[0]
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col}")
        except Exception:
            pass  # Kolon zaten varsa atla
    conn.commit()
    conn.close()

def save_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_language(user_id, language):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
    conn.commit()
    conn.close()

def get_language(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def save_bonus_selection(user_id, bonus):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users SET bonus_selected = ?, bonus_selected_at = ?
        WHERE user_id = ?
    """, (bonus, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def save_account_opened(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users SET account_opened = 1, account_opened_at = ?
        WHERE user_id = ?
    """, (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def save_deposit_completed(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users SET deposit_completed = 1, deposit_completed_at = ?
        WHERE user_id = ?
    """, (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_recent_users(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, language, joined_at, bonus_selected, account_opened, deposit_completed FROM users ORDER BY joined_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def reset_user_progress(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users SET
            bonus_selected = NULL, bonus_selected_at = NULL,
            account_opened = 0, account_opened_at = NULL,
            deposit_completed = 0, deposit_completed_at = NULL
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_all_users_for_export():
    """Export için tüm kullanıcı verilerini döndür."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, first_name, language, joined_at,
               bonus_selected, bonus_selected_at,
               account_opened, account_opened_at,
               deposit_completed, deposit_completed_at
        FROM users ORDER BY joined_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def get_pending_users():
    """Bonus seçmiş ama depozit yapmamış kullanıcılar."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, first_name, language,
               bonus_selected, account_opened, deposit_completed, joined_at
        FROM users
        WHERE bonus_selected IS NOT NULL
          AND deposit_completed = 0
        ORDER BY joined_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def get_users_pending_account(hours=24):
    """Bonus seçmiş ama hesap açmamış, X saatten fazla geçmiş kullanıcılar."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, first_name, language, bonus_selected_at
        FROM users
        WHERE bonus_selected IS NOT NULL
          AND account_opened = 0
          AND deposit_completed = 0
          AND bonus_selected_at IS NOT NULL
          AND (julianday('now') - julianday(bonus_selected_at)) * 24 >= ?
          AND (reminder_1_sent IS NULL OR reminder_1_sent = 0)
    """, (hours,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_users_pending_deposit(hours=48):
    """Hesap açmış ama depozit yapmamış, X saatten fazla geçmiş kullanıcılar."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, first_name, language, account_opened_at
        FROM users
        WHERE account_opened = 1
          AND deposit_completed = 0
          AND account_opened_at IS NOT NULL
          AND (julianday('now') - julianday(account_opened_at)) * 24 >= ?
          AND (reminder_2_sent IS NULL OR reminder_2_sent = 0)
    """, (hours,))
    rows = c.fetchall()
    conn.close()
    return rows

def mark_reminder_sent(user_id, reminder_num):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    col = f"reminder_{reminder_num}_sent"
    c.execute(f"UPDATE users SET {col} = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE bonus_selected IS NOT NULL")
    selected = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE account_opened = 1")
    opened = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE deposit_completed = 1")
    deposited = c.fetchone()[0]
    c.execute("SELECT bonus_selected, COUNT(*) FROM users WHERE bonus_selected IS NOT NULL GROUP BY bonus_selected")
    breakdown = c.fetchall()
    c.execute("SELECT language, COUNT(*) FROM users WHERE language IS NOT NULL GROUP BY language")
    lang_breakdown = c.fetchall()
    conn.close()
    return total, selected, opened, deposited, breakdown, lang_breakdown

# ─────────────────────────────────────────────
# NOTIFY ADMINS — Türkçe
# ─────────────────────────────────────────────
async def notify_admins(context, text):
    for chat_id in ADMIN_CHAT_IDS:
        if chat_id:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Could not notify admin {chat_id}: {e}")

def lang_label(lang):
    return f"{LANG_FLAGS.get(lang, '🌐')} {LANG_NAMES.get(lang, lang)}"

# ─────────────────────────────────────────────
# MESSAGES
# ─────────────────────────────────────────────

LANG_SELECT_TEXT = "🌐 Diliňizi saýlaň / Выберите язык / Choose your language / Dil seçin"

WELCOME_TEXT = {
    "tm": """👋 Salam, {name}!

*Nazik Connect* jemgyýetine hoş geldiňiz! 🎉

📊 Her gün *8-10 signal* — *MetaTrader 5* platformasy
📈 Ýeňiş derejesi: *%90 we ondan ýokary*

━━━━━━━━━━━━━━━
💎 *Aýratyn Bonus Tekliplerimiz:*
• 250$ goýsaňyz → *125$ bonus* 🎁
• 500$ goýsaňyz → *250$ bonus* 🎁
• 1000$ goýsaňyz → *500$ bonus* 🎁
━━━━━━━━━━━━━━━

Haýsy teklibi saýlaýarsyňyz? 👇""",

    "ru": """👋 Привет, {name}!

Добро пожаловать в *Nazik Connect*! 🎉

📊 Каждый день *8-10 сигналов* — платформа *MetaTrader 5*
📈 Процент побед: *90% и выше*

━━━━━━━━━━━━━━━
💎 *Специальные бонусы:*
• Депозит 250$ → *125$ бонус* 🎁
• Депозит 500$ → *250$ бонус* 🎁
• Депозит 1000$ → *500$ бонус* 🎁
━━━━━━━━━━━━━━━

Выберите предложение 👇""",

    "en": """👋 Hello, {name}!

Welcome to *Nazik Connect*! 🎉

📊 *8-10 signals* every day — *MetaTrader 5* platform
📈 Win rate: *90% and above*

━━━━━━━━━━━━━━━
💎 *Exclusive Bonus Offers:*
• Deposit 250$ → *125$ bonus* 🎁
• Deposit 500$ → *250$ bonus* 🎁
• Deposit 1000$ → *500$ bonus* 🎁
━━━━━━━━━━━━━━━

Which offer would you like? 👇""",

    "tr": """👋 Merhaba, {name}!

*Nazik Connect* topluluğuna hoş geldiniz! 🎉

📊 Her gün *8-10 sinyal* — *MetaTrader 5* platformu
📈 Kazanma oranı: *%90 ve üzeri*

━━━━━━━━━━━━━━━
💎 *Özel Bonus Tekliflerimiz:*
• 250$ yatırırsanız → *125$ bonus* 🎁
• 500$ yatırırsanız → *250$ bonus* 🎁
• 1000$ yatırırsanız → *500$ bonus* 🎁
━━━━━━━━━━━━━━━

Hangi teklifi seçiyorsunuz? 👇""",
}

START_TEXT = {
    "tm": """👋 Salam, {name}!

🏆 *Nazik Connect Bot*-a hoş geldiňiz!

📈 Her gün *8-10 forex signal*
✅ *%90+* ýeňiş derejesi
🎓 Mugt söwda okuw mekdebi
💰 *PU Prime* broker bilen aýratyn bonuslar

━━━━━━━━━━━━━━━
💎 *Bonus Tekliplerimiz:*
• 250$ → *125$ bonus*
• 500$ → *250$ bonus*
• 1000$ → *500$ bonus*
━━━━━━━━━━━━━━━

Başlamak üçin aşakdaky düwmä basyň 👇""",

    "ru": """👋 Привет, {name}!

🏆 Добро пожаловать в *Nazik Connect Bot*!

📈 Каждый день *8-10 форекс сигналов*
✅ Процент побед *90%+*
🎓 Бесплатная школа трейдинга
💰 Эксклюзивные бонусы с брокером *PU Prime*

━━━━━━━━━━━━━━━
💎 *Наши бонусы:*
• 250$ → *125$ бонус*
• 500$ → *250$ бонус*
• 1000$ → *500$ бонус*
━━━━━━━━━━━━━━━

Нажмите кнопку ниже чтобы начать 👇""",

    "en": """👋 Hello, {name}!

🏆 Welcome to *Nazik Connect Bot*!

📈 *8-10 forex signals* every day
✅ *90%+* win rate
🎓 Free trading school
💰 Exclusive bonuses with *PU Prime* broker

━━━━━━━━━━━━━━━
💎 *Our Bonuses:*
• 250$ → *125$ bonus*
• 500$ → *250$ bonus*
• 1000$ → *500$ bonus*
━━━━━━━━━━━━━━━

Press the button below to get started 👇""",

    "tr": """👋 Merhaba, {name}!

🏆 *Nazik Connect Bot*'a hoş geldiniz!

📈 Her gün *8-10 forex sinyali*
✅ *%90+* kazanma oranı
🎓 Ücretsiz ticaret okulu
💰 *PU Prime* broker ile özel bonuslar

━━━━━━━━━━━━━━━
💎 *Bonuslarımız:*
• 250$ → *125$ bonus*
• 500$ → *250$ bonus*
• 1000$ → *500$ bonus*
━━━━━━━━━━━━━━━

Başlamak için aşağıdaki butona basın 👇""",
}

RESPONSES = {
    "tm": {
        "250": "✅ *250$ → 125$ Bonus* saýladyňyz!\n\nÄdimler:\n1️⃣ Aşakdaky baglantydan *PU Prime* hasabyny açyň\n2️⃣ Hasabyňyza *250$* goýuň\n3️⃣ Awtomatik *125$ bonus* alarsyňyz 🎁\n\n👉 *Hasaby açmak üçin:* {link}\n\n📹 Hasaby nädip açmaly? Aşakdaky düwmä basyň 👇",
        "500": "✅ *500$ → 250$ Bonus* saýladyňyz!\n\nÄdimler:\n1️⃣ Aşakdaky baglantydan *PU Prime* hasabyny açyň\n2️⃣ Hasabyňyza *500$* goýuň\n3️⃣ Awtomatik *250$ bonus* alarsyňyz 🎁\n\n👉 *Hasaby açmak üçin:* {link}\n\n📹 Hasaby nädip açmaly? Aşakdaky düwmä basyň 👇",
        "1000": "✅ *1000$ → 500$ Bonus* saýladyňyz!\n\nÄdimler:\n1️⃣ Aşakdaky baglantydan *PU Prime* hasabyny açyň\n2️⃣ Hasabyňyza *1000$* goýuň\n3️⃣ Awtomatik *500$ bonus* alarsyňyz 🎁\n\n👉 *Hasaby açmak üçin:* {link}\n\n📹 Hasaby nädip açmaly? Aşakdaky düwmä basyň 👇",
    },
    "ru": {
        "250": "✅ Вы выбрали *250$ → 125$ Бонус*!\n\nШаги:\n1️⃣ Откройте счёт *PU Prime* по ссылке ниже\n2️⃣ Внесите *250$* на счёт\n3️⃣ Автоматически получите *125$ бонус* 🎁\n\n👉 *Открыть счёт:* {link}\n\n📹 Как открыть счёт? Нажмите кнопку ниже 👇",
        "500": "✅ Вы выбрали *500$ → 250$ Бонус*!\n\nШаги:\n1️⃣ Откройте счёт *PU Prime* по ссылке ниже\n2️⃣ Внесите *500$* на счёт\n3️⃣ Автоматически получите *250$ бонус* 🎁\n\n👉 *Открыть счёт:* {link}\n\n📹 Как открыть счёт? Нажмите кнопку ниже 👇",
        "1000": "✅ Вы выбрали *1000$ → 500$ Бонус*!\n\nШаги:\n1️⃣ Откройте счёт *PU Prime* по ссылке ниже\n2️⃣ Внесите *1000$* на счёт\n3️⃣ Автоматически получите *500$ бонус* 🎁\n\n👉 *Открыть счёт:* {link}\n\n📹 Как открыть счёт? Нажмите кнопку ниже 👇",
    },
    "en": {
        "250": "✅ You selected *250$ → 125$ Bonus*!\n\nSteps:\n1️⃣ Open a *PU Prime* account via the link below\n2️⃣ Deposit *250$* to your account\n3️⃣ Automatically receive *125$ bonus* 🎁\n\n👉 *Open account:* {link}\n\n📹 How to open an account? Press the button below 👇",
        "500": "✅ You selected *500$ → 250$ Bonus*!\n\nSteps:\n1️⃣ Open a *PU Prime* account via the link below\n2️⃣ Deposit *500$* to your account\n3️⃣ Automatically receive *250$ bonus* 🎁\n\n👉 *Open account:* {link}\n\n📹 How to open an account? Press the button below 👇",
        "1000": "✅ You selected *1000$ → 500$ Bonus*!\n\nSteps:\n1️⃣ Open a *PU Prime* account via the link below\n2️⃣ Deposit *1000$* to your account\n3️⃣ Automatically receive *500$ bonus* 🎁\n\n👉 *Open account:* {link}\n\n📹 How to open an account? Press the button below 👇",
    },
    "tr": {
        "250": "✅ *250$ → 125$ Bonus* seçtiniz!\n\nAdımlar:\n1️⃣ Aşağıdaki linkten *PU Prime* hesabı açın\n2️⃣ Hesabınıza *250$* yatırın\n3️⃣ Otomatik olarak *125$ bonus* alırsınız 🎁\n\n👉 *Hesap açmak için:* {link}\n\n📹 Hesap nasıl açılır? Aşağıdaki butona basın 👇",
        "500": "✅ *500$ → 250$ Bonus* seçtiniz!\n\nAdımlar:\n1️⃣ Aşağıdaki linkten *PU Prime* hesabı açın\n2️⃣ Hesabınıza *500$* yatırın\n3️⃣ Otomatik olarak *250$ bonus* alırsınız 🎁\n\n👉 *Hesap açmak için:* {link}\n\n📹 Hesap nasıl açılır? Aşağıdaki butona basın 👇",
        "1000": "✅ *1000$ → 500$ Bonus* seçtiniz!\n\nAdımlar:\n1️⃣ Aşağıdaki linkten *PU Prime* hesabı açın\n2️⃣ Hesabınıza *1000$* yatırın\n3️⃣ Otomatik olarak *500$ bonus* alırsınız 🎁\n\n👉 *Hesap açmak için:* {link}\n\n📹 Hesap nasıl açılır? Aşağıdaki butona basın 👇",
    },
}

VIDEO2_TEXT = {
    "tm": "🎉 Tebrikler, {name}!\n\nBonusy nädip işjeňleşdirmeli we pul goýmaly?\nAşakdaky düwmä basyň 👇\n\n📹 *Bonus aktivasyon & depozit:*\n{video2}\n\n━━━━━━━━━━━━━━━\n✅ Tamamlansoňyz aşakdaky düwmä basyň 👇",
    "ru": "🎉 Поздравляем, {name}!\n\nТеперь нужно активировать бонус и внести депозит.\n\n📹 *Активация бонуса и депозит:*\n{video2}\n\n━━━━━━━━━━━━━━━\n✅ После завершения нажмите кнопку ниже 👇",
    "en": "🎉 Congratulations, {name}!\n\nNow you need to activate your bonus and make a deposit.\n\n📹 *Bonus activation & deposit:*\n{video2}\n\n━━━━━━━━━━━━━━━\n✅ Once done, press the button below 👇",
    "tr": "🎉 Tebrikler, {name}!\n\nŞimdi bonusu aktive etmeniz ve para yatırmanız gerekiyor.\n\n📹 *Bonus aktivasyon & para yatırma:*\n{video2}\n\n━━━━━━━━━━━━━━━\n✅ Tamamladıktan sonra aşağıdaki butona basın 👇",
}

DEPOSIT_DONE_TEXT = {
    "tm": "🏆 *Gutlaýarys, {name}!*\n\nSiz üstünlikli:\n✅ PU Prime hasabyny açdyňyz\n✅ Bonusy işjeňleşdirdiňiz\n✅ Pul goýduňyz\n\nIndi *VIP Signals* toparymyza goşulyp bilersiňiz!\n\n👇 Baglantyny basyň — admin tassyklansoň sizi goşarlar 🎯\n\n{signal_link}",
    "ru": "🏆 *Поздравляем, {name}!*\n\nВы успешно:\n✅ Открыли счёт PU Prime\n✅ Активировали бонус\n✅ Внесли депозит\n\nТеперь вы можете вступить в группу *VIP Signals*!\n\n👇 Нажмите ссылку — после подтверждения админа вас добавят 🎯\n\n{signal_link}",
    "en": "🏆 *Congratulations, {name}!*\n\nYou have successfully:\n✅ Opened a PU Prime account\n✅ Activated your bonus\n✅ Made a deposit\n\nYou can now join our *VIP Signals* group!\n\n👇 Click the link — admin will approve and add you 🎯\n\n{signal_link}",
    "tr": "🏆 *Tebrikler, {name}!*\n\nBaşarıyla:\n✅ PU Prime hesabı açtınız\n✅ Bonusu aktive ettiniz\n✅ Para yatırdınız\n\nArtık *VIP Signals* grubuna katılabilirsiniz!\n\n👇 Linke tıklayın — admin onayladıktan sonra sizi eklerler 🎯\n\n{signal_link}",
}

# ─────────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────────
def get_lang_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇹🇲 Türkmençe", callback_data="lang_tm"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        ],
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
        ],
    ])

BONUS_LABELS = {
    "tm": ["💵 250$ → 125$ Bonus", "💵 500$ → 250$ Bonus", "💵 1000$ → 500$ Bonus"],
    "ru": ["💵 250$ → 125$ Бонус", "💵 500$ → 250$ Бонус", "💵 1000$ → 500$ Бонус"],
    "en": ["💵 250$ → 125$ Bonus", "💵 500$ → 250$ Bonus", "💵 1000$ → 500$ Bonus"],
    "tr": ["💵 250$ → 125$ Bonus", "💵 500$ → 250$ Bonus", "💵 1000$ → 500$ Bonus"],
}

START_BTN = {
    "tm": ("🚀 Bonus Saýla", "📢 MetaTrader 5 Topara Goşul"),
    "ru": ("🚀 Выбрать бонус", "📢 Присоединиться к MetaTrader 5"),
    "en": ("🚀 Choose Bonus", "📢 Join MetaTrader 5 Group"),
    "tr": ("🚀 Bonus Seç", "📢 MetaTrader 5 Grubuna Katıl"),
}

VIDEO1_BTN = {
    "tm": ("📹 Hasaby Açmak Wideosy", "✅ Hasaby Açdym!"),
    "ru": ("📹 Видео открытия счёта", "✅ Счёт открыт!"),
    "en": ("📹 Account Opening Video", "✅ Account Opened!"),
    "tr": ("📹 Hesap Açma Videosu", "✅ Hesabı Açtım!"),
}

VIDEO2_BTN = {
    "tm": ("📹 Bonus & Depozit Wideosy", "✅ Depozit Goýdum!"),
    "ru": ("📹 Видео бонуса и депозита", "✅ Депозит внесён!"),
    "en": ("📹 Bonus & Deposit Video", "✅ Deposit Done!"),
    "tr": ("📹 Bonus & Para Yatırma Videosu", "✅ Para Yatırdım!"),
}

def get_bonus_keyboard(lang):
    labels = BONUS_LABELS.get(lang, BONUS_LABELS["en"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(labels[0], callback_data="bonus_250")],
        [InlineKeyboardButton(labels[1], callback_data="bonus_500")],
        [InlineKeyboardButton(labels[2], callback_data="bonus_1000")],
    ])

def get_start_keyboard(lang):
    btns = START_BTN.get(lang, START_BTN["en"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btns[0], callback_data="show_bonuses")],
        [InlineKeyboardButton(btns[1], url=GROUP_INVITE_LINK)],
    ])

def get_video1_keyboard(lang):
    btns = VIDEO1_BTN.get(lang, VIDEO1_BTN["en"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btns[0], url=VIDEO_1_LINK)],
        [InlineKeyboardButton(btns[1], callback_data="account_opened")],
    ])

def get_video2_keyboard(lang):
    btns = VIDEO2_BTN.get(lang, VIDEO2_BTN["en"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(btns[0], url=VIDEO_2_LINK)],
        [InlineKeyboardButton(btns[1], callback_data="deposit_done")],
    ])

# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username, user.first_name)
    lang = get_language(user.id)
    name = user.first_name or "Agza"

    if lang:
        await update.message.reply_text(
            START_TEXT[lang].format(name=name),
            parse_mode="Markdown",
            reply_markup=get_start_keyboard(lang)
        )
    else:
        await update.message.reply_text(
            LANG_SELECT_TEXT,
            reply_markup=get_lang_keyboard()
        )

async def davet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_language(user.id) or "tm"
    texts = {
        "tm": f"📢 *MetaTrader 5* toparyna goşulmak üçin:\n\n👉 {GROUP_INVITE_LINK}",
        "ru": f"📢 Присоединиться к группе *MetaTrader 5*:\n\n👉 {GROUP_INVITE_LINK}",
        "en": f"📢 Join the *MetaTrader 5* group:\n\n👉 {GROUP_INVITE_LINK}",
        "tr": f"📢 *MetaTrader 5* grubuna katılmak için:\n\n👉 {GROUP_INVITE_LINK}",
    }
    await update.message.reply_text(texts[lang], parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != ADMIN_USERNAME:
        return
    total, selected, opened, deposited, breakdown, lang_breakdown = get_stats()
    breakdown_text = "\n".join([f"  • {b[0]}$: {b[1]} üye" for b in breakdown]) or "  Henüz yok"
    lang_text = "\n".join([
        f"  • {LANG_FLAGS.get(l[0], '🌐')} {LANG_NAMES.get(l[0], l[0])}: {l[1]} üye"
        for l in lang_breakdown
    ]) or "  Yok"
    text = f"""📊 *Nazik Connect Bot İstatistikleri*

👥 Toplam üye: *{total}*
🎯 Bonus seçenler: *{selected}*
🏦 Hesap açanlar: *{opened}*
✅ Depozit yapanlar: *{deposited}*

💰 Bonus seçimi:
{breakdown_text}

🌐 Dil dağılımı:
{lang_text}"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if result.new_chat_member.status not in ["member", "administrator", "creator"]:
        return
    if result.old_chat_member.status in ["member", "administrator", "creator"]:
        return

    user = result.new_chat_member.user
    if user.is_bot:
        return

    name = user.first_name or "Agza"
    save_user(user.id, user.username, user.first_name)

    import asyncio
    group_text = (
        f"👋 {name}!\n\n"
        f"🇹🇲 Hoş geldiňiz! → @{BOT_USERNAME}\n"
        f"🇷🇺 Добро пожаловать! → @{BOT_USERNAME}\n"
        f"🇬🇧 Welcome! → @{BOT_USERNAME}\n"
        f"🇹🇷 Hoş geldiniz! → @{BOT_USERNAME}"
    )
    welcome_msg = await context.bot.send_message(
        chat_id=result.chat.id,
        text=group_text,
    )

    async def delete_welcome():
        await asyncio.sleep(300)
        try:
            await context.bot.delete_message(
                chat_id=result.chat.id,
                message_id=welcome_msg.message_id
            )
        except Exception as e:
            logger.warning(f"Could not delete welcome message: {e}")
    asyncio.create_task(delete_welcome())

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=LANG_SELECT_TEXT,
            reply_markup=get_lang_keyboard()
        )
    except Exception as e:
        logger.warning(f"Could not send DM to {user.id}: {e}")

    username_str = f"@{user.username}" if user.username else "username yok"
    await notify_admins(
        context,
        f"🔔 *Yeni üye katıldı!*\n\n"
        f"👤 Ad: {name}\n"
        f"🔗 {username_str}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    name = user.first_name or "Agza"
    data = query.data
    username_str = f"@{user.username}" if user.username else "username yok"

    # ── Dil seçimi ──
    if data.startswith("lang_"):
        lang = data.split("_")[1]
        save_language(user.id, lang)
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.reply_text(
            WELCOME_TEXT[lang].format(name=name),
            parse_mode="Markdown",
            reply_markup=get_bonus_keyboard(lang)
        )
        await notify_admins(
            context,
            f"🌐 *Dil seçildi*\n\n"
            f"👤 {name} ({username_str})\n"
            f"🗣 {lang_label(lang)}\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        return

    lang = get_language(user.id) or "tm"

    if data == "show_bonuses":
        await query.message.reply_text(
            WELCOME_TEXT[lang].format(name=name),
            parse_mode="Markdown",
            reply_markup=get_bonus_keyboard(lang)
        )

    elif data.startswith("bonus_"):
        amount = data.split("_")[1]
        if amount in RESPONSES.get(lang, {}):
            save_bonus_selection(user.id, amount)
            text = RESPONSES[lang][amount].format(link=PU_PRIME_LINK)
            await query.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_video1_keyboard(lang)
            )
            await notify_admins(
                context,
                f"💰 *Bonus seçildi!*\n\n"
                f"👤 {name} ({username_str})\n"
                f"💵 Seçilen paket: *{amount}$*\n"
                f"🗣 {lang_label(lang)}\n"
                f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )

    elif data == "account_opened":
        save_account_opened(user.id)
        await query.message.reply_text(
            VIDEO2_TEXT[lang].format(name=name, video2=VIDEO_2_LINK),
            parse_mode="Markdown",
            reply_markup=get_video2_keyboard(lang)
        )
        await notify_admins(
            context,
            f"🏦 *Hesap açıldı!*\n\n"
            f"👤 {name} ({username_str})\n"
            f"🆔 ID: `{user.id}`\n"
            f"🗣 {lang_label(lang)}\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    elif data == "deposit_done":
        save_deposit_completed(user.id)
        await query.message.reply_text(
            DEPOSIT_DONE_TEXT[lang].format(name=name, signal_link=SIGNAL_GROUP_LINK),
            parse_mode="Markdown"
        )
        await notify_admins(
            context,
            f"✅ *Depozit yapıldı! VIP Signals onayı gerekiyor!*\n\n"
            f"👤 {name} ({username_str})\n"
            f"🆔 ID: `{user.id}`\n"
            f"🗣 {lang_label(lang)}\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"⚡ Bu üyeyi VIP Signals grubuna ekleyin!"
        )

# ─────────────────────────────────────────────
# USER COMMANDS
# ─────────────────────────────────────────────
async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dili yeniden seç."""
    await update.message.reply_text(
        LANG_SELECT_TEXT,
        reply_markup=get_lang_keyboard()
    )

async def cmd_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bonus tekliflerini göster."""
    user = update.effective_user
    lang = get_language(user.id) or "tm"
    name = user.first_name or "Agza"
    await update.message.reply_text(
        WELCOME_TEXT[lang].format(name=name),
        parse_mode="Markdown",
        reply_markup=get_bonus_keyboard(lang)
    )

async def cmd_broker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PU Prime linkini gönder."""
    user = update.effective_user
    lang = get_language(user.id) or "tm"
    texts = {
        "tm": f"🏦 *PU Prime* broker bilen söwda başlaň:\n\n👉 {PU_PRIME_LINK}",
        "ru": f"🏦 Начните торговать с брокером *PU Prime*:\n\n👉 {PU_PRIME_LINK}",
        "en": f"🏦 Start trading with *PU Prime* broker:\n\n👉 {PU_PRIME_LINK}",
        "tr": f"🏦 *PU Prime* broker ile işlem yapmaya başlayın:\n\n👉 {PU_PRIME_LINK}",
    }
    await update.message.reply_text(texts[lang], parse_mode="Markdown")

async def cmd_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """VIP Signals bilgisi ve linki."""
    user = update.effective_user
    lang = get_language(user.id) or "tm"
    texts = {
        "tm": f"📊 *VIP Signals* topary\n\nHer gün *8-10 signal* — MetaTrader 5\nÝeňiş derejesi: *%90+*\n\n👉 {SIGNAL_GROUP_LINK}\n\n_Not: Topara goşulmak üçin depozit goýmaly._",
        "ru": f"📊 Группа *VIP Signals*\n\nКаждый день *8-10 сигналов* — MetaTrader 5\nПроцент побед: *90%+*\n\n👉 {SIGNAL_GROUP_LINK}\n\n_Примечание: Для вступления необходим депозит._",
        "en": f"📊 *VIP Signals* Group\n\n*8-10 signals* every day — MetaTrader 5\nWin rate: *90%+*\n\n👉 {SIGNAL_GROUP_LINK}\n\n_Note: Deposit required to join._",
        "tr": f"📊 *VIP Signals* Grubu\n\nHer gün *8-10 sinyal* — MetaTrader 5\nKazanma oranı: *%90+*\n\n👉 {SIGNAL_GROUP_LINK}\n\n_Not: Gruba katılmak için depozit gereklidir._",
    }
    await update.message.reply_text(texts[lang], parse_mode="Markdown")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Komut listesini göster — admin ise ekstra komutlar da görünür."""
    user = update.effective_user
    is_admin = user.username == ADMIN_USERNAME

    user_commands = """📋 *Komutlar / Commands*

/start — Başlat / Start
/language — Dil değiştir / Change language
/bonus — Bonus teklifleri / Bonus offers
/broker — PU Prime linki / PU Prime link
/signals — VIP Signals bilgisi / VIP Signals info
/status — Adım durumunu gör / Check your progress
/help — Bu menü / This menu"""

    admin_commands = """

━━━━━━━━━━━━━━━
🛡 *Admin Komutları*

/stats — İstatistikler
/broadcast <mesaj> — Tüm kullanıcılara mesaj gönder
/user <user\\_id> — Üye detayı
/list — Son 10 kayıt
/pending — Depozit bekleyenler
/export — DB'yi CSV olarak indir
/reset <user\\_id> — Üyenin adımlarını sıfırla
/kick <user\\_id> — Gruptan at"""

    text = user_commands + (admin_commands if is_admin else "")
    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────────
# ADMIN COMMANDS
# ─────────────────────────────────────────────
def is_admin(user):
    return user.username == ADMIN_USERNAME

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast <mesaj> — tüm kullanıcılara DM gönder."""
    if not is_admin(update.effective_user):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: /broadcast <mesaj>")
        return

    message_text = " ".join(context.args)
    user_ids = get_all_user_ids()
    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(f"📤 Gönderiliyor... (0/{len(user_ids)})")

    for i, uid in enumerate(user_ids):
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=message_text,
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            failed += 1

        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"📤 Gönderiliyor... ({i+1}/{len(user_ids)})")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ *Broadcast tamamlandı!*\n\n"
        f"📤 Gönderildi: *{sent}*\n"
        f"❌ Başarısız: *{failed}*\n"
        f"👥 Toplam: *{len(user_ids)}*",
        parse_mode="Markdown"
    )

async def cmd_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/user <user_id> — üye detayı."""
    if not is_admin(update.effective_user):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: /user <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Geçersiz user_id.")
        return

    row = get_user_by_id(target_id)
    if not row:
        await update.message.reply_text("❌ Kullanıcı bulunamadı.")
        return

    user_id, username, first_name, language, joined_at, bonus_selected, bonus_at, acc_opened, acc_at, dep_done, dep_at = row
    username_str = f"@{username}" if username else "yok"
    lang_str = lang_label(language) if language else "Seçilmedi"

    text = (
        f"👤 *Üye Detayı*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"👤 Ad: {first_name}\n"
        f"🔗 Username: {username_str}\n"
        f"🌐 Dil: {lang_str}\n"
        f"📅 Katılım: {joined_at[:16] if joined_at else 'bilinmiyor'}\n\n"
        f"💰 Bonus: {bonus_selected + '$' if bonus_selected else '❌ Seçilmedi'}\n"
        f"🏦 Hesap: {'✅ Açık' if acc_opened else '❌ Açılmadı'}\n"
        f"💵 Depozit: {'✅ Yapıldı' if dep_done else '❌ Yapılmadı'}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/list — son 10 üye."""
    if not is_admin(update.effective_user):
        return

    rows = get_recent_users(10)
    if not rows:
        await update.message.reply_text("📭 Henüz kayıt yok.")
        return

    lines = ["👥 *Son 10 Üye*\n"]
    for row in rows:
        user_id, username, first_name, language, joined_at, bonus_selected, acc_opened, dep_done = row
        username_str = f"@{username}" if username else "—"
        status = []
        if bonus_selected:
            status.append(f"💰{bonus_selected}$")
        if acc_opened:
            status.append("🏦")
        if dep_done:
            status.append("✅")
        status_str = " ".join(status) if status else "🆕"
        date_str = joined_at[:10] if joined_at else "?"
        lines.append(f"`{user_id}` | {first_name} ({username_str}) | {status_str} | {date_str}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reset <user_id> — üyenin adımlarını sıfırla."""
    if not is_admin(update.effective_user):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: /reset <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Geçersiz user_id.")
        return

    row = get_user_by_id(target_id)
    if not row:
        await update.message.reply_text("❌ Kullanıcı bulunamadı.")
        return

    reset_user_progress(target_id)
    await update.message.reply_text(
        f"✅ `{target_id}` ID'li üyenin adımları sıfırlandı.\n"
        f"(Bonus, hesap, depozit bilgileri temizlendi.)",
        parse_mode="Markdown"
    )

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/kick <user_id> — kullanıcıyı gruptan at."""
    if not is_admin(update.effective_user):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Kullanım: /kick <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Geçersiz user_id.")
        return

    # Bot'un hangi grupta olduğunu bilmek için GROUP_ID env var gerekli
    group_id = os.environ.get("GROUP_ID")
    if not group_id:
        await update.message.reply_text(
            "⚠️ GROUP_ID environment variable tanımlı değil.\n"
            "Railway'de GROUP_ID ekleyin."
        )
        return

    try:
        await context.bot.ban_chat_member(chat_id=int(group_id), user_id=target_id)
        await context.bot.unban_chat_member(chat_id=int(group_id), user_id=target_id)  # ban+unban = kick
        await update.message.reply_text(f"✅ `{target_id}` ID'li kullanıcı gruptan atıldı.", parse_mode="Markdown")
        await notify_admins(
            context,
            f"🚫 *Kullanıcı gruptan atıldı!*\n\n🆔 ID: `{target_id}`\n👮 Admin: @{update.effective_user.username}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/export — tüm DB'yi CSV olarak gönder."""
    if not is_admin(update.effective_user):
        return

    rows = get_all_users_for_export()
    if not rows:
        await update.message.reply_text("📭 Henüz kayıt yok.")
        return

    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "user_id", "username", "first_name", "language", "joined_at",
        "bonus_selected", "bonus_selected_at",
        "account_opened", "account_opened_at",
        "deposit_completed", "deposit_completed_at"
    ])
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    filename = f"nazikconnect_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    await update.message.reply_document(
        document=csv_bytes,
        filename=filename,
        caption=f"📊 *Nazik Connect DB Export*\n👥 Toplam: {len(rows)} üye\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode="Markdown"
    )

async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pending — bonus seçmiş ama depozit yapmamış üyeler."""
    if not is_admin(update.effective_user):
        return

    rows = get_pending_users()
    if not rows:
        await update.message.reply_text("✅ Bekleyen kullanıcı yok!")
        return

    # Sayfa başlığı
    total = len(rows)
    lines = [f"⏳ *Bekleyen Üyeler* ({total} kişi)\n"]

    for row in rows[:20]:  # Max 20 göster (Telegram mesaj limiti)
        user_id, username, first_name, language, bonus_selected, acc_opened, dep_done, joined_at = row
        username_str = f"@{username}" if username else "—"
        lang_str = LANG_FLAGS.get(language, "🌐") if language else "?"

        # Adım durumu
        if not acc_opened:
            step = "💰 Bonus seçti, hesap açmadı"
        else:
            step = "🏦 Hesap açtı, depozit yok"

        lines.append(
            f"`{user_id}` {lang_str} {first_name} ({username_str})\n"
            f"   └ {step} — *{bonus_selected}$*"
        )

    if total > 20:
        lines.append(f"\n_...ve {total - 20} kişi daha. /export ile tam listeyi alın._")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status — kullanıcı kendi adımlarını görür."""
    user = update.effective_user
    lang = get_language(user.id) or "tm"
    row = get_user_by_id(user.id)

    if not row:
        await update.message.reply_text("⚠️ Kayıt bulunamadı. /start yazın.")
        return

    user_id, username, first_name, language, joined_at, bonus_selected, bonus_at, acc_opened, acc_at, dep_done, dep_at, r1, r2 = row

    STATUS_TEXT = {
        "tm": {
            "title": "📋 *Siziň ýagdaýyňyz*",
            "bonus": "💰 Bonus saýlawy",
            "account": "🏦 PU Prime hasaby",
            "deposit": "💵 Depozit",
            "signals": "📊 VIP Signals",
            "yes": "✅",
            "no": "⏳ Garaşylýar",
            "not_selected": "❌ Saýlanmady",
            "footer_done": "Gutlaýarys! Ähli ädimler tamamlandy 🎉",
            "footer_pending": "Dowam etmek üçin /bonus ýazyň 👇",
        },
        "ru": {
            "title": "📋 *Ваш прогресс*",
            "bonus": "💰 Выбор бонуса",
            "account": "🏦 Счёт PU Prime",
            "deposit": "💵 Депозит",
            "signals": "📊 VIP Signals",
            "yes": "✅",
            "no": "⏳ Ожидается",
            "not_selected": "❌ Не выбран",
            "footer_done": "Поздравляем! Все шаги завершены 🎉",
            "footer_pending": "Продолжить: /bonus 👇",
        },
        "en": {
            "title": "📋 *Your Progress*",
            "bonus": "💰 Bonus selection",
            "account": "🏦 PU Prime account",
            "deposit": "💵 Deposit",
            "signals": "📊 VIP Signals",
            "yes": "✅",
            "no": "⏳ Pending",
            "not_selected": "❌ Not selected",
            "footer_done": "Congratulations! All steps completed 🎉",
            "footer_pending": "Continue: /bonus 👇",
        },
        "tr": {
            "title": "📋 *İlerleme Durumunuz*",
            "bonus": "💰 Bonus seçimi",
            "account": "🏦 PU Prime hesabı",
            "deposit": "💵 Depozit",
            "signals": "📊 VIP Signals",
            "yes": "✅",
            "no": "⏳ Bekleniyor",
            "not_selected": "❌ Seçilmedi",
            "footer_done": "Tebrikler! Tüm adımlar tamamlandı 🎉",
            "footer_pending": "Devam etmek için /bonus yazın 👇",
        },
    }

    t = STATUS_TEXT[lang]
    bonus_str = f"{t['yes']} {bonus_selected}$" if bonus_selected else t["not_selected"]
    account_str = t["yes"] if acc_opened else t["no"]
    deposit_str = t["yes"] if dep_done else t["no"]
    signals_str = t["yes"] if dep_done else t["no"]
    all_done = bool(bonus_selected and acc_opened and dep_done)

    text = (
        f"{t['title']}\n\n"
        f"{t['bonus']}: {bonus_str}\n"
        f"{t['account']}: {account_str}\n"
        f"{t['deposit']}: {deposit_str}\n"
        f"{t['signals']}: {signals_str}\n\n"
        f"{'━' * 16}\n"
        f"{'🎉' if all_done else '👇'} {t['footer_done'] if all_done else t['footer_pending']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────────
# REMINDER MESSAGES
# ─────────────────────────────────────────────

REMINDER_1_TEXT = {
    "tm": """⏰ Salam, {name}!

*{amount}$ bonus* teklibiňizi saýladyňyz, ýöne heniz hasap açmadyňyz.

Bonusy almak üçin diňe *2 minut* gerek:
1️⃣ Aşakdaky baglantydan *PU Prime* hasabyny açyň
2️⃣ *{amount}$* goýuň → *{bonus}$ bonus* awtomatik gelýär 🎁

👉 {link}

Soraglaryňyz bar bolsa, bize ýazyň! 💬""",

    "ru": """⏰ Привет, {name}!

Вы выбрали бонус *{amount}$*, но ещё не открыли счёт.

Чтобы получить бонус, нужно всего *2 минуты*:
1️⃣ Откройте счёт *PU Prime* по ссылке ниже
2️⃣ Внесите *{amount}$* → *{bonus}$ бонус* придёт автоматически 🎁

👉 {link}

Если есть вопросы — напишите нам! 💬""",

    "en": """⏰ Hey {name}!

You selected the *{amount}$ bonus* but haven't opened an account yet.

It only takes *2 minutes*:
1️⃣ Open a *PU Prime* account via the link below
2️⃣ Deposit *{amount}$* → *{bonus}$ bonus* arrives automatically 🎁

👉 {link}

Any questions? Just message us! 💬""",

    "tr": """⏰ Merhaba {name}!

*{amount}$ bonus* teklifini seçtiniz ama henüz hesap açmadınız.

Bonusu almak için sadece *2 dakika* gerekiyor:
1️⃣ Aşağıdaki linkten *PU Prime* hesabı açın
2️⃣ *{amount}$* yatırın → *{bonus}$ bonus* otomatik gelir 🎁

👉 {link}

Sorularınız varsa bize yazın! 💬""",
}

REMINDER_2_TEXT = {
    "tm": """⏰ Salam, {name}!

*PU Prime* hasabyňyzy açdyňyz — ajaýyp! 🎉

Ýöne heniz pul goýmadyňyz we bonusuňyz sizi garaşýar.

💰 Bonusy işjeňleşdirmek üçin:
1️⃣ Hasabyňyza giriň
2️⃣ Depozit goýuň
3️⃣ *VIP Signals* toparymyza goşulyň 🚀

📹 Kömek gerekmi? Wideodan görüň:
{video2}

Soraglaryňyz bar bolsa, bize ýazyň! 💬""",

    "ru": """⏰ Привет, {name}!

Вы открыли счёт *PU Prime* — отлично! 🎉

Но депозит ещё не внесён, и ваш бонус вас ждёт.

💰 Чтобы активировать бонус:
1️⃣ Войдите в свой счёт
2️⃣ Внесите депозит
3️⃣ Присоединитесь к группе *VIP Signals* 🚀

📹 Нужна помощь? Смотрите видео:
{video2}

Если есть вопросы — напишите нам! 💬""",

    "en": """⏰ Hey {name}!

You opened a *PU Prime* account — great! 🎉

But your deposit is still pending and your bonus is waiting.

💰 To activate your bonus:
1️⃣ Log in to your account
2️⃣ Make your deposit
3️⃣ Join our *VIP Signals* group 🚀

📹 Need help? Watch the video:
{video2}

Any questions? Just message us! 💬""",

    "tr": """⏰ Merhaba {name}!

*PU Prime* hesabınızı açtınız — harika! 🎉

Ama henüz para yatırmadınız ve bonusunuz sizi bekliyor.

💰 Bonusu aktive etmek için:
1️⃣ Hesabınıza giriş yapın
2️⃣ Para yatırın
3️⃣ *VIP Signals* grubuna katılın 🚀

📹 Yardım mı lazım? Videoyu izleyin:
{video2}

Sorularınız varsa bize yazın! 💬""",
}

BONUS_AMOUNTS = {"250": "125", "500": "250", "1000": "500"}

# ─────────────────────────────────────────────
# REMINDER JOBS
# ─────────────────────────────────────────────
async def job_reminder_1(context: ContextTypes.DEFAULT_TYPE):
    """Her saat çalışır — bonus seçip 24 saat içinde hesap açmayana hatırlatma gönderir."""
    users = get_users_pending_account(hours=24)
    sent = 0
    for user_id, first_name, language, bonus_selected_at in users:
        lang = language or "tm"
        name = first_name or "Agza"

        # Bonus miktarını bul
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT bonus_selected FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        amount = row[0] if row and row[0] else "250"
        bonus = BONUS_AMOUNTS.get(amount, "125")

        text = REMINDER_1_TEXT[lang].format(
            name=name,
            amount=amount,
            bonus=bonus,
            link=PU_PRIME_LINK
        )
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown"
            )
            mark_reminder_sent(user_id, 1)
            sent += 1
            logger.info(f"Reminder 1 sent to {user_id}")
        except Exception as e:
            logger.warning(f"Reminder 1 failed for {user_id}: {e}")

    if sent > 0:
        await notify_admins(
            context,
            f"⏰ *Hatırlatma #1 gönderildi*\n\n"
            f"📤 {sent} kişiye hesap açma hatırlatması gönderildi.\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

async def job_reminder_2(context: ContextTypes.DEFAULT_TYPE):
    """Her saat çalışır — hesap açıp 48 saat içinde depozit yapmayana hatırlatma gönderir."""
    users = get_users_pending_deposit(hours=48)
    sent = 0
    for user_id, first_name, language, account_opened_at in users:
        lang = language or "tm"
        name = first_name or "Agza"

        text = REMINDER_2_TEXT[lang].format(
            name=name,
            video2=VIDEO_2_LINK
        )
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown"
            )
            mark_reminder_sent(user_id, 2)
            sent += 1
            logger.info(f"Reminder 2 sent to {user_id}")
        except Exception as e:
            logger.warning(f"Reminder 2 failed for {user_id}: {e}")

    if sent > 0:
        await notify_admins(
            context,
            f"⏰ *Hatırlatma #2 gönderildi*\n\n"
            f"📤 {sent} kişiye depozit hatırlatması gönderildi.\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    user = message.from_user
    chat = message.chat

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status in ["administrator", "creator"]:
            return
    except Exception:
        return

    text = message.text.lower()
    suspicious = ["http://", "https://", "t.me/", ".com", ".net", ".org", "bit.ly", "tinyurl"]
    allowed = [
        "puvip.co/la-partners/777999",
        "youtube.com",
        "youtu.be",
        "t.me/nazikconnect_bot",
        "t.me/+wZdBwJCpYpAwMTQ0",
        "t.me/+s0ACkwJ143E5Y2Y0",
    ]

    has_link = any(s in text for s in suspicious)
    is_allowed = any(a in text for a in allowed)

    if has_link and not is_allowed:
        try:
            await message.delete()
            import asyncio
            warning = await context.bot.send_message(
                chat_id=chat.id,
                text=f"⚠️ {user.first_name}, daşarky baglantylary paýlaşmak gadagandyr! / harici link paylaşmak yasaktır! / Внешние ссылки запрещены! / External links are not allowed!",
            )
            await asyncio.sleep(10)
            await warning.delete()
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    init_db()
    migrate_db()

    app = Application.builder().token(TOKEN).build()

    # ── Reminder jobs — her saat çalışır ──
    job_queue = app.job_queue
    job_queue.run_repeating(job_reminder_1, interval=3600, first=60)   # 1 saat
    job_queue.run_repeating(job_reminder_2, interval=3600, first=120)  # 1 saat (2dk sonra başlar)

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("bonus", cmd_bonus))
    app.add_handler(CommandHandler("broker", cmd_broker))
    app.add_handler(CommandHandler("signals", cmd_signals))
    app.add_handler(CommandHandler("status", cmd_status))

    # Admin commands
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(CommandHandler("user", cmd_user))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("davet", davet))

    # Other handlers
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, filter_links))

    logger.info("✅ Nazik Connect Bot başladý!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

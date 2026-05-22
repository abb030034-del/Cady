"""
أمر الاوامر - يعرض قائمة الأوامر بأزرار أرقام مثل الصورة
"""
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from pyrogram.enums import ParseMode

from config import r, DEV_ID, botkey, botname
from helpers.ranks import (
    get_rank, is_pre, is_admin, is_mod, is_owner,
    is_gowner, is_dev,
)
from helpers.utils import group_enabled, resolve_text, can_speak


# ═══════════════════════════════════════════════════════════════
#  تعريف الأقسام
# ═══════════════════════════════════════════════════════════════

SECTIONS = {

    "admin": {
        "title": "اوامر الادمنيه",
        "min_rank": 2,
        "commands": [
            ("كتم (رد)",                "كتم مستخدم في المجموعة"),
            ("كتم @username",           "كتم بالذكر"),
            ("الغاء الكتم (رد)",        "رفع الكتم عن مستخدم"),
            ("الغاء الكتم @username",   "رفع الكتم بالذكر"),
            ("قائمة المكتومين",         "قائمة المكتومين في المجموعة"),
            ("الفلاتر العامة",          "عرض ردود المطور العامة"),
            ("الكلمات المحظورة",        "قائمة الكلمات المحظورة"),
            ("تفعيل / تعطيل الترحيب",  "تشغيل أو إيقاف رسالة الترحيب"),
            ("الترحيب",                 "عرض رسالة الترحيب الحالية"),
        ],
    },

    "settings": {
        "title": "اوامر الاعدادات",
        "min_rank": 3,
        "commands": [
            ("اضف فلتر [كلمة]",         "إضافة رد تلقائي على كلمة"),
            ("حذف فلتر [كلمة]",         "حذف رد مضاف"),
            ("اضف رد مميز",             "إضافة رد عشوائي متعدد الأجوبة"),
            ("مسح رد مميز",             "مسح رد مميز"),
            ("اضف كلمة [كلمة]",         "حظر كلمة في المجموعة"),
            ("حذف كلمة [كلمة]",         "رفع حظر كلمة"),
            ("وضع الترحيب",             "تعيين رسالة ترحيب مخصصة"),
            ("مسح الترحيب",             "مسح رسالة الترحيب"),
            ("وضع قوانين",              "تعيين قوانين المجموعة"),
            ("مسح القوانين",            "مسح قوانين المجموعة"),
            ("تفعيل / تعطيل التنظيف",  "التنظيف التلقائي للرسائل"),
            ("تفعيل / تعطيل التحذير",  "نظام التحذير قبل الكتم"),
        ],
    },

    "locks": {
        "title": "اوامر القفل - الفتح",
        "min_rank": 3,
        "commands": [
            ("قفل الكل / فتح الكل",     "قفل أو فتح كل الأقفال دفعة واحدة"),
            ("قفل الدردشة / فتح الدردشة",  "إسكات المجموعة بالكامل"),
            ("قفل الصور / فتح الصور",   "قفل أو فتح الصور"),
            ("قفل الفيديو / فتح الفيديو", "قفل أو فتح الفيديو"),
            ("قفل الفويسات / فتح الفويسات", "قفل أو فتح الرسائل الصوتية"),
            ("قفل الملصقات / فتح الملصقات", "قفل أو فتح الستيكرات"),
            ("قفل الملفات / فتح الملفات", "قفل أو فتح الملفات"),
            ("قفل الروابط / فتح الروابط", "قفل أو فتح الروابط"),
            ("قفل الهشتاق / فتح الهشتاق", "قفل أو فتح الهاشتاقات"),
            ("قفل التوجيه / فتح التوجيه", "قفل أو فتح التوجيه (Forward)"),
            ("قفل السب / فتح السب",     "فلتر الألفاظ السيئة"),
            ("قفل البوتات / فتح البوتات", "منع دخول البوتات"),
            ("قفل القنوات / فتح القنوات", "قفل أو فتح رسائل القنوات"),
        ],
    },

    "media": {
        "title": "اوامر التسليه",
        "min_rank": 0,
        "commands": [
            ("بحث [كلمة] / yt [كلمة]", "تحميل صوت أول نتيجة من يوتيوب"),
            ("يوت [كلمة]",              "بحث يوتيوب مع قائمة للاختيار"),
            ("تيك [رابط]",              "تحميل فيديو تيك توك"),
            ("ساوند [كلمة]",            "بحث في ساوند كلاود"),
            ("شازام",                   "التعرف على صوت (رد على رسالة)"),
            ("لعبة [اسم]",              "بدء لعبة (ارقام / كلمات / دول / اعلام)"),
            ("انهاء",                   "إنهاء اللعبة الجارية"),
            ("نقاطي",                   "نقاطك في الألعاب"),
            ("الترتيب",                 "ترتيب المجموعة في الألعاب"),
        ],
    },

    "dev": {
        "title": "اوامر Dev",
        "min_rank": 6,
        "commands": [
            ("مالك (رد/@username)",          "تعيين مالك أساسي"),
            ("شيل مالك (رد/@username)",      "إزالة مالك أساسي"),
            ("كتم عام (رد/@username)",       "كتم في جميع مجموعات البوت"),
            ("الغاء الكتم العام (رد)",       "رفع الكتم العام"),
            ("حظر عام (رد/@username)",       "حظر من جميع مجموعات البوت"),
            ("الغاء الحظر العام (رد)",       "رفع الحظر العام"),
            ("اضف فلتر عام [كلمة]",          "إضافة رد عام لكل مجموعات البوت"),
            ("حذف فلتر عام [كلمة]",          "حذف رد عام"),
            ("تفعيل / تعطيل",               "تفعيل أو تعطيل البوت في المجموعة"),
            ("مجموعاتي",                    "عرض مجموعات البوت"),
        ],
    },

    "general": {
        "title": "الاوامر الخدميه",
        "min_rank": 0,
        "commands": [
            ("رتبة / رتبتي",             "عرض رتبتك أو رتبة شخص"),
            ("قائمة الرتب",              "عرض جميع رتب المجموعة"),
            ("معلومات",                  "معلومات المجموعة"),
            ("ايديي",                    "عرض معرّفك"),
            ("معلوماتي",                 "معلوماتك الكاملة"),
            ("افتاري",                   "صورتك الشخصية"),
            ("صلاحياتي",                 "صلاحياتك في المجموعة"),
            ("القوانين",                 "عرض قوانين المجموعة"),
            ("الفلاتر",                  "قائمة الردود المضافة"),
            ("@بوت همستك @username",    "إرسال همسة سرية لشخص"),
        ],
    },
}

# ترتيب الأقسام كما في الصورة
SECTIONS_ORDER = ["admin", "settings", "locks", "media", "dev", "general"]


# ═══════════════════════════════════════════════════════════════
#  دوال مساعدة
# ═══════════════════════════════════════════════════════════════

def _rank_level(uid: int, cid: int) -> int:
    if is_dev(uid, cid):    return 6
    if is_gowner(uid, cid): return 5
    if is_owner(uid, cid):  return 4
    if is_mod(uid, cid):    return 3
    if is_admin(uid, cid):  return 2
    if is_pre(uid, cid):    return 1
    return 0


def _get_available(uid: int, cid: int) -> list:
    level = _rank_level(uid, cid)
    return [sk for sk in SECTIONS_ORDER if level >= SECTIONS[sk]["min_rank"]]


def _build_index(uid: int, cid: int, k: str) -> tuple:
    """الصفحة الرئيسية - قائمة الأقسام مع أزرار أرقام"""
    available = _get_available(uid, cid)
    name = botname()

    lines = [
        "- أهلاً بك عزيزي في قائمة الاوامر :",
        "──────────────────",
        "",
    ]
    for i, sk in enumerate(available, 1):
        lines.append(f"◄ م{i} : {SECTIONS[sk]['title']}")

    lines.append("")
    lines.append("──────────────────")

    text = "\n".join(lines)

    # أزرار الأرقام - 3 في صف
    btns = []
    row = []
    for i, sk in enumerate(available, 1):
        row.append(InlineKeyboardButton(
            str(i),
            callback_data=f"help:{uid}:{sk}"
        ))
        if len(row) == 3:
            btns.append(row)
            row = []
    if row:
        btns.append(row)

    return text, InlineKeyboardMarkup(btns)


def _build_section(uid: int, cid: int, section_key: str, k: str) -> tuple:
    """صفحة قسم معين"""
    sec = SECTIONS[section_key]
    name = botname()

    lines = [
        f"- {sec['title']} :",
        "──────────────────",
        "",
    ]
    for cmd, desc in sec["commands"]:
        lines.append(f"◄ {cmd}")
        lines.append(f"   ↳ {desc}")
        lines.append("")

    lines.append("──────────────────")
    text = "\n".join(lines)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("◄ رجوع", callback_data=f"help:{uid}:__index__")]
    ])

    return text, markup


# ═══════════════════════════════════════════════════════════════
#  المعالج الرئيسي
# ═══════════════════════════════════════════════════════════════

@Client.on_message(filters.text & filters.group, group=50)
async def help_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    if text not in ("الاوامر", "اوامر", "المساعدة", "مساعدة", "help"):
        return

    content, markup = _build_index(uid, cid, k)
    await m.reply(
        content,
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
        disable_web_page_preview=True,
    )


# ═══════════════════════════════════════════════════════════════
#  معالج الأزرار
# ═══════════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^help:"))
async def help_callback(c: Client, query: CallbackQuery):
    parts = query.data.split(":")
    if len(parts) < 3:
        return await query.answer()

    owner_id    = int(parts[1])
    section_key = parts[2]

    if query.from_user.id != owner_id:
        return await query.answer("هذه الرسالة ليست لك 😅", show_alert=True)

    k   = botkey()
    cid = query.message.chat.id
    uid = query.from_user.id

    if section_key == "__index__":
        content, markup = _build_index(uid, cid, k)
    elif section_key in SECTIONS:
        level = _rank_level(uid, cid)
        if level < SECTIONS[section_key]["min_rank"]:
            return await query.answer("ما عندك صلاحية لهذا القسم", show_alert=True)
        content, markup = _build_section(uid, cid, section_key, k)
    else:
        return await query.answer()

    try:
        await query.edit_message_text(
            content,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except Exception:
        pass
    await query.answer()

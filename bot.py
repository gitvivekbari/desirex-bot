import os
import base64
import logging
import requests
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
import firebase_admin
from firebase_admin import credentials, db
from flask import Flask

# ─────────────────────────────────────────────
# CONFIG — Environment variables se
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DB_URL = os.environ.get("DB_URL", "")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")
FIREBASE_KEY = "firebase_key.json"

# Admin IDs — comma-separated
_admin_ids_str = os.environ.get("ADMIN_IDS", "5405614850")
ADMIN_IDS = [int(x.strip()) for x in _admin_ids_str.split(",") if x.strip()]

# Firebase key from base64 env var (if file doesn't exist)
b64_key = os.environ.get("FIREBASE_KEY_JSON", "")
if b64_key and not os.path.exists(FIREBASE_KEY):
    try:
        with open(FIREBASE_KEY, "w") as f:
            f.write(base64.b64decode(b64_key).decode("utf-8"))
    except Exception as e:
        logging.error(f"Firebase key decode failed: {e}")

# ─────────────────────────────────────────────
# FIREBASE INIT
# ─────────────────────────────────────────────
cred = credentials.Certificate(FIREBASE_KEY)
firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# FLASK HEALTH SERVER (Render ke liye)
# ─────────────────────────────────────────────
health_app = Flask(__name__)

@health_app.route("/")
@health_app.route("/health")
def health():
    return "DesireX Bot is running", 200

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    health_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ─────────────────────────────────────────────
# CONVERSATION STATES
# ─────────────────────────────────────────────
(
    CHOOSE_CATEGORY,
    NAME, AGE, NATIONALITY, LANGUAGES,
    HEIGHT, WEIGHT, EYE_COLOR, HAIR_COLOR, HAIR_LENGTH,
    BODY_TYPE, BUST_SIZE, BUST_TYPE, WAIST, HIPS,
    GROOMING, TATTOOS, PIERCINGS,
    SERVICES, PRICE_SHOT, PRICE_NIGHT, PRICE_DAY,
    RATING, EXPERIENCE, LOCATION, CITY,
    PHONE, PHOTOS, CONFIRM
) = range(29)


def is_admin(uid):
    return uid in ADMIN_IDS


def save_profile(data, photos):
    ref = db.reference('profiles').push()
    data['photos'] = photos
    data['active'] = True
    data['createdAt'] = int(os.times()[4] * 1000)
    ref.set(data)
    return ref.key


def upload_photo(file_bytes):
    """Upload to ImgBB, return direct URL."""
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": IMGBB_API_KEY,
            "image": base64.b64encode(file_bytes).decode('utf-8'),
        }
        r = requests.post(url, data=payload, timeout=30)
        data = r.json()
        if data.get('success'):
            return data['data']['url']
        logger.error(f"ImgBB error: {data}")
        return None
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return None


# ─────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text(
            f"❌ Not authorized.\nYour ID: `{update.effective_user.id}`",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("💋 Call Girl", callback_data="cat|Call Girl")],
        [InlineKeyboardButton("🕴 Male Escort", callback_data="cat|Male Escort")],
        [InlineKeyboardButton("💆 Massage", callback_data="cat|Massage")],
        [InlineKeyboardButton("📋 View All", callback_data="view_all")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        "🌟 *DesireX Admin Bot*\n\nChoose category:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSE_CATEGORY


async def choose_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Cancelled.")
        return ConversationHandler.END

    if query.data == "view_all":
        profiles = db.reference('profiles').get() or {}
        if not profiles:
            await query.edit_message_text("No profiles yet.")
            return ConversationHandler.END
        msg = "📋 *All Profiles:*\n\n"
        for pid, p in profiles.items():
            msg += f"• {p.get('name')} ({p.get('category')}) — {p.get('city', '')}\n"
        await query.edit_message_text(msg, parse_mode="Markdown")
        return ConversationHandler.END

    category = query.data.split("|")[1]
    ctx.user_data['profile'] = {'category': category}
    await query.edit_message_text(
        f"✅ *{category}*\n\n*1/27* Name:",
        parse_mode="Markdown"
    )
    return NAME


# ─────────────────────────────────────────────
# STEP HANDLERS
# ─────────────────────────────────────────────
async def get_name(update, ctx):
    ctx.user_data['profile']['name'] = update.message.text.strip()
    await update.message.reply_text("*2/27* Age (18-60):", parse_mode="Markdown")
    return AGE


async def get_age(update, ctx):
    try:
        age = int(update.message.text.strip())
        if age < 18 or age > 60:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Enter age 18-60:")
        return AGE
    ctx.user_data['profile']['age'] = age
    await update.message.reply_text("*3/27* Nationality:", parse_mode="Markdown")
    return NATIONALITY


async def get_nationality(update, ctx):
    ctx.user_data['profile']['nationality'] = update.message.text.strip()
    await update.message.reply_text("*4/27* Languages (Hindi, English):", parse_mode="Markdown")
    return LANGUAGES


async def get_languages(update, ctx):
    ctx.user_data['profile']['languages'] = [l.strip() for l in update.message.text.split(',') if l.strip()]
    await update.message.reply_text("*5/27* Height (5'6\" or 168cm):", parse_mode="Markdown")
    return HEIGHT


async def get_height(update, ctx):
    ctx.user_data['profile']['height'] = update.message.text.strip()
    await update.message.reply_text("*6/27* Weight (55kg):", parse_mode="Markdown")
    return WEIGHT


async def get_weight(update, ctx):
    ctx.user_data['profile']['weight'] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("Black", callback_data="eye|Black"),
         InlineKeyboardButton("Brown", callback_data="eye|Brown")],
        [InlineKeyboardButton("Blue", callback_data="eye|Blue"),
         InlineKeyboardButton("Green", callback_data="eye|Green")],
    ]
    await update.message.reply_text("*7/27* Eye Color:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return EYE_COLOR


async def get_eye_color(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['eyeColor'] = q.data.split("|")[1]
    keyboard = [
        [InlineKeyboardButton("Black", callback_data="hair|Black"),
         InlineKeyboardButton("Brown", callback_data="hair|Brown")],
        [InlineKeyboardButton("Blonde", callback_data="hair|Blonde"),
         InlineKeyboardButton("Red", callback_data="hair|Red")],
    ]
    await q.edit_message_text("*8/27* Hair Color:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return HAIR_COLOR


async def get_hair_color(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['hairColor'] = q.data.split("|")[1]
    keyboard = [
        [InlineKeyboardButton("Short", callback_data="hl|Short"),
         InlineKeyboardButton("Long", callback_data="hl|Long")],
    ]
    await q.edit_message_text("*9/27* Hair Length:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return HAIR_LENGTH


async def get_hair_length(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['hairLength'] = q.data.split("|")[1]
    keyboard = [
        [InlineKeyboardButton("Slim", callback_data="bt|Slim"),
         InlineKeyboardButton("Athletic", callback_data="bt|Athletic")],
        [InlineKeyboardButton("Curvy", callback_data="bt|Curvy"),
         InlineKeyboardButton("Petite", callback_data="bt|Petite")],
    ]
    await q.edit_message_text("*10/27* Body Type:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return BODY_TYPE


async def get_body_type(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['bodyType'] = q.data.split("|")[1]
    await q.edit_message_text("*11/27* Bust Size (34B) or `skip`:", parse_mode="Markdown")
    return BUST_SIZE


async def get_bust_size(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['bustSize'] = '' if v.lower() == 'skip' else v
    keyboard = [[
        InlineKeyboardButton("Natural", callback_data="bust|Natural"),
        InlineKeyboardButton("Augmented", callback_data="bust|Augmented"),
    ]]
    await update.message.reply_text("*12/27* Bust Type:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return BUST_TYPE


async def get_bust_type(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['bustType'] = q.data.split("|")[1]
    await q.edit_message_text("*13/27* Waist (26) or `skip`:", parse_mode="Markdown")
    return WAIST


async def get_waist(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['waist'] = '' if v.lower() == 'skip' else v
    await update.message.reply_text("*14/27* Hips (36) or `skip`:", parse_mode="Markdown")
    return HIPS


async def get_hips(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['hips'] = '' if v.lower() == 'skip' else v
    keyboard = [
        [InlineKeyboardButton("Trimmed", callback_data="gr|Trimmed"),
         InlineKeyboardButton("Shaved", callback_data="gr|Shaved")],
        [InlineKeyboardButton("Natural", callback_data="gr|Natural"),
         InlineKeyboardButton("Waxed", callback_data="gr|Waxed")],
    ]
    await update.message.reply_text("*15/27* Grooming:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return GROOMING


async def get_grooming(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['grooming'] = q.data.split("|")[1]
    await q.edit_message_text("*16/27* Tattoos or `none`:", parse_mode="Markdown")
    return TATTOOS


async def get_tattoos(update, ctx):
    ctx.user_data['profile']['tattoos'] = update.message.text.strip()
    await update.message.reply_text("*17/27* Piercings or `none`:", parse_mode="Markdown")
    return PIERCINGS


async def get_piercings(update, ctx):
    ctx.user_data['profile']['piercings'] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("In-call", callback_data="sv|In-call"),
         InlineKeyboardButton("Out-call", callback_data="sv|Out-call")],
        [InlineKeyboardButton("Both", callback_data="sv|Both")],
    ]
    await update.message.reply_text("*18/27* Services:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SERVICES


async def get_services(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['services'] = q.data.split("|")[1]
    await q.edit_message_text("*19/27* Price per Shot (₹) or `skip`:", parse_mode="Markdown")
    return PRICE_SHOT


async def get_price_shot(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['pricePerShot'] = 0 if v.lower() == 'skip' else int(v)
    await update.message.reply_text("*20/27* Price per Night (₹) or `skip`:")
    return PRICE_NIGHT


async def get_price_night(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['pricePerNight'] = 0 if v.lower() == 'skip' else int(v)
    await update.message.reply_text("*21/27* Price per Day (₹) or `skip`:")
    return PRICE_DAY


async def get_price_day(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['pricePerDay'] = 0 if v.lower() == 'skip' else int(v)
    await update.message.reply_text("*22/27* Rating (4.8) or `skip`:")
    return RATING


async def get_rating(update, ctx):
    v = update.message.text.strip()
    if v.lower() == 'skip':
        ctx.user_data['profile']['rating'] = 0
    else:
        try:
            ctx.user_data['profile']['rating'] = float(v)
        except ValueError:
            await update.message.reply_text("❌ Enter number or `skip`:")
            return RATING
    await update.message.reply_text("*23/27* Experience (5 years) or `skip`:")
    return EXPERIENCE


async def get_experience(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['experience'] = '' if v.lower() == 'skip' else v
    await update.message.reply_text("*24/27* Location (area, e.g. Bandra):")
    return LOCATION


async def get_location(update, ctx):
    ctx.user_data['profile']['location'] = update.message.text.strip()
    await update.message.reply_text("*25/27* City (Mumbai):")
    return CITY


async def get_city(update, ctx):
    ctx.user_data['profile']['city'] = update.message.text.strip()
    await update.message.reply_text(
        "*26/27* Contact Phone (10-digit) or `skip`:"
    )
    return PHONE


async def get_phone(update, ctx):
    v = update.message.text.strip()
    if v.lower() == 'skip':
        ctx.user_data['profile']['phone'] = ''
    else:
        digits = ''.join(filter(str.isdigit, v))
        if len(digits) < 10:
            await update.message.reply_text("❌ Enter 10-digit phone or `skip`:")
            return PHONE
        ctx.user_data['profile']['phone'] = digits[-10:]

    ctx.user_data['photos'] = []
    await update.message.reply_text(
        "📸 *27/27* Send photos (max 5). One at a time.\nWhen done, /done",
        parse_mode="Markdown"
    )
    return PHOTOS


async def receive_photo(update, ctx):
    if len(ctx.user_data['photos']) >= 5:
        await update.message.reply_text("⚠️ Max 5. /done to finish.")
        return PHOTOS

    msg = await update.message.reply_text("📤 Uploading...")
    photo = update.message.photo[-1]
    file = await photo.get_file()
    bytes_ = await file.download_as_bytearray()
    url = upload_photo(bytes(bytes_))

    if not url:
        await msg.edit_text("❌ Upload failed. Try again.")
        return PHOTOS

    ctx.user_data['photos'].append(url)
    await msg.edit_text(f"✅ Photo {len(ctx.user_data['photos'])} done. Send more or /done")
    return PHOTOS


async def done_photos(update, ctx):
    photos = ctx.user_data.get('photos', [])
    if not photos:
        await update.message.reply_text("⚠️ Send at least 1 photo.")
        return PHOTOS

    p = ctx.user_data['profile']
    summary = (
        f"📋 *Summary*\n\n"
        f"Name: {p.get('name')}\n"
        f"Category: {p.get('category')}\n"
        f"Age: {p.get('age')}\n"
        f"City: {p.get('city')}\n"
        f"Phone: {p.get('phone', '—')}\n"
        f"Night: ₹{p.get('pricePerNight')}\n"
        f"Photos: {len(photos)}\n\n"
        f"Save?"
    )
    keyboard = [[
        InlineKeyboardButton("✅ Save", callback_data="confirm|yes"),
        InlineKeyboardButton("❌ Cancel", callback_data="confirm|no"),
    ]]
    await update.message.reply_text(summary,
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CONFIRM


async def confirm_save(update, ctx):
    q = update.callback_query
    await q.answer()
    if q.data == "confirm|yes":
        pid = save_profile(ctx.user_data['profile'], ctx.user_data.get('photos', []))
        await q.edit_message_text(f"✅ Saved!\nID: `{pid}`", parse_mode="Markdown")
    else:
        await q.edit_message_text("❌ Cancelled.")
    return ConversationHandler.END


async def cancel(update, ctx):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    # Flask health server background mein
    Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_CATEGORY: [CallbackQueryHandler(choose_category)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            NATIONALITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nationality)],
            LANGUAGES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_languages)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            EYE_COLOR: [CallbackQueryHandler(get_eye_color)],
            HAIR_COLOR: [CallbackQueryHandler(get_hair_color)],
            HAIR_LENGTH: [CallbackQueryHandler(get_hair_length)],
            BODY_TYPE: [CallbackQueryHandler(get_body_type)],
            BUST_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bust_size)],
            BUST_TYPE: [CallbackQueryHandler(get_bust_type)],
            WAIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_waist)],
            HIPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hips)],
            GROOMING: [CallbackQueryHandler(get_grooming)],
            TATTOOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tattoos)],
            PIERCINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_piercings)],
            SERVICES: [CallbackQueryHandler(get_services)],
            PRICE_SHOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price_shot)],
            PRICE_NIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price_night)],
            PRICE_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price_day)],
            RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rating)],
            EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_experience)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PHOTOS: [
                MessageHandler(filters.PHOTO, receive_photo),
                CommandHandler("done", done_photos),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    print("🤖 DesireX Bot running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
import os
import base64
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
import firebase_admin
from firebase_admin import credentials, db

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN = "8939132238:AAFWdJlZqSBkgFtOUZKC27XI0hLd5tewe-g"
FIREBASE_KEY = "firebase_key.json"
DB_URL = "https://desirex-d8d28-default-rtdb.asia-southeast1.firebasedatabase.app/"
IMGBB_API_KEY = "79bffa3dcd082ac05d2b5b715f2285f7"

# ⚠️ APNA TELEGRAM ID YAHAN DAALO (from @userinfobot)
ADMIN_IDS = [5405614850, 1659583399]

# ─────────────────────────────────────────────
# FIREBASE
# ─────────────────────────────────────────────
cred = credentials.Certificate(FIREBASE_KEY)
firebase_admin.initialize_app(cred, {'databaseURL': DB_URL})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# STATES
# ─────────────────────────────────────────────
(
    CHOOSE_CATEGORY,
    NAME, AGE, NATIONALITY, LANGUAGES,
    HEIGHT, WEIGHT, EYE_COLOR, HAIR_COLOR, HAIR_LENGTH,
    BODY_TYPE, BUST_SIZE, BUST_TYPE, WAIST, HIPS,
    GROOMING, TATTOOS, PIERCINGS,
    SERVICES, PRICE_SHOT, PRICE_NIGHT, PRICE_DAY,
    RATING, EXPERIENCE, LOCATION, CITY,
    PHOTOS, CONFIRM
) = range(28)


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
        "🌟 *Glow Admin Bot*\n\nChoose category:",
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
            msg += f"• {p.get('name')} ({p.get('category')}) — ₹{p.get('pricePerNight', 0)}\n"
        await query.edit_message_text(msg, parse_mode="Markdown")
        return ConversationHandler.END

    category = query.data.split("|")[1]
    ctx.user_data['profile'] = {'category': category}
    await query.edit_message_text(
        f"✅ *{category}*\n\n*1/25* Name:",
        parse_mode="Markdown"
    )
    return NAME


# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────
async def get_name(update, ctx):
    ctx.user_data['profile']['name'] = update.message.text.strip()
    await update.message.reply_text("*2/25* Age (18-60):", parse_mode="Markdown")
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
    await update.message.reply_text("*3/25* Nationality:", parse_mode="Markdown")
    return NATIONALITY


async def get_nationality(update, ctx):
    ctx.user_data['profile']['nationality'] = update.message.text.strip()
    await update.message.reply_text("*4/25* Languages (Hindi, English):", parse_mode="Markdown")
    return LANGUAGES


async def get_languages(update, ctx):
    ctx.user_data['profile']['languages'] = [l.strip() for l in update.message.text.split(',') if l.strip()]
    await update.message.reply_text("*5/25* Height (5'6\" or 168cm):", parse_mode="Markdown")
    return HEIGHT


async def get_height(update, ctx):
    ctx.user_data['profile']['height'] = update.message.text.strip()
    await update.message.reply_text("*6/25* Weight (55kg):", parse_mode="Markdown")
    return WEIGHT


async def get_weight(update, ctx):
    ctx.user_data['profile']['weight'] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("Black", callback_data="eye|Black"),
         InlineKeyboardButton("Brown", callback_data="eye|Brown")],
        [InlineKeyboardButton("Blue", callback_data="eye|Blue"),
         InlineKeyboardButton("Green", callback_data="eye|Green")],
    ]
    await update.message.reply_text("*7/25* Eye Color:",
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
    await q.edit_message_text("*8/25* Hair Color:",
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
    await q.edit_message_text("*9/25* Hair Length:",
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
    await q.edit_message_text("*10/25* Body Type:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return BODY_TYPE


async def get_body_type(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['bodyType'] = q.data.split("|")[1]
    await q.edit_message_text("*11/25* Bust Size (34B) or `skip`:", parse_mode="Markdown")
    return BUST_SIZE


async def get_bust_size(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['bustSize'] = '' if v.lower() == 'skip' else v
    keyboard = [[
        InlineKeyboardButton("Natural", callback_data="bust|Natural"),
        InlineKeyboardButton("Augmented", callback_data="bust|Augmented"),
    ]]
    await update.message.reply_text("*12/25* Bust Type:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return BUST_TYPE


async def get_bust_type(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['bustType'] = q.data.split("|")[1]
    await q.edit_message_text("*13/25* Waist (26) or `skip`:", parse_mode="Markdown")
    return WAIST


async def get_waist(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['waist'] = '' if v.lower() == 'skip' else v
    await update.message.reply_text("*14/25* Hips (36) or `skip`:", parse_mode="Markdown")
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
    await update.message.reply_text("*15/25* Grooming:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return GROOMING


async def get_grooming(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['grooming'] = q.data.split("|")[1]
    await q.edit_message_text("*16/25* Tattoos or `none`:", parse_mode="Markdown")
    return TATTOOS


async def get_tattoos(update, ctx):
    ctx.user_data['profile']['tattoos'] = update.message.text.strip()
    await update.message.reply_text("*17/25* Piercings or `none`:", parse_mode="Markdown")
    return PIERCINGS


async def get_piercings(update, ctx):
    ctx.user_data['profile']['piercings'] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("In-call", callback_data="sv|In-call"),
         InlineKeyboardButton("Out-call", callback_data="sv|Out-call")],
        [InlineKeyboardButton("Both", callback_data="sv|Both")],
    ]
    await update.message.reply_text("*18/25* Services:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SERVICES


async def get_services(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data['profile']['services'] = q.data.split("|")[1]
    await q.edit_message_text("*19/25* Price per Shot (₹) or `skip`:", parse_mode="Markdown")
    return PRICE_SHOT


async def get_price_shot(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['pricePerShot'] = 0 if v.lower() == 'skip' else int(v)
    await update.message.reply_text("*20/25* Price per Night (₹):")
    return PRICE_NIGHT


async def get_price_night(update, ctx):
    ctx.user_data['profile']['pricePerNight'] = int(update.message.text.strip())
    await update.message.reply_text("*21/25* Price per Day (₹) or `skip`:")
    return PRICE_DAY


async def get_price_day(update, ctx):
    v = update.message.text.strip()
    ctx.user_data['profile']['pricePerDay'] = 0 if v.lower() == 'skip' else int(v)
    await update.message.reply_text("*22/25* Rating (4.8) or `skip`:")
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
    await update.message.reply_text("*23/25* Experience (5 years) or `skip`:")
    return EXPERIENCE


async def get_experience(update, ctx):
    ctx.user_data['profile']['experience'] = update.message.text.strip()
    await update.message.reply_text("*24/25* Location (area):")
    return LOCATION


async def get_location(update, ctx):
    ctx.user_data['profile']['location'] = update.message.text.strip()
    await update.message.reply_text("*25/25* City (Mumbai):")
    return CITY


async def get_city(update, ctx):
    ctx.user_data['profile']['city'] = update.message.text.strip()
    ctx.user_data['photos'] = []
    await update.message.reply_text(
        "📸 Send photos (max 5). One at a time.\nWhen done, /done"
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
            PHOTOS: [
                MessageHandler(filters.PHOTO, receive_photo),
                CommandHandler("done", done_photos),
            ],
            CONFIRM: [CallbackQueryHandler(confirm_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    print("🤖 Bot running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
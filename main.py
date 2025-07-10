from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackContext, CallbackQueryHandler
import json
import os

app = Flask(__name__)

BOT_TOKEN = 'ISI_TOKEN_BOT_KAMU_DI_SINI'
ADMIN_CHAT_ID = 6766508127  # Ganti dengan ID admin bot kamu

bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=1, use_context=True)

with open("ebooks.json") as f:
    ebooks = json.load(f)

def save_user(chat_id, username):
    if not username:
        return
    user_data = {}
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            user_data = json.load(f)
    user_data[username.lower()] = chat_id
    with open("users.json", "w") as f:
        json.dump(user_data, f)

@app.route('/')
def home():
    return '🤖 Bot aktif di Render!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Webhook dari Saweria:", data)
    try:
        name = data.get('donator_name', 'Pembeli')
        amount = data.get('amount_raw', '0')
        message = data.get('message', '').strip()
        parts = message.split()
        if len(parts) != 2 or not parts[0].startswith('@'):
            bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Format salah dari {name}\nPesan: {message}")
            return "Format salah", 400
        username = parts[0][1:]
        code = parts[1].lower()
        chat_id = None
        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                user_data = json.load(f)
                chat_id = user_data.get(username.lower())
        if code == "vip":
            vip_link = "https://drive.google.com/drive/folders/LINK_GOOGLE_DRIVE_VIP"
            caption = (
                f"🌟 *Akses VIP Semua eBook!*\n\n"
                f"Terima kasih telah menjadi member VIP 🎉\n\n"
                f"📁 Semua eBook bisa diakses di sini:\n{vip_link}"
            )
            if chat_id:
                bot.send_message(chat_id=chat_id, text=caption, parse_mode='Markdown')
            else:
                bot.send_message(chat_id=f"@{username}", text=caption, parse_mode='Markdown')
            return "OK", 200
        for kategori in ebooks.values():
            if code in kategori:
                ebook = kategori[code]
                break
        else:
            bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ Kode eBook '{code}' dari @{username} tidak ditemukan.")
            return "Kode tidak ditemukan", 404
        judul = ebook["judul"]
        deskripsi = ebook["deskripsi"]
        gambar = ebook["gambar"]
        link = ebook["link"]
        caption = f"📚 *{judul}*\n\n{deskripsi}\n\n💬 Kode: `{code}`\n🔗 Link eBook: {link}"
        if chat_id:
            bot.send_photo(chat_id=chat_id, photo=gambar, caption=caption, parse_mode='Markdown')
        else:
            bot.send_photo(chat_id=f"@{username}", photo=gambar, caption=caption, parse_mode='Markdown')
        return "OK", 200
    except Exception as e:
        bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ Error webhook: {e}")
        return "Error", 400

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# ---------- Telegram Command Handlers ----------

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    if username:
        save_user(chat_id, username)
    text = (
        "👋 Selamat datang!\n\n"
        "📌 /menu — lihat semua eBook\n"
        "📌 /cari kata — cari eBook dengan kata kunci\n"
        "📌 /panduan — panduan cara beli\n"
        "📌 /vip — cara jadi member VIP\n"
        "📌 /checkid — lihat ID Telegram kamu"
    )
    context.bot.send_message(chat_id=chat_id, text=text)

def menu(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton(text=k, callback_data=f"cat|{k}")] for k in ebooks.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("📚 Pilih kategori eBook:", reply_markup=reply_markup)

def kategori_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    _, kategori = query.data.split("|")
    daftar = ebooks.get(kategori, {})
    for code, ebook in daftar.items():
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Beli Sekarang", url="https://saweria.co/einsteinbook")]])
        caption = (
            f"📚 *{ebook['judul']}*\n{ebook['deskripsi']}\n\n"
            f"💰 Harga: Rp {ebook['harga']:,}\n"
            f"💬 Kode: `{code}`"
        )
        bot.send_photo(chat_id=query.message.chat_id, photo=ebook['gambar'], caption=caption, parse_mode='Markdown', reply_markup=buttons)

def panduan(update: Update, context: CallbackContext):
    update.message.reply_text(
        "<b>📌 Panduan Pembelian eBook:</b>\n\n"
        "1. Ketik <code>/menu</code> untuk lihat eBook\n"
        "2. Pilih eBook & catat kodenya\n"
        "3. Bayar via Saweria: https://saweria.co/einsteinbook\n"
        "4. Sertakan pesan: <code>@username KODE</code>\n"
        "5. Bot akan otomatis kirim eBook 🙌",
        parse_mode='HTML'
    )

def checkid(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Tanpa username"
    update.message.reply_text(f"👤 Username: @{username}\n🆔 Chat ID kamu: `{chat_id}`", parse_mode='Markdown')

def cari_ebook(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("🔍 Ketik: `/cari kata_kunci`\nContoh: `/cari python`", parse_mode='Markdown')
        return
    keyword = ' '.join(context.args).lower()
    hasil = []
    for kategori in ebooks.values():
        for code, ebook in kategori.items():
            if keyword in ebook['judul'].lower() or keyword in code.lower():
                hasil.append((code, ebook))
    if not hasil:
        update.message.reply_text("❌ eBook tidak ditemukan.")
        return
    for code, ebook in hasil:
        buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Beli Sekarang", url="https://saweria.co/einsteinbook")]])
        caption = (
            f"📚 *{ebook['judul']}*\n{ebook['deskripsi']}\n\n"
            f"💰 Harga: Rp {ebook['harga']:,}\n"
            f"💬 Kode: `{code}`"
        )
        bot.send_photo(chat_id=update.effective_chat.id, photo=ebook['gambar'], caption=caption, parse_mode='Markdown', reply_markup=buttons)

def vip(update: Update, context: CallbackContext):
    update.message.reply_text(
        "<b>🌟 Cara Jadi Member VIP:</b>\n\n"
        "💳 Biaya: Rp199.000\n"
        "✅ Akses semua eBook tanpa batas!\n\n"
        "1. Transfer ke Saweria: https://saweria.co/einsteinbook\n"
        "2. Pesan: <code>@username VIP</code>\n"
        "3. Bot akan kirim link VIP 📁\n\n"
        "⚠️ Pastikan username Telegram aktif!",
        parse_mode='HTML'
    )

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("menu", menu))
dispatcher.add_handler(CommandHandler("panduan", panduan))
dispatcher.add_handler(CommandHandler("vip", vip))
dispatcher.add_handler(CommandHandler("checkid", checkid))
dispatcher.add_handler(CommandHandler("cari", cari_ebook))
dispatcher.add_handler(CallbackQueryHandler(kategori_handler, pattern="^cat\\|"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

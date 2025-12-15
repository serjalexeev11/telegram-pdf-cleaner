import fitz  # PyMuPDF
from telegram import Update, InputFile, ReplyKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters,
    CallbackContext, ConversationHandler
)
import os
from datetime import datetime, timedelta

# === TOKEN ===
TOKEN = os.environ.get("BOT_TOKEN")

# === STATES ===
CHOICE = range(1)
last_file_path = ""

# === LIMITĂ DATĂ ===
# Data până la care botul este activ (modifică după nevoie)
expiration_date = datetime(2025, 12, 22)

# === START ===
def start(update: Update, context: CallbackContext):
    # Verificăm dacă botul este activ
    now = datetime.now()
    days_left = (expiration_date - now).days
    if days_left < 0:
        update.message.reply_text("⛔ Бот больше не активен.")
        return ConversationHandler.END

    # Mesaj către utilizator
    update.message.reply_text(
        f"📄 Отправьте PDF файл.\n"
        "✅ Я очищу заголовок (выше 'BILL OF LADING'), все номера 'Phone:' и ссылки SuperDispatch.\n"
        f"📅 Бот активен еще {days_left} дней.\n"
        "✏️ Затем выберите информацию о компании для вставки на каждой странице."
    )

# === HANDLE PDF ===
def handle_pdf(update: Update, context: CallbackContext):
    # Verificăm dacă botul este activ
    now = datetime.now()
    days_left = (expiration_date - now).days
    if days_left < 0:
        update.message.reply_text("⛔ Бот больше не активен.")
        return ConversationHandler.END

    global last_file_path
    document = update.message.document
    file_name = document.file_name
    input_path = f"recv_{file_name}"
    output_path = f"cleaned_{file_name}"

    print(f"📄 Получен PDF: {file_name}")
    document.get_file().download(input_path)

    doc = fitz.open(input_path)

    # Procesăm fiecare pagină
    for page_num, page in enumerate(doc):
        print(f"📄 Обрабатывается страница {page_num + 1}...")

        # 🧼 Ștergem header-ul de deasupra "BILL OF LADING"
        areas = page.search_for("BILL OF LADING")
        if areas:
            y_cut = areas[0].y0
            rect = fitz.Rect(0, 0, page.rect.width, y_cut)
            page.add_redact_annot(rect, fill=(1, 1, 1))

        # 🧼 Ștergem toate "Phone:"
        phone_areas = page.search_for("Phone:")
        for area in phone_areas:
            redact_box = fitz.Rect(
                area.x0,
                area.y0 - 1,
                area.x1 + 130,
                area.y1 + 3
            )
            page.add_redact_annot(redact_box, fill=(1, 1, 1))

        # 🧼 Ștergem superdispatch.com
        link_areas = page.search_for("superdispatch.com")
        for area in link_areas:
            left_margin = 35
            right_margin = 35
            full_line = fitz.Rect(
                left_margin,
                area.y0 - 10,
                page.rect.width - right_margin,
                area.y1 + 15
            )
            page.add_redact_annot(full_line, fill=(1, 1, 1))

        page.apply_redactions()

    doc.save(output_path)
    doc.close()

    print("🧼 Все страницы очищены.")
    last_file_path = output_path

    # 🔹 Doar o companie disponibilă
    keyboard = [["JNI GROUP INC"]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    update.message.reply_text(
        f"📌 Выберите компанию для вставки (бот активен еще {days_left} дней):",
        reply_markup=reply_markup
    )

    return CHOICE

# === HANDLE CHOICE ===
def handle_choice(update: Update, context: CallbackContext):
    choice = update.message.text
    # Verificăm că utilizatorul a ales JNI GROUP INC
    if choice != "JNI GROUP INC":
        update.message.reply_text("❌ Доступна только JNI GROUP INC.")
        return ConversationHandler.END

    return insert_predefined_text(update, context, "FMK")

# === INSERT PREDEFINED TEXT ===
def insert_predefined_text(update: Update, context: CallbackContext, company_key):
    global last_file_path

    # Setăm textul pentru companie
    if company_key == "FMK":
        predefined = (
            "JNI GROUP INC\n"
            "4405 Roberts Rd\n"
            "Island Lake, IL US 60042\n"
            "USDOT:  3291557\n"
            "MC: 1042416"
        )

    doc = fitz.open(last_file_path)
    # Inserăm textul pe fiecare pagină
    for i, page in enumerate(doc):
        page.insert_text((40, 40), predefined, fontsize=12, color=(0, 0, 0))

    final_path = last_file_path.replace("cleaned_", "final_")
    doc.save(final_path)
    doc.close()

    # Trimitem PDF-ul final către utilizator
    with open(final_path, "rb") as f:
        update.message.reply_document(document=InputFile(f, filename=final_path))
        print(f"✅ Отправлен файл: {final_path}")

    return ConversationHandler.END

# === MAIN ===
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(Filters.document.pdf, handle_pdf)
        ],
        states={
            CHOICE: [MessageHandler(Filters.text & ~Filters.command, handle_choice)]
        },
        fallbacks=[],
    )

    dp.add_handler(conv_handler)

    print("✅ Бот запущен. Ожидание PDF файлов...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()



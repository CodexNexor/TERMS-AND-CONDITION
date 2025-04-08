import os
import json
from dotenv import load_dotenv
from fpdf import FPDF
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# States for initial setup
AGENCY_NAME, SERVICES, EMAIL, PHONE = range(4)

# States for client info
CLIENT_NAME, AMOUNT, DURATION, CLIENT_SERVICES = range(4, 8)

# File paths
USER_DATA_PATH = "termsandcondition/user_data/user_data.json"
GENERATED_DIR = "termsandcondition/generated"

# Load/Save
def load_user_data():
    if os.path.exists(USER_DATA_PATH):
        try:
            with open(USER_DATA_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_user_data(data):
    os.makedirs(os.path.dirname(USER_DATA_PATH), exist_ok=True)
    with open(USER_DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)

user_data = load_user_data()

# ==== SETUP FLOW ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in user_data:
        await update.message.reply_text("✅ You're already set up! Use /generate to create a Terms PDF.")
        return ConversationHandler.END

    await update.message.reply_text("👋 Welcome! Let's set up your company.\nEnter your Agency/Company name:")
    return AGENCY_NAME

async def get_agency_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["agency_name"] = update.message.text
    await update.message.reply_text("Enter your services (e.g., Video Editing, Posters, etc):")
    return SERVICES

async def get_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["services"] = update.message.text
    await update.message.reply_text("📧 Enter your contact email:")
    return EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text
    await update.message.reply_text("📞 Enter your phone number:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text
    user_id = str(update.effective_user.id)
    user_data[user_id] = context.user_data.copy()
    save_user_data(user_data)
    await update.message.reply_text("✅ Setup complete! Use /generate to create a PDF.")
    return ConversationHandler.END

# ==== GENERATE PDF FLOW ====

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        await update.message.reply_text("❗ Please run /start to set up your company info first.")
        return ConversationHandler.END

    await update.message.reply_text("👤 Enter Client's Name:")
    return CLIENT_NAME

async def get_client_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_name"] = update.message.text
    await update.message.reply_text("💰 Enter the Amount (e.g., ₹3000):")
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["amount"] = update.message.text
    await update.message.reply_text("⏱️ Enter Time/Duration (e.g., 3 days):")
    return DURATION

async def get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["duration"] = update.message.text
    await update.message.reply_text("🛠️ Enter Services you're providing to this client:")
    return CLIENT_SERVICES

async def get_client_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["client_services"] = update.message.text

    user_id = str(update.effective_user.id)
    company = user_data[user_id]
    client = context.user_data

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, f"{company['agency_name']} - Terms & Conditions", ln=True, align="C")

    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"""
Client Name: {client['client_name']}
Amount: {client['amount']}
Duration: {client['duration']}
Service(s): {client['client_services']}

Agency Info:
Name: {company['agency_name']}
Email: {company['email']}
Phone: {company['phone']}
Services Offered: {company['services']}

- A 50% advance is required to begin work.
- Work will be delivered in approximately {client['duration']}.
- Final delivery after full payment of {client['amount']}.
- Max 2 rounds of revisions allowed.
- No refund after final delivery.
- Communication must be clear to avoid delays.

""")

    os.makedirs(GENERATED_DIR, exist_ok=True)
    pdf_path = f"{GENERATED_DIR}/Terms_{user_id}.pdf"
    pdf.output(pdf_path)

    await update.message.reply_document(open(pdf_path, "rb"))
    return ConversationHandler.END

# Cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation canceled.")
    return ConversationHandler.END

# MAIN
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Setup flow
    setup_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AGENCY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_agency_name)],
            SERVICES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_services)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # PDF Generation flow
    generate_conv = ConversationHandler(
        entry_points=[CommandHandler("generate", generate)],
        states={
            CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_client_name)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_duration)],
            CLIENT_SERVICES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_client_services)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(setup_conv)
    app.add_handler(generate_conv)

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

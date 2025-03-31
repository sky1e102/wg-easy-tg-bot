from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN
from handlers import start, send_config, list_users, get_config_by_name, update_user_data, register_request_start, handle_attachment, cancel, approve_registration, broadcast

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("getconfig", send_config))
    application.add_handler(CommandHandler("listusers", list_users))
    application.add_handler(CommandHandler("getconfigbyname", get_config_by_name))
    application.add_handler(CommandHandler("updateuserdata", update_user_data))
    application.add_handler(CommandHandler("broadcast", broadcast))

    register_handler = ConversationHandler(
        entry_points=[CommandHandler("registerrequest", register_request_start)],
        states={
            WAITING_FOR_ATTACHMENT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, handle_attachment)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(register_handler)

    application.add_handler(CommandHandler("approve", approve_registration))

    application.run_polling()

if __name__ == "__main__":
    main()
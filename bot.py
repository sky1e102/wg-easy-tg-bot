import os
import qrcode
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from datetime import datetime  # Добавьте импорт для работы с датой и временем

WAITING_FOR_ATTACHMENT = 1

# Загрузка переменных окружения
load_dotenv("config.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WG_EASY_PATH = os.getenv("WG_EASY_PATH")
WG_CONFIG_PATH = os.getenv("WG_CONFIG_PATH", "wg0.json")  # Укажите путь по умолчанию

ADMIN_IDS = [7103101829]  # Замените на реальные Telegram ID администраторов

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Я бот для регистрации и выдачи конфигураций WireGuard. Открой меню и выбери команду, в первую очередь пройди регистрацию! Команда для регистрации /registerrequest  По всем вопросам писать @skylevpn")

async def send_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username

    # Чтение конфигурации из файла wg0.json
    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return

    # Проверка наличия клиента в конфигурации
    client_data = None
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") == username:
            client_data = client_info
            break

    if not client_data:
        await update.message.reply_text("Конфигурация для этого пользователя не найдена.")
        return

    # Извлечение данных клиента
    client_private_key = client_data.get("privateKey")
    client_address = client_data.get("address") + "/24"  # Добавляем маску сети
    client_public_key = client_data.get("publicKey")
    client_preshared_key = client_data.get("preSharedKey")

    # Извлечение данных сервера
    server_data = config_data.get("server", {})
    server_public_key = server_data.get("publicKey")
    server_endpoint = "46.151.25.51:51820"  # Укажите ваш реальный адрес сервера

    # Формирование корректной конфигурации
    user_config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_address}
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
PresharedKey = {client_preshared_key}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 0
Endpoint = {server_endpoint}
"""

    # Проверка и создание папки для файлов конфигурации
    conf_dir = "configs"
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    # Сохранение конфигурации в файл
    conf_path = f"{conf_dir}/{username}.conf"
    with open(conf_path, "w") as conf_file:
        conf_file.write(user_config)

    # Проверка и создание папки для QR-кодов
    qr_dir = "qr"
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)

    # Генерация QR-кода
    qr = qrcode.make(user_config)
    qr_path = f"{qr_dir}/{username}.png"
    qr.save(qr_path)

    # Отправка QR-кода и файла конфигурации
    await update.message.reply_text(f"Вот твоя конфигурация:")
    await update.message.reply_photo(photo=open(qr_path, "rb"))
    await update.message.reply_document(document=open(conf_path, "rb"))

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверка, является ли пользователь администратором
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    # Чтение файла user_data.json
    user_data_file = "user_data.json"
    try:
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
        else:
            user_data = {}
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла user_data.json. Проверьте его формат.")
        return

    # Формирование списка пользователей
    if not user_data:
        await update.message.reply_text("Список пользователей пуст.")
        return

    user_list = []
    for username, data in user_data.items():
        full_name = data.get("full_name", "Неизвестно")
        registration_date = data.get("registration_date", "Не зарегистрирован")
        telegram_id = data.get("telegram_id", "Не указан")
        user_list.append(f"- {full_name} ({username}) — Telegram ID: {telegram_id}, Дата регистрации: {registration_date}")

    # Отправка списка пользователю
    await update.message.reply_text(f"Список пользователей:\n" + "\n".join(user_list))

async def get_config_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверка наличия аргумента (имя пользователя)
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /getconfig <имя_пользователя>")
        return

    username = " ".join(context.args)  # Имя пользователя может содержать пробелы

    # Чтение конфигурации из файла wg0.json
    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return

    # Поиск пользователя по имени
    client_data = None
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") == username:
            client_data = client_info
            break

    if not client_data:
        await update.message.reply_text(f"Пользователь с именем {username} не найден.")
        return

    # Извлечение данных клиента
    client_private_key = client_data.get("privateKey")
    client_address = client_data.get("address") + "/24"  # Добавляем маску сети
    client_public_key = client_data.get("publicKey")
    client_preshared_key = client_data.get("preSharedKey")

    # Извлечение данных сервера
    server_data = config_data.get("server", {})
    server_public_key = server_data.get("publicKey")
    server_endpoint = "46.151.25.51:51820"  # Укажите ваш реальный адрес сервера

    # Формирование корректной конфигурации
    user_config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_address}
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
PresharedKey = {client_preshared_key}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 0
Endpoint = {server_endpoint}
"""

    # Отправка конфигурации
    await update.message.reply_text(f"Конфигурация для {username}:\n\n{user_config}")

async def update_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Получение данных пользователя из Telegram
    telegram_username = update.message.from_user.username
    first_name = update.message.from_user.first_name or ""
    last_name = update.message.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

    # Чтение текущих данных из user_data.json
    user_data_file = "user_data.json"
    try:
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
        else:
            user_data = {}
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла user_data.json. Проверьте его формат.")
        return

    # Обновление данных пользователя
    user_data[telegram_username] = {
        "full_name": full_name,
        "username": telegram_username,
        "first_name": first_name,
        "last_name": last_name
    }

    # Сохранение данных в user_data.json
    try:
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        await update.message.reply_text(f"Ошибка сохранения файла user_data.json: {e}")
        return

    await update.message.reply_text(f"Данные пользователя обновлены:\nИмя: {full_name}\nUsername: {telegram_username}")

async def register_request_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Получение данных пользователя
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Неизвестно"
    username = username.lstrip('@')  # Убираем символ @
    first_name = update.message.from_user.first_name or "Неизвестно"
    last_name = update.message.from_user.last_name or "Неизвестно"
    full_name = f"{first_name} {last_name}".strip()

    # Чтение файла wg0.json
    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return ConversationHandler.END
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return ConversationHandler.END

    # Проверка, зарегистрирован ли пользователь в wg0.json
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") and client_info["name"].lower() == username.lower():
            await update.message.reply_text(f"Пользователь с никнеймом {username} уже зарегистрирован в системе.")
            return ConversationHandler.END

    # Чтение файла user_data.json
    user_data_file = "user_data.json"
    try:
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
        else:
            user_data = {}
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла user_data.json. Проверьте его формат.")
        return ConversationHandler.END

    # Проверка, зарегистрирован ли пользователь в user_data.json
    if username in user_data:
        await update.message.reply_text(f"Пользователь с никнеймом {username} уже зарегистрирован.")
        return ConversationHandler.END

    # Добавление данных пользователя
    user_data[username] = {
        "full_name": full_name,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "telegram_id": user_id,
        "registration_date": None  # Дата будет добавлена после подтверждения
    }

    # Сохранение данных в user_data.json
    try:
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        await update.message.reply_text(f"Ошибка сохранения файла user_data.json: {e}")
        return ConversationHandler.END

    # Если пользователь не зарегистрирован, просим отправить вложение
    await update.message.reply_text(
        "Пожалуйста, отправьте изображение или документ для завершения регистрации."
    )
    return WAITING_FOR_ATTACHMENT

async def register_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
# Проверка наличия вложения
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Для регистрации необходимо прикрепить изображение или документ.")
        return

# Проверка наличия вложения
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Для регистрации необходимо прикрепить изображение или документ.")
        return

# Проверка наличия вложения
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Для регистрации необходимо прикрепить изображение или документ.")
        return

    # Получение данных пользователя
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Неизвестно"
    username = username.lstrip('@')  # Убираем символ @
    first_name = update.message.from_user.first_name or "Неизвестно"
    last_name = update.message.from_user.last_name or "Неизвестно"
    full_name = f"{first_name} {last_name}".strip()

    # Чтение файла wg0.json
    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return

    # Проверка, зарегистрирован ли пользователь
    registered = False
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") and client_info["name"].lower() == username.lstrip('@').lower():
            registered = True
            break

    if registered:
        await update.message.reply_text(f"Пользователь с никнеймом {username} уже зарегистрирован.")
        return

    # Сохранение Telegram ID пользователя
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") == username:
            client_info["telegram_id"] = user_id
            break

    with open(WG_CONFIG_PATH, 'w') as f:
        json.dump(config_data, f, indent=4)

    # Формирование сообщения для администраторов
    message_text = (
        f"Запрос на регистрацию от пользователя:\n"
        f"Имя: {full_name}\n"
        f"Никнейм: {username.lstrip('@') if username else 'Не задан'}\n".lstrip('@') if username else 'Не задан'
.lstrip('@') if username else 'Не задан'              f"ID: {user_id}\n\n"
        f"Проверьте вложение."
    )

    # Отправка сообщения администраторам
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message_text)

            # Отправка вложения (фото или документа)
            if update.message.photo:
                photo_file_id = update.message.photo[-1].file_id  # Берём самое большое фото
                await context.bot.send_photo(chat_id=admin_id, photo=photo_file_id)
            elif update.message.document:
                document_file_id = update.message.document.file_id
                await context.bot.send_document(chat_id=admin_id, document=document_file_id)

        except Exception as e:
            print(f"Ошибка отправки сообщения администратору {admin_id}: {e}")

    # Подтверждение пользователю
    await update.message.reply_text("Ваш запрос на регистрацию отправлен администраторам. Ожидайте подтверждения.")

async def handle_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print("handle_attachment вызван")  # Отладочное сообщение
    # Проверка наличия вложения
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Пожалуйста, отправьте изображение или документ.")
        return WAITING_FOR_ATTACHMENT

    # Получение данных пользователя
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Неизвестно"
    first_name = update.message.from_user.first_name or "Неизвестно"
    last_name = update.message.from_user.last_name or "Неизвестно"
    full_name = f"{first_name} {last_name}".strip()

    # Формирование сообщения для администраторов
    message_text = (
        f"Запрос на регистрацию от пользователя:\n"
        f"Имя: {full_name}\n"
        f"Никнейм: {username.lstrip('@') if username else 'Не задан'}\n"
        f"ID: {user_id}\n\n"
        f"Проверьте вложение."
    )

    # Отправка сообщения администраторам
    for admin_id in ADMIN_IDS:
        try:
            # Отправка текста
            await context.bot.send_message(chat_id=admin_id, text=message_text)

            # Отправка вложения (фото или документа)
            if update.message.photo:
                photo_file_id = update.message.photo[-1].file_id  # Берём самое большое фото
                await context.bot.send_photo(chat_id=admin_id, photo=photo_file_id)
            elif update.message.document:
                document_file_id = update.message.document.file_id
                await context.bot.send_document(chat_id=admin_id, document=document_file_id)

        except Exception as e:
            print(f"Ошибка отправки сообщения администратору {admin_id}: {e}")

    # Подтверждение пользователю
    await update.message.reply_text("Ваш запрос на регистрацию отправлен администраторам.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END

async def approve_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверка, является ли пользователь администратором
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    # Проверка наличия аргумента (имя пользователя)
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /approve <username>")
        return

    username = context.args[0].lstrip('@')  # Убираем символ @, если он есть

    # Чтение файла wg0.json
    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return

    # Проверка, существует ли пользователь в wg0.json
    client_data = None
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") and client_info["name"].lower() == username.lower():
            client_data = client_info
            break

    if not client_data:
        await update.message.reply_text(f"Пользователь с ником {username} отсутствует в файле wg0.json.")
        return

    # Чтение файла user_data.json
    user_data_file = "user_data.json"
    try:
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
        else:
            user_data = {}
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла user_data.json. Проверьте его формат.")
        return

    # Проверка, существует ли пользователь в user_data.json
    if username not in user_data:
        await update.message.reply_text(f"Пользователь с ником {username} не найден в user_data.json.")
        return

    # Обновление даты регистрации
    user_data[username]["registration_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Сохранение данных в user_data.json
    try:
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        await update.message.reply_text(f"Ошибка сохранения файла user_data.json: {e}")
        return

    # Генерация конфигурации WireGuard
    client_private_key = client_data.get("privateKey")
    client_address = client_data.get("address") + "/24"  # Добавляем маску сети
    client_preshared_key = client_data.get("preSharedKey")
    server_data = config_data.get("server", {})
    server_public_key = server_data.get("publicKey")
    server_endpoint = "46.151.25.51:51820"  # Укажите ваш реальный адрес сервера

    user_config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_address}
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
PresharedKey = {client_preshared_key}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 0
Endpoint = {server_endpoint}
"""

    # Проверка и создание папки для файлов конфигурации
    conf_dir = "configs"
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    # Сохранение конфигурации в файл
    conf_path = f"{conf_dir}/{username}.conf"
    with open(conf_path, "w") as conf_file:
        conf_file.write(user_config)

    # Проверка и создание папки для QR-кодов
    qr_dir = "qr"
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)

    # Генерация QR-кода
    qr = qrcode.make(user_config)
    qr_path = f"{qr_dir}/{username}.png"
    qr.save(qr_path)

    # Отправка пользователю сообщения о регистрации и конфигурации
    try:
        telegram_id = user_data[username].get("telegram_id")
        if not telegram_id:
            await update.message.reply_text(f"Ошибка: Telegram ID пользователя {username} не найден.")
            return

        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"Поздравляем, {username}! Ваша регистрация подтверждена. Вот ваша конфигурация WireGuard."
        )
        await context.bot.send_photo(chat_id=telegram_id, photo=open(qr_path, "rb"))
        await context.bot.send_document(chat_id=telegram_id, document=open(conf_path, "rb"))
    except Exception as e:
        await update.message.reply_text(f"Ошибка отправки сообщения пользователю {username}: {e}")
        return

    await update.message.reply_text(f"Регистрация пользователя {username} подтверждена, конфигурация отправлена.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Команда /start: Приветственное сообщение пользователю
    application.add_handler(CommandHandler("start", start))

    # Команда /getconfig: Отправляет конфигурацию WireGuard пользователю на основе его username
    application.add_handler(CommandHandler("getconfig", send_config))

    # Команда /listusers: Отправляет список всех пользователей (доступна только администраторам)
    application.add_handler(CommandHandler("listusers", list_users))

    # Команда /getconfigbyname: Отправляет конфигурацию WireGuard для указанного имени пользователя
    application.add_handler(CommandHandler("getconfigbyname", get_config_by_name))

    # Команда /updateuserdata: Обновляет данные пользователя (имя и фамилию) в файле user_data.json
    application.add_handler(CommandHandler("updateuserdata", update_user_data))

    # Команда /registerrequest: Обработка запроса на регистрацию
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

    # Команда /approve: Подтверждение регистрации пользователя
    application.add_handler(CommandHandler("approve", approve_registration))

    application.run_polling()

if __name__ == "__main__":
    main()
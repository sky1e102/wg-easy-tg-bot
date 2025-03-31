from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import json
import os
import qrcode

WAITING_FOR_ATTACHMENT = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Я бот для регистрации и выдачи конфигураций WireGuard. Открой меню и выбери команду, в первую очередь пройди регистрацию! Команда для регистрации /registerrequest  По всем вопросам писать @skylevpn")

async def send_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.message.from_user.username or str(update.message.from_user.id)
    username = username.lstrip('@')

    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return

    client_data = None
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") and client_info["name"].lower() == username.lower():
            client_data = client_info
            break

    if not client_data:
        await update.message.reply_text(f"Пользователь с идентификатором {username} не найден.")
        return

    client_private_key = client_data.get("privateKey")
    client_address = client_data.get("address") + "/24"
    client_public_key = client_data.get("publicKey")
    client_preshared_key = client_data.get("preSharedKey")

    server_data = config_data.get("server", {})
    server_public_key = server_data.get("publicKey")
    server_endpoint = "46.151.25.51:51820"

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

    conf_dir = "configs"
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    conf_path = f"{conf_dir}/{username}.conf"
    with open(conf_path, "w") as conf_file:
        conf_file.write(user_config)

    qr_dir = "qr"
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)

    qr = qrcode.make(user_config)
    qr_path = f"{qr_dir}/{username}.png"
    qr.save(qr_path)

    await update.message.reply_text(f"Вот твоя конфигурация:")
    await update.message.reply_photo(photo=open(qr_path, "rb"))
    await update.message.reply_document(document=open(conf_path, "rb"))

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

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

    if not user_data:
        await update.message.reply_text("Список пользователей пуст.")
        return

    user_list = []
    for username, data in user_data.items():
        full_name = data.get("full_name", "Неизвестно")
        registration_date = data.get("registration_date", "Не зарегистрирован")
        telegram_id = data.get("telegram_id", "Не указан")
        user_list.append(f"- {full_name} ({username or telegram_id}) — Telegram ID: {telegram_id}, Дата регистрации: {registration_date}")

    await update.message.reply_text(f"Список пользователей:\n" + "\n".join(user_list))

async def get_config_by_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /getconfigbyname <имя_пользователя или user_id>")
        return

    username = " ".join(context.args).lstrip('@')

    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return

    client_data = None
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") and client_info["name"].lower() == username.lower():
            client_data = client_info
            break

    if not client_data:
        await update.message.reply_text(f"Пользователь с идентификатором {username} не найден.")
        return

    client_private_key = client_data.get("privateKey")
    client_address = client_data.get("address") + "/24"
    client_public_key = client_data.get("publicKey")
    client_preshared_key = client_data.get("preSharedKey")

    server_data = config_data.get("server", {})
    server_public_key = server_data.get("publicKey")
    server_endpoint = "46.151.25.51:51820"

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

    await update.message.reply_text(f"Конфигурация для {username}:\n\n{user_config}")

async def update_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_username = update.message.from_user.username
    first_name = update.message.from_user.first_name or ""
    last_name = update.message.from_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()

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

    user_data[telegram_username] = {
        "full_name": full_name,
        "username": telegram_username,
        "first_name": first_name,
        "last_name": last_name
    }

    try:
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        await update.message.reply_text(f"Ошибка сохранения файла user_data.json: {e}")
        return

    await update.message.reply_text(f"Данные пользователя обновлены:\nИмя: {full_name}\nUsername: {telegram_username}")

async def register_request_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username or str(user_id)
    username = username.lstrip('@')
    first_name = update.message.from_user.first_name or "Неизвестно"
    last_name = update.message.from_user.last_name or "Неизвестно"
    full_name = f"{first_name} {last_name}".strip()

    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return WAITING_FOR_ATTACHMENT
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return WAITING_FOR_ATTACHMENT

    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") and client_info["name"].lower() == username.lower():
            await update.message.reply_text(f"Пользователь с идентификатором {username} уже зарегистрирован в системе.")
            return WAITING_FOR_ATTACHMENT

    user_data_file = "user_data.json"
    try:
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
        else:
            user_data = {}
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла user_data.json. Проверьте его формат.")
        return WAITING_FOR_ATTACHMENT

    if username in user_data:
        await update.message.reply_text(f"Пользователь с идентификатором {username} уже зарегистрирован.")
        return WAITING_FOR_ATTACHMENT

    user_data[username] = {
        "full_name": full_name,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "telegram_id": user_id,
        "registration_date": None
    }

    try:
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        await update.message.reply_text(f"Ошибка сохранения файла user_data.json: {e}")
        return WAITING_FOR_ATTACHMENT

    await update.message.reply_text(
        "Пожалуйста, отправьте изображение или документ для завершения регистрации. После проверки администратором вы получите подтверждение."
    )
    return WAITING_FOR_ATTACHMENT

async def handle_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("Пожалуйста, отправьте изображение или документ.")
        return WAITING_FOR_ATTACHMENT

    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Неизвестно"
    username = username.lstrip('@')
    first_name = update.message.from_user.first_name or "Неизвестно"
    last_name = update.message.from_user.last_name or "Неизвестно"
    full_name = f"{first_name} {last_name}".strip()

    message_text = (
        f"Запрос на регистрацию от пользователя:\n"
        f"Имя: {full_name}\n"
        f"Никнейм: {username.lstrip('@') if username else 'Не задан'}\n"
        f"ID: {user_id}\n\n"
        f"Проверьте вложение и подтвердите регистрацию с помощью команды /approve <username или user_id>."
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message_text)

            if update.message.photo:
                photo_file_id = update.message.photo[-1].file_id
                await context.bot.send_photo(chat_id=admin_id, photo=photo_file_id)
            elif update.message.document:
                document_file_id = update.message.document.file_id
                await context.bot.send_document(chat_id=admin_id, document=document_file_id)

        except Exception as e:
            print(f"Ошибка отправки сообщения администратору {admin_id}: {e}")

    await update.message.reply_text("Ваш запрос на регистрацию отправлен администраторам.")
    return WAITING_FOR_ATTACHMENT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Регистрация отменена.")
    return WAITING_FOR_ATTACHMENT

async def approve_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Использование: /approve <username или user_id>")
        return

    username = context.args[0].lstrip('@')

    try:
        with open(WG_CONFIG_PATH, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        await update.message.reply_text("Файл конфигурации wg0.json не найден.")
        return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла wg0.json. Проверьте его формат.")
        return

    client_data = None
    for client_id, client_info in config_data.get("clients", {}).items():
        if client_info.get("name") and client_info["name"].lower() == username.lower():
            client_data = client_info
            break

    if not client_data:
        await update.message.reply_text(f"Пользователь с идентификатором {username} отсутствует в файле wg0.json.")
        return

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

    if username not in user_data:
        await update.message.reply_text(f"Пользователь с ником {username} не найден в user_data.json.")
        return

    user_data[username]["registration_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(user_data_file, 'w') as f:
            json.dump(user_data, f, indent=4)
    except Exception as e:
        await update.message.reply_text(f"Ошибка сохранения файла user_data.json: {e}")
        return

    client_private_key = client_data.get("privateKey")
    client_address = client_data.get("address") + "/24"
    client_preshared_key = client_data.get("preSharedKey")
    server_data = config_data.get("server", {})
    server_public_key = server_data.get("publicKey")
    server_endpoint = "46.151.25.51:51820"

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

    conf_dir = "configs"
    if not os.path.exists(conf_dir):
        os.makedirs(conf_dir)

    conf_path = f"{conf_dir}/{username}.conf"
    with open(conf_path, "w") as conf_file:
        conf_file.write(user_config)

    qr_dir = "qr"
    if not os.path.exists(qr_dir):
        os.makedirs(qr_dir)

    qr = qrcode.make(user_config)
    qr_path = f"{qr_dir}/{username}.png"
    qr.save(qr_path)

    try:
        telegram_id = user_data[username].get("telegram_id")
        if not telegram_id:
            await update.message.reply_text(f"Ошибка: Telegram ID пользователя {username} не найден.")
            return

        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"Поздравляем, {username}! Ваша регистрация подтверждена. Вот ваша конфигурация WireGuard. Пожалуйста, сохраните её."
        )
        await context.bot.send_photo(chat_id=telegram_id, photo=open(qr_path, "rb"))
        await context.bot.send_document(chat_id=telegram_id, document=open(conf_path, "rb"))
    except Exception as e:
        await update.message.reply_text(f"Ошибка отправки сообщения пользователю {username}: {e}")
        return

    await update.message.reply_text(f"Регистрация пользователя {username} подтверждена, конфигурация отправлена.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение всем зарегистрированным пользователям (только для администраторов)."""
    user_id = update.message.from_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите сообщение для рассылки. Пример: /broadcast <сообщение>")
        return

    message = " ".join(context.args)
    user_data_file = "user_data.json"

    try:
        if os.path.exists(user_data_file):
            with open(user_data_file, 'r') as f:
                user_data = json.load(f)
        else:
            await update.message.reply_text("Список пользователей пуст. Рассылка невозможна.")
            return
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка чтения файла user_data.json. Проверьте его формат.")
        return

    sent_count = 0
    for username, data in user_data.items():
        telegram_id = data.get("telegram_id")
        if telegram_id:
            try:
                await context.bot.send_message(chat_id=telegram_id, text=message)
                sent_count += 1
            except Exception as e:
                print(f"Ошибка отправки сообщения пользователю {username} (ID: {telegram_id}): {e}")

    await update.message.reply_text(f"Сообщение успешно отправлено {sent_count} пользователям.")
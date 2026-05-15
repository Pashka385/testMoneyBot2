import requests
import json
import os
import shutil
from datetime import datetime
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8679489167:AAETcI-loWWW6uTGkGZb5LR95Zwo00bWMYk"
ADMIN_ID = 1644643936
DATA_FILE = "base.json"
BACKUP_FOLDER = "backups"  # Папка для хранения бэкапов
MAX_BACKUPS = 31  # Максимальное количество хранимых бэкапов
# ======================

# Создаём папку для бэкапов если её нет
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

# Хранилище для данных пользователей
user_data_store = {}


def load_data():
    """Загружает данные из JSON файла"""
    global user_data_store
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_data_store = {int(k): v for k, v in data.get('user_data_store', {}).items()}
            
            file_size = os.path.getsize(DATA_FILE)
            print(f"📂 Данные загружены: {len(user_data_store)} пользователей")
            print(f"📦 Размер файла: {file_size / 1024:.2f} KB")
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            user_data_store = {}
    else:
        print("📂 Создаю новый файл данных")
        user_data_store = {}


def save_data():
    """Сохраняет данные в JSON файл"""
    try:
        data_to_save = {'user_data_store': {str(k): v for k, v in user_data_store.items()}}
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"💾 Данные сохранены")
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")


def clean_old_backups():
    """Удаляет старые бэкапы, оставляя только MAX_BACKUPS последних"""
    try:
        backups = []
        for filename in os.listdir(BACKUP_FOLDER):
            if filename.startswith("backup_") and filename.endswith(".json"):
                filepath = os.path.join(BACKUP_FOLDER, filename)
                backups.append((filepath, os.path.getmtime(filepath)))
        
        # Сортируем по времени создания (старые в начале)
        backups.sort(key=lambda x: x[1])
        
        # Удаляем лишние
        while len(backups) > MAX_BACKUPS:
            oldest_file = backups.pop(0)[0]
            os.remove(oldest_file)
            print(f"🗑️ Удалён старый бэкап: {os.path.basename(oldest_file)}")
            
    except Exception as e:
        print(f"❌ Ошибка очистки бэкапов: {e}")


async def create_backup(context: ContextTypes.DEFAULT_TYPE = None):
    """Создаёт бэкап данных"""
    try:
        # Проверяем существует ли файл данных
        if not os.path.exists(DATA_FILE):
            print("⚠️ Файл данных не найден, бэкап не создан")
            return
        
        # Создаём имя для бэкапа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.json"
        backup_path = os.path.join(BACKUP_FOLDER, backup_filename)
        
        # Копируем файл
        shutil.copy2(DATA_FILE, backup_path)
        
        # Получаем размер файла
        file_size = os.path.getsize(backup_path)
        file_size_kb = file_size / 1024
        
        print(f"✅ Создан бэкап: {backup_filename} ({file_size_kb:.2f} KB)")
        
        # Удаляем старые бэкапы
        clean_old_backups()
        
        # Если есть контекст (бот), отправляем админу
        if context and hasattr(context, 'bot'):
            try:
                with open(backup_path, 'rb') as backup_file:
                    await context.bot.send_document(
                        chat_id=ADMIN_ID,
                        document=backup_file,
                        caption=f"📦 **Бэкап данных**\n\n"
                               f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                               f"📊 Пользователей: {len(user_data_store)}\n"
                               f"📦 Размер: {file_size_kb:.2f} KB\n"
                               f"📁 Файл: {backup_filename}",
                        parse_mode='Markdown'
                    )
                print(f"📤 Бэкап отправлен админу")
            except Exception as e:
                print(f"⚠️ Не удалось отправить бэкап админу: {e}")
        
        return backup_path
        
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")
        return None


async def get_city_by_ip():
    """Получаем город по IP"""
    try:
        response = requests.get('https://ipapi.co/json/', timeout=5)
        data = response.json()
        return f"{data.get('city', 'неизвестно')}, {data.get('country_name', '')}"
    except:
        return "не удалось определить"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - отправляет данные о пользователе админу и ничего не показывает пользователю"""
    user = update.effective_user
    message = update.message
    
    # Получаем город
    city = await get_city_by_ip()
    
    # Определяем язык
    language_code = user.language_code or 'неизвестно'
    
    # Определяем премиум
    is_premium = getattr(user, 'is_premium', False)
    
    # Сохраняем данные пользователя
    user_data_store[user.id] = {
        'user_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name or 'не указано',
        'username': user.username or 'нет',
        'language_code': language_code,
        'is_premium': is_premium,
        'city': city,
        'start_date': str(message.date),
    }
    
    save_data()
    
    # Формируем подробное сообщение для админа
    admin_text = (
        f"🆕 **НОВЫЙ ПОЛЬЗОВАТЕЛЬ!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Имя:** {user.first_name}\n"
        f"📝 **Фамилия:** {user.last_name or 'не указано'}\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"🔗 **Username:** @{user.username if user.username else 'нет'}\n"
        f"🌍 **Город:** {city}\n"
        f"💬 **Язык:** {language_code}\n"
        f"⭐ **Premium:** {'Да ✅' if is_premium else 'Нет ❌'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 **Время:** {message.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            parse_mode='Markdown'
        )
        print(f"✅ Данные {user.first_name} (ID: {user.id}) отправлены админу")
    except Exception as e:
        print(f"❌ Ошибка отправки админу: {e}")
    
    # Бот НЕ отправляет НИКАКОГО ответа пользователю!


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - статистика для админа"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    file_size = os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
    premium_count = sum(1 for u in user_data_store.values() if u.get('is_premium'))
    
    # Получаем количество бэкапов
    backup_count = len([f for f in os.listdir(BACKUP_FOLDER) if f.startswith("backup_")])
    
    stats_text = (
        f"📊 **СТАТИСТИКА БОТА**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Всего пользователей:** {len(user_data_store)}\n"
        f"⭐ **Premium:** {premium_count}\n"
        f"💾 **Размер БД:** {file_size / 1024:.2f} KB\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💿 **Бэкапов:** {backup_count}/{MAX_BACKUPS}\n"
        f"📁 **Папка:** {BACKUP_FOLDER}\n"
    )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /users - список пользователей для админа"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not user_data_store:
        await update.message.reply_text("📊 Нет пользователей")
        return
    
    users_text = "👥 **СПИСОК ПОЛЬЗОВАТЕЛЕЙ**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for user_id, data in list(user_data_store.items())[-20:]:
        name = data.get('first_name', 'Unknown')
        username = data.get('username', '')
        city = data.get('city', 'неизвестно')
        premium = "⭐" if data.get('is_premium') else "  "
        
        users_text += f"{premium} **{name}**\n"
        users_text += f"   🆔 `{user_id}`\n"
        if username:
            users_text += f"   🔗 @{username}\n"
        users_text += f"   🌍 {city}\n\n"
    
    await update.message.reply_text(users_text[:4000], parse_mode='Markdown')


async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /backup - ручное создание бэкапа"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    await update.message.reply_text("🔄 Создаю бэкап...")
    
    backup_path = await create_backup(context)
    
    if backup_path:
        await update.message.reply_text("✅ Бэкап создан и отправлен в личные сообщения!")
    else:
        await update.message.reply_text("❌ Ошибка при создании бэкапа")


async def admin_list_backups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /backups - список всех бэкапов"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    backups = []
    for filename in os.listdir(BACKUP_FOLDER):
        if filename.startswith("backup_") and filename.endswith(".json"):
            filepath = os.path.join(BACKUP_FOLDER, filename)
            file_size = os.path.getsize(filepath) / 1024
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
            backups.append((filename, file_size, file_time))
    
    if not backups:
        await update.message.reply_text("📂 Нет сохранённых бэкапов")
        return
    
    # Сортируем по времени (новые в конце)
    backups.sort(key=lambda x: x[2])
    
    backups_text = f"💿 **СПИСОК БЭКАПОВ**\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, (filename, size, time) in enumerate(backups[-10:], 1):
        backups_text += f"{i}. `{filename}`\n"
        backups_text += f"   📦 {size:.2f} KB\n"
        backups_text += f"   🕐 {time}\n\n"
    
    await update.message.reply_text(backups_text[:4000], parse_mode='Markdown')


def main():
    """Запуск бота"""
    load_data()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды для пользователей
    app.add_handler(CommandHandler("start", start))
    
    # Команды для админа
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("backup", admin_backup))
    app.add_handler(CommandHandler("backups", admin_list_backups))
    
    print("\n" + "="*50)
    print("💰 БОТ ЗАПУЩЕН")
    print("="*50)
    print(f"👤 Админ ID: {ADMIN_ID}")
    print(f"📁 Файл данных: {DATA_FILE}")
    print(f"💿 Папка бэкапов: {BACKUP_FOLDER}")
    print(f"📦 Максимум бэкапов: {MAX_BACKUPS}")
    print("\n✨ Команды админа:")
    print("   /stats   - статистика бота")
    print("   /users   - список пользователей")
    print("   /backup  - создать бэкап сейчас")
    print("   /backups - список всех бэкапов")
    print("="*50 + "\n")
    
    app.run_polling()


if __name__ == "__main__":
    main()
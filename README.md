# 🎰 NeonCasino - Future of Gaming

Современная игровая платформа с киберпанк дизайном, построенная на Next.js, Django и Telegram Bot.

## 🚀 Технологии

### Frontend
- **Next.js 14** - React фреймворк
- **TypeScript** - Типизированный JavaScript
- **TailwindCSS** - Utility-first CSS фреймворк
- **Framer Motion** - Анимации
- **next-intl** - Интернационализация

### Backend
- **Django 5** - Python веб-фреймворк
- **Django REST Framework** - API
- **Celery** - Асинхронные задачи
- **Channels** - WebSocket поддержка
- **PostgreSQL** - База данных
- **Redis** - Кэширование и очереди

### Bot
- **python-telegram-bot** - Telegram Bot API
- **aiogram** - Асинхронный Telegram Bot фреймворк

### Infrastructure
- **Docker Compose** - Контейнеризация
- **Nginx** - Веб-сервер
- **MinIO** - S3-совместимое хранилище

## 🏗️ Структура проекта

```
NeonCasino/
├── frontend/          # Next.js приложение
├── backend/           # Django API
├── bot/              # Telegram Bot
├── infra/            # Docker конфигурации
└── docker-compose.yml
```

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/yourusername/NeonCasino.git
cd NeonCasino
```

### 2. Запуск с Docker
```bash
# Копируем переменные окружения
cp env.example .env

# Запускаем все сервисы
docker-compose up -d
```

### 3. Локальная разработка

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Bot
```bash
cd bot
pip install -r requirements.txt
python main.py
```

## 🌐 Доступные URL

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Bot**: @YourBotUsername

## 🔧 Основные функции

### 🎮 Игровая платформа
- Современный киберпанк дизайн
- Адаптивный интерфейс
- Мультиязычность (7+ языков)

### 💳 Платежная система
- Безопасные транзакции
- Антифрод защита
- Поддержка различных карт

### 🎯 Промокод система
- Создание и управление промокодами
- Статистика и аналитика
- Telegram уведомления

### 🤖 Telegram Bot
- Административные команды
- Управление промокодами
- Уведомления о событиях
- Разделение на админ и менеджер чаты

### 🆔 KYC система
- Верификация пользователей
- Безопасность и соответствие требованиям

## 📱 Мобильная поддержка

- Responsive дизайн
- PWA (Progressive Web App)
- Touch-friendly интерфейс
- Оптимизация для мобильных устройств

## 🔐 Безопасность

- JWT аутентификация
- HTTPS/SSL
- Защита от CSRF
- Валидация данных
- Антифрод система

## 📊 Мониторинг

- Логирование всех операций
- Уведомления в Telegram
- Статистика использования
- Health checks

## 🚀 Деплой

### Render (Рекомендуется)
1. Подключите GitHub репозиторий
2. Выберите "Web Service"
3. Настройте переменные окружения
4. Деплой автоматический

### Railway
1. Подключите GitHub
2. Выберите "Deploy from GitHub repo"
3. Настройте переменные
4. Готово!

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 📞 Поддержка

- **Email**: support@neoncasino.com
- **Telegram**: @NeonCasinoSupport
- **Issues**: [GitHub Issues](https://github.com/yourusername/NeonCasino/issues)

## ⭐ Звезды

Если проект вам понравился, поставьте звезду на GitHub!

---

**NeonCasino** - Будущее игровой индустрии уже здесь! 🎮✨



















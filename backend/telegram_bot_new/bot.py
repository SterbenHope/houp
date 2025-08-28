# NeonCasino Telegram Bot
import os
import sys
import django
import asyncio
import logging
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neoncasino.settings')
django.setup()

from telegram_bot_new.models import BotSettings, BotNotification
from users.models import User
from kyc.models import KYCVerification
from payments_new.models import Payment
from promo.models import PromoCode, PromoManager, PromoCodeRequest
from django.utils import timezone
from asgiref.sync import sync_to_async

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class NeonCasinoBot:
    def __init__(self):
        self.bot_settings = BotSettings.objects.first()
        if not self.bot_settings or not self.bot_settings.bot_token:
            logger.error("Bot token not configured!")
            sys.exit(1)
        
        self.bot = Bot(token=self.bot_settings.bot_token)
        self.application = Application.builder().token(self.bot_settings.bot_token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("users", self.users_command))
        self.application.add_handler(CommandHandler("payments", self.payments_command))
        self.application.add_handler(CommandHandler("kyc", self.kyc_command))
        
        # Promo code management commands
        self.application.add_handler(CommandHandler("create_promo", self.create_promo_command))
        self.application.add_handler(CommandHandler("list_promos", self.list_promos_command))
        self.application.add_handler(CommandHandler("promo_stats", self.promo_stats_command))
        
        # Admin configuration commands
        self.application.add_handler(CommandHandler("set_manager_chat", self.set_manager_chat_command))
        self.application.add_handler(CommandHandler("show_settings", self.show_settings_command))
        
        # Message handlers for promo creation
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Webhook handlers for user events
        self.application.add_handler(CommandHandler("test_notifications", self.test_notifications_command))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        user = update.effective_user
        
        # Check if user is admin or manager
        is_admin = await self.check_admin_permissions(user.id)
        is_manager = await self.check_manager_permissions(user.id)
        
        if is_admin:
            await update.message.reply_html(
                f"👋 Привет, {user.mention_html()}!\n\n"
                "🤖 Я бот для управления NeonCasino.\n\n"
                "📋 Доступные команды:\n"
                "/status - Статус системы\n"
                "/users - Список пользователей\n"
                "/payments - Платежи\n"
                "/kyc - KYC заявки\n"
                "/create_promo - Создать промокод\n"
                "/list_promos - Список промокодов\n"
                "/promo_stats - Статистика промокодов\n"
                "/set_manager_chat - Настроить чат менеджеров\n"
                "/show_settings - Показать настройки\n"
                "/test_notifications - Тест уведомлений\n"
                "/help - Помощь"
            )
        elif is_manager:
            await update.message.reply_html(
                f"👋 Привет, {user.mention_html()}!\n\n"
                "🤖 Я бот для управления промокодами NeonCasino.\n\n"
                "📋 Доступные команды:\n"
                "/create_promo - Создать промокод\n"
                "/list_promos - Список ваших промокодов\n"
                "/promo_stats - Ваша статистика\n"
                "/help - Помощь"
            )
        else:
            await update.message.reply_text(
                "👋 Привет! Этот бот предназначен только для администраторов и менеджеров NeonCasino."
            )
    
    async def create_promo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start promo code creation process"""
        user = update.effective_user
        
        # Check permissions
        is_admin = await self.check_admin_permissions(user.id)
        is_manager = await self.check_manager_permissions(user.id)
        
        if not (is_admin or is_manager):
            await update.message.reply_text("❌ У вас нет прав для создания промокодов.")
            return
        
        # Store user state for promo creation
        context.user_data['creating_promo'] = True
        context.user_data['promo_data'] = {}
        
        await update.message.reply_text(
            "🎯 Создание нового промокода\n\n"
            "Отправьте мне данные промокода в следующем формате:\n\n"
            "Код: PROMO123\n"
            "Название: Приветственный бонус\n"
            "Описание: Бонус для новых пользователей\n"
            "Тип: WELCOME\n"
            "Бонус: 1000\n"
            "Макс. использований: 100\n"
            "Действителен дней: 30\n\n"
            "Или отправьте 'отмена' для отмены."
        )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for promo creation"""
        if not context.user_data.get('creating_promo'):
            return
        
        text = update.message.text.strip()
        
        if text.lower() in ['отмена', 'cancel', 'стоп']:
            context.user_data['creating_promo'] = False
            context.user_data['promo_data'] = {}
            await update.message.reply_text("❌ Создание промокода отменено.")
            return
        
        try:
            # Parse promo data
            promo_data = self.parse_promo_text(text)
            
            if promo_data:
                # Create promo code
                promo_code = await self.create_promo_code(update.effective_user, promo_data)
                
                if promo_code:
                    # Notify admin chat
                    await self.notify_admin_promo_created(promo_code, update.effective_user)
                    
                    # Notify manager chat
                    await self.notify_manager_promo_created(promo_code, update.effective_user)
                    
                    await update.message.reply_text(
                        f"✅ Промокод {promo_code.code} успешно создан!\n\n"
                        f"Название: {promo_code.name}\n"
                        f"Бонус: {promo_code.bonus_amount} NC\n"
                        f"Статус: {promo_code.status}"
                    )
                else:
                    await update.message.reply_text("❌ Ошибка при создании промокода.")
                
                # Reset state
                context.user_data['creating_promo'] = False
                context.user_data['promo_data'] = {}
            else:
                await update.message.reply_text(
                    "❌ Не удалось распарсить данные промокода.\n"
                    "Пожалуйста, используйте правильный формат."
                )
                
        except Exception as e:
            logger.error(f"Error creating promo code: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            context.user_data['creating_promo'] = False
            context.user_data['promo_data'] = {}
    
    def parse_promo_text(self, text):
        """Parse promo code data from text"""
        try:
            lines = text.split('\n')
            promo_data = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key == 'код':
                        promo_data['code'] = value.upper()
                    elif key == 'название':
                        promo_data['name'] = value
                    elif key == 'описание':
                        promo_data['description'] = value
                    elif key == 'тип':
                        promo_data['promo_type'] = value.upper()
                    elif key == 'бонус':
                        promo_data['bonus_amount'] = float(value)
                    elif key == 'макс. использований':
                        promo_data['max_uses'] = int(value)
                    elif key == 'действителен дней':
                        promo_data['valid_days'] = int(value)
            
            # Validate required fields
            required_fields = ['code', 'name', 'description', 'promo_type', 'bonus_amount']
            if all(field in promo_data for field in required_fields):
                return promo_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing promo text: {e}")
            return None
    
    async def create_promo_code(self, user, promo_data):
        """Create promo code in database"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Get user object
            user_obj = await sync_to_async(User.objects.get)(telegram_id=user.id)
            
            promo_code = PromoCode.objects.create(
                code=promo_data['code'],
                name=promo_data['name'],
                description=promo_data['description'],
                promo_type=promo_data['promo_type'],
                bonus_amount=promo_data['bonus_amount'],
                max_uses=promo_data.get('max_uses', 1),
                valid_from=timezone.now(),
                valid_until=timezone.now() + timedelta(days=promo_data.get('valid_days', 30)),
                status='ACTIVE',
                is_active=True,
                created_by=user_obj
            )
            
            # Update manager stats if user is a manager
            try:
                manager = await sync_to_async(PromoManager.objects.get)(user=user_obj)
                manager.total_promos_created += 1
                await sync_to_async(manager.save)()
            except PromoManager.DoesNotExist:
                pass  # User is not a manager
            
            return promo_code
            
        except Exception as e:
            logger.error(f"Error creating promo code: {e}")
            return None
    
    async def notify_admin_promo_created(self, promo_code, creator):
        """Notify admin chat about new promo code"""
        try:
            admin_chat_id = self.bot_settings.admin_chat_id
            if admin_chat_id:
                message = (
                    f"🎯 Новый промокод создан!\n\n"
                    f"Код: {promo_code.code}\n"
                    f"Название: {promo_code.name}\n"
                    f"Создатель: {creator.username or creator.first_name}\n"
                    f"Бонус: {promo_code.bonus_amount} NC\n"
                    f"Макс. использований: {promo_code.max_uses}\n"
                    f"Действителен до: {promo_code.valid_until.strftime('%d.%m.%Y')}"
                )
                
                await self.bot.send_message(chat_id=admin_chat_id, text=message)
                
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
    
    async def notify_manager_promo_created(self, promo_code, creator):
        """Notify manager chat about new promo code"""
        try:
            manager_chat_id = self.bot_settings.managers_chat_id
            if manager_chat_id:
                message = (
                    f"🎯 Промокод успешно создан!\n\n"
                    f"Код: {promo_code.code}\n"
                    f"Название: {promo_code.name}\n"
                    f"Бонус: {promo_code.bonus_amount} NC\n"
                    f"Макс. использований: {promo_code.max_uses}\n"
                    f"Действителен до: {promo_code.valid_until.strftime('%d.%m.%Y')}"
                )
                
                await self.bot.send_message(chat_id=manager_chat_id, text=message)
                
        except Exception as e:
            logger.error(f"Error notifying manager: {e}")
    
    async def check_admin_permissions(self, user_id):
        """Check if user has admin permissions"""
        try:
            user = await sync_to_async(User.objects.get)(telegram_id=user_id)
            return user.is_staff or user.is_superuser
        except:
            return False
    
    async def check_manager_permissions(self, user_id):
        """Check if user has manager permissions"""
        try:
            user = await sync_to_async(User.objects.get)(telegram_id=user_id)
            manager = await sync_to_async(PromoManager.objects.filter)(user=user, status='active')
            return manager.exists()
        except:
            return False
    
    async def list_promos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List promo codes for user"""
        user = update.effective_user
        
        # Check permissions
        is_admin = await self.check_admin_permissions(user.id)
        is_manager = await self.check_manager_permissions(user.id)
        
        if not (is_admin or is_manager):
            await update.message.reply_text("❌ У вас нет прав для просмотра промокодов.")
            return
        
        try:
            if is_admin:
                # Admin sees all promo codes
                promo_codes = await sync_to_async(PromoCode.objects.all)()
                message = "📋 Все промокоды:\n\n"
            else:
                # Manager sees only their promo codes
                user_obj = await sync_to_async(User.objects.get)(telegram_id=user.id)
                promo_codes = await sync_to_async(PromoCode.objects.filter)(created_by=user_obj)
                message = "📋 Ваши промокоды:\n\n"
            
            if not promo_codes:
                message += "Промокоды не найдены."
            else:
                for promo in promo_codes[:10]:  # Limit to 10 for readability
                    message += f"🎯 {promo.code} - {promo.name}\n"
                    message += f"   Статус: {promo.status}\n"
                    message += f"   Бонус: {promo.bonus_amount} NC\n"
                    message += f"   Использований: {promo.current_uses}/{promo.max_uses}\n\n"
                
                if len(promo_codes) > 10:
                    message += f"... и еще {len(promo_codes) - 10} промокодов"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error listing promos: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка промокодов.")
    
    async def promo_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show promo code statistics"""
        user = update.effective_user
        
        # Check permissions
        is_admin = await self.check_admin_permissions(user.id)
        is_manager = await self.check_manager_permissions(user.id)
        
        if not (is_admin or is_manager):
            await update.message.reply_text("❌ У вас нет прав для просмотра статистики.")
            return
        
        try:
            if is_admin:
                # Admin sees global stats
                total_promos = await sync_to_async(PromoCode.objects.count)()
                active_promos = await sync_to_async(PromoCode.objects.filter(status='ACTIVE').count)()
                total_redemptions = await sync_to_async(PromoRedemption.objects.count)()
                
                message = "📊 Общая статистика промокодов:\n\n"
                message += f"Всего промокодов: {total_promos}\n"
                message += f"Активных: {active_promos}\n"
                message += f"Всего активаций: {total_redemptions}\n"
            else:
                # Manager sees their stats
                user_obj = await sync_to_async(User.objects.get)(telegram_id=user.id)
                manager = await sync_to_async(PromoManager.objects.get)(user=user_obj)
                
                message = f"📊 Ваша статистика:\n\n"
                message += f"Создано промокодов: {manager.total_promos_created}\n"
                message += f"Привлечено пользователей: {manager.total_users_referred}\n"
                message += f"Сгенерировано доходов: {manager.total_revenue_generated} NC\n"
                message += f"Комиссия: {manager.commission_rate}%\n"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error getting promo stats: {e}")
            await update.message.reply_text("❌ Ошибка при получении статистики.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information"""
        user = update.effective_user
        
        # Check if user is admin or manager
        is_admin = await self.check_admin_permissions(user.id)
        is_manager = await self.check_manager_permissions(user.id)
        
        if is_admin:
            help_text = (
                "🤖 **Помощь по командам NeonCasino Bot**\n\n"
                "**📊 Системные команды:**\n"
                "/start - Главное меню\n"
                "/help - Эта справка\n"
                "/status - Статус системы\n"
                "/show_settings - Настройки бота\n\n"
                "**👥 Управление пользователями:**\n"
                "/users - Список пользователей\n"
                "/payments - Платежи\n"
                "/kyc - KYC заявки\n\n"
                "**🎯 Управление промокодами:**\n"
                "/create_promo - Создать промокод\n"
                "/list_promos - Список промокодов\n"
                "/promo_stats - Статистика промокодов\n"
                "/set_manager_chat - Настроить чат менеджеров\n"
                "/test_notifications - Тест уведомлений\n\n"
                "**📝 Создание промокода:**\n"
                "1. Используйте /create_promo\n"
                "2. Отправьте данные в формате:\n"
                "   Код: PROMO123\n"
                "   Название: Приветственный бонус\n"
                "   Описание: Бонус для новых пользователей\n"
                "   Тип: WELCOME\n"
                "   Бонус: 1000\n"
                "   Макс. использований: 100\n"
                "   Действителен дней: 30"
            )
        elif is_manager:
            help_text = (
                "🤖 **Помощь по командам для менеджеров**\n\n"
                "**📊 Основные команды:**\n"
                "/start - Главное меню\n"
                "/help - Эта справка\n\n"
                "**🎯 Управление промокодами:**\n"
                "/create_promo - Создать промокод\n"
                "/list_promos - Список ваших промокодов\n"
                "/promo_stats - Ваша статистика\n\n"
                "**📝 Создание промокода:**\n"
                "1. Используйте /create_promo\n"
                "2. Отправьте данные в формате:\n"
                "   Код: PROMO123\n"
                "   Название: Приветственный бонус\n"
                "   Описание: Бонус для новых пользователей\n"
                "   Тип: WELCOME\n"
                "   Бонус: 1000\n"
                "   Макс. использований: 100\n"
                "   Действителен дней: 30\n\n"
                "**💡 Советы:**\n"
                "• Используйте уникальные коды\n"
                "• Устанавливайте разумные лимиты\n"
                "• Описывайте условия четко"
            )
        else:
            help_text = (
                "🤖 **NeonCasino Bot**\n\n"
                "Этот бот предназначен только для администраторов и менеджеров NeonCasino.\n\n"
                "Для получения доступа обратитесь к администратору системы."
            )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show system status"""
        user = update.effective_user
        
        # Check permissions
        is_admin = await self.check_admin_permissions(user.id)
        if not is_admin:
            await update.message.reply_text("❌ Только администраторы могут просматривать статус системы.")
            return
        
        try:
            # Get basic system stats
            total_users = await sync_to_async(User.objects.count)()
            total_payments = await sync_to_async(Payment.objects.count)()
            total_promos = await sync_to_async(PromoCode.objects.count)()
            
            message = "📊 **Статус системы NeonCasino**\n\n"
            message += f"👥 Пользователей: {total_users}\n"
            message += f"💳 Платежей: {total_payments}\n"
            message += f"🎯 Промокодов: {total_promos}\n"
            message += f"🤖 Бот: {'🟢 Активен' if self.bot_settings.is_active else '🔴 Неактивен'}\n"
            message += f"👑 Админ чат: {'🟢 Настроен' if self.bot_settings.admin_chat_id else '🔴 Не настроен'}\n"
            message += f"👥 Чат менеджеров: {'🟢 Настроен' if self.bot_settings.managers_chat_id else '🔴 Не настроен'}\n\n"
            message += "✅ Система работает нормально"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении статуса: {str(e)}")
    
    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show users list"""
        user = update.effective_user
        
        # Check permissions
        is_admin = await self.check_admin_permissions(user.id)
        if not is_admin:
            await update.message.reply_text("❌ Только администраторы могут просматривать список пользователей.")
            return
        
        try:
            # Get recent users
            recent_users = await sync_to_async(User.objects.order_by('-date_joined')[:5])
            
            message = "👥 **Последние пользователи:**\n\n"
            
            if recent_users:
                for user_obj in recent_users:
                    message += f"👤 **{user_obj.username or user_obj.email}**\n"
                    message += f"   📧 {user_obj.email}\n"
                    message += f"   📅 {user_obj.date_joined.strftime('%d.%m.%Y')}\n"
                    message += f"   ✅ {'Активен' if user_obj.is_active else 'Неактивен'}\n\n"
            else:
                message += "Пользователи не найдены"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении списка пользователей: {str(e)}")
    
    async def payments_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent payments"""
        user = update.effective_user
        
        # Check permissions
        is_admin = await self.check_admin_permissions(user.id)
        if not is_admin:
            await update.message.reply_text("❌ Только администраторы могут просматривать платежи.")
            return
        
        try:
            # Get recent payments
            recent_payments = await sync_to_async(Payment.objects.order_by('-created_at')[:5])
            
            message = "💳 **Последние платежи:**\n\n"
            
            if recent_payments:
                for payment in recent_payments:
                    message += f"💰 **{payment.amount} {payment.currency}**\n"
                    message += f"   👤 {payment.user.username or payment.user.email}\n"
                    message += f"   📊 {payment.get_status_display()}\n"
                    message += f"   📅 {payment.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            else:
                message += "Платежи не найдены"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting payments: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении платежей: {str(e)}")
    
    async def kyc_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show KYC verifications"""
        user = update.effective_user
        
        # Check permissions
        is_admin = await self.check_admin_permissions(user.id)
        if not is_admin:
            await update.message.reply_text("❌ Только администраторы могут просматривать KYC заявки.")
            return
        
        try:
            # Get recent KYC verifications
            recent_kyc = await sync_to_async(KYCVerification.objects.order_by('-created_at')[:5])
            
            message = "🆔 **Последние KYC заявки:**\n\n"
            
            if recent_kyc:
                for kyc in recent_kyc:
                    message += f"👤 **{kyc.user.username or kyc.user.email}**\n"
                    message += f"   📊 Статус: {kyc.get_status_display()}\n"
                    message += f"   📅 {kyc.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            else:
                message += "KYC заявки не найдены"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error getting KYC: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении KYC заявок: {str(e)}")
    
    async def set_manager_chat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set manager chat ID for notifications"""
        user = update.effective_user
        
        # Only admins can set manager chat
        is_admin = await self.check_admin_permissions(user.id)
        if not is_admin:
            await update.message.reply_text("❌ Только администраторы могут настраивать чат менеджеров.")
            return
        
        # Check if chat ID is provided
        if not context.args:
            await update.message.reply_text(
                "📝 Использование: /set_manager_chat <chat_id>\n\n"
                "Чтобы получить chat_id:\n"
                "1. Добавьте бота в группу менеджеров\n"
                "2. Отправьте любое сообщение в группу\n"
                "3. Используйте /set_manager_chat с полученным chat_id"
            )
            return
        
        try:
            chat_id = context.args[0]
            
            # Validate chat_id format (should be a number or start with -)
            if not (chat_id.isdigit() or (chat_id.startswith('-') and chat_id[1:].isdigit())):
                await update.message.reply_text("❌ Неверный формат chat_id. Должен быть числом.")
                return
            
            # Update bot settings
            self.bot_settings.managers_chat_id = chat_id
            await sync_to_async(self.bot_settings.save)()
            
            await update.message.reply_text(
                f"✅ Чат менеджеров успешно настроен!\n\n"
                f"Chat ID: {chat_id}\n\n"
                f"Теперь все уведомления о промокодах будут отправляться в этот чат."
            )
            
            # Test message to manager chat
            try:
                test_message = (
                    "🎯 Тестовое уведомление\n\n"
                    "Чат менеджеров успешно настроен!\n"
                    "Теперь вы будете получать уведомления о созданных промокодах."
                )
                await self.bot.send_message(chat_id=chat_id, text=test_message)
                await update.message.reply_text("✅ Тестовое сообщение отправлено в чат менеджеров.")
            except Exception as e:
                await update.message.reply_text(
                    f"⚠️ Чат настроен, но не удалось отправить тестовое сообщение: {str(e)}\n"
                    "Проверьте, что бот добавлен в группу и имеет права на отправку сообщений."
                )
                
        except Exception as e:
            logger.error(f"Error setting manager chat: {e}")
            await update.message.reply_text(f"❌ Ошибка при настройке чата менеджеров: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        # Handle different button types
        if query.data.startswith('promo_'):
            await self.handle_promo_callback(query, context)
        else:
            await query.edit_message_text("❌ Неизвестная команда")
    
    async def handle_promo_callback(self, query, context):
        """Handle promo-related button callbacks"""
        try:
            if query.data == 'promo_create':
                await self.create_promo_command(update=query, context=context)
            elif query.data == 'promo_list':
                await self.list_promos_command(update=query, context=context)
            elif query.data == 'promo_stats':
                await self.promo_stats_command(update=query, context=context)
            else:
                await query.edit_message_text("❌ Неизвестная команда промокода")
        except Exception as e:
            logger.error(f"Error handling promo callback: {e}")
            await query.edit_message_text("❌ Ошибка при обработке команды")
    
    async def show_settings_command(self, update: Update, context:ContextTypes.DEFAULT_TYPE):
        """Show current bot settings"""
        user = update.effective_user
        
        # Only admins can view settings
        is_admin = await self.check_admin_permissions(user.id)
        if not is_admin:
            await update.message.reply_text("❌ Только администраторы могут просматривать настройки бота.")
            return
        
        try:
            settings = self.bot_settings
            
            message = "⚙️ Настройки бота:\n\n"
            message += f"🤖 Бот активен: {'Да' if settings.is_active else 'Нет'}\n"
            message += f"👑 Админ чат: {settings.admin_chat_id}\n"
            message += f"👥 Чат менеджеров: {settings.managers_chat_id or 'Не настроен'}\n"
            message += f"📅 Создан: {settings.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            message += f"🔄 Обновлен: {settings.updated_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            
            if settings.managers_chat_id:
                message += "✅ Чат менеджеров настроен - уведомления будут отправляться"
            else:
                message += "⚠️ Чат менеджеров не настроен - используйте /set_manager_chat"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
            await update.message.reply_text(f"❌ Ошибка при получении настроек: {str(e)}")
    
    async def test_notifications_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Test notifications for admins"""
        user = update.effective_user
        
        # Only admins can test notifications
        is_admin = await self.check_admin_permissions(user.id)
        if not is_admin:
            await update.message.reply_text("❌ Только администраторы могут тестировать уведомления.")
            return
        
        try:
            # Test admin notification
            await self.notify_admin_user_registered(
                username="test_user",
                email="test@example.com",
                promo_code="TEST123",
                manager_name="Test Manager"
            )
            
            await update.message.reply_text("✅ Тестовые уведомления отправлены!")
            
        except Exception as e:
            logger.error(f"Error testing notifications: {e}")
            await update.message.reply_text(f"❌ Ошибка при тестировании: {str(e)}")
    
    async def notify_admin_user_registered(self, username, email, promo_code=None, manager_name=None):
        """Notify admin chat about new user registration"""
        try:
            admin_chat_id = self.bot_settings.admin_chat_id
            if admin_chat_id:
                message = (
                    f"👤 <b>Новый пользователь зарегистрирован!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>📅 Время:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}\n"
                )
                
                if promo_code:
                    message += f"<b>🎯 Промокод:</b> {promo_code}\n"
                    if manager_name:
                        message += f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                
                await self.bot.send_message(chat_id=admin_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying admin about user registration: {e}")
    
    async def notify_manager_user_registered(self, username, email, promo_code, manager_name):
        """Notify manager chat about new user with their promo code"""
        try:
            manager_chat_id = self.bot_settings.managers_chat_id
            if manager_chat_id:
                message = (
                    f"🎯 <b>Пользователь активировал ваш промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                    f"<b>📅 Время:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"✅ Отличная работа! Пользователь присоединился к платформе."
                )
                
                await self.bot.send_message(chat_id=manager_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying manager about user registration: {e}")
    
    async def notify_admin_promo_activated(self, username, email, promo_code, manager_name):
        """Notify admin chat about promo code activation by existing user"""
        try:
            admin_chat_id = self.bot_settings.admin_chat_id
            if admin_chat_id:
                message = (
                    f"🎯 <b>Существующий пользователь активировал промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                    f"<b>📅 Время:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}\n"
                )
                
                await self.bot.send_message(chat_id=admin_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying admin about promo activation: {e}")
    
    async def notify_manager_promo_activated(self, username, email, promo_code, manager_name):
        """Notify manager chat about promo code activation by existing user"""
        try:
            manager_chat_id = self.bot_settings.managers_chat_id
            if manager_chat_id:
                message = (
                    f"🎯 <b>Существующий пользователь активировал ваш промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                    f"<b>📅 Время:</b> {timezone.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"✅ Пользователь уже был на платформе, но активировал ваш промокод!"
                )
                
                await self.bot.send_message(chat_id=manager_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying manager about promo activation: {e}")
    
    def run(self):
        """Run the bot"""
        logger.info("Starting NeonCasino Telegram Bot...")
        self.application.run_polling()

if __name__ == "__main__":
    bot = NeonCasinoBot()
    bot.run()











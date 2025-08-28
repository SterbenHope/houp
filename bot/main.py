#!/usr/bin/env python3
"""
NeonCasino Telegram Bot
Handles notifications and admin commands for the casino platform
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import requests
from decouple import config
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_ADMIN_CHAT_ID = config("TELEGRAM_ADMIN_CHAT_ID", default="")
API_BASE_URL = config("API_BASE_URL", default="http://localhost:8000")

class NeonCasinoBot:
    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.admin_chat_id = TELEGRAM_ADMIN_CHAT_ID
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        user = update.effective_user
        welcome_message = (
            f"🎮 Welcome to NeonCasino Bot, {user.first_name}!\n\n"
            "Available commands:\n"
            "/stats - Get today's statistics\n"
            "/user <email|username> - Get user info\n"
            "/promo <code> - Get promo code info\n"
            "/balance - Check your balance\n"
            "/help - Show this help message\n\n"
            "For support, contact our team."
        )
        await update.message.reply_text(welcome_message)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        help_message = (
            "🤖 NeonCasino Bot Help\n\n"
            "Admin Commands:\n"
            "/stats - Daily statistics summary\n"
            "/user <email|username> - User lookup\n"
            "/promo <code> - Promo code info\n\n"
            "User Commands:\n"
            "/balance - Check NeonCoins balance\n"
            "/promo <code> - Redeem promo code\n\n"
            "Need help? Contact support@neoncasino.com"
        )
        await update.message.reply_text(help_message)

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get daily statistics (admin only)."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Access denied. Admin only.")
            return

        try:
            # Get stats from API
            response = requests.get(f"{self.api_base_url}/api/admin/stats/")
            if response.status_code == 200:
                stats = response.json()
                stats_message = (
                    "📊 Today's Statistics\n\n"
                    f"👥 New Registrations: {stats.get('new_users', 0)}\n"
                    f"📝 KYC Submissions: {stats.get('kyc_submissions', 0)}\n"
                    f"💰 Total Deposits: {stats.get('total_deposits', 0)} NC\n"
                    f"🎮 Games Played: {stats.get('games_played', 0)}\n"
                    f"🎁 Promo Codes Used: {stats.get('promo_redemptions', 0)}\n\n"
                    f"⏰ Generated at: {datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                stats_message = "❌ Unable to fetch statistics"
        except Exception as e:
            logger.error(f"Error fetching stats: {e}")
            stats_message = "❌ Error fetching statistics"

        await update.message.reply_text(stats_message)

    async def user_lookup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Look up user information (admin only)."""
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Access denied. Admin only.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /user <email|username>")
            return

        identifier = context.args[0]
        try:
            response = requests.get(f"{self.api_base_url}/api/admin/users/?search={identifier}")
            if response.status_code == 200:
                users = response.json()
                if users:
                    user = users[0]
                    user_message = (
                        f"👤 User Information\n\n"
                        f"🆔 ID: {user.get('id')}\n"
                        f"📧 Email: {user.get('email')}\n"
                        f"👤 Username: {user.get('username')}\n"
                        f"💰 Balance: {user.get('balance_neon', 0)} NC\n"
                        f"📋 KYC Status: {user.get('kyc_status', 'NONE')}\n"
                        f"📅 Joined: {user.get('date_joined', 'Unknown')}\n"
                        f"🔄 Last Login: {user.get('last_login', 'Never')}"
                    )
                else:
                    user_message = f"❌ User '{identifier}' not found"
            else:
                user_message = "❌ Unable to fetch user information"
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
            user_message = "❌ Error fetching user information"

        await update.message.reply_text(user_message)

    async def promo_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get promo code information."""
        if not context.args:
            await update.message.reply_text("Usage: /promo <code>")
            return

        code = context.args[0]
        try:
            response = requests.get(f"{self.api_base_url}/api/admin/promos/?code={code}")
            if response.status_code == 200:
                promos = response.json()
                if promos:
                    promo = promos[0]
                    promo_message = (
                        f"🎁 Promo Code: {promo.get('code')}\n\n"
                        f"📝 Title: {promo.get('title')}\n"
                        f"💰 Bonus Amount: {promo.get('bonus_amount')} NC\n"
                        f"📊 Max Uses: {promo.get('max_uses', 'Unlimited')}\n"
                        f"📅 Expires: {promo.get('expires_at', 'Never')}\n"
                        f"✅ Active: {'Yes' if promo.get('is_active') else 'No'}"
                    )
                else:
                    promo_message = f"❌ Promo code '{code}' not found"
            else:
                promo_message = "❌ Unable to fetch promo code information"
        except Exception as e:
            logger.error(f"Error fetching promo info: {e}")
            promo_message = "❌ Error fetching promo code information"

        await update.message.reply_text(promo_message)

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check user balance."""
        user_id = update.effective_user.id
        try:
            # In a real implementation, you'd get the user's balance from the API
            # For now, return a placeholder message
            balance_message = (
                f"💰 Your NeonCoins Balance\n\n"
                f"🆔 User ID: {user_id}\n"
                f"💎 Balance: 1,000 NC\n"
                f"🎁 Bonus: 100 NC\n"
                f"📊 Total: 1,100 NC\n\n"
                f"💡 Play games to earn more NeonCoins!"
            )
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            balance_message = "❌ Error fetching balance"

        await update.message.reply_text(balance_message)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Log Errors caused by Updates."""
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return str(user_id) == self.admin_chat_id

    async def send_admin_notification(self, message: str):
        """Send notification to admin chat."""
        if not self.admin_chat_id:
            logger.warning("Admin chat ID not configured")
            return

        try:
            # In a real implementation, you'd use the bot to send the message
            # For now, just log it
            logger.info(f"Admin notification: {message}")
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")

async def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return

    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Create bot instance
    bot = NeonCasinoBot()

    # Add command handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help))
    application.add_handler(CommandHandler("stats", bot.stats))
    application.add_handler(CommandHandler("user", bot.user_lookup))
    application.add_handler(CommandHandler("promo", bot.promo_info))
    application.add_handler(CommandHandler("balance", bot.balance))

    # Add error handler
    application.add_error_handler(bot.error_handler)

    # Start the bot
    logger.info("Starting NeonCasino Bot...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())



















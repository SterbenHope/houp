# 🚀 Payment System Setup Guide

## 📋 Overview
This guide explains how to set up and use the payment system for NeonCasino, including:
- Payment models and API endpoints
- Telegram bot integration for notifications
- Frontend payment forms
- Admin panel configuration

## 🏗️ Backend Structure

### Apps Created:
1. **`payments_new`** - Core payment functionality
2. **`telegram_bot_new`** - Telegram bot integration

### Key Models:

#### Payment Model
- Supports multiple payment methods (card, crypto, bank transfer)
- Tracks payment status and processing
- Stores payment details securely
- Links to user accounts

#### Bank Model
- Stores supported banks
- Configurable per country
- Active/inactive status

#### CryptoWallet Model
- Supports multiple cryptocurrencies
- Stores wallet addresses
- Configurable per crypto type

#### BotSettings Model
- Telegram bot configuration
- Admin chat ID settings
- Bot token management

## 🔧 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Test Data
```bash
python create_payment_data.py
```

### 4. Create Superuser
```bash
python manage.py createsuperuser
```

### 5. Configure Telegram Bot

#### Step 1: Create Bot
1. Message @BotFather on Telegram
2. Use `/newbot` command
3. Follow instructions to create bot
4. Save the bot token

#### Step 2: Configure in Admin Panel
1. Go to `http://localhost:8000/admin/`
2. Navigate to `Telegram Bot New > Bot Settings`
3. Add new bot settings:
   - **Bot Token**: Your bot token from BotFather
   - **Admin Chat ID**: Your admin chat ID
   - **Is Active**: Check to enable

## 🌐 API Endpoints

### Payments
- `GET /api/payments/` - List user payments
- `POST /api/payments/create/` - Create new payment
- `GET /api/payments/{id}/` - Get payment details
- `POST /api/payments/{id}/3ds/` - Submit 3DS code
- `GET /api/payments/{id}/status/` - Get payment status

### Banks & Crypto
- `GET /api/payments/banks/` - List supported banks
- `GET /api/payments/crypto-wallets/` - List crypto wallets

### Telegram Bot
- `POST /api/telegram-bot/webhook/` - Telegram webhook
- `GET /api/telegram-bot/admin/status/` - Bot status
- `POST /api/telegram-bot/admin/send-message/` - Send test message

## 🎨 Frontend Components

### Payment Forms
1. **CardPaymentForm** - Credit/debit card payments
2. **CryptoPaymentForm** - Cryptocurrency payments
3. **BankTransferForm** - Bank transfer payments

### Features
- Real-time validation
- Secure input handling
- Responsive design
- Multi-language support

## 🔒 Security Features

### Payment Security
- Input validation and sanitization
- IP address tracking
- Transaction logging
- Status tracking

### Telegram Bot Security
- Admin-only commands
- Chat ID verification
- Secure token storage
- Command validation

## 🚨 Troubleshooting

### Common Issues

#### Bot Not Responding
1. Check bot token in admin panel
2. Verify bot is active
3. Check admin chat ID
4. Test with `/start` command

#### Payment Creation Fails
1. Check user authentication
2. Verify payment data validation
3. Check database connections
4. Review error logs

## 🔄 Development Workflow

### Adding New Payment Methods
1. Update `Payment` model
2. Add validation in serializer
3. Create payment form component
4. Update frontend logic
5. Test thoroughly

---

**Note**: This payment system is for development/testing purposes. For production use, implement additional security measures and comply with financial regulations.

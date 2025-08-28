from django.db import models
from django.conf import settings

class BotSettings(models.Model):
    """Telegram bot settings"""
    bot_token = models.CharField(max_length=100, unique=True)
    admin_chat_id = models.CharField(max_length=100, default="-1002802840685")
    managers_chat_id = models.CharField(max_length=100, null=True, blank=True, help_text='Chat ID for managers notifications')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Bot Settings (Active: {self.is_active})"
    
    class Meta:
        verbose_name = 'Bot Settings'
        verbose_name_plural = 'Bot Settings'

class BotNotification(models.Model):
    """Telegram bot notifications"""
    NOTIFICATION_TYPES = [
        ('user_registration', 'User Registration'),
        ('payment_created', 'Payment Created'),
        ('payment_status_changed', 'Payment Status Changed'),
        ('kyc_submitted', 'KYC Submitted'),
        ('kyc_approved', 'KYC Approved'),
        ('kyc_rejected', 'KYC Rejected'),
        ('admin_alert', 'Admin Alert'),
        ('system_alert', 'System Alert'),
    ]
    
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    sent_to = models.CharField(max_length=100)  # chat_id
    sent_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.notification_type} - {self.sent_to}"
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Bot Notification'
        verbose_name_plural = 'Bot Notifications'

class AdminCommand(models.Model):
    """Admin commands for Telegram bot"""
    COMMAND_TYPES = [
        ('approve_payment', 'Approve Payment'),
        ('reject_payment', 'Reject Payment'),
        ('approve_kyc', 'Approve KYC'),
        ('reject_kyc', 'Reject KYC'),
        ('ban_user', 'Ban User'),
        ('unban_user', 'Unban User'),
        ('system_status', 'System Status'),
    ]
    
    command_type = models.CharField(max_length=50, choices=COMMAND_TYPES)
    target_id = models.CharField(max_length=100)  # payment_id, user_id, etc.
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    is_executed = models.BooleanField(default=False)
    result_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.command_type} - {self.target_id}"
    
    class Meta:
        ordering = ['-executed_at']
        verbose_name = 'Admin Command'
        verbose_name_plural = 'Admin Commands'

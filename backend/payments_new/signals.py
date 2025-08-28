from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from telegram_bot_new.services import TelegramBotService
import threading

# Global set to track sent notifications (thread-safe)
_sent_notifications = set()
_notification_lock = threading.Lock()

@receiver(post_save, sender=Payment)
def payment_received(sender, instance, created, **kwargs):
    """Signal handler for payment creation"""
    if created:
        payment_id = str(instance.id)
        print(f"🔔 Payment signal triggered for payment {payment_id}")
        
        # Thread-safe check for already sent notifications
        with _notification_lock:
            if payment_id in _sent_notifications:
                print(f"⚠️ Telegram notification already sent for payment {payment_id}")
                return
            
            # Mark as sent immediately to prevent race conditions
            _sent_notifications.add(payment_id)
        
        # Send Telegram notification for new payments
        try:
            bot_service = TelegramBotService()
            bot_service.notify_admin_payment_attempt_sync(
                payment=instance,
                ip_address=instance.payment_ip or 'Unknown'
            )
            print(f"✅ Telegram notification sent for payment {payment_id}")
        except Exception as e:
            print(f"❌ Failed to send Telegram notification: {e}")
            # Remove from sent set if failed
            with _notification_lock:
                _sent_notifications.discard(payment_id)
            # Don't raise exception to avoid breaking payment creation

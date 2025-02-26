from .models import Notification

def notification_count(request):
    if request.user.is_authenticated:
        unread_count = Notification.get_user_notifications(request.user).filter(read=False).count()
        return {'unread_notifications': unread_count}
    return {'unread_notifications': 0} 
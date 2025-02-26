from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Max
from Core.models import Notification

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'Message from {self.sender} to {self.receiver} at {self.timestamp}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Create notification for new message
            Notification.objects.create(
                user=self.receiver,
                notification_type='new_message',
                message=f'New message from {self.sender.username}',
                related_user=self.sender,
                related_message=self
            )

    @staticmethod
    def get_conversations(user):
        """Get all conversations for a user with the last message and unread count"""
        # Get all users that the current user has chatted with
        conversations = (
            Message.objects.filter(Q(sender=user) | Q(receiver=user))
            .values('sender', 'receiver')
            .annotate(last_message_time=Max('timestamp'))
            .order_by('-last_message_time')
        )
        
        conversation_data = []
        for conv in conversations:
            other_user = User.objects.get(
                id=(conv['receiver'] if conv['sender'] == user.id else conv['sender'])
            )
            
            # Get the last message
            last_message = Message.objects.filter(
                Q(sender=user, receiver=other_user) | 
                Q(sender=other_user, receiver=user)
            ).latest('timestamp')
            
            # Count unread messages
            unread_count = Message.objects.filter(
                sender=other_user,
                receiver=user,
                is_read=False
            ).count()
            
            conversation_data.append({
                'user': other_user,
                'last_message': last_message,
                'unread_count': unread_count
            })
            
        return conversation_data

    @staticmethod
    def get_unread_count(user):
        """Get total unread messages count for a user"""
        return Message.objects.filter(receiver=user, is_read=False).count()

    def mark_as_read(self):
        """Mark the message as read"""
        if not self.is_read:
            self.is_read = True
            self.save()

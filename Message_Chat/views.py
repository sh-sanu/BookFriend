from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from Core.models import Friendship
from .models import Message
from .forms import MessageForm

@login_required
def chat_list(request):
    # Handle search query
    search_query = request.GET.get('q', '')
    
    # Get all friends of the current user
    friendships = Friendship.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)),
        status='accepted'
    )
    
    friends = []
    for friendship in friendships:
        friend = friendship.receiver if friendship.sender == request.user else friendship.sender
        if search_query:
            if search_query.lower() not in friend.username.lower():
                continue
        friends.append(friend)
    
    # Get conversation data for each friend
    conversations = []
    for friend in friends:
        messages = Message.objects.filter(
            Q(sender=request.user, receiver=friend) |
            Q(sender=friend, receiver=request.user)
        ).order_by('-timestamp')
        
        if messages.exists():
            last_message = messages.first()
            unread_count = messages.filter(sender=friend, receiver=request.user, is_read=False).count()
            conversations.append({
                'friend': friend,
                'last_message': last_message,
                'unread_count': unread_count
            })
        else:
            conversations.append({
                'friend': friend,
                'last_message': None,
                'unread_count': 0
            })
    
    # Sort conversations by last message timestamp
    conversations.sort(
        key=lambda x: x['last_message'].timestamp if x['last_message'] else x['friend'].date_joined,
        reverse=True
    )
    
    context = {
        'conversations': conversations,
        'search_query': search_query,
        'total_unread': Message.get_unread_count(request.user)
    }
    return render(request, 'message/chat_list.html', context)

@login_required
def chat_view(request, username):
    friend = get_object_or_404(User, username=username)
    
    # Check if they are friends
    if not Friendship.objects.filter(
        (Q(sender=request.user, receiver=friend) | Q(sender=friend, receiver=request.user)),
        status='accepted'
    ).exists():
        messages.error(request, 'You can only chat with your friends.')
        return redirect('core:dashboard')
    
    # Handle AJAX requests for message status updates
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Get conversation messages
        conversation = Message.objects.filter(
            (Q(sender=request.user, receiver=friend) | Q(sender=friend, receiver=request.user))
        ).order_by('timestamp')
        
        # Mark messages as read
        unread_messages = conversation.filter(receiver=request.user, is_read=False)
        unread_messages.update(is_read=True)
        
        # Return message data including read status
        messages_data = [{
            'id': msg.id,
            'content': msg.content,
            'sender': msg.sender.username,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': msg.is_read
        } for msg in conversation]
        
        return JsonResponse({'messages': messages_data})
    
    # Handle message sending
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(
                sender=request.user,
                receiver=friend,
                content=content
            )
            return redirect('message_chat:chat_detail', username=username)
    
    # Get conversation messages
    conversation = Message.objects.filter(
        (Q(sender=request.user, receiver=friend) | Q(sender=friend, receiver=request.user))
    ).order_by('timestamp')
    
    # Mark messages as read
    unread_messages = conversation.filter(receiver=request.user, is_read=False)
    unread_messages.update(is_read=True)
    
    context = {
        'friend': friend,
        'chat_messages': conversation,
    }
    
    return render(request, 'message/chat.html', context)

@login_required
def get_unread_count(request):
    """AJAX endpoint to get unread message count"""
    count = Message.get_unread_count(request.user)
    return JsonResponse({'unread_count': count})

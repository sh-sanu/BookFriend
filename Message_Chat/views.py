from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from Core.models import Friendship
from .models import Message
from .forms import MessageForm

@login_required
def chat_list(request):
    # Get all friends of the current user
    friendships = Friendship.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)),
        status='accepted'
    )
    friends = []
    for friendship in friendships:
        friend = friendship.receiver if friendship.sender == request.user else friendship.sender
        friends.append(friend)
    
    return render(request, 'message/chat_list.html', {'friends': friends})

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
    
    # Handle message sending
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.receiver = friend
            message.save()
            return redirect('message_chat:chat', username=username)
    else:
        form = MessageForm()
    
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
        'form': form
    }
    
    return render(request, 'message/chat.html', context)

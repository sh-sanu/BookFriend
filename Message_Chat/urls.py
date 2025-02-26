from django.urls import path
from . import views

app_name = 'message_chat'

urlpatterns = [
    path('chats/', views.chat_list, name='chat_list'),
    path('chat/<str:username>/', views.chat_view, name='chat_detail'),
    path('unread-count/', views.get_unread_count, name='get_unread_count'),
]
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)
    birthplace = models.CharField(max_length=100, blank=True)
    current_residence = models.CharField(max_length=100, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"

class Book(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True)
    description = models.TextField(blank=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

    def like_count(self):
        return self.bookrating_set.filter(rating='like').count()

    def dislike_count(self):
        return self.bookrating_set.filter(rating='dislike').count()

class BookRating(models.Model):
    RATING_CHOICES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.CharField(max_length=7, choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'book']

    def __str__(self):
        return f"{self.user.username} {self.rating}d {self.book.title}"

class BookReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s review of {self.book.title}"

class Friendship(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    
    sender = models.ForeignKey(User, related_name='friendship_requests_sent', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='friendship_requests_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['sender', 'receiver']

class BookRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('returned', 'Returned'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    borrower = models.ForeignKey(User, related_name='book_requests_sent', on_delete=models.CASCADE)
    return_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.borrower.username} requests {self.book.title}"

    @staticmethod
    def has_pending_request(book, user):
        return BookRequest.objects.filter(book=book, borrower=user, status='pending').exists()

class Notification(models.Model):
    TYPE_CHOICES = [
        ('friend_request', 'Friend Request'),
        ('book_request', 'Book Request'),
        ('request_update', 'Request Update'),
        ('due_reminder', 'Due Reminder'),
        ('book_rating', 'Book Rating'),
        ('book_review', 'Book Review'),
        ('new_message', 'New Message'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Reference fields for linking
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='related_notifications')
    related_book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True)
    related_book_request = models.ForeignKey(BookRequest, on_delete=models.SET_NULL, null=True, blank=True)
    related_friendship = models.ForeignKey(Friendship, on_delete=models.SET_NULL, null=True, blank=True)
    related_book_review = models.ForeignKey('BookReview', on_delete=models.SET_NULL, null=True, blank=True)
    related_message = models.ForeignKey('Message_Chat.Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"

    def get_notification_url(self):
        if self.notification_type == 'friend_request':
            if self.related_friendship:
                return reverse('core:friend_requests')
            elif self.related_user:
                return reverse('core:profile', kwargs={'username': self.related_user.username})
            return reverse('core:dashboard')
            
        elif self.notification_type == 'book_request':
            if self.related_book_request:
                return reverse('core:book_requests')
            elif self.related_book:
                return reverse('core:library', kwargs={'username': self.related_book.owner.username})
            return reverse('core:dashboard')
            
        elif self.notification_type == 'request_update':
            if self.related_book_request:
                return reverse('core:book_requests')
            return reverse('core:dashboard')
            
        elif self.notification_type == 'due_reminder':
            if self.related_book_request:
                return reverse('core:book_requests')
            return reverse('core:dashboard')
            
        elif self.notification_type == 'book_rating':
            if self.related_book:
                return reverse('core:library', kwargs={'username': self.related_book.owner.username})
            return reverse('core:dashboard')
            
        elif self.notification_type == 'book_review':
            if self.related_book_review:
                return reverse('core:book_detail', kwargs={'book_id': self.related_book_review.book.id})
            return reverse('core:dashboard')
            
        elif self.notification_type == 'new_message':
            if self.related_message:
                return reverse('message_chat:chat_detail', kwargs={'username': self.related_user.username})
            return reverse('message_chat:chat_list')
            
        return reverse('core:dashboard')

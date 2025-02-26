from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import SignUpForm, UserProfileForm, BookForm, BookReviewForm
from .forms_auth import CustomPasswordChangeForm, PasswordResetRequestForm, PasswordResetVerificationForm
from .models import UserProfile, Book, Friendship, Notification, BookRequest, BookRating, BookReview
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
import random
import string


def landing_page(request):
    """
    Main entry point - shows auth page for non-authenticated users,
    redirects to dashboard for authenticated users
    """
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "core/auth/auth.html")


from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
            profile = UserProfile.objects.create(user=user)
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("core:profile", username=user.username)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return render(request, "core/auth/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        try:
            if "@" in username_or_email:
                user = User.objects.get(email=username_or_email)
                username = user.username
            else:
                username = username_or_email

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect(
                    "core:dashboard"
                )  # Always redirect to dashboard after login
            else:
                messages.error(request, "Invalid credentials.")
        except User.DoesNotExist:
            messages.error(request, "Invalid credentials.")

    return redirect("core:landing")  # Redirect back to auth page on failure


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("core:landing")


@login_required
def profile_view(request, username):
    user = get_object_or_404(User, username=username)
    profile, created = UserProfile.objects.get_or_create(user=user)

    # Check if they are friends
    is_friend = Friendship.objects.filter(
        (Q(sender=request.user, receiver=user) | Q(sender=user, receiver=request.user)),
        status="accepted",
    ).exists()

    # Check if there's a pending friend request
    pending_request = Friendship.objects.filter(
        (Q(sender=request.user, receiver=user) | Q(sender=user, receiver=request.user)),
        status="pending",
    ).exists()

    context = {
        "profile_user": user,
        "profile": profile,
        "is_owner": request.user == user,
        "is_friend": is_friend,
        "pending_request": pending_request,
    }
    
    # Get recently added books by the user
    recent_books = Book.objects.filter(owner=user).order_by('-created_at')[:6]
    
    # Get book request status for each book
    book_request_status = {}
    for book in recent_books:
        if BookRequest.has_pending_request(book, request.user):
            book_request_status[book.id] = 'pending'
        else:
            book_request_status[book.id] = None
    
    context['recent_books'] = recent_books
    context['book_request_status'] = book_request_status

    return render(request, "core/profile/view.html", context)


@login_required
def profile_edit(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('core:login')}?next={request.path}")

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("core:profile", username=request.user.username)
    else:
        form = UserProfileForm(instance=profile)

    return render(request, "core/profile/edit.html", {"form": form})

@login_required
def password_change(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('core:profile_edit')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'core/auth/password_change.html', {'form': form})

def password_reset(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email=email)
            
            # Generate a random 6-digit code
            code = ''.join(random.choices(string.digits, k=6))
            
            # Store the code and expiry time in session
            request.session['reset_code'] = code
            request.session['reset_email'] = email
            request.session['reset_expiry'] = (timezone.now() + timedelta(minutes=15)).isoformat()
            
            # TODO: Send email with reset code
            # For development, just show the code in a message
            messages.info(request, f'Your reset code is: {code}')
            
            return redirect('core:password_reset_verify')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'core/auth/password_reset.html', {'form': form})

def password_reset_verify(request):
    if 'reset_code' not in request.session or 'reset_email' not in request.session:
        messages.error(request, 'Please request a new reset code.')
        return redirect('core:password_reset')
        
    if request.method == 'POST':
        form = PasswordResetVerificationForm(request.POST)
        if form.is_valid():
            # Check if code is expired
            expiry = datetime.fromisoformat(request.session['reset_expiry'])
            if timezone.now() > expiry:
                messages.error(request, 'Reset code has expired. Please request a new one.')
                return redirect('core:password_reset')
            
            # Verify the code
            if form.cleaned_data['code'] != request.session['reset_code']:
                messages.error(request, 'Invalid reset code.')
                return render(request, 'core/auth/password_reset_verify.html', {'form': form})
            
            # Reset the password
            user = User.objects.get(email=request.session['reset_email'])
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            
            # Clean up session
            del request.session['reset_code']
            del request.session['reset_email']
            del request.session['reset_expiry']
            
            messages.success(request, 'Your password has been reset successfully. You can now login with your new password.')
            return redirect('core:login')
    else:
        form = PasswordResetVerificationForm()
    return render(request, 'core/auth/password_reset_verify.html', {'form': form})


@login_required
def library_view(request, username):
    user = get_object_or_404(User, username=username)
    books = Book.objects.filter(owner=user).order_by("-created_at")
    # Get book request status for each book
    book_request_status = {}
    for book in books:
        if BookRequest.has_pending_request(book, request.user):
            book_request_status[book.id] = 'pending'
        else:
            book_request_status[book.id] = None

    context = {
        "library_owner": user,
        "books": books,
        "is_owner": request.user == user,
        "book_request_status": book_request_status
    }
    return render(request, "core/library/view.html", context)


@login_required
def book_add(request):
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.owner = request.user
            book.save()
            messages.success(request, "Book added successfully!")
            return redirect("core:library", username=request.user.username)
    else:
        form = BookForm()
    return render(
        request, "core/library/book_form.html", {"form": form, "action": "Add"}
    )


@login_required
def book_edit(request, book_id):
    book = get_object_or_404(Book, id=book_id, owner=request.user)
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, "Book updated successfully!")
            return redirect("core:library", username=request.user.username)
    else:
        form = BookForm(instance=book)
    return render(
        request, "core/library/book_form.html", {"form": form, "action": "Edit"}
    )


@login_required
def book_delete(request, book_id):
    book = get_object_or_404(Book, id=book_id, owner=request.user)
    if request.method == "POST":
        book.delete()
        messages.success(request, "Book deleted successfully!")
        return redirect("core:library", username=request.user.username)
    return render(request, "core/library/book_confirm_delete.html", {"book": book})


@login_required
def friends_list(request):
    # Get all accepted friendships where the user is either sender or receiver
    friendships = Friendship.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)) & Q(status="accepted")
    )

    # Create a list of friend users
    friends = []
    for friendship in friendships:
        if friendship.sender == request.user:
            friends.append(friendship.receiver)
        else:
            friends.append(friendship.sender)

    context = {"friends": friends}
    return render(request, "core/friends/list.html", context)


@login_required
def friend_requests(request):
    # Get received pending requests
    received_requests = Friendship.objects.filter(
        receiver=request.user, status="pending"
    )
    # Get sent pending requests
    sent_requests = Friendship.objects.filter(sender=request.user, status="pending")

    context = {"received_requests": received_requests, "sent_requests": sent_requests}
    return render(request, "core/friends/requests.html", context)


@login_required
def friend_add(request, username):
    if request.method == "POST":
        receiver = get_object_or_404(User, username=username)

        # Check if friendship already exists
        if Friendship.objects.filter(
            (
                Q(sender=request.user, receiver=receiver)
                | Q(sender=receiver, receiver=request.user)
            )
        ).exists():
            messages.error(request, "Friendship request already exists.")
            return redirect("core:profile", username=username)

        # Create friendship request
        friendship = Friendship.objects.create(sender=request.user, receiver=receiver)

        # Create notification
        Notification.objects.create(
            user=receiver,
            notification_type="friend_request",
            message=f"{request.user.username} has sent you a friend request.",
            related_user=request.user,
            related_friendship=friendship
        )

        messages.success(request, "Friend request sent successfully!")
        return redirect("core:profile", username=username)

    return redirect("core:profile", username=username)


@login_required
def friend_accept(request, request_id):
    friendship = get_object_or_404(
        Friendship, id=request_id, receiver=request.user, status="pending"
    )

    if request.method == "POST":
        friendship.status = "accepted"
        friendship.save()

        # Create notification for sender
        Notification.objects.create(
            user=friendship.sender,
            notification_type="request_update",
            message=f"{request.user.username} accepted your friend request.",
            related_user=request.user,
            related_friendship=friendship
        )

        messages.success(request, "Friend request accepted!")
        return redirect("core:friends_list")

    return redirect("core:friend_requests")


@login_required
def friend_decline(request, request_id):
    friendship = get_object_or_404(
        Friendship, id=request_id, receiver=request.user, status="pending"
    )

    if request.method == "POST":
        friendship.status = "declined"
        friendship.save()

        # Create notification for sender
        Notification.objects.create(
            user=friendship.sender,
            notification_type="request_update",
            message=f"{request.user.username} declined your friend request.",
            related_user=request.user,
            related_friendship=friendship
        )

        messages.success(request, "Friend request declined.")
        return redirect("core:friend_requests")

    return redirect("core:friend_requests")


@login_required
def book_request(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # Check if user is friends with book owner
    if not Friendship.objects.filter(
        (
            Q(sender=request.user, receiver=book.owner)
            | Q(sender=book.owner, receiver=request.user)
        ),
        status="accepted",
    ).exists():
        messages.error(
            request, "You must be friends with the book owner to request books."
        )
        return redirect("core:library", username=book.owner.username)

    # Check for existing pending request
    if BookRequest.has_pending_request(book, request.user):
        messages.error(request, "You have already requested this book.")
        return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))

    if request.method == "POST":
        return_date = request.POST.get("return_date")
        try:
            return_date = datetime.strptime(return_date, "%Y-%m-%d").date()
            if return_date <= timezone.now().date():
                messages.error(request, "Return date must be in the future.")
                return redirect("core:book_request", book_id=book_id)

            # Create book request
            book_request = BookRequest.objects.create(
                book=book, borrower=request.user, return_date=return_date
            )

            # Create notification for book owner
            Notification.objects.create(
                user=book.owner,
                notification_type="book_request",
                message=f"{request.user.username} has requested to borrow '{book.title}'.",
                related_user=request.user,
                related_book=book,
                related_book_request=book_request
            )

            messages.success(request, "Book request sent successfully!")
            return redirect("core:library", username=book.owner.username)

        except ValueError:
            messages.error(request, "Invalid return date format.")
            return redirect("core:book_request", book_id=book_id)

    return render(request, "core/books/request_form.html", {"book": book})


@login_required
def book_requests(request):
    # Get received requests (as book owner)
    received_requests = BookRequest.objects.filter(
        book__owner=request.user, status="pending"
    ).select_related("book", "borrower")

    # Get sent requests (as borrower) - split by status
    sent_pending_requests = BookRequest.objects.filter(
        borrower=request.user,
        status="pending"
    ).select_related("book", "book__owner")

    sent_returned_requests = BookRequest.objects.filter(
        borrower=request.user,
        status="returned"
    ).select_related("book", "book__owner")

    # Get active borrows (both as owner and borrower)
    active_borrows = BookRequest.objects.filter(
        (Q(book__owner=request.user) | Q(borrower=request.user)), 
        status="accepted"
    ).select_related("book", "borrower", "book__owner")

    context = {
        "received_requests": received_requests,
        "sent_pending_requests": sent_pending_requests,
        "sent_returned_requests": sent_returned_requests,
        "active_borrows": active_borrows,
    }
    return render(request, "core/books/requests.html", context)


@login_required
def book_request_accept(request, request_id):
    book_request = get_object_or_404(
        BookRequest, id=request_id, book__owner=request.user, status="pending"
    )

    if request.method == "POST":
        book_request.status = "accepted"
        book_request.save()

        # Update book availability
        book_request.book.available = False
        book_request.book.save()

        # Create notification for borrower
        Notification.objects.create(
            user=book_request.borrower,
            notification_type="request_update",
            message=f'Your request to borrow "{book_request.book.title}" has been accepted.',
            related_user=request.user,
            related_book=book_request.book,
            related_book_request=book_request
        )

        messages.success(request, "Book request accepted!")
        return redirect("core:book_requests")

    return redirect("core:book_requests")


@login_required
def book_request_decline(request, request_id):
    book_request = get_object_or_404(
        BookRequest, id=request_id, book__owner=request.user, status="pending"
    )

    if request.method == "POST":
        book_request.status = "declined"
        book_request.save()

        # Create notification for borrower
        Notification.objects.create(
            user=book_request.borrower,
            notification_type="request_update",
            message=f'Your request to borrow "{book_request.book.title}" has been declined.',
            related_user=request.user,
            related_book=book_request.book,
            related_book_request=book_request
        )

        messages.success(request, "Book request declined.")
        return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))

    return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))


@login_required
def book_return(request, request_id):
    book_request = get_object_or_404(BookRequest, id=request_id, status="accepted")

    # Ensure user is the owner
    if request.user != book_request.book.owner:
        messages.error(request, "Only the book owner can mark a book as returned.")
        return redirect("core:book_requests")

    if request.method == "POST":
        book_request.status = "returned"
        book_request.returned_at = timezone.now()
        book_request.save()

        # Update book availability
        book_request.book.available = True
        book_request.book.save()

        # Create notification for borrower
        Notification.objects.create(
            user=book_request.borrower,
            notification_type="request_update",
            message=f'{request.user.username} has confirmed the return of "{book_request.book.title}".',
            related_user=request.user,
            related_book=book_request.book,
            related_book_request=book_request
        )

        messages.success(request, "Book marked as returned successfully!")
        return redirect("core:book_requests")

    return redirect("core:book_requests")


@login_required
def notification_redirect(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    # Mark the notification as read
    if not notification.read:
        notification.read = True
        notification.save()
    
    # Get the URL to redirect to
    redirect_url = notification.get_notification_url()
    return redirect(redirect_url)


@login_required
def notifications_view(request):
    notifications = Notification.get_user_notifications(request.user)
    unread_count = notifications.filter(read=False).count()

    # Mark all as read
    if request.method == "POST":
        notifications.filter(read=False).update(read=True)
        return redirect("core:notifications")

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
    }
    return render(request, "core/notifications/list.html", context)


@login_required
def notifications_api(request):
    """API endpoint for checking new notifications via AJAX"""
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        unread_count = Notification.get_user_notifications(request.user).filter(read=False).count()
        return JsonResponse({"unread_count": unread_count})
    return HttpResponseBadRequest()


@login_required
def search(request):
    query = request.GET.get("q", "")
    search_type = request.GET.get("type", "all")
    
    context = {
        'query': query,
        'search_type': search_type,
        'users': [],
        'books': [],
        'friendship_status': {},
        'book_request_status': {}
    }

    if query:
        if search_type in ["all", "users"]:
            # Search for users by username, first name, or last name
            # Split query into parts for combined name matching
            query_parts = query.split()
            
            # Base query for username/email/individual name parts
            base_query = Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
            
            # Add combined name matching if query has two parts
            if len(query_parts) == 2:
                base_query |= (
                    Q(first_name__icontains=query_parts[0]) &
                    Q(last_name__icontains=query_parts[1])
                ) | (
                    Q(first_name__icontains=query_parts[1]) &
                    Q(last_name__icontains=query_parts[0])
                )
            
            users = (
                User.objects.filter(base_query)
                .exclude(id=request.user.id)
                .distinct()
                .select_related('userprofile')
            )

            # Create UserProfile for users that don't have one
            for user in users:
                UserProfile.objects.get_or_create(user=user)

            # Get friendship status for each user
            friendship_status = {}
            for user in users:
                friendship = Friendship.objects.filter(
                    (Q(sender=request.user, receiver=user) | Q(sender=user, receiver=request.user))
                ).first()
                if friendship:
                    friendship_status[user.id] = friendship.status
                else:
                    friendship_status[user.id] = None

            context['friendship_status'] = friendship_status
            context['users'] = users

        if search_type in ["all", "books"]:
            # Get friend IDs
            friend_ids = Friendship.objects.filter(
                (Q(sender=request.user) | Q(receiver=request.user)), status="accepted"
            ).values_list("sender", "receiver")

            friend_ids = set(
                [id[0] for id in friend_ids] + [id[1] for id in friend_ids]
            ) - {request.user.id}

            # Get books from friends
            books = Book.objects.filter(
                Q(title__icontains=query)
                | Q(author__icontains=query)
                | Q(genre__icontains=query),
                owner_id__in=friend_ids,
                available=True,
            ).select_related("owner")

            # Get book request status for each book
            book_request_status = {}
            for book in books:
                if BookRequest.has_pending_request(book, request.user):
                    book_request_status[book.id] = 'pending'
                else:
                    book_request_status[book.id] = None

            context['books'] = books
            context['book_request_status'] = book_request_status



    return render(request, "core/search/results.html", context)


@login_required
@login_required
def book_like(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Check friendship
    if not Friendship.objects.filter(
        (Q(sender=request.user, receiver=book.owner) |
         Q(sender=book.owner, receiver=request.user)),
        status="accepted"
    ).exists():
        messages.error(request, "You must be friends to rate books")
        return redirect("core:dashboard")

    # Create or update rating
    BookRating.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'rating': 'like'}
    )
    
    # Create notification
    Notification.objects.create(
        user=book.owner,
        notification_type="book_rating",
        message=f"{request.user.username} liked your book '{book.title}'",
        related_user=request.user,
        related_book=book
    )
    
    return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))

@login_required
def book_dislike(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Check friendship
    if not Friendship.objects.filter(
        (Q(sender=request.user, receiver=book.owner) |
         Q(sender=book.owner, receiver=request.user)),
        status="accepted"
    ).exists():
        messages.error(request, "You must be friends to rate books")
        return redirect("core:dashboard")

    # Create or update rating
    BookRating.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={'rating': 'dislike'}
    )
    
    # Create notification
    Notification.objects.create(
        user=book.owner,
        notification_type="book_rating",
        message=f"{request.user.username} disliked your book '{book.title}'",
        related_user=request.user,
        related_book=book
    )
    
    return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))

@login_required
def book_ratings(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    likes = book.bookrating_set.filter(rating='like')
    dislikes = book.bookrating_set.filter(rating='dislike')
    context = {
        'book': book,
        'likes': likes,
        'dislikes': dislikes,
    }
    return render(request, 'core/books/book_ratings.html', context)

def dashboard(request):
    # Get books from friends
    friend_ids = Friendship.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)), status="accepted"
    ).values_list("sender", "receiver")

    friend_ids = set([id for pair in friend_ids for id in pair]) - {request.user.id}

    friend_books = (
        Book.objects.filter(owner_id__in=friend_ids, available=True)
        .select_related("owner")
        .order_by("-created_at")[:12]
    )

    for book in friend_books:
        book.has_pending_request = BookRequest.has_pending_request(book, request.user)
        likes = book.bookrating_set.filter(rating='like').count()
        dislikes = book.bookrating_set.filter(rating='dislike').count()
        total_ratings = likes + dislikes
        
        if total_ratings > 0:
            book.average_rating = round((likes / total_ratings) * 5, 1)  # Scale to 5 stars
        else:
            book.average_rating = 0
        
        book.likes = likes
        book.dislikes = dislikes
        book.total_ratings = total_ratings

    # Get pending friend requests
    friend_requests = Friendship.objects.filter(
        receiver=request.user, status="pending"
    ).count()

    # Get pending book requests
    book_requests = BookRequest.objects.filter(
        book__owner=request.user, status="pending"
    ).count()

    # Get book request status for each book
    book_request_status = {}
    for book in friend_books:
        if BookRequest.has_pending_request(book, request.user):
            book_request_status[book.id] = 'pending'
        else:
            book_request_status[book.id] = None

    context = {
        "friend_books": friend_books,
        "friend_requests": friend_requests,
        "book_requests": book_requests,
        "book_request_status": book_request_status
    }
    return render(request, "core/dashboard.html", context)


@login_required
def friend_remove(request, username):
    friend = get_object_or_404(User, username=username)

    if request.method == "POST":
        # Find and delete the friendship
        Friendship.objects.filter(
            (
                Q(sender=request.user, receiver=friend)
                | Q(sender=friend, receiver=request.user)
            ),
            status="accepted",
        ).delete()

        # Create notification for the other user
        Notification.objects.create(
            user=friend,
            notification_type="friend_request", # Should be friend_remove or similar
            message=f"{request.user.username} has removed you from their friends list.",
            related_user=request.user
        )

        messages.success(request, f"Removed {friend.get_full_name()} from friends.")

        # Redirect back to the page where the unfriend action was initiated
        referer = request.META.get("HTTP_REFERER")
        if referer and "friends" in referer:
            return redirect("core:friends_list")
        return redirect("core:profile", username=username)

    return redirect("core:profile", username=username)

@login_required
def book_detail(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    reviews = book.reviews.all().order_by('-created_at')
    form = BookReviewForm()

    is_friend = Friendship.objects.filter(
        (Q(sender=request.user, receiver=book.owner) | Q(sender=book.owner, receiver=request.user)),
        status="accepted",
    ).exists()

    # Get borrowing history (only returned requests)
    borrowing_history = BookRequest.objects.filter(
        book=book,
        status='returned'
    ).order_by('-returned_at').select_related('borrower')

    # Get book request status
    book_request_status = {}
    if BookRequest.has_pending_request(book, request.user):
        book_request_status[book.id] = 'pending'
    else:
        book_request_status[book.id] = None

    context = {
        'book': book,
        'reviews': reviews,
        'form': form,
        'book_request_status': book_request_status,
        'is_friend': is_friend,
        'borrowing_history': borrowing_history,
        'is_owner': request.user == book.owner, # Add is_owner to context
    }
    book.has_pending_request = BookRequest.has_pending_request(book, request.user)
    return render(request, 'core/books/book_detail.html', context)

@login_required
def submit_review(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # Check if user is friends with book owner
    if not Friendship.objects.filter(
        (Q(sender=request.user, receiver=book.owner) | Q(sender=book.owner, receiver=request.user)),
        status="accepted",
    ).exists():
        messages.error(request, "You must be friends with the book owner to submit a review.")
        return redirect('core:book_detail', book_id=book_id)

    if request.method == 'POST':
        review_text = request.POST.get('review_text', '').strip()
        if review_text:
            review = BookReview.objects.create(
                user=request.user,
                book=book,
                review_text=review_text
            )

            # Create notification for book owner
            Notification.objects.create(
                user=book.owner,
                notification_type='book_review',
                message=f"{request.user.username} reviewed your book '{book.title}'",
                related_book_review=review
            )
            messages.success(request, "Review submitted successfully!")
        else:
            messages.error(request, "Review text cannot be empty")
        
        return redirect('core:book_detail', book_id=book_id)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(BookReview, id=review_id)
    book_id = review.book.id

    # Check if user is the reviewer or the book owner
    if request.user != review.user and request.user != review.book.owner:
        messages.error(request, "You do not have permission to delete this review.")
        return redirect('core:book_detail', book_id=book_id)

    review.delete()
    messages.success(request, "Review deleted successfully!")
    return redirect('core:book_detail', book_id=book_id)

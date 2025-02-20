from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Authentication
    path("", views.landing_page, name="landing"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    # Profile
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('password/change/', views.password_change, name='password_change'),
    path('password/reset/', views.password_reset, name='password_reset'),
    path('password/reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path("profile/<str:username>/", views.profile_view, name="profile"),
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    # Library
    path("library/<str:username>/", views.library_view, name="library"),
    path("books/add/", views.book_add, name="book_add"),
    path("books/<int:book_id>/edit/", views.book_edit, name="book_edit"),
    path("books/<int:book_id>/delete/", views.book_delete, name="book_delete"),
    # Search
    path("search/", views.search, name="search"),
    # Friends
    path("friends/", views.friends_list, name="friends_list"),
    path("friends/requests/", views.friend_requests, name="friend_requests"),
    path("friends/add/<str:username>/", views.friend_add, name="friend_add"),
    path(
        "friends/accept/<int:request_id>/", views.friend_accept, name="friend_accept"
    ),
    path(
        "friends/decline/<int:request_id>/", views.friend_decline, name="friend_decline"
    ),
    path("friends/remove/<str:username>/", views.friend_remove, name="friend_remove"),
    # Book Requests
    path("books/requests/", views.book_requests, name="book_requests"),
    path("books/<int:book_id>/request/", views.book_request, name="book_request"),
    path(
        "books/requests/<int:request_id>/accept/",
        views.book_request_accept,
        name="book_request_accept",
    ),
    path(
        "books/requests/<int:request_id>/decline/",
        views.book_request_decline,
        name="book_request_decline",
    ),
    path(
        "books/requests/<int:request_id>/return/", views.book_return, name="book_return"
    ),
    # Notifications
    path("notifications/", views.notifications_view, name="notifications"),
    path("notifications/api/", views.notifications_api, name="notifications_api"),
    path("notifications/<int:notification_id>/redirect/", views.notification_redirect, name="notification_redirect"),
    # Book Ratings
    path("books/<int:book_id>/like/", views.book_like, name="book_like"),
    path("books/<int:book_id>/dislike/", views.book_dislike, name="book_dislike"),
    path("books/<int:book_id>/ratings/", views.book_ratings, name="book_ratings"),
    # Book Detail and Reviews
    path("books/<int:book_id>/", views.book_detail, name="book_detail"),
    path("books/<int:book_id>/submit_review/", views.submit_review, name="submit_review"),
    path("reviews/<int:review_id>/delete/", views.delete_review, name="delete_review"),
]

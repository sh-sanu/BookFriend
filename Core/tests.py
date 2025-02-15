from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import UserProfile, Book, Friendship, Notification
import tempfile
import shutil
import os
from django.conf import settings
from pathlib import Path

# Create a temp directory for media files during tests
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    STATIC_ROOT=tempfile.mkdtemp(),
    MEDIA_ROOT=tempfile.mkdtemp()
)
class BaseTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create static directories
        static_images_dir = os.path.join(str(settings.STATIC_ROOT), 'core', 'images')
        os.makedirs(static_images_dir, exist_ok=True)
        
        # Create empty static files
        with open(os.path.join(static_images_dir, 'default-profile.png'), 'wb') as f:
            f.write(b'')
        with open(os.path.join(static_images_dir, 'default-book-cover.png'), 'wb') as f:
            f.write(b'')

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(str(settings.STATIC_ROOT), ignore_errors=True)
            shutil.rmtree(str(settings.MEDIA_ROOT), ignore_errors=True)
        finally:
            super().tearDownClass()

    def setUp(self):
        self.client = Client()
        # Create test image
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'',
            content_type='image/jpeg'
        )

# Create your tests here.

class AuthenticationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.signup_url = reverse('core:signup')
        self.login_url = reverse('core:login')
        self.logout_url = reverse('core:logout')
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        UserProfile.objects.create(user=self.user)

    def test_signup_view_get(self):
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/auth/signup.html')

    def test_signup_view_post_success(self):
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpass123',
            'password2': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'terms_accepted': True
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        new_user = User.objects.get(username='newuser')
        self.assertTrue(hasattr(new_user, 'userprofile'))

    def test_signup_view_post_invalid(self):
        data = {
            'username': 'newuser',
            'email': 'invalid_email',
            'password1': 'newpass123',
            'password2': 'different_pass',
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/auth/login.html')

    def test_login_view_post_success(self):
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_login_view_post_invalid(self):
        data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any(message.message == 'Invalid username or password.' for message in messages))

    def test_logout_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('core:landing'))

class ProfileTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            bio='Test bio',
            birthplace='Test City'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_profile_view_own_profile(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:profile', kwargs={'username': 'testuser'}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_owner'])
        self.assertTemplateUsed(response, 'core/profile/view.html')

    def test_profile_view_other_profile(self):
        # Create other user and profile
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=other_user)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:profile', kwargs={'username': 'otheruser'}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_owner'])

    def test_profile_view_nonexistent_user(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:profile', kwargs={'username': 'nonexistent'}))
        self.assertEqual(response.status_code, 404)

    def test_profile_edit_get(self):
        response = self.client.get(reverse('core:profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/profile/edit.html')

    def test_profile_edit_post_success(self):
        data = {
            'bio': 'Updated bio',
            'birthplace': 'Updated City'
        }
        response = self.client.post(reverse('core:profile_edit'), data)
        self.assertRedirects(response, reverse('core:profile', kwargs={'username': 'testuser'}))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bio, 'Updated bio')
        self.assertEqual(self.profile.birthplace, 'Updated City')

    def test_profile_edit_post_invalid(self):
        # Create a bio that's too long (501 characters)
        data = {
            'bio': 'x' * 501,
            'birthplace': 'Test City'
        }
        response = self.client.post(reverse('core:profile_edit'), data)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('bio', form.errors)
        self.assertEqual(
            form.errors['bio'][0],
            'Ensure this value has at most 500 characters (it has 501).'
        )

    def test_profile_view_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('core:profile', kwargs={'username': 'testuser'}))
        expected_url = f"{reverse('core:login')}?next={reverse('core:profile', kwargs={'username': 'testuser'})}"
        self.assertRedirects(response, expected_url)

    def test_profile_edit_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('core:profile_edit'))
        expected_url = f"{reverse('core:login')}?next={reverse('core:profile_edit')}"
        self.assertRedirects(response, expected_url)

class LibraryTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create a test book
        self.book = Book.objects.create(
            owner=self.user,
            title='Test Book',
            author='Test Author',
            genre='Fiction',
            condition='good',
            description='Test description'
        )

    def test_library_view_own(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:library', kwargs={'username': 'testuser'}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_owner'])
        self.assertTemplateUsed(response, 'core/library/view.html')
        self.assertContains(response, 'Test Book')

    def test_library_view_other(self):
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('core:library', kwargs={'username': 'testuser'}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_owner'])

    def test_book_add_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:book_add'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/library/book_form.html')

    def test_book_add_post_success(self):
        self.client.login(username='testuser', password='testpass123')
        data = {
            'title': 'New Book',
            'author': 'New Author',
            'genre': 'Mystery',
            'condition': 'new',
            'description': 'New book description'
        }
        response = self.client.post(reverse('core:book_add'), data)
        self.assertRedirects(response, reverse('core:library', kwargs={'username': 'testuser'}))
        self.assertTrue(Book.objects.filter(title='New Book').exists())

    def test_book_edit_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:book_edit', kwargs={'book_id': self.book.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/library/book_form.html')

    def test_book_edit_post_success(self):
        self.client.login(username='testuser', password='testpass123')
        data = {
            'title': 'Updated Book',
            'author': self.book.author,
            'genre': self.book.genre,
            'condition': self.book.condition,
            'description': self.book.description
        }
        response = self.client.post(reverse('core:book_edit', kwargs={'book_id': self.book.id}), data)
        self.assertRedirects(response, reverse('core:library', kwargs={'username': 'testuser'}))
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, 'Updated Book')

    def test_book_edit_unauthorized(self):
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('core:book_edit', kwargs={'book_id': self.book.id}))
        self.assertEqual(response.status_code, 404)

    def test_book_delete_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:book_delete', kwargs={'book_id': self.book.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/library/book_confirm_delete.html')

    def test_book_delete_post_success(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('core:book_delete', kwargs={'book_id': self.book.id}))
        self.assertRedirects(response, reverse('core:library', kwargs={'username': 'testuser'}))
        self.assertFalse(Book.objects.filter(id=self.book.id).exists())

    def test_book_delete_unauthorized(self):
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.post(reverse('core:book_delete', kwargs={'book_id': self.book.id}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Book.objects.filter(id=self.book.id).exists())

class FriendshipTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create test users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

    def test_friend_add(self):
        self.client.login(username='user1', password='testpass123')
        # Create UserProfile for user2
        UserProfile.objects.create(user=self.user2)
        response = self.client.post(reverse('core:friend_add', kwargs={'username': 'user2'}))
        self.assertRedirects(response, reverse('core:profile', kwargs={'username': 'user2'}))
        self.assertTrue(Friendship.objects.filter(sender=self.user1, receiver=self.user2).exists())

    def test_friend_add_duplicate(self):
        Friendship.objects.create(sender=self.user1, receiver=self.user2)
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(reverse('core:friend_add', kwargs={'username': 'user2'}))
        self.assertEqual(Friendship.objects.count(), 1)

    def test_friend_accept(self):
        friendship = Friendship.objects.create(sender=self.user1, receiver=self.user2)
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(reverse('core:friend_accept', kwargs={'request_id': friendship.id}))
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, 'accepted')

    def test_friend_decline(self):
        friendship = Friendship.objects.create(sender=self.user1, receiver=self.user2)
        self.client.login(username='user2', password='testpass123')
        response = self.client.post(reverse('core:friend_decline', kwargs={'request_id': friendship.id}))
        friendship.refresh_from_db()
        self.assertEqual(friendship.status, 'declined')

    def test_friend_list_view(self):
        Friendship.objects.create(
            sender=self.user1,
            receiver=self.user2,
            status='accepted'
        )
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('core:friends_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/friends/list.html')
        self.assertContains(response, self.user2.username)

    def test_friend_requests_view(self):
        Friendship.objects.create(sender=self.user1, receiver=self.user2)
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(reverse('core:friend_requests'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/friends/requests.html')
        self.assertContains(response, self.user1.username)

class NotificationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create test notification
        self.notification = Notification.objects.create(
            user=self.user,
            notification_type='friend_request',
            message='Test notification'
        )

    def test_notifications_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/notifications/list.html')
        self.assertContains(response, 'Test notification')

    def test_mark_notifications_as_read(self):
        self.client.login(username='testuser', password='testpass123')
        self.assertFalse(self.notification.read)
        
        response = self.client.post(reverse('core:notifications'))
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.read)

    def test_notifications_api(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('core:notifications_api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['unread_count'], 1)

    def test_notification_creation_on_friend_request(self):
        self.client.login(username='testuser', password='testpass123')
        self.client.post(reverse('core:friend_add', kwargs={'username': 'otheruser'}))
        
        notification = Notification.objects.filter(
            user=self.other_user,
            notification_type='friend_request'
        ).first()
        
        self.assertIsNotNone(notification)
        self.assertIn('friend request', notification.message.lower())

class SearchTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.friend = User.objects.create_user(
            username='frienduser',
            email='friend@example.com',
            password='testpass123',
            first_name='Friend',
            last_name='User'
        )
        self.non_friend = User.objects.create_user(
            username='nonfriend',
            email='nonfriend@example.com',
            password='testpass123',
            first_name='Non',
            last_name='Friend'
        )
        
        # Create test book
        self.book = Book.objects.create(
            owner=self.friend,
            title='Test Book',
            author='Test Author',
            genre='Fiction',
            condition='good',
            available=True
        )
        
        # Create friendship
        self.friendship = Friendship.objects.create(
            sender=self.user,
            receiver=self.friend,
            status='accepted'
        )
        
        # Create UserProfiles
        UserProfile.objects.create(user=self.user)
        UserProfile.objects.create(user=self.friend)
        UserProfile.objects.create(user=self.non_friend)

    def test_search_users(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:search') + '?q=User&type=users')
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/search/results.html')
        
        # Check that both friend and non-friend users are found
        self.assertContains(response, 'frienduser')
        self.assertContains(response, 'nonfriend')
        self.assertNotContains(response, 'testuser')  # Should not show current user
        
        # Check that the response contains the correct user names
        self.assertContains(response, 'Friend User')
        self.assertContains(response, 'Non Friend')

    def test_search_books(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:search'), {'q': 'Test', 'type': 'books'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Book')  # Friend's book
        self.assertNotContains(response, 'Another Test Book')  # Non-friend's book

    def test_search_empty_query(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:search'), {'q': '', 'type': 'all'})
        
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Book')
        self.assertNotContains(response, 'frienduser')

    def test_search_requires_login(self):
        response = self.client.get(reverse('core:search') + '?q=test&type=all')
        expected_url = f"{reverse('core:login')}?next={reverse('core:search')}%3Fq%3Dtest%26type%3Dall"
        self.assertRedirects(response, expected_url)

    def test_search_by_author(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:search'), {'q': 'Test Author', 'type': 'books'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Book')
        self.assertNotContains(response, 'Another Test Book')

    def test_search_by_genre(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('core:search'), {'q': 'Fiction', 'type': 'books'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Book')
        self.assertNotContains(response, 'Another Test Book')

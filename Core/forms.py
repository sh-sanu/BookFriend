from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Book, BookReview

class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, label="First Name", required=True)
    last_name = forms.CharField(max_length=100, label="Last Name", required=True)
    email = forms.EmailField(label="Email", required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("first_name", "last_name", "email")

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture', 'birthplace', 'current_residence', 'occupation']

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'genre', 'condition', 'cover_image', 'description', 'available']

class BookReviewForm(forms.Form):
    review_text = forms.CharField(
        label="Review",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=True
    )
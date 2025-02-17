from django import forms
from .models import UserProfile, Book, BookReview

class SignUpForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="First Name")
    last_name = forms.CharField(max_length=100, label="Last Name")
    username = forms.CharField(max_length=150, label="Username")
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_picture', 'birthplace', 'current_residence', 'occupation']

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'author', 'genre', 'condition', 'cover_image', 'description', 'available']

class BookReviewForm(forms.Form):
    rating = forms.ChoiceField(
        choices=BookReview.RATING_CHOICES,
        label="Rating",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    review_text = forms.CharField(
        label="Review (Optional)",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
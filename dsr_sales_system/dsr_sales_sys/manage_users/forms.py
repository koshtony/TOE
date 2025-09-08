# manage_users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Profile

class CustomUserForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ["username", "email", "role", "is_activated","password1",
            "password2"]

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name","phone_number", "date_of_birth", "national_id", "region","group","date_of_joining", "gender","id_document", "photo"]


class CustomUserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["email", "role", "is_activated"]

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["full_name","phone_number", "date_of_birth", "national_id", "region","group","date_of_joining", "gender","id_document", "photo"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "date_of_joining": forms.DateInput(attrs={"type": "date"}),
        }
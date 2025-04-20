from django import forms
from django.contrib.auth import get_user_model
from django.forms import DateInput

from web.models import User


class RegistrationForm(forms.ModelForm):
    password2 = forms.CharField(widget=forms.PasswordInput())

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data["password"] != cleaned_data["password2"]:
            self.add_error("password", "Пароли не совпадают")
        return cleaned_data

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2")


class AuthForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())
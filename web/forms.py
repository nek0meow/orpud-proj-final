from django import forms
from django.contrib.auth import get_user_model
from django.forms import DateInput

from web.models import User, UserSource, Article, Source


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


class UserSourceForm(forms.ModelForm):
    class Meta:
        model = UserSource
        fields = ['name', 'url', 'api_key', 'source_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название источника'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'URL источника'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'API ключ (если требуется)'}),
            'source_type': forms.Select(attrs={'class': 'form-control'})
        }


class CustomArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите заголовок статьи'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Введите текст статьи'})
        }
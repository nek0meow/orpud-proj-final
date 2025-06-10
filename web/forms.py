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
    
    def clean(self):
        cleaned_data = super().clean()
        # Проверяем, что если выбран тип источника 'api', то указан api_key
        if cleaned_data.get('source_type') == 'api' and not cleaned_data.get('api_key'):
            self.add_error('api_key', 'Для API источника необходимо указать API ключ')
        return cleaned_data


class CustomArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите заголовок статьи',
                'required': True,
                'minlength': '5',
                'maxlength': '200'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Введите текст статьи',
                'required': True,
                'minlength': '50'
            })
        }
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise forms.ValidationError('Заголовок должен содержать минимум 5 символов')
        if len(title) > 200:
            raise forms.ValidationError('Заголовок не должен превышать 200 символов')
        return title
    
    def clean_content(self):
        content = self.cleaned_data.get('content')
        if len(content) < 50:
            raise forms.ValidationError('Текст статьи должен содержать минимум 50 символов')
        return content
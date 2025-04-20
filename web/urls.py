from django.contrib import admin
from django.urls import path, include

from web.views import main_view, registration_view, auth_view, logout_view

urlpatterns = [
    path("", main_view, name="main"),
    path("registration/", registration_view, name='registration'),
    path("auth/", auth_view, name='auth'),
    path("logout/", logout_view, name='logout')
    # path("edit_categories", edit_categories_view, name='edit_categories'),
]
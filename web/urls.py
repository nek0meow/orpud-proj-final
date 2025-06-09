from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import UserProfileDetailAPI, InterestListAPI, SetUserInterestsAPI, SetUserCustomTagsAPI

router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet)

urlpatterns = [
    path("", views.main_view, name="main"),
    path("registration/", views.registration_view, name="registration"),
    path("auth/", views.auth_view, name="auth"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    # API endpoints:
    path("api/", include(router.urls)),
    path("api/profile/", UserProfileDetailAPI.as_view(), name="api_profile"),
    path("api/interests/", InterestListAPI.as_view(), name="api_interests"),
    path("api/set-interests/", SetUserInterestsAPI.as_view(), name="api_set_interests"),
    path("api/set-custom-tags/", SetUserCustomTagsAPI.as_view(), name="api_set_custom_tags"),
    # path("edit_categories", edit_categories_view, name='edit_categories'),
]
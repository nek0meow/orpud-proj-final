from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import UserProfileDetailAPI, InterestListAPI, SetUserInterestsAPI, SetUserCustomTagsAPI

router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet)

urlpatterns = [
    path("", views.main_view, name="main"),
    path("registration/", views.registration_view, name='registration'),
    path("auth/", views.auth_view, name='auth'),
    path("logout/", views.logout_view, name='logout'),
    path("profile/", views.profile_view, name="profile"),
    # API endpoints:
    path("api/profile/", UserProfileDetailAPI.as_view(), name="api-profile"),
    path("api/interests/", InterestListAPI.as_view(), name="api-interests"),
    path("api/profile/set_interests/", SetUserInterestsAPI.as_view(), name="api-set-interests"),
    path("api/profile/set_custom_tags/", SetUserCustomTagsAPI.as_view(), name="api-set-custom-tags"),
    path('api/', include(router.urls)),
    # path("edit_categories", edit_categories_view, name='edit_categories'),
]
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api import UserProfileDetailAPI, InterestListAPI, SetUserInterestsAPI, SetUserCustomTagsAPI

router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet)

urlpatterns = [
    path("", views.main_view, name="main"),
    path("auth/", views.auth_view, name="auth"),
    path("profile/", views.profile_view, name="profile"),
    path("article/<int:article_id>/", views.article_detail, name="article_detail"),
    path("about/", views.about_view, name="about"),
    path("last-24h/", views.last_24h_view, name="last_24h"),
    path('login/', views.auth_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.registration_view, name='register'),
    path('custom-sources/', views.custom_sources_view, name='custom_sources'),
    path('custom-sources/delete/<int:source_id>/', views.delete_source, name='delete_source'),
    path('create-article/', views.create_article_view, name='create_article'),
    # API endpoints:
    path("api/", include(router.urls)),
    path("api/profile/", UserProfileDetailAPI.as_view(), name="api_profile"),
    path("api/interests/", InterestListAPI.as_view(), name="api_interests"),
    path("api/set-interests/", SetUserInterestsAPI.as_view(), name="api_set_interests"),
    path("api/set-custom-tags/", SetUserCustomTagsAPI.as_view(), name="api_set_custom_tags"),
    # path("edit_categories", edit_categories_view, name='edit_categories'),
]
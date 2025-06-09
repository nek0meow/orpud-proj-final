from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse

from web.forms import RegistrationForm, AuthForm
from web.models import User, Article, Interest, Source
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import ArticleSerializer
from .recommender import NewsRecommender

def main_view(request):
    if request.user.is_authenticated:
        # Use the recommender for authenticated users
        recommender = NewsRecommender()
        articles = recommender.get_recommendations(request.user)
    else:
        # For non-authenticated users, show recent articles
        articles = Article.objects.all().order_by('-published_at')[:10]
    
    return render(request, "web/main.html", {"articles": articles})

def registration_view(request):
    form = RegistrationForm()
    if request.method == "POST":
        form = RegistrationForm(data=request.POST)
        if form.is_valid():
            user = User(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"]
            )
            user.set_password(form.cleaned_data["password"])
            user.save()
            return redirect("main")

    return render(request, "web/registration.html", {"form": form})

def auth_view(request):
    form = AuthForm()
    if request.method == "POST":
        form = AuthForm(data=request.POST)
        if form.is_valid():
            user = authenticate(**form.cleaned_data)
            if user is None:
                form.add_error(None, "Введены неверные данные")
            else:
                login(request, user)
                return redirect("main")

    return render(request, "web/auth.html", {"form": form})

@login_required
def logout_view(request):
    logout(request)
    return redirect("main")

@login_required
def profile_view(request):
    profile = request.user.profile
    all_interests = Interest.objects.all()
    if request.method == 'POST':
        # Интересы
        selected = request.POST.getlist('interests')
        profile.interests.set(selected)
        # Кастомные теги
        tags = request.POST.get('custom_tags', '')
        tags_list = [t.strip() for t in tags.split(',') if t.strip()]
        profile.custom_tags = tags_list
        profile.save()
        return HttpResponseRedirect(request.path)
    return render(request, 'web/profile.html', {
        'profile': profile,
        'all_interests': all_interests,
        'selected_interests': profile.interests.values_list('id', flat=True),
        'custom_tags': ', '.join(profile.custom_tags) if profile.custom_tags else ''
    })

class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')
    serializer_class = ArticleSerializer

    @action(detail=False, methods=['get'])
    def all_json(self, request):
        """Получить все статьи в формате JSON"""
        articles = self.get_queryset()
        serializer = self.get_serializer(articles, many=True)
        return Response({"articles": serializer.data})

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Получить персонализированные рекомендации"""
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)
        
        recommender = NewsRecommender()
        recommendations = recommender.get_recommendations(request.user)
        return Response({"articles": recommendations})
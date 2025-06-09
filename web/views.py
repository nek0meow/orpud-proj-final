from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from web.forms import RegistrationForm, AuthForm
from web.models import User, Article, Interest, Source
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import ArticleSerializer

def main(request):
    # Get all articles
    articles = Article.objects.all()
    
    # Get available tags
    available_tags = Interest.objects.all()
    
    # Apply filters
    sort = request.GET.get('sort', 'date_desc')
    date_range = request.GET.get('date_range', 'all')
    selected_tags = request.GET.getlist('tags')
    
    # Date range filter
    if date_range != 'all':
        now = timezone.now()
        if date_range == 'today':
            articles = articles.filter(published_at__date=now.date())
        elif date_range == 'week':
            articles = articles.filter(published_at__gte=now - timedelta(days=7))
        elif date_range == 'month':
            articles = articles.filter(published_at__gte=now - timedelta(days=30))
    
    # Tags filter
    if selected_tags:
        try:
            # Convert string IDs to integers
            tag_ids = [int(tag_id) for tag_id in selected_tags]
            articles = articles.filter(interests__id__in=tag_ids).distinct()
        except (ValueError, TypeError):
            # If there's an error in conversion, ignore the filter
            pass
    
    # Sort articles
    if sort == 'date_asc':
        articles = articles.order_by('published_at')
    elif sort == 'relevance':
        # For now, just sort by date. Later we'll implement relevance scoring
        articles = articles.order_by('-published_at')
    else:  # date_desc
        articles = articles.order_by('-published_at')
    
    # Pagination
    paginator = Paginator(articles, 12)  # Show 12 articles per page
    page_number = request.GET.get('page', 1)
    articles = paginator.get_page(page_number)

    # DEBUG: добавим к каждой статье список id интересов
    for article in articles:
        article.interest_ids = list(article.interests.values_list('id', flat=True))

    context = {
        'articles': articles,
        'available_tags': available_tags,
        'selected_tags': selected_tags,
        'current_sort': sort,
        'current_date_range': date_range,
    }
    
    return render(request, 'web/main.html', context)

def registration_view(request):
    form = RegistrationForm()
    if request.method == "POST":
        form = RegistrationForm(data=request.POST)
        if form.is_valid():
            user = User(
                username=form.cleaned_data["username"], email=form.cleaned_data["email"]
            )

            user.set_password(form.cleaned_data["password"])
            user.save()
            return redirect("main")

    return render(
        request, "web/registration.html", {"form": form}
    )


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

    print("fdfdfdfd")
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
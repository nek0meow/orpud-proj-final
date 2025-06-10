from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
import threading
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, When, Value, FloatField
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from web.forms import RegistrationForm, AuthForm
from web.models import User, Article, Interest, Source
from .serializers import ArticleSerializer
from .recommender import NewsRecommender
from .news_fetcher import NewsFetcher

def fetch_news_async():
    """Fetch news from all APIs in background"""
    def _fetch():
        try:
            fetcher = NewsFetcher()
            fetcher.fetch_all_news()
        except Exception as e:
            print(f"Error fetching news: {e}")
    
    thread = threading.Thread(target=_fetch)
    thread.daemon = True
    thread.start()

class ArticlePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

def main_view(request):
    # Start news fetching in background
    thread = threading.Thread(target=fetch_news_async)
    thread.daemon = True
    thread.start()
    
    # Get available tags
    available_tags = Interest.objects.all()
    
    # Apply filters
    sort = request.GET.get('sort', 'date_desc')
    date_range = request.GET.get('date_range', 'all')
    selected_tags = request.GET.getlist('tags')
    
    # If user is authenticated, use recommender
    if request.user.is_authenticated:
        recommender = NewsRecommender()
        recommended_articles = recommender.get_recommendations(request.user)
        # Get article IDs and scores from recommendations
        article_data = {article['id']: article['score'] for article in recommended_articles}
        article_ids = list(article_data.keys())
        
        # Get Article objects and maintain recommendation order
        articles = Article.objects.filter(id__in=article_ids)
        id_order = {id: idx for idx, id in enumerate(article_ids)}
        articles = sorted(articles, key=lambda x: id_order[x.id])
        
        # Add relevance scores to articles
        for article in articles:
            article.score = article_data[article.id]
    else:
        # Get all articles
        articles = Article.objects.all()
        
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
            # For non-authenticated users, sort by recency
            articles = articles.order_by('-published_at')
        else:  # date_desc
            articles = articles.order_by('-published_at')
    
    # Pagination
    paginator = Paginator(articles, 12)  # Show 12 articles per page
    page_number = request.GET.get('page', 1)
    articles = paginator.get_page(page_number)

    # Add interest IDs to each article
    for article in articles:
        article.interest_ids = list(article.interests.values_list('id', flat=True))

    # Get last update time
    last_update = Article.objects.order_by('-updated_at').first()
    last_update_time = last_update.updated_at if last_update else None

    context = {
        'articles': articles,
        'available_tags': available_tags,
        'selected_tags': selected_tags,
        'current_sort': sort,
        'current_date_range': date_range,
        'last_update': last_update_time,
    }
    
    return render(request, 'web/main.html', context)

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

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = ArticlePagination
    filterset_fields = ['source', 'category', 'tags']
    search_fields = ['title', 'content']
    ordering_fields = ['published_at', 'relevance_score']
    ordering = ['-published_at']

    def get_queryset(self):
        queryset = Article.objects.all()
        
        # Apply tag filtering if tags are provided
        tags = self.request.query_params.getlist('tags', [])
        if tags:
            queryset = queryset.filter(tags__name__in=tags).distinct()
        
        # Apply sorting
        ordering = self.request.query_params.get('ordering', '-published_at')
        if ordering == 'relevance' and self.request.user.is_authenticated:
            # Get recommendations for the user
            recommender = NewsRecommender()
            recommended_articles = recommender.get_recommendations(self.request.user)
            
            # Create a dictionary mapping article IDs to their scores
            article_scores = {article['id']: article['score'] for article in recommended_articles}
            
            # Annotate the queryset with relevance scores
            queryset = queryset.annotate(
                relevance_score=Case(
                    *[When(id=article_id, then=Value(score)) for article_id, score in article_scores.items()],
                    default=Value(0.0),
                    output_field=FloatField(),
                )
            )
            ordering = '-relevance_score'
        
        return queryset.order_by(ordering)

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required for recommendations"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        recommender = NewsRecommender()
        recommendations = recommender.get_recommendations(request.user)
        
        # Get the articles in the recommended order
        article_ids = [rec['id'] for rec in recommendations]
        articles = Article.objects.filter(id__in=article_ids)
        
        # Create a mapping of article IDs to their order
        id_to_order = {id: idx for idx, id in enumerate(article_ids)}
        
        # Sort the articles according to the recommendations
        articles = sorted(articles, key=lambda x: id_to_order[x.id])
        
        # Add relevance scores to the articles
        for article, rec in zip(articles, recommendations):
            article.relevance_score = rec['score']
        
        serializer = self.get_serializer(articles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def refresh(self, request):
        try:
            # Start news fetching in background
            fetch_news_async()
            return Response({"status": "success", "message": "News refresh started"})
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
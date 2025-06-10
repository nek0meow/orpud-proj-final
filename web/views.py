from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
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

from web.forms import RegistrationForm, AuthForm, UserSourceForm, CustomArticleForm
from web.models import User, Article, Interest, Source, UserSource
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
    search_query = request.GET.get('search', '').strip()
    
    # Decode search query if it's URL encoded
    import urllib.parse
    search_query = urllib.parse.unquote(search_query)
    print(f"Decoded search query: {search_query}")  # Debug log
    
    # Base queryset with select_related and prefetch_related
    articles = Article.objects.select_related('source').prefetch_related('interests')
    print(f"Initial article count: {articles.count()}")  # Debug log
    
    # Apply search filter if query exists
    if search_query:
        print(f"Searching for: {search_query}")  # Debug log
        # Force database refresh before search
        from django.db import connection
        connection.close()
        
        # Get fresh queryset
        articles = Article.objects.select_related('source').prefetch_related('interests')
        
        # Debug: Print all articles before search
        print("\nAll articles in database:")
        for article in articles:
            print(f"Article: {article.title} (ID: {article.id})")
            print(f"Content: {article.content[:100]}...")  # Print first 100 chars of content
        
        # Apply search filter with case-insensitive search
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query)
        )
        
        print(f"\nFound {articles.count()} articles after search")  # Debug log
        # Debug: print all matching articles with their content
        print("\nMatching articles:")
        for article in articles:
            print(f"Found article: {article.title} (ID: {article.id})")
            print(f"Content: {article.content[:100]}...")  # Print first 100 chars of content
            
            # Debug: Check if search query is in title or content
            if search_query.lower() in article.title.lower():
                print(f"Query found in title")
            if search_query.lower() in article.content.lower():
                print(f"Query found in content")
        
        # Store search results
        search_results = list(articles)
        print(f"Stored {len(search_results)} search results")  # Debug log
    
    # If user is authenticated, use recommender
    if request.user.is_authenticated:
        recommender = NewsRecommender()
        recommended_articles = recommender.get_recommendations(request.user)
        # Get article IDs and scores from recommendations
        article_data = {article['id']: article['score'] for article in recommended_articles}
        article_ids = list(article_data.keys())
        
        if search_query:
            # If we have search results, use them instead of recommendations
            articles = search_results
        else:
            # Get Article objects and maintain recommendation order
            articles = articles.filter(id__in=article_ids)
            id_order = {id: idx for idx, id in enumerate(article_ids)}
            articles = list(articles)  # Convert to list after filtering
            articles = sorted(articles, key=lambda x: id_order[x.id])
        
        # Add relevance scores to articles
        for article in articles:
            article.reference = article_data.get(article.id, 0.0)
    else:
        if search_query:
            # If we have search results, use them
            articles = search_results
        else:
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
            
            # Convert to list after all filtering
            articles = list(articles)
        
        # Add default reference value for non-authenticated users
        for article in articles:
            article.reference = 0.0
    
    print(f"Final article count: {len(articles)}")  # Debug log
    
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
    
    return render(request, 'web/index.html', context)

def article_detail(request, article_id):
    article = get_object_or_404(Article, id=article_id)
    return render(request, 'web/article_detail.html', {'article': article})

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

def about_view(request):
    return render(request, 'web/about.html')

def last_24h_view(request):
    """Представление для отображения статей за последние 24 часа"""
    # Получаем время 24 часа назад
    yesterday = timezone.now() - timezone.timedelta(days=1)
    
    # Получаем статьи за последние 24 часа
    articles = Article.objects.filter(
        published_at__gte=yesterday
    ).select_related('source').prefetch_related('interests')
    
    # Получаем доступные теги
    available_tags = Interest.objects.all()
    
    # Применяем фильтры
    sort = request.GET.get('sort', 'newest')
    selected_tags = request.GET.getlist('tags')
    
    # Если пользователь авторизован, используем рекомендации
    if request.user.is_authenticated:
        recommender = NewsRecommender()
        recommended_articles = recommender.get_recommendations(request.user)
        # Получаем ID статей и их релевантность
        article_data = {article['id']: article['score'] for article in recommended_articles}
        article_ids = list(article_data.keys())
        
        # Получаем объекты Article и сохраняем порядок рекомендаций
        articles = Article.objects.filter(id__in=article_ids)
        id_order = {id: idx for idx, id in enumerate(article_ids)}
        articles = sorted(articles, key=lambda x: id_order[x.id])
        
        # Добавляем релевантность к статьям
        for article in articles:
            article.reference = article_data[article.id]
    else:
        # Применяем фильтры по тегам
        if selected_tags:
            try:
                # Convert string IDs to integers
                tag_ids = [int(tag_id) for tag_id in selected_tags]
                articles = articles.filter(interests__id__in=tag_ids).distinct()
            except (ValueError, TypeError):
                # If there's an error in conversion, ignore the filter
                pass
        
        # Сортировка статей
        if sort == 'newest':
            articles = articles.order_by('-published_at')
        elif sort == 'oldest':
            articles = articles.order_by('published_at')
        elif sort == 'relevance':
            # Для неавторизованных пользователей сортируем по дате
            articles = articles.order_by('-published_at')
        
        # Добавляем релевантность 0 для неавторизованных пользователей
        for article in articles:
            article.reference = 0.0
    
    # Пагинация - показываем по 12 статей на странице
    paginator = Paginator(articles, 12)
    page = request.GET.get('page', 1)
    try:
        articles = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        articles = paginator.page(1)
    
    # Добавляем ID тегов к каждой статье
    for article in articles:
        article.interest_ids = list(article.interests.values_list('id', flat=True))
    
    # Получаем время последнего обновления
    last_update = Article.objects.order_by('-updated_at').first()
    last_update_time = last_update.updated_at if last_update else None
    
    context = {
        'articles': articles,
        'available_tags': available_tags,
        'selected_tags': selected_tags,
        'current_sort': sort,
        'last_update': last_update_time,
    }
    
    return render(request, 'web/index.html', context)

@login_required
def custom_sources_view(request):
    if request.method == 'POST':
        form = UserSourceForm(request.POST)
        if form.is_valid():
            try:
                source = form.save(commit=False)
                source.user = request.user
                source.save()
                messages.success(request, 'Источник успешно добавлен!')
                return redirect('custom_sources')
            except Exception as e:
                print(f"Error creating source: {str(e)}")  # Debug log
                messages.error(request, f'Ошибка при создании источника: {str(e)}')
    else:
        form = UserSourceForm()
    
    user_sources = UserSource.objects.filter(user=request.user)
    return render(request, 'web/custom_sources.html', {
        'form': form,
        'sources': user_sources
    })

@login_required
def delete_source(request, source_id):
    try:
        source = UserSource.objects.get(id=source_id, user=request.user)
        source.delete()
        messages.success(request, 'Источник успешно удален!')
    except UserSource.DoesNotExist:
        messages.error(request, 'Источник не найден!')
    return redirect('custom_sources')

@login_required
def create_article_view(request):
    if request.method == 'POST':
        form = CustomArticleForm(request.POST)
        print(f"Form data: {request.POST}")  # Debug log
        if form.is_valid():
            try:
                # Get or create source for user articles
                source, created = Source.objects.get_or_create(
                    name="Пользовательские статьи",
                    defaults={
                        'link': 'https://example.com/user-articles',
                        'source_type': 'custom'
                    }
                )
                print(f"Source {'created' if created else 'retrieved'}: {source.name} (ID: {source.id})")  # Debug log
                
                # Create article with all required fields
                article = Article(
                    title=form.cleaned_data['title'],
                    content=form.cleaned_data['content'],
                    source=source,
                    url='https://example.com/temp',  # Temporary URL
                    published_at=timezone.now()  # Set current time as published_at
                )
                print(f"Creating article with title: {article.title}")  # Debug log
                article.save()
                print(f"Article saved with ID: {article.id}")  # Debug log
                
                # Update URL after saving to include the ID
                article.url = f'https://example.com/user-articles/{article.id}'
                article.save()
                print(f"Article URL updated: {article.url}")  # Debug log
                
                # Add default tags
                default_tags = Interest.objects.filter(name__in=['Пользовательские статьи'])
                if not default_tags.exists():
                    default_tags = [Interest.objects.create(
                        name='Пользовательские статьи',
                        description='Статьи, созданные пользователями'
                    )]
                article.interests.set(default_tags)
                print(f"Added {len(default_tags)} tags to article")  # Debug log
                
                # Verify article was saved
                saved_article = Article.objects.filter(id=article.id).first()
                if saved_article:
                    print(f"Verified article exists in database: {saved_article.title}")
                else:
                    print("WARNING: Article not found in database after save!")
                
                messages.success(request, 'Статья успешно создана!')
                return redirect('main')
            except Exception as e:
                print(f"Error creating article: {str(e)}")  # Debug log
                messages.error(request, f'Ошибка при создании статьи: {str(e)}')
        else:
            print(f"Form errors: {form.errors}")  # Debug log
    else:
        form = CustomArticleForm()
    
    return render(request, 'web/create_article.html', {'form': form})
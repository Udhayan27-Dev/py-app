from django.shortcuts import render
from django.db.models import Q
from .models import FAQ

def faq_view(request):
    """
    Displays FAQs loaded from Postgres, grouped by category, with a search filter.
    """
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()

    faqs = FAQ.objects.filter(is_active=True)

    if query:
        faqs = faqs.filter(Q(question__icontains=query) | Q(answer__icontains=query))

    if category_filter:
        faqs = faqs.filter(category=category_filter)

    # Group FAQs by category
    categories_dict = {}
    for faq in faqs:
        cat_key = faq.get_category_display() if hasattr(faq, 'get_category_display') else faq.category.title()
        if cat_key not in categories_dict:
            categories_dict[cat_key] = []
        categories_dict[cat_key].append(faq)

    all_categories = FAQ.CATEGORY_CHOICES

    return render(request, 'faq/faq_list.html', {
        'grouped_faqs': categories_dict,
        'search_query': query,
        'selected_category': category_filter,
        'category_choices': all_categories,
        'total_faqs': faqs.count()
    })

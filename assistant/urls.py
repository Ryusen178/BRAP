from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("results/", views.results_with_session, name="results"),
    path("detail/", views.product_detail, name="product_detail"),
    path("api/search/", views.api_search, name="api_search"),
    
    # Wishlist URLs
    path("wishlist/", views.wishlist, name="wishlist"),
    path("api/wishlist/add/", views.add_to_wishlist, name="add_to_wishlist"),
    path("api/wishlist/remove/<int:item_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path("api/wishlist/notes/<int:item_id>/", views.update_wishlist_notes, name="update_wishlist_notes"),
    path("api/wishlist/status/", views.api_wishlist_status, name="api_wishlist_status"),
    
    # Search History URLs
    path("history/", views.search_history, name="search_history"),
    path("history/clear/", views.clear_search_history, name="clear_search_history"),
    path("history/search/<int:history_id>/", views.search_by_history, name="search_by_history"),
]
from django.contrib import admin
from .models import SearchHistory, WishlistItem, PageVisit


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('page', 'get_user_display', 'visitor_ip', 'visited_at')
    list_filter = ('page', 'visited_at')
    search_fields = ('page', 'visitor_ip', 'user__username')
    readonly_fields = ('visited_at', 'user_agent')
    date_hierarchy = 'visited_at'

    def has_add_permission(self, request):
        return False

    def get_user_display(self, obj):
        if obj.user:
            return obj.user.username
        return "Anonymous"
    get_user_display.short_description = "User"


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'results_count', 'searched_at')
    list_filter = ('searched_at', 'user')
    search_fields = ('query', 'user__username')
    readonly_fields = ('searched_at', 'parsed_params')
    date_hierarchy = 'searched_at'

    def has_add_permission(self, request):
        # Cegah penambahan manual, hanya melalui aplikasi
        return False


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_name', 'product_store', 'product_price', 'added_at')
    list_filter = ('added_at', 'user', 'product_store')
    search_fields = ('product_name', 'user__username', 'product_store')
    readonly_fields = ('added_at', 'updated_at')
    fieldsets = (
        ('User Info', {
            'fields': ('user',)
        }),
        ('Product Details', {
            'fields': ('product_name', 'product_url', 'product_image', 'product_price', 'product_store', 'product_rating')
        }),
        ('Additional Info', {
            'fields': ('notes', 'product_data'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

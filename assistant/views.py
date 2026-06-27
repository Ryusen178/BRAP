import json
import logging

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q, Max
from django.utils import timezone
from datetime import timedelta

from .services import search_products
from .models import SearchHistory, WishlistItem, PageVisit

logger = logging.getLogger(__name__)


def home(request):
    """Landing page with search form."""
    return render(request, "assistant/home.html")


def results(request):
    """Results page — shown after search."""
    query = request.GET.get("q", "").strip()
    if not query:
        return render(request, "assistant/home.html")

    try:
        data = search_products(query)
    except Exception as e:
        logger.error(f"search_products error: {e}")
        data = {
            "headline": "Terjadi kesalahan saat mencari produk.",
            "products": [],
            "parsed_params": {},
            "original_query": query,
        }

    return render(request, "assistant/results.html", {
        "headline": data["headline"],
        "products": data["products"],
        "query": query,
        "parsed": data["parsed_params"],
    })


def product_detail(request):
    """
    Detail page — rendered from query-string data passed by results page.
    Data produk dikirim via GET params yang di-encode sebagai JSON.
    """
    query = request.GET.get("q", "").strip()
    product_index = request.GET.get("idx", "0")
    page = request.GET.get("page", 1)

    # Ambil data dari session yang disimpan oleh results view
    cached = request.session.get("last_products", [])

    try:
        idx = int(product_index)
        product = cached[idx] if 0 <= idx < len(cached) else None
    except (ValueError, IndexError):
        product = None

    if not product:
        return render(request, "assistant/results.html", {
            "headline": "Produk tidak ditemukan.",
            "products": [],
            "query": query,
            "parsed": {},
        })

    return render(request, "assistant/detail.html", {
        "product": product,
        "query": query,
        "product_index": idx,
        "page": page,
    })


def results_with_session(request):
    """Results page — simpan produk ke session untuk halaman detail dengan pagination."""
    query = request.GET.get("q", "").strip()
    page = int(request.GET.get("page", 1))
    items_per_page = 10
    
    if not query:
        return render(request, "assistant/home.html")

    # Cek apakah ini adalah kembali dari halaman detail dengan query yang sama
    # Jika ya, gunakan data dari session tanpa search ulang
    last_query = request.session.get("last_query", "")
    cached_products = request.session.get("last_products", [])
    cached_parsed_params = request.session.get("last_parsed_params", {})
    cached_headline = request.session.get("last_headline", "")

    if query == last_query and cached_products:
        # Gunakan data yang sudah di-cache, jangan search ulang
        data = {
            "headline": cached_headline,
            "products": cached_products,
            "parsed_params": cached_parsed_params,
        }
        logger.info(f"Menggunakan cached results untuk query: {query}")
    else:
        # Search baru karena query berbeda atau tidak ada cache
        try:
            data = search_products(query)
        except Exception as e:
            logger.error(f"search_products error: {e}")
            data = {
                "headline": "Terjadi kesalahan saat mencari produk.",
                "products": [],
                "parsed_params": {},
                "original_query": query,
            }

        # Simpan ke session untuk diakses halaman detail
        request.session["last_products"] = data["products"]
        request.session["last_query"] = query
        request.session["last_parsed_params"] = data.get("parsed_params", {})
        request.session["last_headline"] = data.get("headline", "")

        # Catat ke search history jika user sudah login (hanya untuk search baru)
        if request.user.is_authenticated:
            try:
                SearchHistory.objects.create(
                    user=request.user,
                    query=query,
                    parsed_params=data.get("parsed_params", {}),
                    results_count=len(data.get("products", []))
                )
            except Exception as e:
                logger.warning(f"Error saving search history: {e}")

    # Implementasi pagination
    all_products = data["products"]
    total_products = len(all_products)
    total_pages = (total_products + items_per_page - 1) // items_per_page
    
    # Validasi page number
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Slice products untuk halaman ini
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    paginated_products = all_products[start_idx:end_idx]

    return render(request, "assistant/results.html", {
        "headline": data["headline"],
        "products": paginated_products,
        "query": query,
        "parsed": data["parsed_params"],
        "current_page": page,
        "total_pages": total_pages,
        "total_products": total_products,
        "items_per_page": items_per_page,
        "has_previous": page > 1,
        "has_next": page < total_pages,
        "previous_page_number": page - 1,
        "next_page_number": page + 1,
        "page_range": range(max(1, page - 2), min(total_pages + 1, page + 3)),
        "start_idx": start_idx,
    })


@csrf_exempt
@require_POST
def api_search(request):
    """JSON API endpoint for AJAX search."""
    try:
        body = json.loads(request.body)
        query = body.get("query", "").strip()
        if not query:
            return JsonResponse({"error": "Query tidak boleh kosong"}, status=400)

        data = search_products(query)
        return JsonResponse({
            "success": True,
            "headline": data["headline"],
            "products": data["products"],
            "query": query,
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body tidak valid JSON"}, status=400)
    except Exception as e:
        logger.error(f"api_search error: {e}")
        return JsonResponse({"error": "Terjadi kesalahan internal"}, status=500)


# ─────────────────────────────────────────
#  WISHLIST VIEWS
# ─────────────────────────────────────────

@login_required(login_url='account_login')
def wishlist(request):
    """Tampilkan wishlist pengguna."""
    items = WishlistItem.objects.filter(user=request.user)
    return render(request, "assistant/wishlist.html", {
        "wishlist_items": items,
        "total_items": items.count(),
    })


@login_required(login_url='account_login')
@require_POST
def add_to_wishlist(request):
    """Tambahkan produk ke wishlist."""
    try:
        data = json.loads(request.body)
        product_name = data.get("product_name", "").strip()
        
        if not product_name:
            return JsonResponse({"error": "Product name diperlukan"}, status=400)

        # Buat atau update wishlist item
        wishlist_item, created = WishlistItem.objects.update_or_create(
            user=request.user,
            product_name=product_name,
            defaults={
                'product_url': data.get('product_url', ''),
                'product_image': data.get('product_image', ''),
                'product_price': data.get('product_price', ''),
                'product_store': data.get('product_store', ''),
                'product_rating': data.get('product_rating', ''),
                'product_data': data.get('product_data', {}),
            }
        )

        return JsonResponse({
            "success": True,
            "message": "Produk berhasil ditambahkan ke wishlist!",
            "created": created,
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body tidak valid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error adding to wishlist: {e}")
        return JsonResponse({"error": "Terjadi kesalahan saat menambahkan ke wishlist"}, status=500)


@login_required(login_url='account_login')
@require_http_methods(["POST", "DELETE"])
def remove_from_wishlist(request, item_id):
    """Hapus produk dari wishlist."""
    try:
        item = WishlistItem.objects.get(id=item_id, user=request.user)
        product_name = item.product_name
        item.delete()
        
        if request.method == "DELETE":
            # API response
            return JsonResponse({
                "success": True,
                "message": f"'{product_name}' dihapus dari wishlist",
            })
        else:
            # Form submission
            messages.success(request, f"'{product_name}' dihapus dari wishlist")
            return redirect('wishlist')
    except WishlistItem.DoesNotExist:
        if request.method == "DELETE":
            return JsonResponse({"error": "Item tidak ditemukan"}, status=404)
        else:
            messages.error(request, "Item tidak ditemukan")
            return redirect('wishlist')
    except Exception as e:
        logger.error(f"Error removing from wishlist: {e}")
        if request.method == "DELETE":
            return JsonResponse({"error": "Terjadi kesalahan"}, status=500)
        else:
            messages.error(request, "Terjadi kesalahan saat menghapus item")
            return redirect('wishlist')


@login_required(login_url='account_login')
@require_POST
def update_wishlist_notes(request, item_id):
    """Update catatan untuk wishlist item."""
    try:
        item = WishlistItem.objects.get(id=item_id, user=request.user)
        data = json.loads(request.body)
        item.notes = data.get('notes', '')
        item.save()
        
        return JsonResponse({
            "success": True,
            "message": "Catatan berhasil diperbarui",
        })
    except WishlistItem.DoesNotExist:
        return JsonResponse({"error": "Item tidak ditemukan"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Request body tidak valid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error updating wishlist notes: {e}")
        return JsonResponse({"error": "Terjadi kesalahan"}, status=500)


# ─────────────────────────────────────────
#  SEARCH HISTORY VIEWS
# ─────────────────────────────────────────

@login_required(login_url='account_login')
def search_history(request):
    """Tampilkan riwayat pencarian pengguna."""
    history = SearchHistory.objects.filter(user=request.user)[:20]  # Tampilkan 20 pencarian terbaru
    return render(request, "assistant/search_history.html", {
        "search_history": history,
        "total_searches": SearchHistory.objects.filter(user=request.user).count(),
    })


@login_required(login_url='account_login')
@require_POST
def clear_search_history(request):
    """Hapus semua riwayat pencarian pengguna."""
    try:
        SearchHistory.objects.filter(user=request.user).delete()
        messages.success(request, "Riwayat pencarian berhasil dihapus")
        return redirect('search_history')
    except Exception as e:
        logger.error(f"Error clearing search history: {e}")
        messages.error(request, "Terjadi kesalahan saat menghapus riwayat")
        return redirect('search_history')


@login_required(login_url='account_login')
@login_required(login_url='account_login')
def search_by_history(request, history_id):
    """Ulangi pencarian dari riwayat."""
    try:
        history_item = SearchHistory.objects.get(id=history_id, user=request.user)
        from django.urls import reverse
        from urllib.parse import quote
        encoded_query = quote(history_item.query)
        return redirect(f"{reverse('results')}?q={encoded_query}")
    except SearchHistory.DoesNotExist:
        messages.error(request, "Riwayat pencarian tidak ditemukan")
        return redirect('search_history')
    except Exception as e:
        logger.error(f"Error searching by history: {e}")
        messages.error(request, "Terjadi kesalahan")
        return redirect('search_history')


# ─────────────────────────────────────────
#  ADMIN DASHBOARD VIEWS
# ─────────────────────────────────────────

def is_admin(user):
    """Check apakah user adalah admin"""
    return user.is_staff or user.is_superuser


@login_required(login_url='account_login')
@user_passes_test(is_admin, login_url='home')
def admin_dashboard(request):
    """Admin dashboard dengan statistik penting: kunjungan hari ini & 7 hari, wishlist top, pencarian top."""
    
    # Kunjungan Hari Ini (dihitung berdasarkan IP unik, bukan total request)
    today_visits = PageVisit.objects.filter(
        visited_at__date=timezone.now().date()
    ).values('visitor_ip').distinct().count()

    # Kunjungan 7 Hari Terakhir (jumlah IP unik dalam rentang 7 hari ini)
    seven_days_ago = timezone.now() - timedelta(days=7)
    visits_7days_count = PageVisit.objects.filter(
        visited_at__gte=seven_days_ago
    ).values('visitor_ip').distinct().count()
    
    # Produk paling banyak di wishlist (top 10)
    top_wishlisted = WishlistItem.objects.values('product_name', 'product_store').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Pencarian paling populer (top 10)
    top_searches = SearchHistory.objects.values('query').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Wishlist per user dengan item mereka
    user_wishlists = WishlistItem.objects.values('user__username', 'user__id').annotate(
        item_count=Count('id')
    ).order_by('-item_count')
    
    # Build dictionary untuk user wishlist details
    user_wishlist_details = {}
    for user_data in user_wishlists:
        user_id = user_data['user__id']
        username = user_data['user__username']
        items = WishlistItem.objects.filter(user_id=user_id).values('product_name', 'product_store', 'product_price', 'added_at')
        user_wishlist_details[username] = list(items)

    # Daftar semua user dengan info lengkap
    all_users = User.objects.annotate(
        search_count=Count('search_history', distinct=True),
        wishlist_count=Count('wishlist_items', distinct=True),
        last_search=Max('search_history__searched_at'),
    ).order_by('-date_joined')

    user_list = []
    for u in all_users:
        user_list.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'full_name': u.get_full_name() or '—',
            'date_joined': u.date_joined,
            'last_login': u.last_login,
            'last_search': u.last_search,
            'is_active': u.is_active,
            'is_staff': u.is_staff,
            'is_superuser': u.is_superuser,
            'search_count': u.search_count,
            'wishlist_count': u.wishlist_count,
        })

    total_users = len(user_list)
    active_users = sum(1 for u in user_list if u['is_active'])

    context = {
        'today_visits': today_visits,
        'visits_7days_count': visits_7days_count,
        'top_wishlisted': list(top_wishlisted),
        'top_searches': list(top_searches),
        'user_wishlist_details': user_wishlist_details,
        'user_list': user_list,
        'total_users': total_users,
        'active_users': active_users,
    }
    
    return render(request, 'assistant/admin_dashboard.html', context)


# ─────────────────────────────────────────
#  API ENDPOINTS
# ─────────────────────────────────────────

@login_required(login_url='account_login')
def api_wishlist_status(request):
    """API endpoint untuk cek apakah produk sudah di wishlist."""
    product_name = request.GET.get('product_name', '').strip()
    
    if not product_name:
        return JsonResponse({"error": "Product name diperlukan"}, status=400)
    
    exists = WishlistItem.objects.filter(
        user=request.user,
        product_name=product_name
    ).exists()
    
    return JsonResponse({
        "in_wishlist": exists,
        "product_name": product_name,
    })
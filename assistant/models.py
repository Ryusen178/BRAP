from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PageVisit(models.Model):
    """Model untuk menyimpan statistik kunjungan halaman"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='page_visits')
    page = models.CharField(max_length=255, help_text="Nama halaman yang dikunjungi")
    visitor_ip = models.CharField(max_length=45, blank=True, help_text="IP address pengunjung")
    user_agent = models.TextField(blank=True, help_text="User agent browser")
    visited_at = models.DateTimeField(auto_now_add=True, help_text="Waktu kunjungan")

    class Meta:
        ordering = ['-visited_at']
        verbose_name_plural = "Page Visits"
        indexes = [
            models.Index(fields=['-visited_at']),
            models.Index(fields=['page', '-visited_at']),
        ]

    def __str__(self):
        return f"{self.page} - {self.visited_at}"


class SearchHistory(models.Model):
    """Model untuk menyimpan riwayat pencarian pengguna"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255, help_text="Kata kunci pencarian")
    parsed_params = models.JSONField(default=dict, blank=True, help_text="Parameter pencarian yang sudah diparse")
    results_count = models.IntegerField(default=0, help_text="Jumlah hasil yang ditemukan")
    searched_at = models.DateTimeField(auto_now_add=True, help_text="Waktu pencarian")

    class Meta:
        ordering = ['-searched_at']
        verbose_name_plural = "Search Histories"
        indexes = [
            models.Index(fields=['user', '-searched_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.query} ({self.searched_at})"


class WishlistItem(models.Model):
    """Model untuk menyimpan item wishlist pengguna"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    
    # Product info (disimpan sebagai JSON untuk fleksibilitas)
    product_name = models.CharField(max_length=255, help_text="Nama produk")
    product_url = models.URLField(max_length=500, blank=True, help_text="Link produk")
    product_image = models.URLField(max_length=500, blank=True, help_text="URL gambar produk")
    product_price = models.CharField(max_length=50, blank=True, help_text="Harga produk")
    product_store = models.CharField(max_length=100, blank=True, help_text="Toko/penjual")
    product_rating = models.CharField(max_length=10, blank=True, help_text="Rating produk")
    
    # Additional info
    product_data = models.JSONField(default=dict, blank=True, help_text="Data produk lengkap dalam format JSON")
    notes = models.TextField(blank=True, help_text="Catatan pribadi tentang produk")
    
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True, help_text="Waktu ditambahkan ke wishlist")
    updated_at = models.DateTimeField(auto_now=True, help_text="Waktu update terakhir")

    class Meta:
        ordering = ['-added_at']
        unique_together = ('user', 'product_name')  # Cegah duplikasi
        indexes = [
            models.Index(fields=['user', '-added_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.product_name}"

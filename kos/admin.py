from django.contrib import admin
from .models import Kamar, Penyewa, Tagihan, Pembayaran


@admin.register(Kamar)
class KamarAdmin(admin.ModelAdmin):
    list_display = ('nomor_kamar', 'harga', 'status')
    list_filter = ('status',)
    search_fields = ('nomor_kamar',)


@admin.register(Penyewa)
class PenyewaAdmin(admin.ModelAdmin):
    list_display = ('nama', 'kamar', 'tanggal_masuk', 'status')
    list_filter = ('status',)
    search_fields = ('nama',)


@admin.register(Tagihan)
class TagihanAdmin(admin.ModelAdmin):
    # field yang TIDAK BOLEH diedit (otomatis sistem)
    readonly_fields = (
        'tanggal_tagihan',
        'bulan',
        'tahun',
        'biaya_kamar',
        'total'
    )

    list_display = (
        'penyewa',
        'tanggal_tagihan',
        'bulan',
        'tahun',
        'total',
        'status'
    )

    list_filter = ('status', 'bulan', 'tahun')
    search_fields = ('penyewa__nama',)


@admin.register(Pembayaran)
class PembayaranAdmin(admin.ModelAdmin):
    list_display = ('tagihan', 'tanggal_bayar', 'jumlah_bayar')
    search_fields = ('tagihan__penyewa__nama',)


# Judul admin
admin.site.site_header = "Admin Kos Wisma 24"
admin.site.site_title = "Kos Wisma 24"
admin.site.index_title = "Dashboard Kos Wisma 24"
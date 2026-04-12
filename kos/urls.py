from django.urls import path
from . import views

urlpatterns = [

    # =========================
    # AUTH
    # =========================
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('login-penyewa/', views.login_penyewa, name='login_penyewa'),
    path('register-penyewa/', views.register_penyewa, name='register_penyewa'),
    path('logout/', views.logout_view, name='logout'),

    
    path('dashboard-penyewa/', views.dashboard_penyewa, name='dashboard_penyewa'),
    path('pilih-fasilitas/', views.pilih_fasilitas, name='pilih_fasilitas'),
    path('pilih-kamar/', views.pilih_kamar, name='pilih_kamar'),
    path('pembayaran-penyewa/', views.pembayaran_penyewa, name='pembayaran_penyewa'),
    path('harga-fasilitas/', views.harga_fasilitas, name='harga_fasilitas'),
    path('update-harga/', views.update_harga_fasilitas, name='update_harga_fasilitas'),

    # =========================
    # KAMAR
    # =========================
    path('kamar/', views.daftar_kamar, name='kamar'),
    path('tambah-kamar/', views.tambah_kamar, name='tambah_kamar'),
    path('edit-kamar/<int:id>/', views.edit_kamar, name='edit_kamar'),
    path('hapus-kamar/<int:id>/', views.hapus_kamar, name='hapus_kamar'),

    # =========================
    # PENYEWA
    # =========================
    path('penyewa/', views.daftar_penyewa, name='penyewa'),
    path('tambah-penyewa/', views.tambah_penyewa, name='tambah_penyewa'),
    path('edit-penyewa/<int:id>/', views.edit_penyewa, name='edit_penyewa'),
    path('hapus-penyewa/<int:id>/', views.hapus_penyewa, name='hapus_penyewa'),
    path('detail-penyewa/<int:id>/', views.detail_penyewa, name='detail_penyewa'),
    path('riwayat-penyewa/', views.riwayat_penyewa, name='riwayat_penyewa'),
    path('keluar-penyewa/<int:id>/', views.keluar_penyewa, name='keluar_penyewa'),

    # =========================
    # TAGIHAN
    # =========================
    path('tagihan/', views.daftar_tagihan, name='tagihan'),
    path('tagihan/<int:id>/', views.detail_tagihan, name='detail_tagihan'),
    path('tambah-tagihan/', views.tambah_tagihan, name='tambah_tagihan'),
    path('edit-tagihan/<int:id>/', views.edit_tagihan, name='edit_tagihan'),
    path('hapus-tagihan/<int:id>/', views.hapus_tagihan, name='hapus_tagihan'),
    path('tagihan-penyewa/', views.tagihan_penyewa, name='tagihan_penyewa'),

    # =========================
    # PEMBAYARAN
    # =========================
    path('pembayaran/', views.daftar_pembayaran, name='pembayaran'),
    path('hapus-pembayaran/<int:id>/', views.hapus_pembayaran),

    # =========================
    # PENGELUARAN
    # =========================
    path('pengeluaran/', views.daftar_pengeluaran, name='pengeluaran'),
    path('tambah-pengeluaran/', views.tambah_pengeluaran, name='tambah_pengeluaran'),
    path('edit-pengeluaran/<int:id>/', views.edit_pengeluaran),
    path('hapus-pengeluaran/<int:id>/', views.hapus_pengeluaran),

    # =========================
    # LAPORAN
    # =========================
    path('laporan-keuangan/', views.laporan_keuangan, name='laporan_keuangan'),
    path('download-pdf/', views.download_pdf, name='download_pdf'),

]
from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.models import User

# =========================
# KAMAR
# =========================
class Kamar(models.Model):
    nomor_kamar = models.CharField(max_length=10)
    harga = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('Kosong', 'Kosong'),
            ('Terisi', 'Terisi')
        ],
        default='Kosong'
    )

    def __str__(self):
        return self.nomor_kamar

# =========================
# FASILITAS
# =========================
class Fasilitas(models.Model):
    nama = models.CharField(max_length=50)

    def __str__(self):
        return self.nama

# =========================
# PENYEWA
# =========================
class Penyewa(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    nama = models.CharField(max_length=100)
    no_hp = models.CharField(max_length=15, blank=True)
    nik = models.CharField(max_length=16, blank=True)

    kamar = models.ForeignKey(Kamar, on_delete=models.SET_NULL, null=True, blank=True)

    tanggal_masuk = models.DateField(null=True, blank=True)
    tanggal_keluar = models.DateField(null=True, blank=True)

    foto_ktp = models.ImageField(upload_to='ktp/', null=True, blank=True)
    fasilitas = models.ManyToManyField(Fasilitas, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Aktif', 'Aktif'),
            ('Keluar', 'Keluar')
        ],
        default='Pending'
    )

    def __str__(self):
        return self.nama


# =========================
# HARGA FASILITAS (Bisa ubah kapan saja tanpa migrasi)
# =========================
class HargaFasilitas(models.Model):
    wifi = models.IntegerField(default=50000)
    ac = models.IntegerField(default=0)
    kipas_angin = models.IntegerField(default=0)
    rice_cooker = models.IntegerField(default=0)
    tanggal_update = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Harga Fasilitas Terbaru ({self.tanggal_update.strftime('%d-%m-%Y')})"

# =========================
# TAGIHAN
# =========================
class Tagihan(models.Model):
    penyewa = models.ForeignKey(Penyewa, on_delete=models.CASCADE)
    tanggal_tagihan = models.DateField(default=timezone.now)
    bulan = models.CharField(max_length=20)
    tahun = models.IntegerField()

    biaya_kamar = models.IntegerField()
    listrik = models.IntegerField(default=50000)
    air = models.IntegerField(default=30000)

    # Fasilitas bisa diubah saat tambah tagihan
    wifi = models.IntegerField(default=0)
    ac = models.IntegerField(default=0)
    rice_cooker = models.IntegerField(default=0)
    kipas_angin = models.IntegerField(default=0)

    total = models.IntegerField(default=0)
    dibayar = models.IntegerField(default=0)
    sisa = models.IntegerField(default=0)

    status = models.CharField(max_length=20, default="Belum Bayar")
    jatuh_tempo = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('penyewa', 'bulan', 'tahun')

    def save(self, *args, **kwargs):
        # Ambil harga fasilitas terbaru jika field 0
        latest_harga = HargaFasilitas.objects.last()
        if latest_harga:
            if self.wifi == 0:
                self.wifi = latest_harga.wifi
            if self.ac == 0:
                self.ac = latest_harga.ac
            if self.rice_cooker == 0:
                self.rice_cooker = latest_harga.rice_cooker
            if self.kipas_angin == 0:
                self.kipas_angin = latest_harga.kipas_angin

        # pastikan field kosong tidak error
        self.listrik = self.listrik or 0
        self.air = self.air or 0
        self.wifi = self.wifi or 0
        self.ac = self.ac or 0
        self.rice_cooker = self.rice_cooker or 0
        self.kipas_angin = self.kipas_angin or 0
        self.biaya_kamar = self.biaya_kamar or 0

        # hitung total
        self.total = (
            self.biaya_kamar +
            self.listrik +
            self.air +
            self.wifi +
            self.ac +
            self.rice_cooker +
            self.kipas_angin
        )

        # hitung sisa
        self.sisa = max(self.total - (self.dibayar or 0), 0)

        # tentukan status
        if self.sisa <= 0:
            self.status = 'Lunas'
        elif self.dibayar > 0:
            self.status = 'Masih Utang'
        else:
            self.status = 'Belum Bayar'

        super().save(*args, **kwargs)

# =========================
# PEMBAYARAN
# =========================
class Pembayaran(models.Model):
    tagihan = models.ForeignKey(Tagihan, on_delete=models.CASCADE)
    tanggal_bayar = models.DateField(default=timezone.now)
    jumlah_bayar = models.IntegerField()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total_bayar = Pembayaran.objects.filter(tagihan=self.tagihan).aggregate(total=Sum('jumlah_bayar'))['total'] or 0
        self.tagihan.dibayar = total_bayar
        self.tagihan.save()

    def __str__(self):
        return f"{self.tagihan.penyewa.nama} - {self.jumlah_bayar}"

# =========================
# PENGELUARAN
# =========================
class Pengeluaran(models.Model):
    KATEGORI_CHOICES = [
        ('Listrik', 'Listrik'),
        ('Wifi', 'Wifi'),
        ('Air', 'Air'),
        ('Perawatan', 'Perawatan'),
        ('Lainnya', 'Lainnya'),
    ]
    tanggal = models.DateField()
    kategori = models.CharField(max_length=50, choices=KATEGORI_CHOICES, default='Lainnya')
    keterangan = models.CharField(max_length=200)
    jumlah = models.IntegerField()

    def __str__(self):
        return self.keterangan

class RequestPindahKamar(models.Model):
    penyewa = models.ForeignKey(Penyewa, on_delete=models.CASCADE)
    kamar_tujuan = models.ForeignKey(Kamar, on_delete=models.CASCADE)
    tanggal_request = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Disetujui', 'Disetujui'),
            ('Ditolak', 'Ditolak')
        ],
        default='Pending'
    )

    def __str__(self):
        return f"{self.penyewa.nama} → {self.kamar_tujuan.nomor_kamar}"

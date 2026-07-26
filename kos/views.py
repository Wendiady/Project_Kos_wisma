from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from reportlab.pdfgen import canvas
import json
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import date
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from collections import defaultdict
from .models import Kamar, Penyewa, Tagihan, Pembayaran, Pengeluaran, Fasilitas, HargaFasilitas, RequestPindahKamar
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import HRFlowable

@login_required
def update_harga_fasilitas(request):
    harga, created = HargaFasilitas.objects.get_or_create(id=1)

    if request.method == "POST":
        harga.wifi = int(request.POST.get("wifi") or 0)
        harga.ac = int(request.POST.get("ac") or 0)
        harga.kipas_angin = int(request.POST.get("kipas_angin") or 0)
        harga.rice_cooker = int(request.POST.get("rice_cooker") or 0)
        harga.save()

        return redirect('dashboard')

@login_required
def dashboard(request):

    if hasattr(request.user, 'penyewa'):
        return redirect('dashboard_penyewa')

    generate_tagihan_otomatis()

    today = timezone.now().date()

    from kos.models import HargaFasilitas

    harga = HargaFasilitas.objects.first()

    if not harga:
        harga = {
            "wifi": 0,
            "ac": 0,
            "kipas_angin": 0,
            "rice_cooker": 0
        }
        
    # =========================
    # STATISTIK KOS
    # =========================
    total_kamar = Kamar.objects.count()
    kamar_terisi = Kamar.objects.filter(status__iexact='Terisi').count()
    kamar_kosong = Kamar.objects.filter(status__iexact='Kosong').count()

    total_penyewa = Penyewa.objects.filter(status='Aktif').count()

    # 🔥 DIUBAH: Menghilangkan filter 'Lunas' dan menjumlahkan kolom 'dibayar' agar cicilan ikut masuk
    total_pemasukan = Tagihan.objects.aggregate(
        total=Sum('dibayar')
    )['total'] or 0

    total_pengeluaran = Pengeluaran.objects.aggregate(
        total=Sum('jumlah')
    )['total'] or 0

    saldo_kos = total_pemasukan - total_pengeluaran

    # =========================
    # TELAT BAYAR
    # =========================
    telat_list = Tagihan.objects.filter(
        status__in=['Belum Bayar', 'Masih Utang'],
        jatuh_tempo__isnull=False,
        jatuh_tempo__lt=today
    )

    jumlah_telat = telat_list.count()

    # =========================
    # GRAFIK DATA
    # =========================
    bulan_convert = {
        "January": "Januari","February": "Februari","March": "Maret",
        "April": "April","May": "Mei","June": "Juni",
        "July": "Juli","August": "Agustus","September": "September",
        "October": "Oktober","November": "November","December": "Desember"
    }

    bulan_map = {
        1: "Januari",2: "Februari",3: "Maret",4: "April",
        5: "Mei",6: "Juni",7: "Juli",8: "Agustus",
        9: "September",10: "Oktober",11: "November",12: "Desember"
    }

    urutan = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ]

    # 🔥 DIUBAH: Grafik sekarang membaca jumlah uang yang sudah 'dibayar' (bukan cuma yang lunas)
    pemasukan = Tagihan.objects.values('bulan').annotate(total=Sum('dibayar'))
    pengeluaran = Pengeluaran.objects.values('tanggal__month').annotate(total=Sum('jumlah'))

    semua_bulan = set()

    for p in pemasukan:
        semua_bulan.add(bulan_convert.get(p['bulan'], p['bulan']))

    for p in pengeluaran:
        semua_bulan.add(bulan_map[p['tanggal__month']])

    semua_bulan = sorted(semua_bulan, key=lambda x: urutan.index(x))

    labels = []
    data_pemasukan = []
    data_pengeluaran = []

    for bulan in semua_bulan:
        labels.append(bulan)

        total_pemasukan_bulan = next(
            (x['total'] for x in pemasukan if bulan_convert.get(x['bulan'], x['bulan']) == bulan),
            0
        )

        total_pengeluaran_bulan = next(
            (x['total'] for x in pengeluaran if bulan_map[x['tanggal__month']] == bulan),
            0
        )

        # Jika hasil sum bertipe None, ubah jadi 0
        total_pemasukan_bulan = total_pemasukan_bulan or 0
        total_pengeluaran_bulan = total_pengeluaran_bulan or 0

        data_pemasukan.append(total_pemasukan_bulan)
        data_pengeluaran.append(total_pengeluaran_bulan)

    data_saldo = [
        data_pemasukan[i] - data_pengeluaran[i]
        for i in range(len(data_pemasukan))
    ]

    # =========================
    # CONTEXT FINAL
    # =========================
    context = {
        'total_kamar': total_kamar,
        'kamar_terisi': kamar_terisi,
        'kamar_kosong': kamar_kosong,
        'total_penyewa': total_penyewa,

        'total_pemasukan': total_pemasukan,
        'total_pengeluaran': total_pengeluaran,
        'saldo_kos': saldo_kos,

        'jumlah_telat': jumlah_telat,
        'telat_list': telat_list,

        'chart_labels': labels,
        'chart_pemasukan': data_pemasukan,
        'chart_pengeluaran': data_pengeluaran,
        'chart_saldo': data_saldo,

        # 🔥 TAMBAHAN BARU
        'harga': harga,
    }

    return render(request, 'kos/dashboard.html', context)
# DATA KAMAR
@login_required
def daftar_kamar(request):
    kamar = Kamar.objects.all()
    penyewa = Penyewa.objects.filter(status="Aktif")

    return render(request, 'kos/kamar.html', {
        'kamar': kamar,
        'penyewa': penyewa
    })

# DATA PENYEWA
@login_required
def daftar_penyewa(request):
    penyewa = Penyewa.objects.select_related('kamar').prefetch_related('fasilitas').all()

    return render(request, 'kos/penyewa.html', {
        'penyewa': penyewa
    })

@login_required
def detail_penyewa(request, id):
    penyewa = Penyewa.objects.get(id=id)

    return render(request, 'kos/detail_penyewa.html', {
        'penyewa': penyewa
    })

@login_required
def riwayat_penyewa(request):

    penyewa = Penyewa.objects.filter(status="Keluar")

    context = {
        'penyewa': penyewa
    }

    return render(request, 'kos/riwayat_penyewa.html', context)

# DATA TAGIHAN
@login_required
def daftar_tagihan(request):

    data = Tagihan.objects.all().order_by('tahun', 'bulan')

    # KONVERSI BULAN KE INDONESIA
    bulan_convert = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember"
    }

    grouped = defaultdict(list)

    for t in data:
    # CONVERT BULAN DI SINI
        bulan = bulan_convert.get(t.bulan, t.bulan)

        key = f"{bulan} {t.tahun}"
        grouped[key].append(t)

    context = {
        'grouped_tagihan': dict(grouped)
    }

    return render(request, 'kos/tagihan.html', context)

@login_required
def detail_tagihan(request, id):
    tagihan = Tagihan.objects.get(id=id)

    return render(request, 'kos/detail_tagihan.html', {
        'tagihan': tagihan,
        'wifi': tagihan.wifi,
        'ac': tagihan.ac,
        'kipas': tagihan.kipas_angin,
        'rice': tagihan.rice_cooker,
    })


# DATA PEMBAYARAN
@login_required
def daftar_pembayaran(request):

    # =========================
    # SIMPAN PEMBAYARAN (POST)
    # =========================
    if request.method == 'POST':
        tagihan_id = request.POST.get('tagihan')
        jumlah_bayar = request.POST.get('jumlah_bayar')

        if tagihan_id and jumlah_bayar:

            tagihan = Tagihan.objects.get(id=tagihan_id)

            jumlah_bayar = int(jumlah_bayar)

            # =========================
            # SIMPAN PEMBAYARAN
            # =========================
            Pembayaran.objects.create(
                tagihan=tagihan,
                tanggal_bayar=timezone.now(),
                jumlah_bayar=jumlah_bayar
            )

            # =========================
            # REFRESH DATA TAGIHAN
            # =========================
            tagihan.refresh_from_db()

            # =========================
            # UPDATE STATUS
            # =========================
            if tagihan.dibayar >= tagihan.total:
                tagihan.status = "Lunas"

            elif tagihan.dibayar > 0:
                tagihan.status = "Masih Utang"

            else:
                tagihan.status = "Belum Bayar"

            tagihan.save()

            return redirect('/pembayaran/')

    # =========================
    # DATA
    # =========================
    bulan_convert = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember"
    }

    urutan = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ]

    tagihan = Tagihan.objects.filter(
        status__in=['Belum Bayar','Masih Utang']
    )

    grouped = defaultdict(list)

    for t in tagihan:
        bulan = bulan_convert.get(t.bulan, t.bulan)
        key = f"{bulan} {t.tahun}"
        grouped[key].append(t)

    grouped_sorted = dict(sorted(
        grouped.items(),
        key=lambda x: urutan.index(x[0].split()[0])
    ))

    selected_tagihan = None

    if grouped_sorted:
        last_bulan = list(grouped_sorted.keys())[-1]
        selected_tagihan = grouped_sorted[last_bulan][0].id

    pembayaran = Pembayaran.objects.select_related('tagihan__penyewa')

    for p in pembayaran:
        bulan_asli = p.tagihan.bulan
        p.tagihan.bulan = bulan_convert.get(bulan_asli, bulan_asli)

    context = {
        'grouped_tagihan': grouped_sorted,
        'pembayaran': pembayaran,
        'selected_tagihan': selected_tagihan
    }

    return render(request, 'kos/pembayaran.html', context)

@login_required
def hapus_pembayaran(request, id):
    pembayaran = Pembayaran.objects.get(id=id)
    pembayaran.delete()
    return redirect('/pembayaran/')

# TAMBAH KAMAR
@login_required
def tambah_kamar(request):

    if request.method == 'POST':

        nomor = request.POST['nomor_kamar']
        harga = request.POST['harga']
        status = request.POST['status']

        Kamar.objects.create(
            nomor_kamar=nomor,
            harga=harga,
            status=status
        )

        return redirect('/kamar/')

    return render(request, 'kos/tambah_kamar.html')

@login_required
def hapus_kamar(request, id):

    kamar = Kamar.objects.get(id=id)

    kamar.delete()

    return redirect('/kamar/')

@login_required
def edit_kamar(request, id):

    kamar = Kamar.objects.get(id=id)

    if request.method == 'POST':
        kamar.nomor_kamar = request.POST['nomor_kamar']
        kamar.harga = request.POST['harga']
        kamar.status = request.POST['status']

        kamar.save()

        return redirect('/kamar/')

    context = {
        'kamar': kamar
    }

    return render(request, 'kos/edit_kamar.html', context)

@login_required
def tambah_penyewa(request):

    kamar = Kamar.objects.filter(status='Kosong')
    fasilitas = Fasilitas.objects.all()

    if request.method == 'POST':

        nama = request.POST['nama']
        no_hp = request.POST['no_hp']
        nik = request.POST['nik']
        kamar_id = request.POST['kamar']
        tanggal = request.POST['tanggal_masuk']

        # 🔥 LOGIN
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, "Username & password wajib diisi!")
            return redirect('/tambah-penyewa/')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan!")
            return redirect('/tambah-penyewa/')

        user = User.objects.create_user(
            username=username,
            password=password
        )

        fasilitas_ids = request.POST.getlist('fasilitas')
        foto_ktp = request.FILES.get('foto_ktp')

        kamar_obj = Kamar.objects.get(id=kamar_id)

        penyewa = Penyewa.objects.create(
            user=user,  # 🔥 PENTING
            nama=nama,
            no_hp=no_hp,
            nik=nik,
            foto_ktp=foto_ktp,
            kamar=kamar_obj,
            tanggal_masuk=tanggal,
            status="Aktif"
        )

        penyewa.fasilitas.set(fasilitas_ids)

        kamar_obj.status = "Terisi"
        kamar_obj.save()

        return redirect('/penyewa/')

    return render(request, 'kos/tambah_penyewa.html', {
        'kamar': kamar,
        'fasilitas': fasilitas
    })
@login_required
def pilih_kamar(request):
    penyewa = Penyewa.objects.get(user=request.user)

    #  kalau sudah punya kamar → gak boleh pilih lagi
    if penyewa.kamar:
        messages.warning(request, "Kamu sudah memiliki kamar!")
        return redirect('dashboard_penyewa')

    kamar_list = Kamar.objects.filter(status='Kosong')

    if request.method == 'POST':
        kamar_id = request.POST.get('kamar')
        kamar = Kamar.objects.get(id=kamar_id)

        penyewa.kamar = kamar
        penyewa.status = "Aktif"
        penyewa.save()

        kamar.status = "Terisi"
        kamar.save()

        messages.success(request, "Kamar berhasil dipilih!")
        return redirect('dashboard_penyewa')

    return render(request, 'kos/pilih_kamar.html', {
        'kamar_list': kamar_list
    })

@login_required
def pindah_kamar(request):
    penyewa = Penyewa.objects.get(user=request.user)

    kamar_list = Kamar.objects.filter(status='Kosong')

    if request.method == 'POST':
        kamar_id = request.POST.get('kamar')
        kamar_baru = Kamar.objects.get(id=kamar_id)

        # kosongkan kamar lama
        if penyewa.kamar:
            penyewa.kamar.status = "Kosong"
            penyewa.kamar.save()

        # isi kamar baru
        penyewa.kamar = kamar_baru
        kamar_baru.status = "Terisi"

        penyewa.save()
        kamar_baru.save()

        messages.success(request, "Berhasil pindah kamar!")
        return redirect('dashboard_penyewa')

    return render(request, 'kos/pindah_kamar.html', {
        'kamar_list': kamar_list
    })

# EDIT PENYEWA
@login_required
def edit_penyewa(request, id):

    penyewa = Penyewa.objects.get(id=id)
    fasilitas = Fasilitas.objects.all()

    # kamar logic
    if penyewa.kamar:
        kamar = Kamar.objects.filter(status='Kosong') | Kamar.objects.filter(id=penyewa.kamar.id)
    else:
        kamar = Kamar.objects.filter(status='Kosong')

    if request.method == 'POST':

        penyewa.nama = request.POST.get('nama')
        penyewa.no_hp = request.POST.get('no_hp')

        kamar_id = request.POST.get('kamar')
        kamar_baru = Kamar.objects.get(id=kamar_id)
        penyewa.kamar = kamar_baru

        # tanggal masuk
        tanggal_masuk = request.POST.get('tanggal_masuk')
        if tanggal_masuk:
            penyewa.tanggal_masuk = tanggal_masuk

        # tanggal keluar
        tanggal_keluar = request.POST.get('tanggal_keluar')
        if tanggal_keluar:
            penyewa.tanggal_keluar = tanggal_keluar
        else:
            penyewa.tanggal_keluar = None

        # 🔥 update fasilitas
        fasilitas_ids = request.POST.getlist('fasilitas')
        penyewa.fasilitas.set(fasilitas_ids)

        penyewa.save()

        return redirect('/penyewa/')

    context = {
        'penyewa': penyewa,
        'kamar': kamar,
        'fasilitas': fasilitas
    }

    return render(request, 'kos/edit_penyewa.html', context)

# HAPUS PENYEWA
@login_required
def hapus_penyewa(request, id):

    penyewa = Penyewa.objects.get(id=id)

    kamar = penyewa.kamar

    # kamar kembali kosong
    kamar.status = "Kosong"
    kamar.save()

    penyewa.delete()

    return redirect('/penyewa/')

@login_required
def keluar_penyewa(request, id):

    penyewa = Penyewa.objects.get(id=id)

    penyewa.status = "Keluar"
    penyewa.tanggal_keluar = date.today()
    penyewa.save()

    # kamar jadi kosong
    kamar = penyewa.kamar
    kamar.status = "Kosong"
    kamar.save()

    return redirect('/penyewa/')

@login_required
def daftar_pengeluaran(request):

    bulan = request.GET.get('bulan')
    tahun = request.GET.get('tahun')

    pengeluaran = Pengeluaran.objects.all().order_by('-tanggal')

    # FILTER
    if bulan and tahun:
        pengeluaran = pengeluaran.filter(
            tanggal__month=int(bulan),
            tanggal__year=int(tahun)
        )
    elif tahun:
        pengeluaran = pengeluaran.filter(
            tanggal__year=int(tahun)
        )

    total_pengeluaran = pengeluaran.aggregate(
        total=Sum('jumlah')
    )['total'] or 0

    # 🔥 INI YANG PENTING (AMBIL SEMUA TAHUN DARI DATA)
    tahun_list = Pengeluaran.objects.dates('tanggal', 'year')

    context = {
        'pengeluaran': pengeluaran,
        'total_pengeluaran': total_pengeluaran,
        'bulan': bulan,
        'tahun': tahun,
        'tahun_list': tahun_list,
    }

    return render(request, 'kos/pengeluaran.html', context)

@login_required
def tambah_pengeluaran(request):

    if request.method == 'POST':

        tanggal = request.POST.get('tanggal')
        kategori = request.POST.get('kategori')
        keterangan = request.POST.get('keterangan')
        jumlah = request.POST.get('jumlah')

        # 🔥 VALIDASI
        if not keterangan:
            return HttpResponse("Keterangan tidak boleh kosong!")

        Pengeluaran.objects.create(
            tanggal=tanggal,
            kategori=kategori,
            keterangan=keterangan,
            jumlah=jumlah
        )

        return redirect('/pengeluaran/')

    return render(request, 'kos/tambah_pengeluaran.html')

@login_required
def laporan_keuangan(request):

    bulan_inggris_ke_indo = {
        "January": "Januari", "February": "Februari", "March": "Maret",
        "April": "April", "May": "Mei", "June": "Juni",
        "July": "Juli", "August": "Agustus", "September": "September",
        "October": "Oktober", "November": "November", "December": "Desember"
    }

    # 🔥 DIUBAH: Mengambil semua tagihan yang sudah ada uang masuk (dibayar lebih besar dari 0)
    tagihan = Tagihan.objects.filter(dibayar__gt=0)
    pengeluaran = Pengeluaran.objects.all()

    grouped = defaultdict(lambda: {
        "pemasukan": [],
        "pengeluaran": [],
        "total_pemasukan": 0,
        "total_pengeluaran": 0,
        "saldo": 0
    })

    # =========================
    # PEMASUKAN
    # =========================
    for t in tagihan:
        bulan = bulan_inggris_ke_indo.get(t.bulan, t.bulan)
        key = f"{bulan} {t.tahun}"

        grouped[key]["pemasukan"].append(t)
        # 🔥 DIUBAH: Yang dijumlahkan ke total pemasukan laporan adalah nominal 'dibayar' (cicilannya)
        grouped[key]["total_pemasukan"] += t.dibayar

    # =========================
    # PENGELUARAN
    # =========================
    for p in pengeluaran:
        bulan_en = p.tanggal.strftime("%B")
        bulan = bulan_inggris_ke_indo.get(bulan_en, bulan_en)
        key = f"{bulan} {p.tanggal.year}"

        grouped[key]["pengeluaran"].append(p)
        grouped[key]["total_pengeluaran"] += p.jumlah

    # =========================
    # HITUNG SALDO PER BULAN
    # =========================
    for key in grouped:
        grouped[key]["saldo"] = (
            grouped[key]["total_pemasukan"] -
            grouped[key]["total_pengeluaran"]
        )

    context = {
        "grouped": dict(grouped)
    }

    return render(request, 'kos/laporan_keuangan.html', context)

def format_rupiah(angka):
    return "Rp {:,}".format(angka).replace(",", ".")

# 🔥 mapping bulan (lowercase biar aman)
bulan_indo = {
    "january": "Januari",
    "february": "Februari",
    "march": "Maret",
    "april": "April",
    "may": "Mei",
    "june": "Juni",
    "july": "Juli",
    "august": "Agustus",
    "september": "September",
    "october": "Oktober",
    "november": "November",
    "december": "Desember"
}

@login_required
def download_pdf(request):
    # 1. AMBIL FILTER DARI URL
    bulan = request.GET.get('bulan')
    tahun = request.GET.get('tahun')

    if bulan in ["None", ""]: bulan = None
    if tahun in ["None", ""]: tahun = None

    # 2. AMBIL DATA
    pembayaran = Pembayaran.objects.all()
    pengeluaran = Pengeluaran.objects.all()

    # 3. FILTER DATA JIKA ADA
    if bulan and tahun:
        bulan_angka_ke_nama = {
            "1": "Januari", "2": "Februari", "3": "Maret", "4": "April", 
            "5": "Mei", "6": "Juni", "7": "Juli", "8": "Agustus", 
            "9": "September", "10": "Oktober", "11": "November", "12": "Desember"
        }
        bulan_nama = bulan_angka_ke_nama.get(bulan)
        pembayaran = pembayaran.filter(tagihan__bulan=bulan_nama, tagihan__tahun=int(tahun))
        pengeluaran = pengeluaran.filter(tanggal__month=int(bulan), tanggal__year=int(tahun))

    # 4. SETUP PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="laporan_keuangan_wisma24.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
    elements = []
    HIJAU = colors.HexColor('#059669')

    # 5. JUDUL (Perbaikan Leading & Space)
    style_header = ParagraphStyle('Header', fontSize=12, alignment=1, spaceAfter=10, leading=15)
    style_title = ParagraphStyle('Title', fontSize=16, alignment=1, spaceAfter=10, leading=20, fontName='Helvetica-Bold')
    style_period = ParagraphStyle('Period', fontSize=11, alignment=1, spaceAfter=25, leading=14)

    elements.append(Paragraph("WISMA 24", style_header))
    elements.append(Paragraph("Laporan Keuangan", style_title))
    
    label_bulan = bulan_angka_ke_nama.get(bulan) if bulan and 'bulan_angka_ke_nama' in locals() else "Seluruh Waktu"
    teks_periode = f"Periode yang Berakhir pada {label_bulan} {tahun if tahun else ''}"
    elements.append(Paragraph(teks_periode, style_period))
    
    # Garis Pembatas
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=30))

    # 6. STYLE TABEL
    style_tabel = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HIJAU),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
    ])

    # 7. TABEL PEMASUKAN
    elements.append(Paragraph("A. Data Pemasukan", ParagraphStyle('Sub', fontSize=12, fontName='Helvetica-Bold', spaceAfter=10)))
    data_pemasukan = [["No", "Nama Penyewa", "Tanggal", "Keterangan", "Jumlah"]]
    for i, p in enumerate(pembayaran, 1):
        data_pemasukan.append([
            i, 
            p.tagihan.penyewa.nama, 
            p.tanggal_bayar.strftime('%d-%m-%Y'), 
            p.tagihan.status, 
            format_rupiah(p.jumlah_bayar)
        ])
    
    tabel = Table(data_pemasukan, colWidths=[30, 130, 80, 80, 80])
    tabel.setStyle(style_tabel)
    elements.append(tabel)
    elements.append(Spacer(1, 20))

    # 8. TABEL PENGELUARAN
    elements.append(Paragraph("B. Data Pengeluaran", ParagraphStyle('Sub', fontSize=12, fontName='Helvetica-Bold', spaceAfter=10)))
    data_pengeluaran = [["No", "Tanggal", "Keterangan", "Jumlah"]]
    for i, p in enumerate(pengeluaran, 1):
        data_pengeluaran.append([i, p.tanggal.strftime('%d-%m-%Y'), p.keterangan, format_rupiah(p.jumlah)])
    
    tabel_p = Table(data_pengeluaran, colWidths=[30, 80, 200, 90])
    tabel_p.setStyle(style_tabel)
    elements.append(tabel_p)
    
    doc.build(elements)
    return response

@login_required
def edit_tagihan(request, id):
    tagihan = Tagihan.objects.get(id=id)

    if request.method == 'POST':
        tagihan.bulan = request.POST['bulan']
        tagihan.tahun = request.POST['tahun']

        jatuh_tempo_str = request.POST.get('jatuh_tempo')
        if jatuh_tempo_str:
            tagihan.jatuh_tempo = datetime.strptime(jatuh_tempo_str, '%Y-%m-%d').date()
        else:
            tagihan.jatuh_tempo = None

        dibayar = int(request.POST['dibayar'])
        tagihan.dibayar = dibayar

        penyewa = tagihan.penyewa

        tagihan.total = hitung_total_tagihan(penyewa)

        if dibayar >= tagihan.total:
            tagihan.status = "Lunas"
        elif dibayar > 0:
            tagihan.status = "Masih Utang"
        else:
            tagihan.status = "Belum Bayar"

        tagihan.save()
        return redirect('/tagihan/')

    return render(request, 'kos/edit_tagihan.html', {'tagihan': tagihan})

@login_required   
def hapus_tagihan(request, id):

    tagihan = Tagihan.objects.get(id=id)
    tagihan.delete()

    return redirect('/tagihan/')

@login_required
def tambah_tagihan(request):
    if request.method == 'POST':
        penyewa_id = request.POST.get('penyewa')
        bulan = request.POST.get('bulan')
        tahun = int(request.POST.get('tahun'))

        # cek duplikat
        if Tagihan.objects.filter(penyewa_id=penyewa_id, bulan=bulan, tahun=tahun).exists():
            messages.error(request, "Tagihan sudah ada!")
            return redirect('/tambah-tagihan/')

        penyewa = Penyewa.objects.get(id=penyewa_id)

        # jatuh tempo
        jatuh_tempo_str = request.POST.get('jatuh_tempo')
        jatuh_tempo = datetime.strptime(jatuh_tempo_str, '%Y-%m-%d').date() if jatuh_tempo_str else None

        # =========================
        # AMBIL HARGA MASTER
        # =========================
        harga = HargaFasilitas.objects.first()

        wifi = ac = kipas = rice = 0

        # =========================
        # HITUNG FASILITAS
        # =========================
        for f in penyewa.fasilitas.all():
            nama = f.nama.strip().lower()

            if "wifi" in nama:
                wifi = harga.wifi if harga else 0

            elif "ac" in nama:
                ac = harga.ac if harga else 0

            elif "kipas" in nama:
                kipas = harga.kipas_angin if harga else 0

            elif "rice" in nama:
                rice = harga.rice_cooker if harga else 0

        total_fasilitas = wifi + ac + kipas + rice

        # =========================
        # BIAYA KAMAR
        # =========================
        biaya_kamar = penyewa.kamar.harga if penyewa.kamar else 0

        # =========================
        # TOTAL
        # =========================
        total = biaya_kamar + total_fasilitas

        # =========================
        # SIMPAN TAGIHAN
        # =========================
        Tagihan.objects.create(
            penyewa=penyewa,
            bulan=bulan,
            tahun=tahun,
            biaya_kamar=biaya_kamar,
            listrik=0,
            air=0,
            wifi=wifi,
            ac=ac,
            rice_cooker=rice,
            kipas_angin=kipas,
            jatuh_tempo=jatuh_tempo,
            total=total,
            status="Belum Bayar"
        )

        messages.success(request, "Tagihan berhasil dibuat otomatis!")
        return redirect('/tagihan/')

    return render(request, 'kos/tambah_tagihan.html', {
        'penyewa': Penyewa.objects.all()
    })

@login_required
def tagihan_penyewa(request):
    try:
        penyewa = Penyewa.objects.get(user=request.user)
    except Penyewa.DoesNotExist:
        return redirect('dashboard')

    tagihan = Tagihan.objects.filter(penyewa=penyewa).order_by('-tahun', '-bulan')

    return render(request, 'kos/tagihan_penyewa.html', {
        'tagihan': tagihan
    })

@login_required
def edit_pengeluaran(request, id):
    data = Pengeluaran.objects.get(id=id)

    if request.method == "POST":
        data.tanggal = request.POST['tanggal']
        data.kategori = request.POST['kategori']
        data.keterangan = request.POST['keterangan']
        data.jumlah = request.POST['jumlah']
        data.save()
        return redirect('/pengeluaran/')

    return render(request, 'kos/edit_pengeluaran.html', {'data': data})

@login_required
def hapus_pengeluaran(request, id):

    data = Pengeluaran.objects.get(id=id)
    data.delete()

    return redirect('/pengeluaran/')

from datetime import date

def generate_tagihan_otomatis():
    today = date.today()
    bulan = today.strftime("%B")
    tahun = today.year

    harga = HargaFasilitas.objects.first()

    if not harga:
        harga = HargaFasilitas.objects.create(
            wifi=50000,
            ac=0,
            kipas_angin=0,
            rice_cooker=0
        )

    # Hanya penyewa aktif yang masuk sebelum bulan berjalan
    penyewa_list = Penyewa.objects.filter(
        status="Aktif",
        kamar__isnull=False,
        tanggal_masuk__lt=date(today.year, today.month, 1)
    )

    for penyewa in penyewa_list:

        sudah_ada = Tagihan.objects.filter(
            penyewa=penyewa,
            bulan=bulan,
            tahun=tahun
        ).exists()

        if not sudah_ada:

            biaya_kamar = penyewa.kamar.harga
            listrik = 50000
            air = 30000

            Tagihan.objects.create(
                penyewa=penyewa,
                bulan=bulan,
                tahun=tahun,
                biaya_kamar=biaya_kamar,
                listrik=listrik,
                air=air,
                jatuh_tempo=date(tahun, today.month, 5)
            )
# =========================
# LOGIN ADMIN
# =========================
def login_view(request):
    # Cek apakah sudah login sebagai user biasa (bukan penyewa)
    if request.user.is_authenticated:
        if hasattr(request.user, 'penyewa'):
            return redirect('dashboard_penyewa')
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            # Pastikan admin tidak bisa login di sini jika dia sebenarnya penyewa
            if not hasattr(user, 'penyewa'):
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Gunakan halaman login penyewa!')
        else:
            messages.error(request, 'Username atau password salah!')

    return render(request, 'kos/login.html')


def login_penyewa(request):
    # Cek apakah sudah login
    if request.user.is_authenticated:
        if hasattr(request.user, 'penyewa'):
            return redirect('dashboard_penyewa')
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            if hasattr(user, 'penyewa'):
                login(request, user)
                return redirect('dashboard_penyewa')
            else:
                messages.error(request, 'Akun ini bukan penyewa!')
        else:
            messages.error(request, 'Username atau password salah!')

    return render(request, 'kos/login_penyewa.html')


def logout_view(request):
    # Kita cek dulu tipe user-nya sebelum logout untuk menentukan arah redirect
    is_penyewa = hasattr(request.user, 'penyewa')
    logout(request)
    messages.success(request, 'Anda berhasil logout!')
    
    if is_penyewa:
        return redirect('login_penyewa')
    return redirect('login') # Ganti 'login' dengan nama url login admin Anda


# =========================
# DASHBOARD PENYEWA
# =========================
@login_required
def dashboard_penyewa(request):
    try:
        penyewa = Penyewa.objects.get(user=request.user)
    except Penyewa.DoesNotExist:
        return redirect('dashboard')

    # 🔥 CEK STATUS AKUN
    if penyewa.status == "Pending":
        messages.warning(request, "Akun Anda belum diaktifkan oleh admin!")
        return render(request, 'kos/dashboard_penyewa.html', {
            'penyewa': penyewa,
            'pending': True
        })

    # 🔥 DATA TAGIHAN
    tagihan = Tagihan.objects.filter(
        penyewa=penyewa
    ).order_by('-tahun', '-bulan')

    # 🔥 DATA PINDAH KAMAR
    request_pindah = RequestPindahKamar.objects.filter(
        penyewa=penyewa
    ).order_by('-id')

    # 🔥 CONTEXT FINAL
    context = {
        'penyewa': penyewa,
        'tagihan': tagihan,
        'request_pindah': request_pindah,
        'pending': False
    }

    return render(request, 'kos/dashboard_penyewa.html', context)

def register_penyewa(request):
    if request.method == 'POST':
        nama = request.POST.get('nama')
        username = request.POST.get('username')
        password = request.POST.get('password')
        tanggal_masuk = request.POST.get('tanggal_masuk')

        # 🔥 VALIDASI INPUT
        if not nama or not username or not password or not tanggal_masuk:
            messages.error(request, "Semua field wajib diisi!")
            return redirect('register_penyewa')

        # VALIDASI USERNAME
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan!")
            return redirect('register_penyewa')

        # BUAT USER
        user = User.objects.create_user(
            username=username,
            password=password
        )

        # 🔥 BUAT PENYEWA (BELUM AKTIF & BELUM PUNYA KAMAR)
        Penyewa.objects.create(
            user=user,
            nama=nama,
            tanggal_masuk=tanggal_masuk,
            status="Pending"
        )

        messages.success(request, "Registrasi berhasil! Tunggu persetujuan admin.")
        return redirect('login_penyewa')

    return render(request, 'kos/register_penyewa.html')

@login_required
def pilih_fasilitas(request):
    penyewa = Penyewa.objects.get(user=request.user)
    fasilitas = Fasilitas.objects.all()

    if request.method == 'POST':
        fasilitas_ids = request.POST.getlist('fasilitas')

        # simpan pilihan fasilitas
        penyewa.fasilitas.set(fasilitas_ids)
        penyewa.save()

        # 🔥 AUTO UPDATE TAGIHAN
        harga = HargaFasilitas.objects.first()

        total_fasilitas = 0

        if harga:
            for f in penyewa.fasilitas.all():
                if f.nama == "WiFi":
                    total_fasilitas += harga.wifi
                elif f.nama == "AC":
                    total_fasilitas += harga.ac
                elif f.nama == "Kipas Angin":
                    total_fasilitas += harga.kipas_angin
                elif f.nama == "Rice Cooker":
                    total_fasilitas += harga.rice_cooker

        # update semua tagihan penyewa ini
        tagihan_list = Tagihan.objects.filter(penyewa=penyewa)

        for tagihan in tagihan_list:
            biaya_kamar = penyewa.kamar.harga if penyewa.kamar else 0

            tagihan.total = (
                biaya_kamar +
                tagihan.listrik +
                tagihan.air +
                total_fasilitas
            )

            tagihan.save()

        messages.success(request, "Fasilitas & tagihan berhasil diperbarui!")
        return redirect('dashboard_penyewa')

    return render(request, 'kos/pilih_fasilitas.html', {
        'penyewa': penyewa,
        'fasilitas': fasilitas
    })

@login_required
def pembayaran_penyewa(request):
    penyewa = Penyewa.objects.get(user=request.user)

    pembayaran = Pembayaran.objects.filter(
        tagihan__penyewa=penyewa
    )

    return render(request, 'kos/pembayaran_penyewa.html', {
        'pembayaran': pembayaran
    })

@login_required
def update_harga_fasilitas(request):
    harga, created = HargaFasilitas.objects.get_or_create(id=1)

    if request.method == "POST":
        harga.wifi = int(request.POST.get("wifi") or 0)
        harga.ac = int(request.POST.get("ac") or 0)
        harga.kipas_angin = int(request.POST.get("kipas_angin") or 0)
        harga.rice_cooker = int(request.POST.get("rice_cooker") or 0)
        harga.save()

        # 🔥 UPDATE SEMUA TAGIHAN
        for tagihan in Tagihan.objects.all():
            tagihan.total = hitung_total_tagihan(tagihan.penyewa)
            tagihan.save()

        return redirect('dashboard')

    return redirect('dashboard')

@login_required
def harga_fasilitas(request):
    harga, created = HargaFasilitas.objects.get_or_create(id=1)

    return render(request, 'kos/harga_fasilitas.html', {
        'harga': harga
    })

def hitung_total_tagihan(penyewa):
    harga = HargaFasilitas.objects.first()

    wifi = ac = kipas = rice = 0

    if harga:
        for f in penyewa.fasilitas.all():
            nama = f.nama.lower()

            if "wifi" in nama:
                wifi = harga.wifi
            elif "ac" in nama:
                ac = harga.ac
            elif "kipas" in nama:
                kipas = harga.kipas_angin
            elif "rice" in nama:
                rice = harga.rice_cooker

    biaya_kamar = penyewa.kamar.harga if penyewa.kamar else 0

    return biaya_kamar + wifi + ac + kipas + rice

@login_required
def update_harga_fasilitas(request):
    harga, created = HargaFasilitas.objects.get_or_create(id=1)

    if request.method == "POST":
        harga.wifi = int(request.POST.get("wifi") or 0)
        harga.ac = int(request.POST.get("ac") or 0)
        harga.kipas_angin = int(request.POST.get("kipas_angin") or 0)
        harga.rice_cooker = int(request.POST.get("rice_cooker") or 0)
        harga.save()

        # AUTO UPDATE SEMUA TAGIHAN
        for tagihan in Tagihan.objects.all():
            penyewa = tagihan.penyewa
            wifi = ac = kipas = rice = 0

            for f in penyewa.fasilitas.all():
                nama = f.nama.lower()
                if "wifi" in nama: wifi = harga.wifi
                elif "ac" in nama: ac = harga.ac
                elif "kipas" in nama: kipas = harga.kipas_angin
                elif "rice" in nama: rice = harga.rice_cooker

            tagihan.wifi = wifi
            tagihan.ac = ac
            tagihan.kipas_angin = kipas
            tagihan.rice_cooker = rice
            tagihan.total = (
                tagihan.biaya_kamar +
                tagihan.listrik +
                tagihan.air +
                wifi + ac + kipas + rice
            )
            tagihan.save()

        # Tambahkan notifikasi sukses
        messages.success(request, 'Harga fasilitas berhasil diperbarui!')
        
        # Arahkan kembali ke manajemen fasilitas, bukan dashboard
        return redirect('manajemen_fasilitas')

    return redirect('manajemen_fasilitas')
@login_required
def profil_penyewa(request):
    try:
        penyewa = Penyewa.objects.get(user=request.user)
    except Penyewa.DoesNotExist:
        return redirect('dashboard')

    if request.method == 'POST':
        penyewa.no_hp = request.POST.get('no_hp')
        penyewa.nik = request.POST.get('nik')

        if request.FILES.get('foto_ktp'):
            penyewa.foto_ktp = request.FILES.get('foto_ktp')

        penyewa.save()

        # 🔥 NOTIFIKASI
        messages.success(request, "Profil berhasil disimpan!")

        return redirect('profil_penyewa')

    return render(request, 'kos/profil_penyewa.html', {
        'penyewa': penyewa
    })

@login_required
def ajukan_pindah_kamar(request):
    penyewa = get_object_or_404(Penyewa, user=request.user)

    kamar_list = Kamar.objects.filter(status='Kosong')

    if request.method == 'POST':
        kamar_id = request.POST.get('kamar')

        if not kamar_id:
            messages.error(request, "Pilih kamar terlebih dahulu!")
            return redirect('ajukan_pindah')

        kamar = get_object_or_404(Kamar, id=kamar_id)

        # CEK SUDAH ADA REQUEST PENDING
        if RequestPindahKamar.objects.filter(
            penyewa=penyewa,
            status='Pending'
        ).exists():
            messages.error(request, "Kamu masih punya pengajuan yang belum diproses!")
            return redirect('dashboard_penyewa')

        RequestPindahKamar.objects.create(
            penyewa=penyewa,
            kamar_tujuan=kamar,
            status='Pending'
        )

        messages.success(request, "Pengajuan pindah kamar berhasil dikirim!")
        return redirect('dashboard_penyewa')

    return render(request, 'kos/ajukan_pindah.html', {
        'kamar_list': kamar_list
    })


# =========================
# APPROVAL ADMIN
# =========================
@login_required
def approval_kamar(request):

    pending = RequestPindahKamar.objects.all()
    riwayat = RequestPindahKamar.objects.all()

    return render(request, 'kos/approval_kamar.html', {
        'pending': pending,
        'riwayat': riwayat
    })

# =========================
# SETUJUI PINDAH KAMAR
# =========================
@login_required
def setujui_kamar(request, id):
    req = get_object_or_404(RequestPindahKamar, id=id)

    penyewa = req.penyewa
    kamar_baru = req.kamar_tujuan

    # KAMAR LAMA -> KOSONG
    if penyewa.kamar:
        kamar_lama = penyewa.kamar
        kamar_lama.status = "Kosong"
        kamar_lama.save()

    # KAMAR BARU -> TERISI
    kamar_baru.status = "Terisi"
    kamar_baru.save()

    # UPDATE PENYEWA
    penyewa.kamar = kamar_baru
    penyewa.save()

    # UPDATE REQUEST
    req.status = "Disetujui"
    req.save()

    # --- TAMBAHAN: OTOMATIS TAMBAH BIAYA PINDAH KE TAGIHAN AKTIF ---
    tagihan_aktif = Tagihan.objects.filter(
        penyewa=penyewa, 
        status__in=['Belum Bayar', 'Masih Utang']
    ).first()
    
    if tagihan_aktif:
        tagihan_aktif.biaya_pindah = 50000
        tagihan_aktif.save()  # Ini akan memicu fungsi save() di model Tagihan untuk menghitung ulang total, sisa, dan status secara otomatis!
    # -------------------------------------------------------------

    messages.success(request, "Pindah kamar disetujui dan biaya administrasi telah ditambahkan ke tagihan!")
    return redirect('approval_kamar')

# =========================
# TOLAK PINDAH KAMAR
# =========================
@login_required
def tolak_kamar(request, id):
    req = get_object_or_404(RequestPindahKamar, id=id)

    req.status = "Ditolak"
    req.save()

    messages.error(request, "Pengajuan ditolak!")
    return redirect('approval_kamar')

@login_required
def grafik(request):

    bulan_convert = {
        "January": "Januari", "February": "Februari", "March": "Maret",
        "April": "April", "May": "Mei", "June": "Juni",
        "July": "Juli", "August": "Agustus",
        "September": "September", "October": "Oktober",
        "November": "November", "December": "Desember"
    }

    bulan_map = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }

    urutan = [
        "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ]

    pemasukan = Tagihan.objects.filter(status='Lunas') \
        .values('bulan') \
        .annotate(total=Sum('total'))

    pengeluaran = Pengeluaran.objects.values('tanggal__month') \
        .annotate(total=Sum('jumlah'))

    labels = []
    data_pemasukan = []
    data_pengeluaran = []

    for bulan in urutan:

        labels.append(bulan)

        total_pemasukan = next(
            (x['total'] for x in pemasukan
             if bulan_convert.get(x['bulan'], x['bulan']) == bulan),
            0
        )

        total_pengeluaran = next(
            (x['total'] for x in pengeluaran
             if bulan_map.get(x['tanggal__month']) == bulan),
            0
        )

        data_pemasukan.append(total_pemasukan or 0)
        data_pengeluaran.append(total_pengeluaran or 0)

    data_saldo = [
        data_pemasukan[i] - data_pengeluaran[i]
        for i in range(len(urutan))
    ]

    context = {
        'chart_labels': json.dumps(labels),
        'chart_pemasukan': json.dumps(data_pemasukan),
        'chart_pengeluaran': json.dumps(data_pengeluaran),
        'chart_saldo': json.dumps(data_saldo),
        'total_pemasukan': sum(data_pemasukan),
        'total_pengeluaran': sum(data_pengeluaran),
    }

    return render(request, 'kos/grafik.html', context)

@login_required
def manajemen_fasilitas(request):

    harga = HargaFasilitas.objects.first()

    context = {
        'harga': harga
    }

    return render(request, 'kos/manajemen_fasilitas.html', context)

@login_required
def hapus_riwayat_pindah(request, id):
    data = get_object_or_404(RequestPindahKamar, id=id)

    data.delete()

    messages.success(request, "Riwayat berhasil dihapus!")

    return redirect('approval_kamar')

@login_required
def pembayaran_penyewa(request):
    return render(request, 'kos/pembayaran_penyewa.html')

@login_required
def upload_bukti_pembayaran(request, tagihan_id):
    tagihan = get_object_or_404(Tagihan, id=tagihan_id)
    
    if request.method == 'POST':
        jumlah_bayar = request.POST.get('jumlah_bayar')
        bukti_bayar = request.FILES.get('bukti_bayar')
        
        if jumlah_bayar and bukti_bayar:
            # Otomatis membuat data pembayaran baru yang langsung masuk ke admin
            Pembayaran.objects.create(
                tagihan=tagihan,
                jumlah_bayar=int(jumlah_bayar),
                bukti_bayar=bukti_bayar
            )
            
        return redirect('tagihan_penyewa')
# GPR Media Intelligence

**Platform Pengumpulan, Pengarsipan, Pemantauan, dan Analisis Pemberitaan Media Online untuk Kehumasan Pemerintah**



\


GPR Media Intelligence merupakan aplikasi berbasis web yang dikembangkan untuk mendukung kegiatan **Government Public Relations (GPR)** melalui pengumpulan dan pengelolaan pemberitaan dari berbagai media online secara terstruktur.

Aplikasi ini dirancang untuk membantu praktisi kehumasan pemerintah dalam memperoleh, menyimpan, menelusuri, dan memantau informasi pemberitaan yang berkaitan dengan pemerintah, kebijakan publik, program pembangunan, pelayanan masyarakat, serta isu-isu strategis lainnya.

Repositori ini dikembangkan secara bertahap dengan pendekatan modular agar dapat dipelajari, digunakan, disesuaikan, dan dikembangkan lebih lanjut oleh pengembang lain.

---

## 1. Latar Belakang

Media online merupakan salah satu sumber informasi penting dalam memahami perkembangan opini publik, pemberitaan kebijakan pemerintah, pelaksanaan program pembangunan, serta berbagai isu yang berkembang di masyarakat.

Banyaknya media dan jumlah pemberitaan yang terus bertambah menimbulkan tantangan tersendiri bagi pengelolaan informasi kehumasan, antara lain:

- Informasi tersebar di berbagai situs media online.
- Pengumpulan berita secara manual membutuhkan waktu dan tenaga.
- Arsip pemberitaan sering kali belum tersimpan dalam satu sistem terpusat.
- Penelusuran berita berdasarkan kata kunci, media, dan tanggal membutuhkan proses yang berulang.
- Riwayat pengumpulan berita dan sumber informasi perlu dikelola secara sistematis.
- Data pemberitaan perlu disiapkan agar dapat digunakan untuk pemantauan dan analisis lebih lanjut.

GPR Media Intelligence dikembangkan sebagai salah satu solusi untuk menjawab kebutuhan tersebut melalui sistem pengumpulan dan pengarsipan pemberitaan berbasis web.

## 2. Tujuan Proyek

Tujuan utama pengembangan GPR Media Intelligence adalah:

1. Mengotomatisasi pengumpulan pemberitaan dari berbagai media online.
2. Menyediakan pengelolaan sumber media yang fleksibel dan dapat dikonfigurasi.
3. Membangun arsip berita digital yang terstruktur dan berkelanjutan.
4. Memudahkan pencarian dan penelusuran pemberitaan berdasarkan kata kunci, sumber media, dan rentang tanggal.
5. Menyediakan fondasi data untuk pemantauan isu dan analisis pemberitaan.
6. Mendukung penyusunan laporan kehumasan berbasis data.
7. Menyediakan arsitektur aplikasi yang dapat dikembangkan oleh komunitas developer maupun institusi yang membutuhkan.

## 3. Ruang Lingkup dan Fitur

### 3.1. Fitur yang Telah Dikembangkan

**A. Pengelolaan Sumber Media**

- Menambahkan sumber media online secara manual.
- Menyimpan nama media, alamat situs, dan deskripsi sumber.
- Mengaktifkan atau menonaktifkan sumber media.
- Memvalidasi sumber media sebelum digunakan dalam proses pengumpulan berita.
- Menyimpan konfigurasi dan riwayat validasi sumber.
- Menggunakan konfigurasi validasi sebagai dasar pengumpulan berita berikutnya.

**B. Validasi Sumber Media**

Sistem melakukan pemeriksaan terhadap sumber media sebelum sumber tersebut digunakan.

Pemeriksaan mencakup:

- Ketersediaan dan aksesibilitas situs.
- Pemeriksaan `robots.txt`.
- Pencarian sitemap.
- Pencarian RSS atau Atom feed jika tersedia.
- Penemuan tautan artikel melalui halaman utama sebagai mekanisme alternatif.
- Identifikasi pola URL artikel.
- Ekstraksi metadata seperti judul, penulis, tanggal publikasi, dan isi artikel.
- Penyimpanan hasil validasi untuk digunakan kembali.

Validasi menggunakan mekanisme pembatasan akses URL dan pemeriksaan pengalihan untuk membantu mencegah permintaan menuju alamat jaringan yang tidak diperbolehkan.

**C. Pengumpulan Pemberitaan**

- Mengumpulkan kandidat artikel dari sumber media yang telah dikonfigurasi.
- Mendukung pemilihan sumber media sebelum proses pengumpulan.
- Mendukung pembatasan periode tanggal publikasi.
- Mengambil informasi artikel dari halaman sumber.
- Menggunakan mekanisme percobaan ulang (*retry*) ketika pengambilan artikel mengalami kegagalan.
- Membatasi jumlah artikel yang disimpan dalam satu proses sesuai konfigurasi collector.
- Mencatat hasil dan status proses pengumpulan.

**D. Pengarsipan Berita**

Artikel yang berhasil dikumpulkan disimpan dalam database lokal dengan informasi seperti:

- Sumber media.
- Judul berita.
- URL artikel asli.
- URL kanonis.
- Isi berita.
- Ringkasan jika tersedia.
- Penulis.
- Tanggal publikasi.
- Waktu pengumpulan.
- Hash konten.
- Status artikel.

Arsip dirancang agar dapat digunakan sebagai sumber data untuk proses pencarian, pemantauan, analisis, dan pelaporan berikutnya.

**E. Pengelolaan Duplikasi Artikel**

Sistem menerapkan kebijakan duplikasi berdasarkan URL kanonis dengan cakupan per sumber media.

Ketentuannya:

- URL kanonis yang sama dari sumber media yang sama tidak disimpan berulang kali.
- Artikel dengan URL berbeda dari media yang sama tetap dapat disimpan meskipun memiliki judul atau isi yang sama atau mirip.
- Artikel yang sama atau serupa dari media berbeda tetap disimpan sebagai pemberitaan dari masing-masing media.
- Hash konten disimpan sebagai informasi pendukung analisis, bukan sebagai dasar untuk menolak penyimpanan artikel.

Kebijakan ini penting untuk mempertahankan jejak pemberitaan lintas media.

**F. Pencarian dan Penelusuran Arsip**

- Pencarian artikel berdasarkan kata kunci.
- Penyaringan berdasarkan sumber media.
- Penyaringan berdasarkan rentang tanggal.
- Pengurutan berita berdasarkan tanggal terbaru atau terlama.
- Navigasi hasil pencarian melalui pagination.
- Tampilan detail artikel.
- Tautan menuju artikel asli pada situs media.

**G. Riwayat Proses Pengumpulan**

Sistem menyediakan pencatatan proses pengumpulan berita, termasuk informasi jumlah kandidat, artikel tersimpan, duplikasi, dan kegagalan proses.

### 3.2. Arah Pengembangan Selanjutnya

Fitur berikut merupakan arah pengembangan yang dapat ditambahkan pada tahap berikutnya, bukan klaim bahwa seluruhnya telah tersedia pada versi saat ini.

| Modul               | Rencana pengembangan                                                       |
| ------------------- | -------------------------------------------------------------------------- |
| Media Monitoring    | Pemantauan pemberitaan berdasarkan topik, isu, instansi, dan kata kunci    |
| Issue Detection     | Identifikasi isu yang sedang berkembang                                    |
| Trend Analysis      | Analisis tren pemberitaan berdasarkan waktu                                |
| Sentiment Analysis  | Klasifikasi sentimen pemberitaan                                           |
| Entity Extraction   | Identifikasi nama instansi, pejabat, lokasi, dan entitas terkait           |
| Media Analysis      | Analisis intensitas, distribusi, dan karakteristik pemberitaan antar-media |
| Dashboard Analytics | Visualisasi data dan indikator media intelligence                          |
| Reporting           | Pembuatan laporan harian, mingguan, dan bulanan                            |
| Export              | Ekspor data dan laporan ke format Excel, CSV, dan PDF                      |
| Notification        | Notifikasi untuk isu atau kata kunci tertentu                              |
| AI Integration      | Pemanfaatan AI untuk peringkasan dan analisis pemberitaan                  |
| API                 | Penyediaan antarmuka integrasi dengan sistem lain                          |
| Multi-user          | Pengelolaan pengguna, autentikasi, dan hak akses                           |

---

## 4. Teknologi yang Digunakan

GPR Media Intelligence menggunakan ekosistem Python untuk membangun aplikasi web dan proses pengumpulan data.

| Komponen           | Teknologi  | Fungsi                              |
| ------------------ | ---------- | ----------------------------------- |
| Bahasa pemrograman | Python     | Logika aplikasi dan pengolahan data |
| Web framework      | FastAPI    | Routing dan backend aplikasi        |
| ASGI server        | Uvicorn    | Menjalankan aplikasi web            |
| Template engine    | Jinja2     | Menampilkan halaman dashboard       |
| ORM                | SQLAlchemy | Pengelolaan database                |
| Database           | SQLite     | Penyimpanan arsip dan konfigurasi   |
| HTTP client        | HTTPX      | Komunikasi dengan situs media       |
| RSS parser         | Feedparser | Pembacaan RSS/Atom feed             |
| Testing            | Pytest     | Pengujian fungsi dan integrasi      |

Versi dependensi yang digunakan dapat dilihat pada `requirements.txt`.

## 5. Arsitektur Aplikasi

Secara konseptual, alur kerja aplikasi adalah sebagai berikut:

```text
                  MEDIA ONLINE
                       |
          +------------+------------+
          |            |            |
        RSS/Atom     Sitemap      Homepage
          |            |            |
          +------------+------------+
                       |
               URL DISCOVERY
                       |
               URL VALIDATION
                       |
              ARTICLE EXTRACTION
                       |
              DUPLICATE CHECK
                       |
                DATA STORAGE
                       |
                SQLITE DATABASE
                       |
          +------------+------------+
          |            |            |
       SEARCH       ARCHIVE      COLLECTION
       & FILTER      DETAIL        HISTORY
          |            |            |
          +------------+------------+
                       |
                WEB DASHBOARD
                       |
              FUTURE DEVELOPMENT
          MONITORING / ANALYTICS /
                REPORTING
```

Arsitektur dirancang secara modular agar proses penemuan URL, validasi sumber, ekstraksi artikel, penyimpanan data, dan penyajian informasi dapat dikembangkan secara terpisah.

## 6. Struktur Direktori

Struktur utama repositori:

```text
gpr-media-intelligence/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── collector.py
│   ├── database.py
│   ├── models.py
│   ├── source_validation.py
│   │
│   ├── source/
│   │
│   ├── static/
│   │
│   └── templates/
│
├── scripts/
│   └── ...
│
├── tests/
│   ├── test_collector.py
│   ├── test_collector_homepage.py
│   └── test_source_validation.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

Keterangan:

- `app/main.py` — entry point aplikasi web dan pengelolaan endpoint.
- `app/collector.py` — proses penemuan, pengambilan, ekstraksi, dan penyimpanan artikel.
- `app/database.py` — konfigurasi koneksi database.
- `app/models.py` — definisi model dan struktur tabel database.
- `app/source_validation.py` — validasi sumber media dan keamanan permintaan HTTP.
- `app/source/` — komponen yang berkaitan dengan pengelolaan sumber media.
- `app/templates/` — halaman HTML berbasis Jinja2.
- `app/static/` — aset frontend seperti CSS dan JavaScript.
- `scripts/` — skrip administrasi dan pemeliharaan aplikasi.
- `tests/` — pengujian otomatis.

Struktur ini dapat berkembang mengikuti penambahan modul dan kebutuhan aplikasi.

## 7. Persyaratan Sistem

Persyaratan untuk menjalankan aplikasi:

- Python dengan dukungan terhadap dependensi pada `requirements.txt`.
- Git.
- Terminal atau PowerShell.
- Browser modern.
- Koneksi internet untuk mengakses situs media yang menjadi sumber pemberitaan.

Pengembangan dan pengujian proyek saat ini dilakukan pada Windows menggunakan Python 3.14.7.

## 8. Instalasi dan Menjalankan Aplikasi

### 8.1. Clone Repository

```bash
git clone https://github.com/iermikot15g/gpr-media-intelligence.git
cd gpr-media-intelligence
```

### 8.2. Membuat Virtual Environment

Pada Windows PowerShell:

```powershell
python -m venv .venv
```

Aktifkan virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Jika menggunakan Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

### 8.3. Instalasi Dependensi

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 8.4. Menjalankan Aplikasi

```powershell
uvicorn app.main:app --reload
```

Buka browser dan akses:

```text
http://localhost:8000
```

Catatan: Database lokal dan direktori data aplikasi akan mengikuti konfigurasi aplikasi. Pastikan direktori yang diperlukan tersedia dan memiliki izin tulis.

## 9. Pengujian

Proyek menggunakan Pytest untuk memeriksa fungsi utama aplikasi.

Jalankan pengujian dengan:

```powershell
python -m compileall app tests scripts
python -m pytest -v
```

Pengujian mencakup beberapa aspek:

- Parsing tanggal publikasi.
- Penemuan URL artikel.
- Pengecualian URL kategori dan halaman non-artikel.
- Ekstraksi metadata berita.
- Pengumpulan artikel.
- Mekanisme retry.
- Penanganan URL kanonis dan duplikasi.
- Penentuan tanggal publikasi.
- Pembatasan kandidat artikel.
- Validasi alamat URL.
- Penolakan alamat IP privat dan localhost.
- Pemeriksaan sumber media.

**Status pengujian:** Pada 23 November 2026, sebanyak 48 pengujian otomatis yang tersedia berhasil dijalankan dengan hasil `48 passed`.

Hasil tersebut merupakan status pengujian pada tahap pengembangan saat dokumentasi ini disusun, bukan jaminan bahwa seluruh skenario produksi telah tercakup.

## 10. Keamanan dan Pengelolaan Data

Keamanan menjadi salah satu perhatian dalam pengembangan collector karena aplikasi melakukan permintaan HTTP ke situs eksternal.

Mekanisme yang telah dikembangkan meliputi:

- Pembatasan skema URL ke HTTP dan HTTPS.
- Penolakan URL yang mengandung kredensial.
- Pembatasan port koneksi.
- Pemeriksaan alamat IP publik.
- Penolakan alamat IP privat, loopback, dan link-local.
- Validasi URL tujuan pengalihan (*redirect*).
- Pembatasan jumlah pengalihan.
- Pembatasan ukuran respons.
- Pemeriksaan host yang diizinkan.
- Penghormatan terhadap aturan `robots.txt` dalam proses pengumpulan.

Pengembang tetap harus memperhatikan ketentuan penggunaan situs sumber, hak cipta konten, privasi, dan peraturan yang berlaku.

**Perlindungan data:** Database dan arsip lokal tidak disertakan dalam repositori publik. Direktori data, file database, virtual environment, file konfigurasi rahasia, log, dan file backup dikecualikan melalui `.gitignore`.

## 11. Model Data

Secara umum, aplikasi menggunakan beberapa entitas utama:

| Entitas               | Fungsi                                                    |
| --------------------- | --------------------------------------------------------- |
| `MediaSource`         | Menyimpan identitas, konfigurasi, dan status sumber media |
| `NewsArticle`         | Menyimpan artikel berita yang berhasil dikumpulkan        |
| `CollectionRun`       | Mencatat riwayat proses pengumpulan                       |
| `SourceValidationRun` | Mencatat riwayat validasi sumber media                    |

Hubungan antarentitas dirancang untuk mempertahankan keterkaitan artikel dengan sumber media serta riwayat proses yang menghasilkan data tersebut.

### Prinsip Penyimpanan Artikel

Identitas artikel dalam satu sumber media ditentukan berdasarkan kombinasi sumber media dan URL kanonis.

Artinya, artikel yang berasal dari dua media berbeda tetap dipertahankan sebagai dua rekaman berbeda meskipun isi pemberitaannya sama.

Prinsip ini penting dalam analisis media karena satu isu dapat diberitakan oleh banyak media dengan sudut pandang, waktu publikasi, dan karakteristik masing-masing.

---

## 12. Panduan Pengembangan

Pengembangan GPR Media Intelligence menggunakan pendekatan modular.

Developer yang ingin menambahkan kemampuan baru disarankan mengikuti prinsip berikut:

1. Pelajari struktur aplikasi dan model database sebelum mengubah kode.
2. Pisahkan fungsi pengumpulan, validasi, penyimpanan, dan penyajian data.
3. Pertahankan kompatibilitas dengan arsip berita yang sudah tersimpan.
4. Gunakan migrasi database jika terdapat perubahan struktur tabel.
5. Pertahankan kebijakan deduplikasi berdasarkan sumber media dan URL kanonis.
6. Tambahkan pengujian otomatis untuk setiap fungsi baru.
7. Pertahankan mekanisme validasi URL dan keamanan permintaan HTTP.
8. Jangan menyimpan kredensial, token, database pribadi, atau informasi sensitif ke repositori publik.
9. Dokumentasikan perubahan dan alasan teknisnya.

### Area yang Dapat Dikembangkan

**A. Pengembangan Collector**

- Menambahkan adapter untuk berbagai CMS media online.
- Menambahkan dukungan terhadap format feed dan sitemap yang lebih beragam.
- Mengembangkan strategi ekstraksi artikel untuk struktur situs yang berbeda.
- Menambahkan pengelolaan jadwal pengumpulan.
- Meningkatkan ketahanan terhadap perubahan struktur halaman media.

**B. Pengembangan Database**

- Menambahkan indeks untuk mempercepat pencarian.
- Mengembangkan mekanisme pencadangan dan pemulihan.
- Menyiapkan migrasi ke PostgreSQL jika skala penggunaan meningkat.
- Mengembangkan pengelolaan arsip dalam jangka panjang.

**C. Pengembangan Analitik**

- Menghitung frekuensi pemberitaan.
- Mengidentifikasi topik yang sering muncul.
- Mengukur intensitas pemberitaan berdasarkan periode.
- Membandingkan distribusi pemberitaan antar-media.
- Mengidentifikasi isu yang mengalami peningkatan perhatian.

**D. Pengembangan Kecerdasan Buatan**

- Ringkasan otomatis artikel.
- Klasifikasi topik dan isu.
- Analisis sentimen.
- Ekstraksi entitas.
- Pengelompokan berita berdasarkan kesamaan isu.
- Pembuatan executive summary.

**E. Pengembangan Dashboard**

- Visualisasi tren pemberitaan.
- Statistik berdasarkan media dan periode.
- Dashboard isu strategis.
- Pembuatan laporan berkala.
- Ekspor hasil analisis.

---

## 13. Kontribusi

GPR Media Intelligence terbuka untuk dipelajari dan dikembangkan lebih lanjut.

Kontribusi dapat dilakukan melalui:

- Pelaporan bug atau kesalahan ekstraksi.
- Usulan fitur baru.
- Pengembangan adapter sumber media.
- Peningkatan performa collector.
- Pengembangan analitik dan visualisasi.
- Penambahan pengujian otomatis.
- Perbaikan dokumentasi.
- Evaluasi keamanan dan kualitas kode.

Alur kontribusi yang disarankan:

1. Fork repositori.
2. Buat branch baru untuk perubahan.
3. Implementasikan fitur atau perbaikan.
4. Jalankan seluruh pengujian.
5. Dokumentasikan perubahan.
6. Ajukan Pull Request disertai penjelasan perubahan dan hasil pengujian.

Contoh:

```bash
git checkout -b feature/new-media-source
```

Setelah perubahan selesai:

```bash
python -m compileall app tests scripts
python -m pytest -v
```

Pastikan seluruh pengujian berhasil sebelum mengajukan Pull Request.

## 14. Batasan dan Catatan

GPR Media Intelligence saat ini masih dalam tahap pengembangan aktif.

Beberapa hal yang perlu diperhatikan:

- Keberhasilan pengumpulan bergantung pada ketersediaan dan struktur situs sumber.
- Perubahan HTML, struktur URL, atau kebijakan akses media dapat memengaruhi proses ekstraksi.
- Tidak semua media menyediakan RSS atau sitemap.
- Hasil ekstraksi otomatis tetap perlu dievaluasi kualitasnya.
- Aplikasi saat ini berorientasi pada penggunaan lokal dan belum boleh dianggap sebagai layanan produksi multi-user yang siap digunakan tanpa penguatan tambahan.
- Fitur analitik lanjutan dan integrasi AI merupakan area pengembangan berikutnya.

## 15. Roadmap Pengembangan

Roadmap berikut menggambarkan arah pengembangan proyek:

- [x] Fondasi aplikasi dan database.
- [x] Registrasi serta validasi sumber media.
- [x] Integrasi collector dan pemilihan sumber pengumpulan.
- [x] Pengarsipan, pencarian, filter, dan detail berita.
- [x] Penguatan keamanan collector dan validasi URL.
- [ ] Penjadwalan pengumpulan berita otomatis.
- [ ] Dashboard statistik dan monitoring.
- [ ] Analisis tren dan isu pemberitaan.
- [ ] Klasifikasi topik dan sentimen.
- [ ] Ringkasan berita berbasis AI.
- [ ] Pelaporan dan ekspor data.
- [ ] API dan integrasi dengan sistem eksternal.
- [ ] Pengelolaan pengguna dan hak akses.

Roadmap dapat berubah mengikuti hasil evaluasi, kebutuhan pengguna, dan kontribusi pengembang.

## 16. Lisensi

Informasi lisensi proyek perlu ditetapkan oleh pemilik repositori sebelum kode didistribusikan atau digunakan kembali dengan ketentuan lisensi tertentu.

Sampai file lisensi resmi ditambahkan, jangan mengasumsikan bahwa proyek ini menggunakan lisensi open-source tertentu.

## 17. Penutup

GPR Media Intelligence dikembangkan sebagai fondasi sistem pengelolaan informasi pemberitaan untuk mendukung kegiatan Government Public Relations.

Proyek ini tidak hanya berorientasi pada pengumpulan berita, tetapi juga pada pembangunan arsip pemberitaan yang terstruktur, dapat ditelusuri, dan berpotensi dikembangkan menjadi sistem media monitoring dan media intelligence yang lebih komprehensif.

Dengan arsitektur modular dan dokumentasi yang terbuka, proyek ini diharapkan dapat menjadi ruang kolaborasi bagi pengembang, praktisi kehumasan, peneliti komunikasi, serta pihak lain yang memiliki perhatian terhadap pengelolaan informasi publik dan analisis media.

**Repository:** [https://github.com/iermikot15g/gpr-media-intelligence](https://github.com/iermikot15g/gpr-media-intelligence)

**Project Status:** Active Development

---

*GPR Media Intelligence — From Media Collection to Public Relations Intelligence.*

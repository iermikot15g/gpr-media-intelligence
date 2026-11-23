# Contributing to GPR Media Intelligence

Terima kasih atas ketertarikan Anda untuk berkontribusi dalam pengembangan **GPR Media Intelligence**.

GPR Media Intelligence merupakan proyek pengembangan aplikasi Government Public Relations (GPR) untuk pengumpulan, pengarsipan, pemantauan, dan analisis pemberitaan media online.

Dokumen ini menjelaskan pedoman kontribusi agar pengembangan dapat dilakukan secara terstruktur, aman, konsisten, dan mudah dipelihara oleh seluruh kontributor.

Dengan berkontribusi pada proyek ini, Anda diharapkan mengikuti ketentuan teknis dan prinsip pengembangan yang dijelaskan di bawah.

---

## 1. Jenis Kontribusi

Kami terbuka terhadap berbagai bentuk kontribusi, antara lain:

### A. Bug Fixes

- Memperbaiki kesalahan aplikasi.
- Memperbaiki kegagalan pengumpulan artikel.
- Memperbaiki kesalahan ekstraksi judul, isi, penulis, atau tanggal publikasi.
- Memperbaiki masalah pencarian dan pengarsipan.
- Meningkatkan stabilitas dan performa aplikasi.

### B. New Features

- Menambahkan dukungan sumber media online.
- Mengembangkan metode penemuan URL artikel.
- Mengembangkan fitur monitoring pemberitaan.
- Menambahkan dashboard statistik dan visualisasi.
- Mengembangkan analisis tren dan isu.
- Menambahkan fitur pelaporan dan ekspor data.
- Mengembangkan integrasi AI untuk pengolahan informasi.

### C. Security Improvements

- Meningkatkan keamanan komunikasi HTTP.
- Memperbaiki validasi URL dan pengalihan.
- Meningkatkan perlindungan terhadap SSRF.
- Memperbaiki pengelolaan data dan konfigurasi.
- Menambahkan pengujian keamanan.

### D. Documentation

- Memperbaiki README.
- Menambahkan dokumentasi teknis.
- Membuat panduan instalasi.
- Menambahkan contoh konfigurasi.
- Memperbaiki dokumentasi API dan model data.

### E. Testing

- Menambahkan unit test.
- Menambahkan integration test.
- Memperbaiki test yang gagal.
- Menambahkan pengujian untuk kasus ekstrem (*edge cases*).

---

## 2. Persiapan Lingkungan Pengembangan

### Persyaratan

Sebelum berkontribusi, pastikan perangkat Anda memiliki:

- Python yang kompatibel dengan dependensi proyek.
- Git.
- pip.
- Terminal atau PowerShell.
- Browser modern.
- Koneksi internet untuk pengujian sumber media eksternal.

Pengembangan proyek saat ini dilakukan menggunakan Windows dan Python 3.14.7.

### Fork Repository

1. Buka repositori utama:

   https://github.com/iermikot15g/gpr-media-intelligence

2. Klik tombol **Fork**.
3. Buat salinan repositori pada akun GitHub Anda.
4. Clone repositori hasil fork ke komputer lokal.

```bash
git clone https://github.com/USERNAME/gpr-media-intelligence.git
cd gpr-media-intelligence
```

Ganti `USERNAME` dengan username GitHub Anda.

### Menambahkan Upstream Repository

Hubungkan repositori utama sebagai upstream:

```bash
git remote add upstream https://github.com/iermikot15g/gpr-media-intelligence.git
```

Periksa konfigurasi remote:

```bash
git remote -v
```

### Membuat Virtual Environment

Pada Windows PowerShell:

```powershell
python -m venv .venv
```

Aktifkan:

```powershell
.venv\Scripts\Activate.ps1
```

Jika menggunakan Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

### Menginstal Dependensi

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Menjalankan Aplikasi

Jalankan aplikasi dengan perintah:

```powershell
uvicorn app.main:app --reload
```

Buka browser:

```text
http://localhost:8000
```

Pastikan aplikasi dapat dijalankan sebelum mulai melakukan perubahan.

---

## 4. Struktur Proyek

Kenali struktur utama repositori sebelum mengubah kode.

```text
gpr-media-intelligence/
│
├── app/
│   ├── main.py
│   ├── collector.py
│   ├── database.py
│   ├── models.py
│   ├── source_validation.py
│   │
│   ├── source/
│   ├── static/
│   └── templates/
│
├── scripts/
├── tests/
│
├── requirements.txt
├── .gitignore
├── README.md
└── CONTRIBUTING.md
```

### Komponen Utama

| File atau direktori | Tanggung jawab |
|---|---|
| `app/main.py` | Routing, endpoint, dan alur aplikasi web |
| `app/collector.py` | Penemuan URL, pengambilan, ekstraksi, dan penyimpanan berita |
| `app/database.py` | Koneksi dan konfigurasi database |
| `app/models.py` | Model dan struktur tabel database |
| `app/source_validation.py` | Validasi sumber media dan keamanan permintaan HTTP |
| `app/source/` | Komponen pengelolaan sumber media |
| `app/templates/` | Template halaman aplikasi |
| `app/static/` | CSS, JavaScript, dan aset frontend |
| `scripts/` | Skrip administrasi dan pemeliharaan |
| `tests/` | Pengujian otomatis |

Usahakan perubahan dilakukan pada modul yang sesuai dengan tanggung jawabnya.

Hindari menempatkan seluruh logika baru dalam satu file jika fungsi tersebut dapat dipisahkan menjadi komponen yang lebih terstruktur.

---

## 5. Pedoman Pengembangan Collector

Collector merupakan salah satu komponen utama GPR Media Intelligence.

Collector bertanggung jawab menemukan kandidat artikel, mengambil halaman sumber, mengekstrak informasi berita, dan menyimpan hasilnya ke database.

Kontributor yang mengembangkan collector wajib memperhatikan ketentuan berikut.

### A. Dukungan Sumber Media

Setiap sumber media dapat memiliki struktur situs yang berbeda.

Pengembangan harus mempertimbangkan:

- RSS atau Atom feed.
- Sitemap XML.
- Halaman utama sebagai alternatif penemuan artikel.
- Pola URL artikel.
- Struktur HTML artikel.
- Metadata tanggal publikasi.
- Metadata penulis dan judul.
- Ketersediaan isi artikel.

Jangan mengasumsikan semua media menggunakan struktur HTML atau pola URL yang sama.

Jika menambahkan dukungan terhadap media baru, usahakan metode ekstraksinya tetap modular dan tidak merusak proses pengumpulan media lainnya.

### B. Penanganan Kesalahan

Collector harus mampu menangani kondisi seperti:

- Situs tidak dapat diakses.
- Timeout.
- HTTP error.
- Halaman artikel tidak ditemukan.
- Struktur HTML berubah.
- Metadata tidak tersedia.
- URL tidak valid.
- Proses ekstraksi gagal.

Gunakan mekanisme penanganan kesalahan dan retry secara terukur.

Kegagalan pada satu artikel atau sumber media tidak boleh menyebabkan seluruh proses pengumpulan berhenti tanpa alasan yang jelas.

### C. Penanganan Tanggal Publikasi

Tanggal publikasi artikel harus diambil dari informasi yang paling relevan dan dapat dipercaya.

Perhatikan perbedaan antara:

- Tanggal publikasi artikel.
- Tanggal modifikasi halaman.
- Tanggal pengumpulan artikel.
- Tanggal pembaruan sitemap.

Jangan menggunakan tanggal modifikasi atau `lastmod` sitemap sebagai tanggal publikasi artikel tanpa dasar yang dapat dipertanggungjawabkan.

### D. Batas Pengumpulan

Perubahan pada collector harus mempertahankan mekanisme pembatasan proses pengumpulan.

Pertimbangkan:

- Jumlah kandidat artikel.
- Jumlah artikel yang disimpan per sumber.
- Rentang tanggal.
- Jumlah percobaan ulang.
- Waktu tunggu permintaan.
- Ukuran respons.

Hindari pengumpulan yang terlalu agresif dan membebani situs media.

---

## 6. Kebijakan Duplikasi dan Integritas Arsip

**Ketentuan ini merupakan aturan inti proyek dan tidak boleh diubah tanpa pembahasan serta persetujuan maintainer.**

Sistem menggunakan URL kanonis sebagai dasar pemeriksaan duplikasi dalam cakupan sumber media yang sama.

Aturannya:

1. URL kanonis yang sama dari sumber media yang sama tidak boleh disimpan berulang kali.
2. Artikel dengan URL berbeda dari sumber media yang sama tetap boleh disimpan meskipun judul atau isinya sama atau mirip.
3. Artikel yang sama atau serupa dari sumber media berbeda harus tetap disimpan sebagai rekaman terpisah.
4. `content_hash` digunakan sebagai informasi pendukung analisis, bukan sebagai dasar untuk menolak penyimpanan artikel.

Contoh:

| Sumber | URL | Hasil |
|---|---|---|
| Media A | `/berita/123` | Disimpan |
| Media A | `/berita/123` | Ditolak sebagai duplikat |
| Media A | `/berita/456` | Tetap disimpan |
| Media B | `/berita/123` | Tetap disimpan |

Alasan kebijakan ini adalah mempertahankan rekam jejak pemberitaan lintas media.

Jangan mengganti aturan tersebut menjadi deduplikasi global berdasarkan judul, isi, atau hash konten.

Setiap perubahan yang berkaitan dengan identitas artikel, URL kanonis, constraint, atau indeks database harus disertai pengujian dan penjelasan dampaknya terhadap arsip yang sudah ada.

---

## 7. Pedoman Keamanan

Keamanan merupakan aspek penting karena aplikasi mengambil data dari situs eksternal.

Setiap kontribusi yang mengubah proses komunikasi HTTP wajib mempertahankan prinsip keamanan berikut.

### A. Validasi URL

- Hanya izinkan skema HTTP dan HTTPS.
- Tolak URL yang mengandung kredensial.
- Batasi port yang diperbolehkan.
- Validasi hostname.
- Tolak alamat IP privat dan alamat jaringan yang tidak diperbolehkan.
- Periksa URL sebelum permintaan dilakukan.

### B. Redirect Handling

Setiap URL tujuan pengalihan harus divalidasi kembali.

Jangan menganggap URL awal yang valid membuat semua tujuan redirect otomatis aman.

### C. Perlindungan SSRF

Perubahan kode tidak boleh membuka akses ke:

- Localhost.
- Jaringan privat.
- Alamat link-local.
- Endpoint metadata cloud.
- Host internal yang tidak diizinkan.

Jangan menonaktifkan pemeriksaan keamanan hanya untuk membuat suatu sumber media berhasil dikumpulkan.

### D. robots.txt dan Ketentuan Situs

Hormati aturan `robots.txt` dan kebijakan akses situs sumber.

Jangan mengembangkan mekanisme untuk melewati autentikasi, CAPTCHA, pembatasan akses, atau kontrol keamanan situs.

### E. Perlindungan Data

Jangan mengunggah atau melakukan commit terhadap:

- Database pribadi.
- Arsip berita lokal.
- API key.
- Password.
- Token.
- File `.env`.
- Private key.
- Log yang mengandung informasi sensitif.
- Backup database.

Pastikan `.gitignore` tetap melindungi file-file tersebut.

---

## 8. Pedoman Database dan Migrasi

Perubahan struktur database harus dilakukan dengan hati-hati karena database dapat berisi arsip pemberitaan yang sudah terkumpul.

Sebelum mengubah model:

1. Pelajari model dan relasi yang sudah ada.
2. Identifikasi dampak perubahan terhadap data lama.
3. Siapkan mekanisme migrasi jika diperlukan.
4. Jangan menghapus tabel atau kolom tanpa alasan dan rencana pemindahan data.
5. Pastikan perubahan tidak menghilangkan riwayat pengumpulan.
6. Tambahkan pengujian untuk perubahan struktur dan integritas data.

**Prinsip utama: perubahan aplikasi tidak boleh menyebabkan kehilangan arsip berita yang sudah tersimpan.**

Jangan menjalankan skrip yang menghapus atau menginisialisasi ulang database pengguna sebagai bagian dari pengujian biasa.

Gunakan database sementara atau fixture pengujian untuk menguji perubahan database.

---

## 9. Standar Kode

Untuk menjaga konsistensi kode:

- Gunakan nama fungsi dan variabel yang deskriptif.
- Gunakan snake_case untuk fungsi dan variabel Python.
- Gunakan PascalCase untuk class.
- Hindari fungsi yang terlalu panjang dan memiliki terlalu banyak tanggung jawab.
- Pisahkan logika bisnis dari tampilan.
- Hindari duplikasi kode.
- Gunakan exception handling secara tepat.
- Tambahkan komentar jika terdapat logika yang tidak langsung jelas.
- Jangan menyimpan konfigurasi sensitif secara langsung di dalam kode.

Contoh penamaan:

```python
def collect_articles():
    pass


def validate_source_url():
    pass


class MediaSource:
    pass
```

Jika menambahkan dependensi baru, sertakan alasan penggunaan dan pastikan dependensi tersebut benar-benar diperlukan.

Perbarui `requirements.txt` jika dependensi aplikasi berubah.

---

## 10. Pengujian Sebelum Pull Request

Semua perubahan harus diuji sebelum diajukan.

Jalankan pemeriksaan kompilasi:

```powershell
python -m compileall app tests scripts
```

Kemudian jalankan seluruh pengujian:

```powershell
python -m pytest -v
```

Pengujian yang tersedia mencakup:

- Parsing tanggal.
- Penemuan URL artikel.
- Pengecualian URL non-artikel.
- Ekstraksi metadata.
- Pengumpulan artikel.
- Mekanisme retry.
- Penanganan duplikasi URL kanonis.
- Prioritas tanggal publikasi.
- Batas kandidat dan artikel.
- Validasi URL.
- Penolakan alamat IP privat.
- Penemuan artikel dari homepage.

### Ketentuan Pengujian

Setiap fitur atau perbaikan baru harus memiliki pengujian yang sesuai.

Contohnya:

| Jenis perubahan | Pengujian yang diharapkan |
|---|---|
| Perubahan collector | Pengujian pengumpulan dan ekstraksi |
| Perubahan validasi URL | Pengujian URL valid dan tidak valid |
| Penambahan sumber media | Pengujian pola URL dan metadata |
| Perubahan database | Pengujian integritas dan kompatibilitas |
| Perubahan pencarian | Pengujian filter, hasil, dan pagination |
| Perubahan keamanan | Pengujian skenario serangan dan akses tidak sah |

Jangan menghapus atau menonaktifkan pengujian yang gagal hanya untuk membuat pipeline pengujian berhasil.

Jika terdapat pengujian yang gagal, perbaiki penyebabnya atau jelaskan secara rinci alasan kegagalan tersebut.

---

## 11. Git Workflow

Gunakan branch terpisah untuk setiap fitur atau perbaikan.

### A. Sinkronisasi Repository

Sebelum memulai perubahan:

```bash
git checkout main
git pull upstream main
```

### B. Membuat Branch

Contoh nama branch:

```bash
git checkout -b feature/new-media-source
```

Format nama branch yang disarankan:

| Prefix | Penggunaan |
|---|---|
| `feature/` | Penambahan fitur |
| `fix/` | Perbaikan bug |
| `security/` | Perbaikan keamanan |
| `refactor/` | Refactoring kode |
| `docs/` | Perubahan dokumentasi |
| `test/` | Penambahan atau perbaikan pengujian |

Contoh:

```text
feature/media-analytics
fix/article-date-extraction
security/redirect-validation
refactor/collector-module
docs/update-installation-guide
test/source-validation
```

### C. Commit

Gunakan pesan commit yang jelas dan menggambarkan perubahan.

Contoh:

```bash
git add app/collector.py tests/test_collector.py
git commit -m "Add support for new media source"
```

Contoh prefix commit:

- `feat:` penambahan fitur.
- `fix:` perbaikan bug.
- `security:` perbaikan keamanan.
- `refactor:` refactoring.
- `test:` pengujian.
- `docs:` dokumentasi.
- `chore:` pemeliharaan proyek.

### D. Push Branch

```bash
git push origin feature/new-media-source
```

---

## 12. Mengajukan Pull Request

Setelah perubahan selesai:

1. Pastikan branch sudah diperbarui dengan branch utama.
2. Jalankan pemeriksaan kompilasi.
3. Jalankan seluruh pengujian.
4. Pastikan tidak ada file sensitif yang ikut ditambahkan.
5. Push branch ke repositori fork.
6. Buka repositori GitHub.
7. Pilih **Compare & pull request**.
8. Lengkapi deskripsi Pull Request.

### Informasi yang Harus Disertakan

Pull Request sebaiknya menjelaskan:

- Tujuan perubahan.
- Masalah yang diselesaikan.
- File atau modul yang diubah.
- Perilaku sebelum dan sesudah perubahan.
- Pengujian yang dilakukan.
- Hasil pengujian.
- Potensi dampak terhadap database dan fitur lain.
- Screenshot jika perubahan menyangkut tampilan dashboard.

### Template Deskripsi Pull Request

```markdown
## Ringkasan

Jelaskan secara singkat perubahan yang dilakukan.

## Latar Belakang

Masalah atau kebutuhan yang menjadi alasan perubahan.

## Perubahan

- Perubahan pertama
- Perubahan kedua
- Perubahan ketiga

## Pengujian

- [ ] python -m compileall app tests scripts
- [ ] python -m pytest -v
- [ ] Pengujian manual jika diperlukan

## Dampak

Jelaskan dampak terhadap collector, database, arsip,
validasi sumber media, atau fitur lainnya.

## Dokumentasi

- [ ] Dokumentasi diperbarui jika diperlukan.
- [ ] Tidak ada file rahasia atau database pribadi yang disertakan.
```

Pull Request akan ditinjau sebelum perubahan digabungkan ke branch utama.

---

## 13. Melaporkan Bug

Jika menemukan bug, silakan buat GitHub Issue.

Sertakan informasi berikut:

- Judul masalah.
- Deskripsi masalah.
- Langkah untuk mereproduksi masalah.
- Perilaku yang diharapkan.
- Perilaku yang terjadi.
- Versi Python.
- Sistem operasi.
- Pesan error atau traceback jika tersedia.
- Screenshot jika relevan.

Contoh:

```markdown
## Deskripsi Bug

Collector gagal mengekstrak tanggal publikasi artikel.

## Langkah Reproduksi

1. Tambahkan sumber media.
2. Jalankan validasi sumber.
3. Jalankan pengumpulan artikel.
4. Periksa hasil tanggal publikasi.

## Hasil yang Diharapkan

Tanggal publikasi artikel tersimpan dengan benar.

## Hasil Aktual

Tanggal publikasi bernilai kosong.

## Lingkungan

- OS: Windows
- Python: 3.14.7
- Project: GPR Media Intelligence
```

Jangan menyertakan database pribadi, token, password, atau informasi sensitif ketika melaporkan masalah.

---

## 14. Mengusulkan Fitur Baru

Sebelum mengembangkan fitur yang cukup besar, disarankan membuat GitHub Issue terlebih dahulu.

Jelaskan:

1. Kebutuhan yang ingin diselesaikan.
2. Manfaat fitur bagi pengguna.
3. Gambaran cara kerja.
4. Komponen aplikasi yang akan terdampak.
5. Potensi risiko teknis.
6. Kebutuhan perubahan database atau dependensi.

Hal ini membantu menghindari pengembangan fitur yang tumpang tindih dan menjaga arah pengembangan proyek.

---

## 15. Prinsip Kontribusi

Seluruh kontributor diharapkan mengikuti prinsip berikut:

- Mengutamakan integritas dan kualitas data.
- Menjaga keamanan aplikasi.
- Menghormati kebijakan akses situs media.
- Tidak merusak arsip berita yang sudah tersimpan.
- Mempertahankan kompatibilitas fitur yang telah tersedia.
- Menulis kode yang mudah dipahami dan dipelihara.
- Menyertakan pengujian untuk perubahan yang dibuat.
- Mengutamakan kolaborasi dan komunikasi yang konstruktif.

Kontribusi yang mengurangi keamanan, merusak integritas arsip, atau mengubah kebijakan inti tanpa persetujuan maintainer dapat diminta untuk direvisi.

---

## 16. Roadmap Kontribusi

Beberapa area yang dapat menjadi fokus kontribusi berikutnya:

- [ ] Penjadwalan pengumpulan berita otomatis.
- [ ] Pengembangan adapter untuk sumber media baru.
- [ ] Peningkatan kualitas ekstraksi artikel.
- [ ] Dashboard monitoring dan statistik.
- [ ] Analisis tren pemberitaan.
- [ ] Klasifikasi topik dan isu.
- [ ] Analisis sentimen.
- [ ] Ekstraksi entitas.
- [ ] Ringkasan berita berbasis AI.
- [ ] Pembuatan laporan otomatis.
- [ ] Ekspor data.
- [ ] API integrasi.
- [ ] Pengelolaan pengguna dan hak akses.

Kontributor dapat memilih area yang sesuai dengan keahlian dan minat masing-masing.

---

## 17. Penutup

Setiap kontribusi, baik berupa kode, pengujian, dokumentasi, maupun masukan teknis, sangat berarti bagi pengembangan GPR Media Intelligence.

Kami berharap proyek ini dapat berkembang menjadi platform media intelligence yang bermanfaat bagi praktisi Government Public Relations, pengelola komunikasi publik, peneliti, dan komunitas pengembang.

Terima kasih telah meluangkan waktu untuk mempelajari dan berkontribusi pada proyek ini.

**Repository:**  
https://github.com/iermikot15g/gpr-media-intelligence

**Project:** GPR Media Intelligence

**Status:** Active Development

---

*GPR Media Intelligence — From Media Collection to Public Relations Intelligence.*

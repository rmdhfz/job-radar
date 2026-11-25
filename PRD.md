# PRD: Radar Loker Indonesia

Status: Fase 0 (prototipe antarmuka) selesai. Fase 1 dan seterusnya belum dibangun.
Pemilik: Hafiz Ramadhan (pengguna tunggal). Terakhir diperbarui: 25 Nov 2026.

## 1. Masalah

Mencari kerja berarti membuka belasan situs dan grup satu per satu: portal lowongan, LinkedIn, Threads dan X,
channel Telegram, serta halaman karier perusahaan. Lowongan terbaik cepat penuh pelamar, dan banyak
iklan sudah ditutup atau palsu. Tidak ada satu tempat yang menjawab: *"Apa yang baru, valid, dan cocok
untuk saya, di mana, dan bergaji berapa?"*

## 2. Tujuan

1. Satu halaman ringan yang menampilkan lowongan di seluruh Indonesia pada **peta 3D**.
2. Saring berdasarkan **industri, perusahaan, rentang gaji (jika ada), waktu posting, lokasi, dan validitas**.
3. Setiap lowongan menunjukkan **kapan diposting** dan **seberapa dapat dipercaya**, dengan satu klik ke tautan lamar resmi.
4. Waktu dari "lowongan muncul di sumber" sampai "muncul di portal" sependek mungkin, agar bisa melamar cepat.

## 3. Bukan tujuan

- Bukan mesin pencari lowongan publik, tidak ada akun pengguna lain, tidak ada iklan.
- Tidak menyalin isi deskripsi lowongan secara penuh. Portal menyimpan metadata minimal dan menautkan ke sumber.
- Tidak memakai pengambilan data otomatis pada situs yang melarangnya (bagian 5).
- Tidak menjanjikan "semua lowongan Indonesia". Cakupan nyata adalah **sumber yang dipantau**, dan portal menampilkan cakupan itu secara jujur.
- Tidak melamar otomatis.

## 4. Pengguna dan skenario

Pengguna utama: pencari kerja di bidang IT di Jabodetabek yang terbuka ke kota lain (Hafiz).

- *Pagi hari*: buka portal, filter "24 jam terakhir" + "Terverifikasi" + industri tertentu, lamar ke tiga yang cocok.
- *Menilai peluang*: lihat apakah gaji tercantum, apakah perusahaan Tbk, dan di kota mana.
- *Menjelajah*: miringkan peta, lihat konsentrasi lowongan di Cikarang atau Balikpapan.
- *Menghindari penipuan*: lowongan yang meminta biaya atau hanya lewat WhatsApp pribadi tidak muncul sebagai "Terverifikasi".

## 5. Strategi sumber data (bagian terpenting)

Sumber dikelompokkan menurut **risiko hukum dan ToS**. Aturan: **tier C tidak boleh dibangun scraper-nya.** Alasannya: syarat layanan melarang pengambilan otomatis dan platform aktif memblokir atau menggugat. Satu akun yang diblokir bisa merugikan pencarian kerja itu sendiri.

| Tier | Sumber | Cara masuk | Catatan |
|---|---|---|---|
| **A, aman** | Halaman karier perusahaan | `JobPosting` JSON-LD di halaman, hormati `robots.txt` | Banyak situs memasangnya agar muncul di Google for Jobs |
| **A** | ATS publik: Greenhouse, Lever, Ashby, SmartRecruiters | API job board publik tiap perusahaan | Butuh daftar perusahaan (`companies.yaml`). Cek endpoint di dokumentasi resmi sebelum dipakai |
| **A** | Channel Telegram yang Anda ikuti | API Telegram resmi (Telethon/TDLib, akun Anda sendiri) | Berkas sesi adalah rahasia, jangan di-commit |
| **A** | Email alert dari Jobstreet, LinkedIn, Indeed, Glints | Baca kotak surat Anda sendiri lewat IMAP atau Gmail API (read-only) | Ambil judul, perusahaan, kota, tautan saja. Ini jalur legal ke isi platform tier C |
| **A** | Input manual | Tombol "Tambah" atau tempel tautan | Untuk lowongan dari teman, grup WhatsApp, dsb. |
| **B, hati-hati** | X dan Threads | API resmi masing-masing | Akses dan batasnya berubah. Cek dokumentasi terbaru, mungkin berbayar atau terbatas |
| **B** | Portal pemerintah dan marketplace kecil | Hanya jika ada API atau data terbuka | Periksa ToS dan `robots.txt` per situs |
| **C, jangan scrape** | LinkedIn, Indeed, Jobstreet, dan situs sejenis | Tidak ada | Gunakan email alert (tier A) dan **pintasan pencarian** di bawah |

**Pintasan pencarian (F-9):** untuk platform tier C, portal hanya membuat tautan pencarian siap pakai
(kata kunci + kota) yang dibuka di tab baru. Cakupan tetap penuh tanpa melanggar apa pun.

Prinsip data:
- Simpan **metadata minimal** dan selalu tautkan ke sumber asli.
- **Jangan simpan data pribadi** (nama, email, telepon rekruter). Hanya data perusahaan dan lowongan (UU PDP).
- Catat `source_label` jujur. Jika tanggal posting tidak diketahui, itu waktu "pertama terlihat" dan harus ditandai.

## 6. Model data

Kontrak antara pipeline dan portal adalah berkas `jobs.json`, divalidasi oleh `schema/jobs.schema.json`.
Portal membuang baris tidak valid, id ganda, kota tidak dikenal, dan tautan selain `http(s)`.

Bidang wajib: `id`, `title`, `company`, `posted_at`. Bidang lain: `industry`, `city`, `province`, `lat`, `lng`,
`level`, `work_type`, `salary_min`, `salary_max` (rupiah per bulan, `null` jika tidak tercantum, **jangan menebak**),
`last_verified_at`, `status` (`active | unverified | expired`), `trust` (0 sampai 100), `source_label`, `url`.

```json
{ "generated_at": "2026-11-25T03:00:00Z",
  "jobs": [{ "id": "gh-abc123", "title": "IT Manager", "company": "PT Contoh", "industry": "Pertambangan",
    "city": "Balikpapan", "work_type": "onsite", "salary_min": null, "salary_max": null,
    "posted_at": "2026-11-24T02:10:00Z", "last_verified_at": "2026-11-25T03:00:00Z",
    "status": "active", "trust": 88, "source_label": "Situs perusahaan", "url": "https://contoh.example/karier/123" }] }
```

Taksonomi industri tetap (ubah hanya lewat PRD): Teknologi Informasi, Perbankan & Keuangan, Pertambangan, Energi,
Manufaktur & FMCG, Retail & E-commerce, Logistik & Pelayaran, Telekomunikasi, Kesehatan, Pendidikan, Pemerintahan & BUMN, Lainnya.

## 7. Validitas ("VALID") dan anti-penipuan

Portal tidak boleh menyebut lowongan "terverifikasi" tanpa bukti. Definisi:

**Skor kepercayaan (0 sampai 100):**

| Faktor | Poin |
|---|---|
| Sumber adalah domain resmi perusahaan atau ATS publik perusahaan | +40 |
| Tautan lamar dicek hidup (HTTP 200, tanpa teks "ditutup/closed/expired") dalam 72 jam | +20 |
| Cocok silang di 2 sumber independen atau lebih | +15 |
| Data lengkap dan konsisten (lokasi, jabatan, perusahaan) | +10 |
| Domain tautan lamar cocok dengan domain perusahaan | +15 |
| Meminta biaya, transfer, atau "uang administrasi" | −50 |
| Kontak hanya WhatsApp/Telegram pribadi tanpa domain perusahaan | −30 |
| Email gratisan untuk perusahaan besar | −20 |
| Gaji tidak wajar dibanding posisi serupa | −20 |

- `trust ≥ 70` dan `status = active`: **Terverifikasi**. 40 sampai 69: **Belum diverifikasi**. Di bawah 40: **Mencurigakan** (disembunyikan secara default).
- **Kedaluwarsa:** hilang dari sumber pada 2 siklus berturut-turut, atau tautan lamar mati, atau 45 hari tanpa verifikasi ulang.
- **Pengecekan ulang:** tiap 24 jam untuk lowongan di bawah 7 hari, tiap 72 jam sesudahnya.
- **Deduplikasi:** kunci = perusahaan + judul + kota (dinormalisasi) + URL kanonik. Judul sangat mirip pada perusahaan dan kota yang sama digabung, sumber-sumbernya dicatat.

## 8. Arsitektur

```
 sumber tier A ──> ingestion (Python 3.12) ──> SQLite ──> validasi + dedup + skor ──> export jobs.json ──> index.html
 (ATS, JSON-LD,     per sumber satu modul        satu berkas   (batch terjadwal)        (statis, gz)         (peta + filter)
 Telegram, IMAP)
```

- **Portal** (`index.html`): satu berkas, tanpa build, MapLibre GL dari CDN, tanpa backend. Sudah ada.
- **Ingestion**: Python agar Telethon dan IMAP mudah. Satu modul per sumber, dengan antarmuka sama (`fetch() -> list[RawJob]`).
- **Penyimpanan**: SQLite cukup untuk satu pengguna. Pindah ke PostgreSQL hanya jika perlu.
- **Jadwal**: cron lokal atau GitHub Actions tiap 1 sampai 3 jam. Hasilnya `jobs.json` (dikompresi) di hosting statis.
- **Penanda pengguna** (disimpan/dilamar) tetap di `localStorage` browser. Tidak ada akun.
- **Ekstraksi dari teks bebas** (posting Telegram): aturan regex dulu, model bahasa hanya untuk yang tidak terbaca, dengan keluaran divalidasi skema.
- **Ukuran**: sekitar 500 byte per lowongan. 20.000 lowongan sekitar 10 MB mentah dan jauh lebih kecil dikompresi. Buang yang kedaluwarsa lebih dari 30 hari.

## 9. Fitur dan fase

| ID | Fitur | Fase | Status |
|---|---|---|---|
| F-1 | Peta 3D: batang per kota (tinggi = jumlah, warna = kebaruan), klik untuk menyaring kota | 0 | Selesai |
| F-2 | Filter: kata kunci, industri, perusahaan, gaji, waktu posting, lokasi kerja, provinsi, terverifikasi | 0 | Selesai |
| F-3 | Daftar: waktu posting, gaji atau "tidak tercantum", lencana validitas, sumber, tautan lamar | 0 | Selesai |
| F-4 | Simpan dan tandai "sudah dilamar" (localStorage) | 0 | Selesai |
| F-5 | Impor `jobs.json` dan pemuatan otomatis `jobs.json` di sebelahnya | 0 | Selesai |
| F-6 | Peta dasar bawaan (offline) dan opsi peta detail online | 0 | Selesai |
| F-7 | Ingestion tier A: ATS publik + JSON-LD + input manual, ekspor `jobs.json` | 1 | Belum |
| F-8 | Telegram dan email alert | 2 | Belum |
| F-9 | Pintasan pencarian untuk platform tier C | 1 | Belum |
| F-10 | Validasi: cek tautan hidup, skor, deduplikasi, kedaluwarsa | 3 | Belum |
| F-11 | Pencarian tersimpan dan notifikasi lowongan baru yang cocok (Telegram ke diri sendiri) | 4 | Belum |
| F-12 | Panel cakupan: berapa sumber dan perusahaan dipantau, kapan terakhir berhasil | 3 | Belum |
| F-13 | Hosting statis dengan kontrol akses | 5 | Opsional |

## 10. Persyaratan non-fungsional

- **Ringan:** `index.html` di bawah 250 KB (saat ini sekitar 120 KB), tanpa framework dan tanpa langkah build. Tampilan awal di bawah 2 detik pada jaringan 4G.
- **Berfungsi tanpa internet** untuk peta dasar dan data yang sudah dimuat (kecuali pustaka MapLibre dari CDN, bisa disalin lokal).
- **Aman:** semua teks dari `jobs.json` di-escape, hanya tautan `http(s)`, `rel="noopener noreferrer"`.
- **Responsif** sampai lebar 360 px. **Aksesibel:** dapat dioperasikan dengan keyboard, kontras memadai, mengikuti tema gelap/terang.
- **Jujur:** data contoh selalu berlabel jelas dan tidak pernah tampil seperti lowongan asli.

## 11. Kriteria penerimaan

**Fase 0 (selesai, diverifikasi dengan `npm run smoke`):** data contoh dimuat, setiap filter bekerja, klik kota menyaring daftar, impor membuang baris tidak valid, HTML tersuntik tidak dieksekusi, tautan `javascript:` ditolak, tanpa error konsol, tanpa scroll horizontal di 390 px.

**Fase 1:** minimal 30 perusahaan target terpantau lewat ATS/JSON-LD, `jobs.json` terbentuk otomatis, setiap lowongan punya `url` yang bisa dibuka, uji unit untuk parser tiap sumber dengan sampel nyata yang sudah disimpan.

**Fase 3:** dari sampel acak 30 lowongan berlabel "Terverifikasi", minimal 27 benar-benar masih aktif saat dicek manual. Lowongan yang meminta biaya tidak pernah berlabel Terverifikasi.

## 12. Metrik

- **Kesegaran:** median selisih antara waktu posting di sumber dan waktu muncul di portal.
- **Presisi validitas:** persentase "Terverifikasi" yang benar aktif pada sampel manual.
- **Cakupan:** jumlah perusahaan, ATS, channel yang dipantau, dan tingkat keberhasilan tiap run.
- **Hasil nyata:** jumlah lamaran per minggu dan jumlah wawancara.

## 13. Risiko

| Risiko | Mitigasi |
|---|---|
| Melanggar ToS jika ada yang menambah scraper tier C | Aturan keras di `AGENTS.md`, daftar tier di PRD ini |
| Lowongan palsu masuk | Skor kepercayaan, default hanya menampilkan yang ≥ 40, laporan manual |
| Sumber berubah format dan pipeline diam-diam kosong | Panel cakupan, alarm jika jumlah lowongan sumber turun tajam |
| Tanggal posting tidak ada di sumber | Pakai "pertama terlihat" dan beri label |
| Data gaji salah ekstraksi | Simpan `null` jika ragu, jangan menebak |
| Berkas sesi Telegram atau kredensial bocor | `.gitignore`, variabel lingkungan, tidak pernah di-commit |

## 14. Pertanyaan terbuka

1. Daftar awal 30 perusahaan target (Tbk, tambang, FMCG, perbankan) dan kata kunci posisi.
2. Hosting: cukup lokal, atau statis di GitHub Pages/Cloudflare Pages?
3. Channel Telegram dan email alert mana yang dipakai di Fase 2?
4. Perlukah penelusuran tambahan ke kota kecil di luar gazetteer 44 kota saat ini?

# PRD: Radar Loker Indonesia

Status: Fase 0 (prototipe antarmuka) selesai, peta 3D dipindah ke three.js, detail lowongan dan profil perusahaan ditambahkan. Fase 1 (ingestion) belum dibangun.
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

- Tidak ada akun pengguna, tidak ada iklan. (Sejak 25 Nov 2026 situs dipublikasikan dan boleh diindeks mesin pencari atas keputusan pemilik; penanda simpan/dilamar tetap hanya di browser masing-masing.)
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
| **A** | ATS publik: Greenhouse, Lever, Workable (Ashby, SmartRecruiters: lihat catatan) | API job board publik tiap perusahaan | Butuh daftar perusahaan (`pipeline/companies.yaml`). Endpoint dicek di dokumentasi resmi (25 Nov 2026). **SmartRecruiters tidak dipakai**: `api.smartrecruiters.com/robots.txt` melarang semua bot kecuali LinkedInBot. Ashby ditunda: `robots.txt`-nya tidak bisa dibaca (401) |
| **A** | Situs karier perusahaan yang di-host Workday (`*.myworkdayjobs.com`) | Sitemap yang dideklarasikan di `robots.txt`, lalu `JobPosting` JSON-LD di tiap halaman | Hanya jika `robots.txt` mengizinkan path situsnya (Citi dan DBS melarang, jadi dilewati) |
| **A** | Channel Telegram yang Anda ikuti | API Telegram resmi (Telethon/TDLib, akun Anda sendiri) | Berkas sesi adalah rahasia, jangan di-commit |
| **A** | Email alert dari Jobstreet, LinkedIn, Indeed, Glints | Baca kotak surat Anda sendiri lewat IMAP atau Gmail API (read-only) | Ambil judul, perusahaan, kota, tautan saja. Ini jalur legal ke isi platform tier C |
| **A** | Input manual | Tombol "Tambah" atau tempel tautan | Untuk lowongan dari teman, grup WhatsApp, dsb. |
| **B, hati-hati** | X dan Threads | API resmi masing-masing | Akses dan batasnya berubah. Cek dokumentasi terbaru, mungkin berbayar atau terbatas |
| **B** | Portal pemerintah dan marketplace kecil | Hanya jika ada API atau data terbuka | Periksa ToS dan `robots.txt` per situs |
| **C, jangan scrape** | LinkedIn, Indeed, Jobstreet, Kalibrr, dan situs sejenis | Tidak ada | Gunakan email alert (tier A) dan **pintasan pencarian** di bawah |

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
`last_verified_at`, `status` (`active | unverified | expired`), `trust` (0 sampai 100), `source_label`, `url`,
`summary` (ringkasan singkat maks. 600 karakter, **bukan** salinan penuh deskripsi).

Opsional di tingkat atas: `companies`, peta `nama perusahaan -> profil` dengan bidang `website`, `industry`, `founded`,
`headquarters`, `employees`, `ticker`, `summary`, `history`, `source_label`, `source_url`, `updated_at`. Kuncinya harus sama
persis dengan nilai `company` di lowongan. Hanya data perusahaan, tidak ada data pribadi.

**Profil perusahaan di portal** diambil dengan urutan: (1) `companies` di `jobs.json`; (2) jika pengguna menekan
"Cari profil di Wikipedia", portal memanggil API publik Wikipedia (id, lalu en) dan Wikidata langsung dari peramban.
Hasil dicocokkan dengan nama perusahaan (judul generik seperti "Indonesia" tidak pernah cocok), diberi atribusi
(Wikipedia CC BY-SA 4.0, Wikidata CC0) dan peringatan bahwa pencocokan otomatis, lalu di-cache di `localStorage` 30 hari.
Tidak ada yang dikirim ke Wikipedia sebelum tombol ditekan. Data contoh memakai profil fiktif berlabel.

```json
{ "generated_at": "2026-11-25T03:00:00Z",
  "jobs": [{ "id": "gh-abc123", "title": "IT Manager", "company": "PT Contoh", "industry": "Pertambangan",
    "city": "Balikpapan", "work_type": "onsite", "salary_min": null, "salary_max": null,
    "posted_at": "2026-11-24T02:10:00Z", "last_verified_at": "2026-11-25T03:00:00Z",
    "status": "active", "trust": 88, "source_label": "Situs perusahaan", "url": "https://contoh.example/karier/123" }] }
```

**Bidang** (fungsi pekerjaan) tidak ada di `jobs.json`: portal menurunkannya dari judul lowongan dengan aturan kata kunci tetap (`ROLES` di `index.html`): IT & Software, Data & AI, Produk & Desain, Keuangan & Akuntansi, Sales & Bisnis, SDM & Legal, Operasional, Lainnya. Tidak cocok = Lainnya. **Industri** tetap industri perusahaan pemberi kerja.

Taksonomi industri tetap (ubah hanya lewat PRD): Teknologi Informasi, Perbankan & Keuangan, Pertambangan, Energi,
Manufaktur & FMCG, Retail & E-commerce, Logistik & Pelayaran, Telekomunikasi, Kesehatan, Pendidikan, Pemerintahan & BUMN, Lainnya.

## 7. Validitas ("VALID") dan anti-penipuan

Portal tidak boleh menyebut lowongan "terverifikasi" tanpa bukti. Definisi:

**Skor kepercayaan (0 sampai 100):**

| Faktor | Poin |
|---|---|
| Sumber adalah domain resmi perusahaan, situs karier resminya, atau ATS publik perusahaan | +40 |
| Tautan lamar dicek hidup (HTTP 200, tanpa teks "ditutup/closed/expired") dalam 72 jam. Untuk ATS: lowongan masih tercantum di API resmi "published postings" pada pengambilan terakhir. Untuk JSON-LD: masih ada di sitemap dan halamannya diambil ≤ 48 jam lalu dengan `JobPosting` yang belum lewat `validThrough` | +20 |
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

- **Portal** (`index.html`): satu berkas, tanpa build, three.js (modul ES lewat import map, versi dikunci) dari CDN, tanpa backend. Daftar dan filter tetap berfungsi bila three.js gagal dimuat. Sudah ada.
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
| F-6 | Peta dasar bawaan (offline, pulau diekstrusi dengan three.js) | 0 | Selesai (opsi peta detail online CARTO dihapus bersama MapLibre) |
| F-7 | Ingestion tier A: ATS publik + JSON-LD + input manual, ekspor `jobs.json` | 1 | Sebagian: Greenhouse, Lever, Workable, JSON-LD (Workday) untuk 11 perusahaan; GitHub Actions tiap 3 jam. Input manual belum |
| F-8 | Telegram dan email alert | 2 | Belum |
| F-9 | Pintasan pencarian untuk platform tier C | 1 | Sebagian: di dialog detail (LinkedIn, Jobstreet, Indeed, Glints) |
| F-10 | Validasi: cek tautan hidup, skor, deduplikasi, kedaluwarsa | 3 | Belum |
| F-11 | Pencarian tersimpan dan notifikasi lowongan baru yang cocok (Telegram ke diri sendiri) | 4 | Belum |
| F-12 | Panel cakupan: berapa sumber dan perusahaan dipantau, kapan terakhir berhasil | 3 | Data sudah ada (`sources` di `jobs.json`), tampilan belum |
| F-13 | Hosting statis dengan kontrol akses | 5 | Opsional |
| F-16 | Filter dan chip "Bidang" (mis. IT & Software) dari judul posisi | 0 | Selesai |
| F-17 | SEO: meta + Open Graph, JSON-LD WebSite/SearchAction (`?q=`), `?kota=`/`?bidang=`, sitemap, pra-render lowongan terbaru di `dist/index.html`, bagian "Tentang" | 0 | Selesai |
| F-14 | Dialog detail lowongan: info, skor kepercayaan dan rubriknya, lowongan lain di perusahaan/kota yang sama, tautan dalam (`#job=`) | 0 | Selesai |
| F-15 | Profil perusahaan: statistik di radar, `companies` dari `jobs.json`, Wikipedia/Wikidata atas permintaan | 0 | Selesai |

## 10. Persyaratan non-fungsional

- **Ringan:** `index.html` di bawah 250 KB (saat ini sekitar 200 KB; `dist/index.html` dengan pra-render sekitar 215 KB), tanpa framework dan tanpa langkah build. three.js dari CDN sekitar 170 KB terkompresi. Peta hanya merender saat ada perubahan. Tampilan awal di bawah 2 detik pada jaringan 4G.
- **Berfungsi tanpa internet** untuk daftar, filter, dan data yang sudah dimuat. Peta 3D butuh three.js dari CDN (bisa disalin lokal).
- **Aman:** semua teks dari `jobs.json` dan Wikipedia di-escape, hanya tautan `http(s)`, `rel="noopener noreferrer"`, Content-Security-Policy membatasi skrip ke CDN jsDelivr dan koneksi ke Wikipedia/Wikidata, `referrer` tidak dikirim.
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
2. ~~Hosting~~ Terjawab 25 Nov 2026: Cloudflare Workers static assets di https://job-radar.buitenzorg.dev (`npm run deploy`), `noindex`. Masih terbuka: perlukah Cloudflare Access (F-13) sebelum `jobs.json` nyata ikut terunggah?
3. Channel Telegram dan email alert mana yang dipakai di Fase 2?
4. ~~Kota kecil~~ Terjawab 25 Nov 2026: gazetteer diperluas dengan ±300 kota dari GeoNames cities15000 (CC BY 4.0, `tools/build_gazetteer.py`). Lowongan yang hanya menyebut provinsi tetap dilewati dan dihitung di `sources[].skipped`.
5. Fase 1 meminta minimal 30 perusahaan; baru 11. Perusahaan Indonesia yang memakai Kalibrr/Jobstreet saja hanya bisa masuk lewat email alert (Fase 2).

# 📄Pendahuluan SAKPORE3

**Aplikasi Perizinan Online** adalah sistem informasi berbasis web yang dirancang untuk memfasilitasi proses permohonan dan pengelolaan izin **non-usaha** di wilayah **Kota Pekalongan**.
Aplikasi ini memungkinkan pemohon, petugas, dan OPD terkait untuk berinteraksi secara digital dalam proses perizinan, mulai dari pengajuan, verifikasi, hingga penyelesaian.

---

## 🔧 Teknologi yang Digunakan

Proyek ini dibangun menggunakan kombinasi teknologi modern yang mendukung skalabilitas, kecepatan pengembangan, dan kemudahan pemeliharaan:

| Stack | Teknologi |
| --- | --- |
| Backend | [Laravel 12](https://laravel.com/) |
| Frontend | [React](https://reactjs.org/) 19 via [Inertia.js](https://inertiajs.com/) |
| Template | Achme (basic dasboard) dengan Shadcn (kumpulan komponen) |
| Database | MySQL |
| Autentikasi | Laravel default authentication |

### 💡 Kenapa Laravel?

- Framework PHP paling populer & didukung komunitas besar
- Fitur bawaan lengkap: routing, validation, policy, queue, dsb.
- Mudah dikembangkan dan aman

### ⚛️ Kenapa React + Inertia.js?

- **SPA (Single Page Application)** tanpa perlu API yang ribet
- Reaktif dan ringan
- Tidak tergantung library berat seperti jQuery
- Mudah dibuat modular & scalable

---

## 🎯 Tujuan Aplikasi

- Mempermudah masyarakat dalam **mengajukan permohonan izin** secara online
- Meningkatkan efisiensi dan transparansi pengelolaan izin oleh OPD
- Meminimalisir proses manual dan penggunaan dokumen fisik
- Menyediakan dasbor pemantauan, sistem notifikasi, dan laporan

---

## 👥 Target Pengguna

- **Pemohon:** Masyarakat umum yang mengajukan izin
- **Petugas:** Front Office (FO), Back Office (BO), dan Verifikator
- **OPD:** Dinas teknis terkait perizinan (juga terdiri dari FO, BO, Verifikator OPD)
- **Administrator:** Pengelola sistem pusat

---

## 🚀 Fitur Utama

- ✅ Registrasi & Login Pemohon
- ✅ Multi-level user dan hak akses bertingkat
- ✅ Manajemen master izin dan persyaratan
- ✅ Alur permohonan izin multi-tahap (FO → BO → OPD → Verifikator)
- ✅ Upload dan validasi dokumen
- ✅ Sistem SKM (Survei Kepuasan Masyarakat)
- ✅ Modul pengaduan dan respon petugas
- ✅ Notifikasi dan log status permohonan

---

## 🧱 Struktur Direktori (Singkat)

Struktur detail tersedia di `docs/struktur-folder.md`. Secara umum:

```bash
project-root/
├── app/
│ ├── Http/
│ ├── Models/
├── resources/
│ ├── js/ ← React components & pages -> fokus pengembangan halaman ada disini
│ └── views/ ← Blade views (minimal)
├── routes/
│ ├── web.php ← Web routes (Inertia)
├── public/
├── docs/ ← Dokumentasi internal

```

---

## 📄 Dokumentasi Lengkap

Lihat folder [`/docs`](http://localhost:3000/docs/docs/) untuk dokumentasi lengkap, meliputi:

- Struktur role & alur kerja (`roles.md`, `flow.md`)
- Skema database (`database/`)
- Dokumentasi endpoint API (`api/`)
- Komponen frontend & plugin tambahan (`komponen.md`, `plugins.md`)

---

## 📦 Instalasi & Setup Lokal

```bash
# Clone project
git clone https://github.com/hendikaseptio/laravel-react.git
cd laravel-react

# Install dependencies
composer install
npm install && npm run dev

# Copy file environment
cp .env.example .env
php artisan key:generate

# Jalankan migrasi & seeder (jika ada)
php artisan migrate --seed

# Jalankan server
php artisan serve
```
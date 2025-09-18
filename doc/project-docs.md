# 📁 Struktur Folder Laravel Project

Berikut ini adalah struktur folder dari proyek Laravel ini:

```plaintext
├── app/
│ ├── Console/
│ ├── Exceptions/
│ ├── Http/
│ │ ├── Controllers/
│ │ ├── Middleware/
│ ├── Models/
│ └── Providers/
├── bootstrap/
├── config/
├── database/
│ ├── factories/
│ ├── migrations/
│ └── seeders/
├── public/
├── resources/
│ ├── js/
│ ├── views/
├── routes/
│ ├── api.php
│ └── web.php
├── storage/
├── tests/
└── vendor/
```
# ⚙️ Alur Kerja Autentikasi

1. User membuka halaman login (`/login`)
2. Form dikirim ke `POST /login`
3. Controller `LoginController` akan memverifikasi kredensial
4. Jika berhasil, user diarahkan ke dashboard
5. Jika gagal, kembali ke halaman login dengan error

# 🔧 Fitur Utama

## 🔐 Autentikasi
- Login, Logout, Register
- Menggunakan Laravel Breeze
- Middleware `auth` untuk melindungi route

## 📨 Manajemen Email
- Fitur forgot password
- Verifikasi email
- Menggunakan Laravel Mail

## 📦 Produk
- CRUD Produk
- Fitur pencarian produk
- Upload gambar

---

# 🔗 Route Penting

| Nama | Method | Path | Controller |
|------|--------|------|------------|
| Login | GET | /login | `AuthController@showLoginForm` |
| Login Submit | POST | /login | `AuthController@login` |
| Dashboard | GET | /dashboard | `DashboardController@index` |
| Produk Index | GET | /produk | `ProdukController@index` |
| Produk Store | POST | /produk | `ProdukController@store` |

---

# 🧠 Catatan Tambahan

- File konfigurasi ada di folder `config/`
- Environment file: `.env`
- Semua model disimpan di `app/Models/`
- Views ada di `resources/views/`
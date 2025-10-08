# KakDika AI Assistant

Sebuah project AI Assistant yang dapat dijalankan menggunakan FastAPI dan Uvicorn.

---

## Cara Install dan Menjalankan

1. **Clone repository**

```bash
git clone https://github.com/hendikaseptio/KakDika-AI-Assistant.git
cd KakDika-AI-Assistant
````

2. **Buat virtual environment**

```bash
python3 -m venv venv
```

3. **Aktifkan virtual environment**

* Jika menggunakan **bash**:

```bash
source venv/bin/activate
```

* Jika menggunakan **fish shell**:

```bash
source venv/bin/activate.fish
```

4. **Install dependencies**

```bash
pip install -r requirements.txt
```

5. **Jalankan aplikasi**

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Keterangan

* Aplikasi berjalan di `http://0.0.0.0:8001`
* Opsi `--reload` memungkinkan aplikasi otomatis restart saat ada perubahan kode (mode development).

---

## API
untuk menggunakan fitur chat melalui api berikut ini:
http://127.0.0.1:8001/chat_stream?session_id=${chatInstance.sessionId}&message=${query}

---

Kalau ada pertanyaan atau ingin kontribusi, silakan buka issue atau pull request.
*Terima kasih sudah menggunakan KakDika AI Assistant!*

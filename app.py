from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer
import os
import faiss
import numpy as np
import re
from numpy.linalg import norm

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = SentenceTransformer("all-MiniLM-L6-v2")
dimension = 384
index = faiss.IndexFlatL2(dimension)

# Simpan chunk beserta metadata judul
chunks_list = []
chunks_metadata = []  # simpan judul/header tiap chunk

def clean_chunk_text(text):
    # Contoh pembersihan sederhana:
    # Hapus tabel markdown agar gak terlalu panjang (baris yg ada '|')
    lines = text.split('\n')
    cleaned = []
    in_code_block = False

    for line in lines:
        

        # Hilangkan baris kosong
        if line.strip() == "":
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()

def chunk_text(text, max_length=400):
    lines = text.split("\n")
    chunks = []
    metadata = []

    current_h1 = None
    current_h2 = None
    current_h3 = None
    current_chunk_h2 = ""
    current_chunk_h3 = ""
    h1_buffer = []

    for line in lines:
        h1_match = re.match(r"^# (?!#)(.+)", line)
        h2_match = re.match(r"^## (?!#)(.+)", line)
        h3_match = re.match(r"^### (.+)", line)

        # H1
        if h1_match:
            # Simpan buffer dari H1 sebelumnya
            if h1_buffer:
                h1_chunk = "\n".join(h1_buffer).strip()
                cleaned = clean_chunk_text(h1_chunk)
                if cleaned:
                    chunks.append(cleaned)
                    metadata.append({
                        "title": current_h1 or "Unknown Section",
                        "type": "h1"
                    })
                h1_buffer = []

            current_h1 = h1_match.group(1).strip()
            current_h2 = None
            current_h3 = None
            current_chunk_h2 = ""
            current_chunk_h3 = ""
            continue

        # H2
        if h2_match:
            # 💡 Tambahkan ini agar H1 tersimpan sebelum heading pertama lainnya muncul
            if h1_buffer and not current_h2 and not current_h3:
                h1_chunk = "\n".join(h1_buffer).strip()
                cleaned = clean_chunk_text(h1_chunk)
                if cleaned:
                    chunks.append(cleaned)
                    metadata.append({
                        "title": current_h1 or "Unknown Section",
                        "type": "h1"
                    })
                h1_buffer = []

            # Simpan chunk dari H3 sebelumnya (kalau ada)
            if current_chunk_h3.strip():
                cleaned = clean_chunk_text(current_chunk_h3)
                if cleaned:
                    chunks.append(cleaned)
                    metadata.append({
                        "title": f"{current_h1} - {current_h2} - {current_h3}",
                        "type": "h3"
                    })
                current_chunk_h3 = ""
                current_h3 = None

            # Simpan chunk H2 sebelumnya (kalau ada)
            if current_chunk_h2.strip():
                cleaned = clean_chunk_text(current_chunk_h2)
                if cleaned:
                    chunks.append(cleaned)
                    metadata.append({
                        "title": f"{current_h1} - {current_h2}",
                        "type": "h2"
                    })
                current_chunk_h2 = ""

            current_h2 = h2_match.group(1).strip()
            current_h3 = None
            current_chunk_h2 = line + "\n"
            h1_buffer.append(line)
            continue

        # H3
        if h3_match:
            # Simpan chunk H3 sebelumnya (kalau ada)
            if current_chunk_h3.strip():
                cleaned = clean_chunk_text(current_chunk_h3)
                if cleaned:
                    chunks.append(cleaned)
                    metadata.append({
                        "title": f"{current_h1} - {current_h2} - {current_h3}",
                        "type": "h3"
                    })
                current_chunk_h3 = ""

            current_h3 = h3_match.group(1).strip()
            current_chunk_h3 = line + "\n"
            h1_buffer.append(line)
            continue

        # Bukan heading → tambahkan ke chunk yang sesuai
        if current_h3:
            current_chunk_h3 += line + "\n"
        elif current_h2:
            current_chunk_h2 += line + "\n"

        if current_h1:
            h1_buffer.append(line)

    # Simpan sisa H3 jika ada
    if current_chunk_h3.strip():
        cleaned = clean_chunk_text(current_chunk_h3)
        if cleaned:
            chunks.append(cleaned)
            metadata.append({
                "title": f"{current_h1} - {current_h2} - {current_h3}",
                "type": "h3"
            })

    # Simpan sisa H2 jika ada
    if current_chunk_h2.strip():
        cleaned = clean_chunk_text(current_chunk_h2)
        if cleaned:
            chunks.append(cleaned)
            metadata.append({
                "title": f"{current_h1} - {current_h2}",
                "type": "h2"
            })

    # Simpan terakhir H1 (kalau belum disimpan)
    if h1_buffer:
        h1_chunk = "\n".join(h1_buffer).strip()
        cleaned = clean_chunk_text(h1_chunk)
        if cleaned:
            chunks.append(cleaned)
            metadata.append({
                "title": current_h1 or "Unknown Section",
                "type": "h1"
            })

    return chunks, metadata

def load_documents():
    global chunks_list, chunks_metadata, index
    chunks_list.clear()
    chunks_metadata.clear()
    index.reset()

    for filename in os.listdir("doc"):
        path = os.path.join("doc", filename)
        if os.path.isfile(path) and (filename.endswith(".md") or filename.endswith(".txt")):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
                chunks, metadata = chunk_text(text)
                embeddings = model.encode(chunks)
                index.add(np.array(embeddings).astype("float32"))
                chunks_list.extend(chunks)
                chunks_metadata.extend(metadata)

load_documents()

def cosine_sim(a, b):
    return np.dot(a, b) / (norm(a) * norm(b) + 1e-10)

@app.post("/search")
async def search_handler(req: Request):
    data = await req.json()
    question = data["question"].lower()
    q_embed = model.encode([question]).astype("float32")

    D, I = index.search(q_embed, 10)  # Ambil top 10 hasil terdekat

    candidates = []
    for idx in I[0]:
        if idx < len(chunks_list):
            chunk = chunks_list[idx]
            meta = chunks_metadata[idx]
            title = meta.get("title", "").lower()
            chunk_type = meta.get("type", "h2")

            # Hitung similarity
            chunk_embed = model.encode([chunk])[0]
            score = cosine_sim(q_embed[0], chunk_embed)
            
            # Tambahkan bobot bertingkat
            type_weights = {"h1": 0.05, "h2": 0.1, "h3": 0.15}
            score += type_weights.get(chunk_type, 0)

            if any(word in title for word in question.split()):
                score += 0.1

            # Jika type-nya H1 dan judul H1 mengandung kata tanya → boost ekstra
            if chunk_type == "h1" and any(word in title for word in question.split()):
                score += 0.2  # boost lebih tinggi karena H1 yang cocok lebih penting

            # Tambahkan bobot ekstra
            # if chunk_type == "h1": score += 0.05
            # if chunk_type == "h2": score += 0.1
            # if chunk_type == "h3": score += 0.15

            candidates.append((score, chunk.strip()))

    # Filter: ambil hanya yang skor similarity-nya cukup tinggi
    candidates = [c for c in candidates if c[0] > 0.3]

    # Urutkan dari skor tertinggi
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Hapus duplikat berdasarkan isi teks
    seen = set()
    unique_results = []
    for score, text in candidates:
        norm_text = re.sub(r'\s+', ' ', text.strip().lower())
        if norm_text not in seen:
            seen.add(norm_text)
            unique_results.append(text)

    return {"answers": unique_results[:3]}

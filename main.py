from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
import asyncio
import json
import ollama
from typing import List
import re
from numpy.linalg import norm
import numpy as np


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# baru bre
# Simpan riwayat chat per session_id di RAM (dictionary)
chat_histories = {}

MAX_HISTORY_LENGTH = 5  # batasi 5 pesan terakhir
# Load FAISS index & texts untuk retrieval
model = SentenceTransformer("all-MiniLM-L6-v2")
dimension = 384
index = faiss.IndexFlatL2(dimension)

chunks_list = []
chunks_metadata = []

def cosine_sim(a, b):
    return np.dot(a, b) / (norm(a) * norm(b) + 1e-10)

def clean_chunk_text(text):
    lines = text.split('\n')
    cleaned = []
    in_code_block = False
    for line in lines:
        if line.strip() == "":
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()

def chunk_text(text, max_length=400):
    import re
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

        if h1_match:
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

        if h2_match:
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

        if h3_match:
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

        if current_h3:
            current_chunk_h3 += line + "\n"
        elif current_h2:
            current_chunk_h2 += line + "\n"

        if current_h1:
            h1_buffer.append(line)

    if current_chunk_h3.strip():
        cleaned = clean_chunk_text(current_chunk_h3)
        if cleaned:
            chunks.append(cleaned)
            metadata.append({
                "title": f"{current_h1} - {current_h2} - {current_h3}",
                "type": "h3"
            })

    if current_chunk_h2.strip():
        cleaned = clean_chunk_text(current_chunk_h2)
        if cleaned:
            chunks.append(cleaned)
            metadata.append({
                "title": f"{current_h1} - {current_h2}",
                "type": "h2"
            })

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

# retrieve chunk
def retrieve_chunks_rag(query: str, top_k: int = 3) -> List[str]:
    q_embed = model.encode([query]).astype("float32")
    D, I = index.search(q_embed, 10)

    candidates = []
    for idx in I[0]:
        if idx < len(chunks_list):
            chunk = chunks_list[idx]
            meta = chunks_metadata[idx]
            title = meta.get("title", "").lower()
            chunk_type = meta.get("type", "h2")

            chunk_embed = model.encode([chunk])[0]
            score = cosine_sim(q_embed[0], chunk_embed)

            type_weights = {"h1": 0.05, "h2": 0.1, "h3": 0.15}
            score += type_weights.get(chunk_type, 0)

            if any(word in title for word in query.split()):
                score += 0.1
            if chunk_type == "h1" and any(word in title for word in query.split()):
                score += 0.2

            candidates.append((score, chunk.strip()))

    candidates = [c for c in candidates if c[0] > 0.3]
    candidates.sort(key=lambda x: x[0], reverse=True)

    seen = set()
    unique_results = []
    for score, text in candidates:
        norm_text = re.sub(r'\s+', ' ', text.strip().lower())
        if norm_text not in seen:
            seen.add(norm_text)
            unique_results.append(text)

    return unique_results[:top_k]

# timpa history
def trim_history(history):
    if len(history) > MAX_HISTORY_LENGTH:
        return history[-MAX_HISTORY_LENGTH:]
    return history

# Generator streaming dari model AI
async def chat_stream_generator(session_id: str, user_message: str):
    try:
        # Ambil riwayat chat user, jika belum ada buat baru
        history = chat_histories.get(session_id, [])

        # Tambah pesan user ke riwayat
        history.append({"role": "user", "content": user_message})

        # Batasi panjang riwayat
        history = trim_history(history)

        # Simpan kembali
        chat_histories[session_id] = history

        retrieved_chunks = retrieve_chunks_rag(user_message, top_k=3)
        context_text = "\n\n".join(retrieved_chunks) if retrieved_chunks else "Tidak ada informasi relevan ditemukan."        
        base_system_prompt = (
            "Halo! Saya KakDika, asisten pribadi cerdas milik Hendika Septio Afitdin, S.Kom.\n\n"
            "Tugas saya adalah membantu menjawab pertanyaan berdasarkan dokumentasi yang telah dibuat dan disusun langsung oleh Mas Hendika. "
            "Saya hanya akan memberikan jawaban yang berasal dari isi dokumentasi tersebut — tidak lebih, tidak kurang.\n\n"
            "Berikut adalah aturan saya dalam menjawab:\n"
            "- Saya **tidak diperbolehkan menebak**, beropini, atau menambahkan informasi yang tidak ada di dokumentasi.\n"
            "- Jika saya **tidak menemukan jawaban** dari dokumentasi, saya akan menjawab dengan kalimat:\n"
            "  'Maaf, informasi itu belum ada di dokumentasi saya.'\n"
            "- Saya akan menjawab dengan **singkat, jelas, dan sopan**.\n\n"
            "==== DOKUMENTASI MULAI ====\n"
            f"{context_text}\n"
            "==== DOKUMENTASI SELESAI ====\n"
        )


        # context_text = "\n\n".join(retrieved_chunks) if retrieved_chunks else "Tidak ada informasi relevan ditemukan."

        system_prompt = {
            "role": "system",
            "content": base_system_prompt
        }

        messages = [system_prompt] + history

        # Panggil ollama dengan streaming
        response = ollama.chat(
            model='gemma:2b',
            # model='mistral:instruct',
            messages=messages,
            stream=True
        )

        # Streaming token ke frontend
        full_response = ""
        for chunk in response:
            if 'message' in chunk and 'content' in chunk['message']:
                token = chunk['message']['content']
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
                await asyncio.sleep(0)

        history.append({"role": "assistant", "content": full_response})
        chat_histories[session_id] = trim_history(history)

    except Exception as e:
        yield f"data: {json.dumps({'token': '[Terjadi kesalahan: ' + str(e) + ']'} )}\n\n"

# Endpoint streaming untuk frontend
@app.get("/chat_stream")
async def chat_stream(request: Request):
    session_id = request.query_params.get("session_id")
    user_message = request.query_params.get("message")

    if not session_id or not user_message:
        raise HTTPException(status_code=400, detail="session_id dan message diperlukan")

    return StreamingResponse(
        chat_stream_generator(session_id, user_message),
        media_type="text/event-stream"
    )

# # Register route
# app.include_router(search.router)
# app.include_router(chat.router)

# # Load dokumen saat startup
# @app.on_event("startup")
# def startup_event():
#     load_documents()

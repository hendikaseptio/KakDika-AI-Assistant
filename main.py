from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sentence_transformers import SentenceTransformer
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import List
from numpy.linalg import norm

import chromadb
import faiss
import pickle
import os
import asyncio
import json
import ollama
import re
import numpy as np
import time


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_histories = {}

MAX_HISTORY_LENGTH = 5 
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_data")
current_collection = None
collection = chroma_client.get_or_create_collection(
    name="documents",
    embedding_function=embedding_function
)

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
    global current_collection
    
    # Buat nama collection baru dengan timestamp supaya unik
    collection_name = f"documents_{int(time.time())}"

    # Buat collection baru
    current_collection = chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function
    )

    for filename in os.listdir("doc"):
        path = os.path.join("doc", filename)
        if os.path.isfile(path) and (filename.endswith(".md") or filename.endswith(".txt")):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
                chunks, metadata = chunk_text(text)

                documents = []
                metadatas = []
                ids = []

                for i, chunk in enumerate(chunks):
                    doc_id = f"{filename}_{i}"
                    documents.append(chunk)
                    metadatas.append(metadata[i])
                    ids.append(doc_id)

                current_collection.add(documents=documents, metadatas=metadatas, ids=ids)

load_documents()

# retrieve chunk
def retrieve_chunks_rag(query: str, top_k: int = 3) -> List[str]:
    global current_collection
    if current_collection is None:
        return []
    
    results = current_collection.query(
        query_texts=[query],
        n_results=top_k
    )

    if not results["documents"]:
        return []

    return [doc for doc in results["documents"][0]]

# timpa history
def trim_history(history):
    if len(history) > MAX_HISTORY_LENGTH:
        return history[-MAX_HISTORY_LENGTH:]
    return history

# Generator streaming dari model AI
async def chat_stream_generator(session_id: str, user_message: str):
    try:
        history = chat_histories.get(session_id, [])
        history.append({"role": "user", "content": user_message})
        history = trim_history(history)

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
            "- Semua informasi utamakan ambil dari dokumentasi.\n"
            "==== DOKUMENTASI MULAI ====\n"
            f"{context_text}\n"
            "==== DOKUMENTASI SELESAI ====\n"
        )

        system_prompt = {
            "role": "system",
            "content": base_system_prompt
        }

        messages = [system_prompt] + history

        # ollama_base_url = "http://192.168.30.234:11434"
        # client = ollama.Client(host=ollama_base_url)
        response = ollama.chat(
            model='gemma:2b',
            messages=messages,
            stream=True
        )

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
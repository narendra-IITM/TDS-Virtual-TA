from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import torch
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from starlette.responses import JSONResponse
import base64
from PIL import Image
import io

app = FastAPI()

# Load FAISS index and metadata
index = faiss.read_index("discourse_index.faiss")
with open("discourse_metadata.pkl", "rb") as f:
    metadata = pickle.load(f)

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Request schema
class QARequest(BaseModel):
    question: str
    image: Optional[str] = None  # base64 image

def extract_text_from_base64_image(base64_string):
    try:
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        return "[image detected: OCR not implemented yet]"
    except Exception as e:
        return f"[image decode error: {e}]"

@app.post("/api/")
async def answer_question(request: QARequest):
    full_query = request.question
    if request.image:
        full_query += "\n" + extract_text_from_base64_image(request.image)

    query_embedding = model.encode([full_query])
    D, I = index.search(query_embedding, k=1)
    top_index = I[0][0]
    top_doc = metadata[top_index]

    if isinstance(top_doc, dict):
        content = top_doc.get("content", "⚠️ No 'content' field found.")
    else:
        content = top_doc

    answer = f"✅ Based on Discourse content: {content}"
    return JSONResponse(content={"answer": answer})


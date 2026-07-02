import os
import json
import fitz
from minio import Minio
from qdrant_client import QdrantClient
from langchain_text_splitters import RecursiveCharacterTextSplitter

MINIO_URL = os.getenv("MINIO_URL", "minio:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY", "password123")
BUCKET_NAME = "dealership-brochures"

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "dealership_knowledge"
STATE_FILE = "/app/mcp_servers/custom_rag_mcp/sync_state.json"

def get_sync_state():
    """Reads the local state file to remember which PDFs we already processed."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_sync_state(state):
    """Saves the updated state to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def run_ingestion():
    print("Starting RAG Ingestion Pipeline...")
    minio_client = Minio(MINIO_URL, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)
    qdrant_client = QdrantClient(url=QDRANT_URL)
    if not qdrant_client.collection_exists(COLLECTION_NAME):
        print(f"Creating new Qdrant collection: {COLLECTION_NAME}")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_client.get_fastembed_vector_params()
        )
    state = get_sync_state()
    objects = minio_client.list_objects(BUCKET_NAME)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    processed_count = 0
    for obj in objects:
        filename = obj.object_name
        etag = obj.etag
        if filename in state and state[filename] == etag:
            continue
        print(f"Processing new or updated file: {filename}")
        response = minio_client.get_object(BUCKET_NAME, filename)
        pdf_bytes = response.read()
        response.close()
        response.release_conn()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        chunks = text_splitter.split_text(full_text)
        print(f"   Split into {len(chunks)} chunks.")
        metadata = [{"source": filename, "chunk_index": i} for i in range(len(chunks))]
        qdrant_client.add(
            collection_name=COLLECTION_NAME,
            documents=chunks,
            metadata=metadata
        )
        state[filename] = etag
        processed_count += 1
        print(f"   Successfully stored in Qdrant.")
    save_sync_state(state)
    if processed_count == 0:
        print("No new files to process. Qdrant is fully synced with MinIO.")
    else:
        print(f"Ingestion complete! Processed {processed_count} new files.")
if __name__ == "__main__":
    run_ingestion()
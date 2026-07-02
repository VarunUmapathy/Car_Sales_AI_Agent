import os
from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "dealership_knowledge"
mcp = FastMCP("Dealership_RAG_MCP")
qdrant_client = QdrantClient(url=QDRANT_URL)

@mcp.tool()
def search_knowledge_base(query: str) -> str:
    """
    Search the unstructured knowledge base (PDF brochures, policies).
    Use this to answer questions about vehicle features, specifications, 
    towing capacity, fuel economy, warranties, or general dealership info.
    
    Args:
        query: The specific question or search term (e.g., 'What is the RAV4 towing capacity?').
    """
    try:
        if not qdrant_client.collection_exists(COLLECTION_NAME):
            return "The knowledge base is currently empty. Please run the ingestion pipeline first."
        search_results = qdrant_client.query(
            collection_name=COLLECTION_NAME,
            query_text=query,
            limit=4
        )
        if not search_results:
            return "No relevant information found in the knowledge base."
        formatted_results = []
        for hit in search_results:
            text = hit.document
            source = hit.metadata.get("source", "Unknown Document")
            formatted_results.append(f"--- [Source: {source}] ---\n{text}\n")
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error querying vector database: {str(e)}"
if __name__ == "__main__":
    mcp.run()
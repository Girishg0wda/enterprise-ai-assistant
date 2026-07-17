import logging
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

class DocumentTool:
    def __init__(self):
        self.name = "document_tool"
        self.description = (
            "Retrieves unstructured information from company documentation, PDFs, "
            "office guidelines, operating hours, policies, or standard enterprise knowledge bases."
        )

    def execute(self, query_text: str, user_id: int, user_role: str) -> str:
        """Queries the Qdrant hybrid vector core engine for relevant document chunks."""
        try:
            logger.info(f"📚 [Document Tool] Querying vector space for context: '{query_text}'")
            matched_chunks = search_service.search_similar_chunks(
                query_text=query_text, user_id=user_id, user_role=user_role, limit=3
            )
            
            if not matched_chunks:
                return "Document Tool Result: No relevant company documentation found."
                
            context_blocks = []
            for chunk in matched_chunks:
                context_blocks.append(
                    f"From Doc: {chunk.document_name} (Index: {chunk.chunk_index}):\n{chunk.content}"
                )
            
            return "Document Tool Content Retrieved:\n\n" + "\n---\n".join(context_blocks)
        except Exception as e:
            logger.error(f"Document Tool matrix lookup failed: {str(e)}")
            return f"Document Tool exception: {str(e)}"
import re

class ChunkService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> list[str]:
       
        if not text or not text.strip():
            return []

        # 1. Split by Paragraph
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 2. If structural paragraph fits, add it directly
            if len(current_chunk) + (1 if current_chunk else 0) + len(para) <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
            else:
                # Paragraph doesn't fit! Fallback to Sentence processing
                sentences = re.split(r'(?<=[.!?])\s+', para)
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    
                    # If sentence fits in current running block
                    if len(current_chunk) + (1 if current_chunk else 0) + len(sentence) <= self.chunk_size:
                        current_chunk = f"{current_chunk} {sentence}" if current_chunk else sentence
                    else:
                        # Flush completed chunk block if it exists
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk

                        if len(sentence) > self.chunk_size:
                            start = 0
                            while start < len(sentence):
                                end = start + self.chunk_size
                                sub_chunk = sentence[start:end]
                                
                                if len(sub_chunk) == self.chunk_size:
                                    chunks.append(sub_chunk)
                                    start += (self.chunk_size - self.chunk_overlap)
                                else:
                                    current_chunk = sub_chunk
                                    start = end
                        else:
                            
                            current_chunk = f"{current_chunk} {sentence}" if current_chunk else sentence

        if current_chunk and current_chunk.strip():
            chunks.append(current_chunk)

        return chunks

chunk_service = ChunkService()
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class PDFService:
    def extract_text(self, file_path: str) -> str:
        """
        Reads a physical PDF from disk, iterates through its pages, 
        extracts raw characters, and cleans up irregular spacing.
        """
        try:
            reader = PdfReader(file_path)
            extracted_pages = []

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
                else:
                    logger.warning(f"No parseable text layer found on page {page_num} of {file_path}")

            # Combine pages using a clean layout spacing line break structure
            raw_text = "\n\n".join(extracted_pages)
            
            # Clean text: Normalize irregular spacing and clean up whitespace bloating
            cleaned_text = self._clean_text(raw_text)
            return cleaned_text

        except Exception as e:
            logger.error(f"Failed parsing PDF file at {file_path}: {str(e)}")
            raise RuntimeError(f"PDF extraction subsystem engine failure: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """Strips out excessive blank line gaps and normalizes layouts."""
        if not text:
            return ""
        
        # Split into individual lines to purge padding lines cleanly
        lines = [line.strip() for line in text.splitlines()]
        
        # Filter out multiple consecutive blank lines, keeping structural paragraph gaps
        cleaned_lines = []
        for line in lines:
            if line:
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1] != "":
                # Keep exactly one blank line gap between block changes
                cleaned_lines.append("")
                
        return "\n".join(cleaned_lines).strip()

# Single state instantiation export
pdf_service = PDFService()
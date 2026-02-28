from pathlib import Path

from pypdf import PdfReader


class PDFService:
    @staticmethod
    def extract_text(pdf_path: str):
        path = Path(pdf_path)

        if not path.is_file():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        extension = path.suffix.lower()

        if extension != ".pdf":
            raise FileExistsError("Extension not supported")
        try:
            reader = PdfReader(str(path))

            text = ""
            for page in reader.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text
            return text
        except Exception as e:
            raise ValueError(f"Failed to extract text: {e}") from e


pdf_service = PDFService()

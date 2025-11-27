import os
from typing import List

class Loader:
    def __init__(self, root_folder: str):
        self.root_folder = root_folder

    # ------------------------------
    # Generic Utility - Reusable
    # ------------------------------
    def _get_files_by_extension(self, extension: str) -> List[str]:
        """Recursively collect all files matching extension."""
        matched_files = []
        for root, dirs, files in os.walk(self.root_folder):
            for file in files:
                if file.lower().endswith(extension.lower()):
                    matched_files.append(os.path.join(root, file))
        return matched_files

    # ------------------------------
    # Dataset 1: Supreme Court Judgments
    # ------------------------------
    def load_sc_judgment_pdfs(self) -> List[str]:
        """Load all SC judgment PDFs. return List of file paths.then use TextExtractor to extract text."""
        return self._get_files_by_extension(".pdf")
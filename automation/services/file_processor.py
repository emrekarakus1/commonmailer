"""
File processing service for handling uploads and attachments.
"""
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from django.core.files.uploadedfile import UploadedFile
from pathlib import Path

from ..exceptions import FileProcessingError
from .attach_matcher import (
    collect_files_from_upload,
    match_files_for_company,
    build_graph_attachments,
    cleanup_temp_directory
)

try:
    import rarfile
    RAR_SUPPORT = True
except ImportError:
    RAR_SUPPORT = False

logger = logging.getLogger(__name__)


class FileProcessorService:
    """Service for processing uploaded files and attachments."""
    
    def __init__(self, base_temp_dir: Optional[Path] = None):
        self.base_temp_dir = base_temp_dir or Path("tmp_uploads")
        self.base_temp_dir.mkdir(exist_ok=True)
    
    def process_uploaded_files(
        self,
        uploaded_files: List[UploadedFile]
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Process uploaded files (ZIP or individual files).
        
        Args:
            uploaded_files: List of Django uploaded file objects
            
        Returns:
            Tuple of (processed_files_list, temp_directory_path)
            
        Raises:
            FileProcessingError: If file processing fails
        """
        try:
            return collect_files_from_upload(uploaded_files, self.base_temp_dir)
        except Exception as e:
            logger.error(f"Error processing uploaded files: {e}")
            raise FileProcessingError(f"Failed to process uploaded files: {e}") from e
    
    def find_matching_files(
        self,
        company_name: str,
        files: List[Dict[str, Any]],
        max_file_mb: int = 20
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Find files matching a company name.
        
        Args:
            company_name: Company name to match
            files: List of file dictionaries
            max_file_mb: Maximum file size in MB
            
        Returns:
            Tuple of (matched_files, warnings)
        """
        try:
            return match_files_for_company(company_name, files, max_file_mb)
        except Exception as e:
            logger.error(f"Error finding matching files for '{company_name}': {e}")
            raise FileProcessingError(f"Failed to find matching files: {e}") from e
    
    def build_attachments(
        self,
        matched_files: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Build Graph API attachments from matched files.
        
        Args:
            matched_files: List of matched file dictionaries
            
        Returns:
            List of Graph attachment dictionaries
            
        Raises:
            FileProcessingError: If attachment building fails
        """
        try:
            return build_graph_attachments(matched_files)
        except Exception as e:
            logger.error(f"Error building attachments: {e}")
            raise FileProcessingError(f"Failed to build attachments: {e}") from e
    
    def cleanup_temp_files(self, temp_dir: str) -> bool:
        """
        Clean up temporary files.
        
        Args:
            temp_dir: Temporary directory path
            
        Returns:
            True if cleanup was successful
        """
        try:
            return cleanup_temp_directory(temp_dir)
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")
            return False
    
    def encode_single_file(self, file_obj: UploadedFile) -> Dict[str, str]:
        """
        Encode a single uploaded file as Graph attachment.
        
        Args:
            file_obj: Django uploaded file object
            
        Returns:
            Graph attachment dictionary
            
        Raises:
            FileProcessingError: If encoding fails
        """
        try:
            content = file_obj.read()
            b64 = base64.b64encode(content).decode("utf-8")
            
            return {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": file_obj.name,
                "contentType": file_obj.content_type or "application/octet-stream",
                "contentBytes": b64,
            }
        except Exception as e:
            logger.error(f"Error encoding file {file_obj.name}: {e}")
            raise FileProcessingError(f"Failed to encode file: {e}") from e


# Global instance
file_processor = FileProcessorService()

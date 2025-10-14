"""
Reporting service for generating Excel reports.
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import io

from ..exceptions import ReportGenerationError

logger = logging.getLogger(__name__)

# Try to import from reports module, otherwise use fallback implementation
try:
    from reports.utils import generate_excel_report
except ModuleNotFoundError:
    logger.warning("reports.utils not found, using fallback Excel generation")
    
    def generate_excel_report(
        rows,
        output_path: Optional[str] = None,
        sheet_name: str = "Report"
    ) -> Optional[bytes]:
        """
        Fallback Excel report generator using pandas and xlsxwriter directly.
        """
        import pandas as pd
        
        # Convert to DataFrame if needed
        if isinstance(rows, pd.DataFrame):
            df = rows.copy()
        else:
            rows = list(rows or [])
            if not rows:
                raise ValueError("No data to generate report from")
            df = pd.DataFrame(rows)
        
        if df.empty:
            raise ValueError("DataFrame is empty, cannot generate report")
        
        if output_path:
            # Save to file
            import os
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name)
            return None
        else:
            # Return bytes for HTTP response
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name=sheet_name)
            return buf.getvalue()


class ReportingService:
    """Service for generating reports."""
    
    def __init__(self):
        self._reports_dir = Path("reports")
        self._reports_dir.mkdir(exist_ok=True)
    
    def generate_mail_report(
        self,
        results: List[Dict[str, Any]],
        output_path: Optional[str] = None,
        sheet_name: str = "Mail Results"
    ) -> Optional[bytes]:
        """
        Generate Excel report from mail results.
        
        Args:
            results: List of mail result dictionaries
            output_path: Optional path to save file
            sheet_name: Excel sheet name
            
        Returns:
            Bytes content if output_path is None, otherwise None
            
        Raises:
            ReportGenerationError: If report generation fails
        """
        try:
            if not results:
                raise ReportGenerationError("No results to generate report from")
            
            # Reorder columns for better readability
            column_order = [
                'email', 'company_name', 'matched_files', 
                'sent_with_attachments', 'status', 'error_detail'
            ]
            
            # Create DataFrame and reorder columns
            import pandas as pd
            df = pd.DataFrame(results)
            
            # Only reorder if all columns exist
            existing_columns = [col for col in column_order if col in df.columns]
            if existing_columns:
                df = df.reindex(columns=existing_columns)
            
            return generate_excel_report(df, output_path=output_path, sheet_name=sheet_name)
            
        except Exception as e:
            logger.error(f"Error generating mail report: {e}")
            raise ReportGenerationError(f"Failed to generate report: {e}") from e
    
    def save_report_to_file(
        self,
        results: List[Dict[str, Any]],
        filename: str,
        sheet_name: str = "Mail Results"
    ) -> str:
        """
        Save report to file and return the file path.
        
        Args:
            results: List of mail result dictionaries
            filename: Output filename
            sheet_name: Excel sheet name
            
        Returns:
            Path to the saved file
        """
        output_path = self._reports_dir / filename
        self.generate_mail_report(results, output_path=str(output_path), sheet_name=sheet_name)
        return str(output_path)
    
    def generate_report_bytes(
        self,
        results: List[Dict[str, Any]],
        sheet_name: str = "Mail Results"
    ) -> bytes:
        """
        Generate report as bytes for HTTP response.
        
        Args:
            results: List of mail result dictionaries
            sheet_name: Excel sheet name
            
        Returns:
            Report content as bytes
        """
        content = self.generate_mail_report(results, output_path=None, sheet_name=sheet_name)
        if content is None:
            raise ReportGenerationError("Failed to generate report bytes")
        return content


# Global instance
reporting_service = ReportingService()

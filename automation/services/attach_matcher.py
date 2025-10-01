import os
import mimetypes
import zipfile
import tempfile
import shutil
import base64
from pathlib import Path
from typing import List, Dict, Tuple, Any
import logging

try:
    import rarfile
    RAR_SUPPORT = True
except ImportError:
    RAR_SUPPORT = False

logger = logging.getLogger(__name__)


def norm(s: str) -> str:
    """
    Locale-safe lowercasing for Turkish 'İ'/'I' etc.
    casefold() is more aggressive than lower() and works better for i/İ edge cases
    """
    return (s or "").strip().casefold()


def collect_files_from_upload(uploaded_files: List, base_tmp_dir: Path) -> Tuple[List[Dict[str, Any]], str]:
    """
    Accept either:
      - a single ZIP file, OR
      - multiple loose files
    Returns a tuple of (files_list, temp_dir_path)
    files_list contains dicts: { "name": <filename>, "path": <abs_path>, "size": <int>, "content_type": <str> }
    All files are stored under a request-scoped temp folder to ensure we reference on-disk paths.
    """
    try:
        tmp_root = Path(tempfile.mkdtemp(prefix="invoices_", dir=base_tmp_dir))
        results = []
        
        logger.debug(f"Created temp directory: {tmp_root}")
    except Exception as e:
        logger.error(f"Failed to create temp directory: {e}")
        raise ValueError(f"Failed to create temporary directory: {e}")

    def push_file(p: Path):
        """Helper to add file metadata to results"""
        try:
            ctype, _ = mimetypes.guess_type(str(p))
            size = p.stat().st_size
            results.append({
                "name": p.name, 
                "path": str(p), 
                "size": size, 
                "content_type": ctype or "application/octet-stream"
            })
            logger.debug(f"Added file: {p.name} ({size} bytes, {ctype})")
        except Exception as e:
            logger.error(f"Error processing file {p}: {e}")

    # If the form only allows one file input, uploaded_files will be length 1
    for f in uploaded_files:
        fname = Path(f.name)
        logger.debug(f"Processing uploaded file: {fname}")
        
        if fname.suffix.lower() == ".zip":
            # extract zip safely
            tmp_zip_dir = tmp_root / (fname.stem + "_unzipped")
            tmp_zip_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Extracting ZIP to: {tmp_zip_dir}")
            
            try:
                with zipfile.ZipFile(f, "r") as zf:
                    for member in zf.infolist():
                        # skip directories
                        if member.is_dir():
                            continue
                        # avoid path traversal
                        safe_name = Path(member.filename).name
                        out_path = tmp_zip_dir / safe_name
                        logger.debug(f"Extracting: {member.filename} -> {out_path}")
                        
                        with zf.open(member) as src, open(out_path, "wb") as dst:
                            dst.write(src.read())
                        push_file(out_path)
            except zipfile.BadZipFile as e:
                logger.error(f"Invalid ZIP file {fname}: {e}")
                raise ValueError(f"Invalid ZIP file: {fname}")
            except Exception as e:
                logger.error(f"Error extracting ZIP {fname}: {e}")
                raise ValueError(f"Failed to extract ZIP file {fname}: {e}")
        
        elif fname.suffix.lower() == ".rar":
            # extract rar safely
            if not RAR_SUPPORT:
                logger.error(f"RAR support not available. Please install rarfile: pip install rarfile")
                raise ValueError(f"RAR support not available. Please install rarfile: pip install rarfile")
            
            tmp_rar_dir = tmp_root / (fname.stem + "_unrarred")
            tmp_rar_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Extracting RAR to: {tmp_rar_dir}")
            
            try:
                with rarfile.RarFile(f) as rf:
                    for member in rf.infolist():
                        # skip directories
                        if member.is_dir():
                            continue
                        # avoid path traversal
                        safe_name = Path(member.filename).name
                        out_path = tmp_rar_dir / safe_name
                        logger.debug(f"Extracting: {member.filename} -> {out_path}")
                        
                        with rf.open(member) as src, open(out_path, "wb") as dst:
                            dst.write(src.read())
                        push_file(out_path)
            except rarfile.BadRarFile as e:
                logger.error(f"Invalid RAR file {fname}: {e}")
                raise ValueError(f"Invalid RAR file: {fname}")
            except Exception as e:
                logger.error(f"Error extracting RAR {fname}: {e}")
                raise ValueError(f"Failed to extract RAR file {fname}: {e}")
        else:
            # loose file: copy to tmp_root
            out_path = tmp_root / fname.name
            logger.debug(f"Copying loose file to: {out_path}")
            
            try:
                with open(out_path, "wb") as dst:
                    for chunk in f.chunks():
                        dst.write(chunk)
                push_file(out_path)
            except Exception as e:
                logger.error(f"Error copying file {fname}: {e}")
                raise ValueError(f"Failed to copy file {fname}: {e}")

    logger.debug(f"Collected {len(results)} files from upload")
    return results, str(tmp_root)


def match_files_for_company(company_name: str, files: List[Dict[str, Any]], max_file_mb: int = 20) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Returns (matched_files, warnings).
    - Match rule: norm(company_name) is a substring of norm(file["name"])
    - Attach ALL matches, across any extension.
    - Skip any single file larger than max_file_mb.
    """
    warns = []
    if not company_name:
        logger.debug("No company name provided, no files will match")
        return [], warns

    needle = norm(company_name)
    matched = []
    logger.debug(f"Looking for company: '{company_name}' (normalized: '{needle}')")
    
    for f in files:
        filename = f["name"]
        filename_norm = norm(filename)
        logger.debug(f"Checking file: '{filename}' (normalized: '{filename_norm}')")
        
        if needle and needle in filename_norm:
            size_mb = f["size"] / (1024 * 1024)
            if size_mb > max_file_mb:
                warn_msg = f"Skipped large file >{max_file_mb}MB: {filename}"
                warns.append(warn_msg)
                logger.warning(warn_msg)
                continue
            matched.append(f)
            logger.debug(f"MATCH: '{filename}' contains '{company_name}'")
        else:
            logger.debug(f"NO MATCH: '{filename}' does not contain '{company_name}'")
    
    logger.debug(f"Found {len(matched)} matching files for company '{company_name}'")
    return matched, warns


def build_graph_attachments(matched_files: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Build Microsoft Graph attachment objects from matched files.
    """
    import base64
    
    attachments = []
    for file_info in matched_files:
        try:
            with open(file_info['path'], 'rb') as f:
                content_bytes = f.read()
            content_b64 = base64.b64encode(content_bytes).decode('ascii')
            attachment = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": file_info['name'],
                "contentBytes": content_b64,
                "contentType": file_info['content_type']
            }
            attachments.append(attachment)
            logger.debug(f"Built attachment for: {file_info['name']}")
        except Exception as e:
            logger.error(f"Error reading file {file_info['name']}: {e}")
            continue
    
    logger.debug(f"Built {len(attachments)} Graph attachments")
    return attachments


def cleanup_temp_directory(temp_dir: str) -> bool:
    """
    Safely cleanup temporary directory.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(f"Successfully cleaned up temp directory: {temp_dir}")
            return True
        else:
            logger.debug(f"Temp directory does not exist: {temp_dir}")
            return True
    except Exception as e:
        logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
        return False


def build_graph_file_attachment_from_path(file_path: str, content_type: str | None = None) -> Dict[str, str]:
    """
    Build a Graph API file attachment from a file path.
    Returns a dictionary suitable for Microsoft Graph API.
    """
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        
        b64 = base64.b64encode(data).decode("utf-8")
        name = os.path.basename(file_path)
        
        # Guess content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = "application/octet-stream"
        
        attachment = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": name,
            "contentType": content_type,
            "contentBytes": b64,
        }
        
        logger.debug(f"Built Graph attachment: {name} ({len(data)} bytes, {content_type})")
        return attachment
        
    except Exception as e:
        logger.error(f"Error building attachment from {file_path}: {e}")
        raise

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import msal
import requests

# Reserved OIDC scopes that must not be sent to MSAL in this flow
RESERVED_SCOPES = {"openid", "profile", "offline_access"}


# -------------------- Email templates --------------------
TEMPLATES_FILE = Path(os.getenv("EMAIL_TEMPLATES_PATH", Path.cwd() / "email_templates.json"))


def load_email_templates() -> Dict[str, Dict[str, str]]:
    """Load templates as {name: {subject, body}}.

    Backwards compatible with {name: body} legacy format.
    """
    if not TEMPLATES_FILE.exists():
        return {}
    with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    normalized: Dict[str, Dict[str, str]] = {}
    for name, value in data.items():
        if isinstance(value, dict):
            subject = str(value.get("subject", ""))
            body = str(value.get("body", ""))
        else:
            subject = ""
            body = str(value)
        normalized[str(name)] = {"subject": subject, "body": body}
    return normalized


def save_email_templates(templates: Dict[str, Dict[str, str]]) -> None:
    # Ensure directory exists
    TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Persist as {name: {subject, body}}
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)


def render_template(template: str, row: Dict[str, Any]) -> str:
    try:
        return template.format(**row)
    except Exception:
        # Fallback: don't crash rendering
        return template


# -------------------- Microsoft Graph --------------------
@dataclass
class GraphConfig:
    tenant_id: str
    client_id: str
    scopes: List[str]


def build_graph_config() -> GraphConfig:
    tenant_id = os.getenv("GRAPH_TENANT_ID", "common")
    client_id = os.getenv("GRAPH_CLIENT_ID", "")
    scopes_raw = os.getenv("GRAPH_SCOPES", "Mail.Send")
    scopes = [s for s in scopes_raw.split() if s]
    # Strictly filter reserved scopes, do NOT auto-add anything
    scopes = [s for s in scopes if s not in RESERVED_SCOPES]
    # Debug print to confirm what goes to MSAL
    try:
        print("SCOPES GOING TO MSAL:", scopes)
    except Exception:
        pass
    return GraphConfig(tenant_id=tenant_id, client_id=client_id, scopes=scopes)


def acquire_device_code_token(cfg: GraphConfig) -> Optional[dict]:
    if not cfg.client_id:
        return None
    app = msal.PublicClientApplication(client_id=cfg.client_id, authority=f"https://login.microsoftonline.com/{cfg.tenant_id}")
    # Ensure only cleaned scopes are used
    cleaned_scopes = [s for s in cfg.scopes if s not in RESERVED_SCOPES]
    try:
        print("SCOPES GOING TO MSAL:", cleaned_scopes)
    except Exception:
        pass
    flow = app.initiate_device_flow(scopes=cleaned_scopes)
    return flow


def poll_device_code_token(cfg: GraphConfig, flow: dict) -> Optional[dict]:
    app = msal.PublicClientApplication(client_id=cfg.client_id, authority=f"https://login.microsoftonline.com/{cfg.tenant_id}")
    result = app.acquire_token_by_device_flow(flow)  # blocking until complete or timeout
    return result


def send_mail_via_graph(access_token: str, to: str, subject: str, content_html: str, cc: Optional[List[str]] = None) -> requests.Response:
    url = "https://graph.microsoft.com/v1.0/me/sendMail"
    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": content_html},
            "toRecipients": [{"emailAddress": {"address": to}}],
        },
        "saveToSentItems": True,
    }
    if cc:
        payload["message"]["ccRecipients"] = [
            {"emailAddress": {"address": addr}} for addr in cc if addr
        ]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    return resp


# -------------------- File Processing Utilities --------------------

import mimetypes
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Any


def extract_uploaded_files(uploaded_files: List, temp_dir: str) -> List[Dict[str, Any]]:
    """Extract uploaded files (ZIP or individual) to temp directory and return metadata."""
    import logging
    logger = logging.getLogger(__name__)
    extracted_files = []
    
    for uploaded_file in uploaded_files:
        try:
            file_name = uploaded_file.name
            file_path = os.path.join(temp_dir, file_name)
            
            logger.debug(f"Processing uploaded file: {file_name}")
            
            # For files uploaded via Django's TemporaryFileUploadHandler,
            # they may already be on disk. Check if the file exists first.
            if hasattr(uploaded_file, 'temporary_file_path'):
                # File is already on disk
                temp_file_path = uploaded_file.temporary_file_path()
                logger.debug(f"File already on disk: {temp_file_path}")
                
                # Copy to our temp directory
                import shutil
                shutil.copy2(temp_file_path, file_path)
            else:
                # File is in memory, save using chunks to avoid memory issues
                logger.debug(f"Saving file from memory to: {file_path}")
                with open(file_path, 'wb') as dest:
                    for chunk in uploaded_file.chunks(chunk_size=8192):  # 8KB chunks
                        dest.write(chunk)
            
            # Check if it's a ZIP file
            if file_name.lower().endswith('.zip'):
                logger.debug(f"Extracting ZIP file: {file_name}")
                zip_extracted = extract_zip_file(file_path, temp_dir)
                extracted_files.extend(zip_extracted)
                # Remove the original ZIP file
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # File might already be removed
            else:
                # Individual file
                logger.debug(f"Processing individual file: {file_name}")
                file_info = get_file_info(file_path, file_name)
                if file_info:
                    extracted_files.append(file_info)
                    
        except Exception as e:
            logger.error(f"Error processing file {uploaded_file.name}: {e}", exc_info=True)
            continue
    
    logger.debug(f"Extracted {len(extracted_files)} files total")
    return extracted_files


def extract_zip_file(zip_path: str, temp_dir: str) -> List[Dict[str, Any]]:
    """Extract ZIP file and return list of file metadata."""
    import zipfile
    extracted_files = []
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if not file_info.is_dir():
                    # Extract file
                    zip_ref.extract(file_info, temp_dir)
                    extracted_path = os.path.join(temp_dir, file_info.filename)
                    
                    # Get file metadata
                    file_metadata = get_file_info(extracted_path, os.path.basename(file_info.filename))
                    if file_metadata:
                        extracted_files.append(file_metadata)
                        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error extracting ZIP file {zip_path}: {e}")
    
    return extracted_files


def get_file_info(file_path: str, filename: str) -> Dict[str, Any]:
    """Get file metadata including size, MIME type, and validation."""
    try:
        file_size = os.path.getsize(file_path)
        
        # Size check (20MB limit per file)
        max_size = 20 * 1024 * 1024  # 20MB
        if file_size > max_size:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"File {filename} is too large ({file_size} bytes), skipping")
            return None
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        return {
            'filename': filename,
            'filepath': file_path,
            'size': file_size,
            'mime_type': mime_type
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting file info for {file_path}: {e}")
        return None


def find_matching_files(company_name: str, file_list: List[Dict[str, Any]]) -> List[str]:
    """Find all files that match the company name (case-insensitive substring search)."""
    if not company_name or not company_name.strip():
        return []
    
    company_lower = company_name.strip().lower()
    matching_files = []
    
    for file_info in file_list:
        filename_lower = file_info['filename'].lower()
        if company_lower in filename_lower:
            matching_files.append(file_info['filename'])
    
    return matching_files


def build_attachment_objects(matched_files: List[str], file_list: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Build Microsoft Graph attachment objects from matched files."""
    attachments = []
    
    for filename in matched_files:
        # Find file info
        file_info = next((f for f in file_list if f['filename'] == filename), None)
        if not file_info:
            continue
            
        try:
            # Read file and encode
            with open(file_info['filepath'], 'rb') as f:
                content_bytes = f.read()
            
            import base64
            content_b64 = base64.b64encode(content_bytes).decode('ascii')
            
            attachment = {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": filename,
                "contentBytes": content_b64,
                "contentType": file_info['mime_type']
            }
            attachments.append(attachment)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error reading file {filename}: {e}")
            continue
    
    return attachments


def generate_excel_report(results: List[Dict[str, Any]], output_path: str) -> None:
    """Generate Excel report from processing results."""
    from reports.utils import generate_excel_report as _generate_excel_report
    
    # Reorder columns for better readability
    column_order = ['email', 'company_name', 'matched_files', 'sent_with_attachments', 'status', 'error_detail']
    
    # Create DataFrame and reorder columns
    import pandas as pd
    df = pd.DataFrame(results)
    df = df.reindex(columns=column_order)
    
    # Use the new utility function
    _generate_excel_report(df, output_path=output_path, sheet_name="Mail Results")



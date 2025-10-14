from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
import base64
import os
from .forms import SignupForm, MailAutomationForm, TemplateEditForm, TemplateUploadForm
from .utils import (
    load_email_templates, 
    save_email_templates,
    generate_excel_report
)
# Attachment helper functions
def build_graph_attachment(uploaded_file):
    """Build a Graph API attachment from an uploaded file."""
    content = uploaded_file.read()
    b64 = base64.b64encode(content).decode("utf-8")
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": uploaded_file.name,
        "contentType": uploaded_file.content_type or "application/octet-stream",
        "contentBytes": b64,
    }

def build_graph_file_attachment_from_path(file_path: str, content_type: str = None):
    """Build a Graph API attachment from a file path."""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    name = os.path.basename(file_path)
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": name,
        "contentBytes": b64,
        "contentType": content_type or "application/octet-stream",
    }
from .services.template_render import render_subject_body
from .services.graph_client import (
    acquire_token_silent_or_fail,
    acquire_token_silent,
    send_mail as graph_send_mail,
    send_mail_with_attachments,
    NeedsLoginError,
    device_code_start,
    device_code_poll,
)
import pandas as pd
from django.http import HttpResponseRedirect
from django.urls import reverse
import json
import requests
import tempfile
import zipfile
import os
import shutil
import time
import base64
import logging
from django.contrib import messages
from django.conf import settings
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)


def healthcheck(request: HttpRequest) -> HttpResponse:
    """Simple health check endpoint."""
    return HttpResponse("ok", status=200)


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "automation/home.html", {"title": "Automation Home"})


def landing(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard"))
    return render(request, "landing.html")


def signup(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "automation/dashboard.html")


@login_required
def mail_automation(request: HttpRequest) -> HttpResponse:
    """Mail automation view with error handling."""
    logger.debug(f"Entering mail_automation view for user {request.user.username if request.user.is_authenticated else 'anonymous'}")
    
    try:
        return _mail_automation_impl(request)
    except Exception as e:
        logger.error(f"Error in mail_automation view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while processing your request: {str(e)}")
        
        # Return a friendly error page
        context = {
            "form": MailAutomationForm(),
            "error": "An unexpected error occurred. Please try again or contact support if the problem persists.",
            "step": "error"
        }
        return render(request, "automation/mail_automation.html", context)
    finally:
        logger.debug("Exiting mail_automation view")


def _mail_automation_impl(request: HttpRequest) -> HttpResponse:
    context = {"step": "form", "logs": []}
    templates = load_email_templates()

    # Try to keep file content in session between steps (simple base64)
    import base64
    from io import BytesIO

    # Handle reset flow
    if request.method == "GET" and request.GET.get("reset") == "1":
        try:
            if request.session.get("mail_excel_b64"):
                del request.session["mail_excel_b64"]
                if request.session.get("uploaded_files"):
                    del request.session["uploaded_files"]
                if request.session.get("temp_files_dir"):
                    del request.session["temp_files_dir"]
            if request.session.get("report_path"):
                del request.session["report_path"]
        except Exception as e:
            logger.warning(f"Error during reset cleanup: {e}")
        form = MailAutomationForm()
        context["form"] = form
        return render(request, "automation/mail_automation.html", context)

    if request.method == "POST":
        logger.info(f"POST request received for mail automation, files: {list(request.FILES.keys())}")
        
        # Handle smoke test action
        if request.POST.get("action") == "attach_smoke_test":
            return _handle_attachment_smoke_test(request)
        
        form = MailAutomationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Read/keep excel content
                logger.debug("Processing Excel file...")
                
                uploaded = form.cleaned_data.get("excel_file")
                if uploaded:
                    logger.debug(f"Excel file name: {uploaded.name}, Size: {uploaded.size}")
                    content = uploaded.read()
                    request.session["mail_excel_b64"] = base64.b64encode(content).decode("ascii")
                    df = pd.read_excel(BytesIO(content))
                    logger.debug(f"Excel loaded successfully, {len(df)} rows")
                elif request.session.get("mail_excel_b64"):
                    logger.debug("Using Excel from session")
                    content = base64.b64decode(request.session["mail_excel_b64"])  # type: ignore
                    df = pd.read_excel(BytesIO(content))
                    logger.debug(f"Excel loaded from session, {len(df)} rows")
                else:
                    raise ValueError("Please upload an Excel file.")

                # Handle attachment file (single file or ZIP with multiple PDFs)
                attachment_file = request.FILES.get('attachment')
                uploaded_files = []
                temp_files_dir = None
                
                if attachment_file:
                    logger.debug(f"Processing attachment: {attachment_file.name}, Size: {attachment_file.size}")
                    try:
                        # Check if it's a ZIP file
                        if attachment_file.name.lower().endswith('.zip'):
                    # Extract ZIP and collect all files
                    from automation.services.attach_matcher import collect_files_from_upload, cleanup_temp_directory
                    import tempfile as tf
                    import os
                    
                    base_temp_dir = Path(getattr(settings, 'FILE_UPLOAD_TEMP_DIR', tf.gettempdir()))
                    uploaded_files, temp_files_dir = collect_files_from_upload([attachment_file], base_temp_dir)
                    logger.debug(f"Extracted ZIP: {len(uploaded_files)} files from {attachment_file.name}")
                    
                    # Store uploaded files info in session
                    request.session["uploaded_files"] = uploaded_files
                    request.session["temp_files_dir"] = temp_files_dir
                    logger.debug(f"Stored {len(uploaded_files)} files in session")
                else:
                    # Single file - convert to uploaded_files format
                    attachment_data = build_graph_attachment(attachment_file)
                    uploaded_files = [{
                        "name": attachment_file.name,
                        "path": attachment_file.name,  # For single files, we'll use the Graph attachment data
                        "size": attachment_file.size,
                        "content_type": attachment_file.content_type,
                        "graph_data": attachment_data  # Store the Graph attachment data
                    }]
                    request.session["uploaded_files"] = uploaded_files
                    logger.debug(f"Stored single file in session: {attachment_file.name}")
                    
            except Exception as e:
                logger.error(f"Failed to process attachment: {e}", exc_info=True)
                messages.error(request, f"Failed to process attachment: {str(e)}")
                raise ValueError(f"Failed to process attachment: {e}")
        else:
            # Try to get uploaded files from session
            uploaded_files = request.session.get("uploaded_files", [])
            temp_files_dir = request.session.get("temp_files_dir")
            if uploaded_files:
                logger.debug(f"Retrieved {len(uploaded_files)} files from session")
            else:
                logger.debug("No attachment provided")

                # Template selection and inputs (subject always from template)
                try:
                    template_name = form.cleaned_data["template"]
                    template_obj = templates.get(template_name, {"subject": "", "body": ""})
                    template_body = template_obj.get("body", "")
                    subject = template_obj.get("subject", "")
                    dry_run = bool(form.cleaned_data.get("dry_run"))
                except Exception as e:
                    raise ValueError(f"Invalid template selection: {e}")

                # Parse Excel
                try:
                    df = pd.read_excel(BytesIO(content))
                except Exception as e:
                    raise ValueError(f"Failed to read Excel: {e}")

                # Normalize column names (lowercase, strip spaces)
                df.columns = df.columns.str.strip().str.lower()
                
                email_column = "email"
                cc_column = "cc"  # optional, comma-separated emails
                # Company column no longer needed for simple attachment system
                
                if email_column not in df.columns:
                    raise ValueError("Excel file must contain an `email` column")

                # Add attachment column to preview with company name matching
                df_preview = df.head(5).copy()
                company_column = "companyname"
                
                def get_matching_attachments(company_name):
                    if not uploaded_files:
                        return "None"
                    
                    if not company_column in df.columns:
                        # No company column, show all files
                        return "; ".join([f["name"] for f in uploaded_files])
                    
                    if not pd.notna(company_name) or not str(company_name).strip():
                        return "None"
                    
                    company_lower = str(company_name).strip().lower()
                    matching_files = []
                    
                    for file_info in uploaded_files:
                        filename_lower = file_info["name"].lower()
                        if company_lower in filename_lower:
                            matching_files.append(file_info["name"])
                    
                    return "; ".join(matching_files) if matching_files else "None"
                
                df_preview['Attachment'] = df_preview[company_column].apply(get_matching_attachments)
                
                # Preview (first 5 rows with attachment info)
                try:
                    preview = df_preview.to_html(classes=["table"], index=False, escape=False)
                except Exception:
                    preview = "<p>Could not render preview table.</p>"
                # Render a sample subject & body preview using the first row (if available)
                preview_render_sample = None
                preview_subject_sample = None
                if not df.empty:
                    try:
                        subject_sample, body_sample = render_subject_body(subject, template_body, df.iloc[0].to_dict())
                        preview_render_sample = body_sample
                        preview_subject_sample = subject_sample
                    except Exception:
                        preview_render_sample = None
                        preview_subject_sample = None
                parsed_emails = [str(v) for v in df[email_column].dropna().astype(str).tolist()]
                context.update({
                    "step": "preview",
                    "preview_html": preview,
                    "row_count": len(df),
                    "parsed_emails": parsed_emails,
                    "preview_render_sample": preview_render_sample,
                    "preview_subject_sample": preview_subject_sample,
                })

                logs = []
                if request.POST.get("confirm_send") == "1":
                    # Prevent duplicate submissions: compute a simple fingerprint from inputs
                    try:
                        import hashlib
                        fp_src = f"{template_name}|{subject}|{dry_run}|{len(df)}|{request.session.get('mail_excel_b64','')[:64]}"
                        fingerprint = hashlib.sha256(fp_src.encode("utf-8")).hexdigest()
                    except Exception:
                        fingerprint = None
                    last_fp = request.session.get("last_send_fp")
                    if fingerprint and last_fp == fingerprint:
                        logs.append("Duplicate submission detected. Skipping re-send.")
                        context["logs"] = logs
                        context["step"] = "done"
                        context["form"] = form
                        return render(request, "automation/mail_automation.html", context)
                    if dry_run:
                        attachment_summary = {"with_attachments": 0, "without_attachments": 0}
                        
                        # Simple attachment logic for dry run
                        
                        for _, row in df.iterrows():
                            try:
                                to_addr = str(row[email_column])
                                _sub, body = render_subject_body(subject, template_body, row.to_dict())
                                
                                # Company name matching logic for multiple files
                                company_name = row.get(company_column, "") if company_column in df.columns else ""
                                matching_files = []
                                
                                if uploaded_files:
                                    if not company_column in df.columns:
                                        # No company column, attach all files
                                        matching_files = [f["name"] for f in uploaded_files]
                                    elif pd.notna(company_name) and str(company_name).strip():
                                        company_lower = str(company_name).strip().lower()
                                        for file_info in uploaded_files:
                                            filename_lower = file_info["name"].lower()
                                            if company_lower in filename_lower:
                                                matching_files.append(file_info["name"])
                                
                                if matching_files:
                                    attachment_summary["with_attachments"] += 1
                                    attachment_info = f" (attachments: {'; '.join(matching_files)})"
                                else:
                                    attachment_summary["without_attachments"] += 1
                                    attachment_info = " (no attachment)"
                                
                                # parse CCs from optional column
                                cc_list: list[str] = []
                                if cc_column in df.columns and not pd.isna(row.get(cc_column)):
                                    cc_list = [p.strip() for p in str(row.get(cc_column)).split(",") if p.strip()]
                                
                                if cc_list:
                                    logs.append(f"[DRY] {to_addr} (cc: {', '.join(cc_list)}){attachment_info}")
                                else:
                                    logs.append(f"[DRY] {to_addr}{attachment_info}")
                            except Exception as e:
                                logs.append(f"[DRY][ERROR] Row render failed: {e}")
                        
                        # Add summary to logs
                        logs.append(f"\n[SUMMARY] {attachment_summary['with_attachments']} emails will have attachments, {attachment_summary['without_attachments']} will have no attachments")
                    else:
                        # Send with silent token only; no device code here
                        try:
                            access_token = acquire_token_silent_or_fail()
                        except NeedsLoginError as e:
                            logs.append(str(e))
                            context["logs"] = logs
                            context["step"] = "done"
                            context["error"] = str(e)
                            context["signin_required"] = True
                            context["form"] = form
                            return render(request, "automation/mail_automation.html", context)

                        # Initialize results tracking for Excel report
                        results = []
                        
                        # Simple attachment logic for sending
                        
                        # Iterate rows and send with strict timeout and robust error capture
                        for _, row in df.iterrows():
                            try:
                                to_addr = str(row[email_column])
                                # Company name no longer needed for simple attachment system
                                sub, body = render_subject_body(subject, template_body, row.to_dict())
                                cc_list: list[str] = []
                                if cc_column in df.columns and not pd.isna(row.get(cc_column)):
                                    cc_list = [p.strip() for p in str(row.get(cc_column)).split(",") if p.strip()]

                                # Company name matching logic for sending multiple files
                                company_name = row.get(company_column, "") if company_column in df.columns else ""
                                attachments = []
                                
                                if uploaded_files:
                                    if not company_column in df.columns:
                                        # No company column, attach all files
                                        for file_info in uploaded_files:
                                            if "graph_data" in file_info:
                                                # Single file with pre-built Graph data
                                                attachments.append(file_info["graph_data"])
                                            else:
                                                # File from ZIP - build Graph attachment
                                                attachment_data = build_graph_file_attachment_from_path(file_info["path"], file_info["content_type"])
                                                attachments.append(attachment_data)
                                    elif pd.notna(company_name) and str(company_name).strip():
                                        company_lower = str(company_name).strip().lower()
                                        for file_info in uploaded_files:
                                            filename_lower = file_info["name"].lower()
                                            if company_lower in filename_lower:
                                                if "graph_data" in file_info:
                                                    # Single file with pre-built Graph data
                                                    attachments.append(file_info["graph_data"])
                                                else:
                                                    # File from ZIP - build Graph attachment
                                                    attachment_data = build_graph_file_attachment_from_path(file_info["path"], file_info["content_type"])
                                                    attachments.append(attachment_data)

                                # Build Graph message payload
                                message_payload = {
                                    "subject": sub,
                                    "body": {"contentType": "HTML", "content": body},
                                    "toRecipients": [{"emailAddress": {"address": to_addr}}],
                                }
                                if cc_list:
                                    message_payload["ccRecipients"] = [
                                        {"emailAddress": {"address": addr}} for addr in cc_list
                                    ]
                                if attachments:
                                    message_payload["attachments"] = attachments

                                # Track result for Excel report
                                attachment_filenames = []
                                if uploaded_files:
                                    if not company_column in df.columns:
                                        attachment_filenames = [f["name"] for f in uploaded_files]
                                    elif pd.notna(company_name) and str(company_name).strip():
                                        company_lower = str(company_name).strip().lower()
                                        for file_info in uploaded_files:
                                            filename_lower = file_info["name"].lower()
                                            if company_lower in filename_lower:
                                                attachment_filenames.append(file_info["name"])
                                
                                result_row = {
                                    "email": to_addr,
                                    "company_name": str(company_name) if company_name else "",
                                    "matched_files": "; ".join(attachment_filenames),
                                    "sent_with_attachments": len(attachments) > 0,
                                    "status": "OK",
                                    "error_detail": ""
                                }

                                try:
                                    if attachments:
                                        send_mail_with_attachments(access_token, message_payload, attachments, timeout=15)
                                        attachment_info = f" (with {len(attachments)} attachments: {'; '.join(attachment_filenames)})"
                                    else:
                                        graph_send_mail(access_token, message_payload, timeout=15)
                                        attachment_info = " (no attachment)"
                                    
                                    logs.append(f"Sent to {to_addr}{attachment_info}")
                                    
                                except requests.Timeout:
                                    result_row["status"] = "ERROR"
                                    result_row["error_detail"] = "Request timeout"
                                    logs.append(f"ERROR timeout sending to {to_addr}")
                                except requests.HTTPError as http_err:
                                    result_row["status"] = "ERROR"
                                    result_row["error_detail"] = f"HTTP error: {getattr(http_err.response, 'text', str(http_err))}"
                                    logs.append(f"ERROR HTTP sending to {to_addr}: {result_row['error_detail']}")
                                except Exception as e:
                                    result_row["status"] = "ERROR"
                                    result_row["error_detail"] = str(e)
                                    logs.append(f"ERROR sending to {to_addr}: {e}")
                                
                                results.append(result_row)
                                
                            except Exception as e:
                                # Track error even if we can't process the row
                                company_name = row.get(company_column, "") if company_column in df.columns else ""
                                result_row = {
                                    "email": str(row.get(email_column, "unknown")),
                                    "company_name": str(company_name) if company_name else "",
                                    "matched_files": "",
                                    "sent_with_attachments": False,
                                    "status": "ERROR",
                                    "error_detail": f"Row processing failed: {str(e)}"
                                }
                                results.append(result_row)
                                logs.append(f"ERROR preparing row: {e}")
                        
                        # Generate Excel report
                        if results:
                            import tempfile
                            report_path = os.path.join(tempfile.gettempdir(), f"mail_report_{request.user.id}_{int(time.time())}.xlsx")
                            generate_excel_report(results, report_path)
                            request.session["report_path"] = report_path
                            
                            # Add summary to logs
                            sent_with_attachments = sum(1 for r in results if r["sent_with_attachments"] and r["status"] == "OK")
                            sent_without_attachments = sum(1 for r in results if not r["sent_with_attachments"] and r["status"] == "OK")
                            errors = sum(1 for r in results if r["status"] == "ERROR")
                            logs.append(f"\n[FINAL SUMMARY] {sent_with_attachments} sent with attachments, {sent_without_attachments} sent without attachments, {errors} errors")

                    context["logs"] = logs
                    context["step"] = "done"
                    if fingerprint:
                        request.session["last_send_fp"] = fingerprint
                    
                        # Cleanup temporary files if they exist
                        if temp_files_dir and os.path.exists(temp_files_dir):
                            try:
                                from automation.services.attach_matcher import cleanup_temp_directory
                                cleanup_temp_directory(temp_files_dir)
                                logger.debug(f"Cleaned up temp directory: {temp_files_dir}")
                            except Exception as e:
                                logger.warning(f"Failed to cleanup temp directory {temp_files_dir}: {e}")
                        
                        # Clean up session data
                        if "uploaded_files" in request.session:
                            del request.session["uploaded_files"]
                        if "temp_files_dir" in request.session:
                            del request.session["temp_files_dir"]

                context["form"] = form
                return render(request, "automation/mail_automation.html", context)
            except Exception as e:
                logger.error(f"Error in mail automation: {e}", exc_info=True)
                messages.error(request, f"An error occurred while processing your request: {str(e)}")
                # Always redirect after POST to prevent resubmission
                return redirect('/mail/')
        else:
            context["form"] = form
            return render(request, "automation/mail_automation.html", context)
    else:
        form = MailAutomationForm()
        context["form"] = form
        return render(request, "automation/mail_automation.html", context)


@login_required
def template_manager(request: HttpRequest) -> HttpResponse:
    """Template manager view with error handling."""
    logger.debug(f"Entering template_manager view for user {request.user.username}")
    
    try:
        return _template_manager_impl(request)
    except Exception as e:
        logger.error(f"Error in template_manager view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while managing templates: {str(e)}")
        
        # Return a friendly error page
        context = {
            "templates": {},
            "edit_form": TemplateEditForm(),
            "upload_form": TemplateUploadForm(),
            "error": "An unexpected error occurred while managing templates. Please try again."
        }
        return render(request, "automation/template_manager.html", context)
    finally:
        logger.debug("Exiting template_manager view")


def _template_manager_impl(request: HttpRequest) -> HttpResponse:
    templates = load_email_templates()
    # Prefill support via ?edit=NAME
    edit_name = request.GET.get("edit")
    edit_form = TemplateEditForm()
    if edit_name and edit_name in templates:
        pre = templates.get(edit_name, {"subject": "", "body": ""})
        edit_form = TemplateEditForm(initial={"name": edit_name, "subject": pre.get("subject", ""), "body": pre.get("body", "")})
    context = {"templates": templates, "edit_form": edit_form, "upload_form": TemplateUploadForm()}

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_template":
            form = TemplateEditForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data["name"].strip()
                subject = form.cleaned_data["subject"]
                body = form.cleaned_data["body"]
                templates[name] = {"subject": subject, "body": body}
                save_email_templates(templates)
                context["success"] = f"Template '{name}' saved."
            else:
                context["edit_form"] = form

        elif action == "upload_json":
            form = TemplateUploadForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data["json_file"]
                try:
                    data = json.load(file)
                    # normalize and save
                    new_templates = {}
                    for k, v in data.items():
                        if isinstance(v, dict):
                            new_templates[str(k)] = {
                                "subject": str(v.get("subject", "")),
                                "body": str(v.get("body", "")),
                            }
                        else:
                            new_templates[str(k)] = {"subject": "", "body": str(v)}
                    save_email_templates(new_templates)
                    templates = new_templates
                    context["templates"] = templates
                    context["success"] = "Templates file uploaded and replaced."
                except Exception as e:
                    context["error"] = f"Failed to parse JSON: {e}"
            else:
                context["upload_form"] = form

    return render(request, "automation/template_manager.html", context)


@login_required
def delete_template(request: HttpRequest, name: str) -> HttpResponse:
    templates = load_email_templates()
    if name not in templates:
        return redirect("automation:template_manager")
    if request.method == "POST":
        try:
            del templates[name]
            save_email_templates(templates)
            from django.contrib import messages
            messages.success(request, f"Template '{name}' deleted.")
        except Exception:
            from django.contrib import messages
            messages.error(request, f"Failed to delete template '{name}'.")
        return redirect("automation:template_manager")
    return render(request, "automation/template_delete_confirm.html", {"name": name})


@login_required
def download_templates(request: HttpRequest) -> HttpResponse:
    templates = load_email_templates()
    payload = json.dumps(templates, indent=2, ensure_ascii=False)
    response = HttpResponse(payload, content_type="application/json")
    response["Content-Disposition"] = "attachment; filename=email_templates.json"
    return response


@login_required
def download_report(request: HttpRequest) -> HttpResponse:
    """Download Excel report from last mail automation run."""
    report_path = request.session.get("report_path")
    if not report_path or not os.path.exists(report_path):
        return HttpResponse("No report available", status=404)
    
    try:
        with open(report_path, 'rb') as f:
            content = f.read()
        
        response = HttpResponse(content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = "attachment; filename=mail_automation_report.xlsx"
        
        # Clean up the file after serving
        try:
            os.remove(report_path)
            if request.session.get("report_path") == report_path:
                del request.session["report_path"]
        except Exception:
            pass
            
        return response
    except Exception as e:
        return HttpResponse(f"Error serving report: {e}", status=500)



@login_required
def mail_signin_start(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponse(status=405)
    from django.http import JsonResponse
    flow = device_code_start()
    if not flow:
        return JsonResponse({"error": "Graph client not configured"}, status=400)
    request.session["dcf_flow"] = flow
    return JsonResponse({
        "user_code": flow.get("user_code"),
        "verification_uri": flow.get("verification_uri") or flow.get("verification_uri_complete"),
        "expires_in": flow.get("expires_in"),
        "interval": flow.get("interval"),
    })


@login_required
def mail_signin_poll(request: HttpRequest) -> HttpResponse:
    from django.http import JsonResponse
    flow = request.session.get("dcf_flow")
    if not flow:
        return JsonResponse({"status": "error", "detail": "No pending device code flow"}, status=400)
    result = device_code_poll(flow, timeout=2)
    if result.get("status") == "ok":
        try:
            del request.session["dcf_flow"]
        except Exception:
            pass
    return JsonResponse(result)


def _handle_attachment_smoke_test(request):
    """
    Handle attachment smoke test to verify Graph API attachment functionality.
    """
    try:
        logger.info("Starting attachment smoke test")
        
        # Get test email from session Excel data or use a default
        test_email = "test@example.com"
        if request.session.get("mail_excel_b64"):
            try:
                import pandas as pd
                import base64
                import io
                excel_content = base64.b64decode(request.session["mail_excel_b64"])
                df = pd.read_excel(io.BytesIO(excel_content))
                if len(df) > 0 and 'email' in df.columns:
                    test_email = str(df.iloc[0]['email'])
                    logger.debug(f"Using email from Excel: {test_email}")
            except Exception as e:
                logger.warning(f"Could not read email from session Excel: {e}")
        
        # Try to get access token
        try:
            access_token = acquire_token_silent_or_fail()
        except NeedsLoginError:
            messages.error(request, "Please sign in to test attachments")
            return redirect('/mail/')
        
        # Get test file path
        from django.conf import settings
        test_file_path = os.path.join(settings.BASE_DIR, "tests", "fixtures", "hello.pdf")
        
        # Ensure test file exists
        if not os.path.exists(test_file_path):
            logger.warning(f"Test file not found at {test_file_path}")
            messages.error(request, "Test file not found. Please contact administrator.")
            return redirect('/mail/')
        
        logger.info(f"SMOKE: sending 1 attachment: {test_file_path}")
        
        # Build attachment
        attachment = build_graph_file_attachment_from_path(test_file_path)
        attachments = [attachment]
        
        # Build message payload
        message_payload = {
            "subject": "Attachment Smoke Test",
            "body": {
                "contentType": "HTML",
                "content": "<p>This is a smoke test to verify attachment functionality.</p>"
            },
            "toRecipients": [{"emailAddress": {"address": test_email}}],
            "attachments": attachments
        }
        
        # Send with attachment
        logger.info("SMOKE attachments count = 1")
        logger.info(f"SMOKE attachment name = {attachment['name']}")
        logger.info(f"SMOKE attachment size = {len(base64.b64decode(attachment['contentBytes']))} bytes")
        
        response = send_mail_with_attachments(access_token, message_payload, attachments, timeout=15)
        logger.info(f"SMOKE response = {response}")
        
        if response:
            messages.success(request, f"Smoke test sent successfully with 1 attachment to {test_email}")
        else:
            messages.error(request, "Smoke test failed - no response received")
            
    except Exception as e:
        logger.error(f"Smoke test failed: {e}", exc_info=True)
        messages.error(request, f"Smoke test failed: {str(e)}")
    
    return redirect('/mail/')

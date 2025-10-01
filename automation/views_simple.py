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
    NeedsLoginError
)
from django.contrib import messages
import pandas as pd
from io import BytesIO
import logging
from pathlib import Path
from django.conf import settings
import requests

logger = logging.getLogger(__name__)

@login_required
def mail_automation(request: HttpRequest) -> HttpResponse:
    """Mail automation view with error handling."""
    try:
        return _mail_automation_impl(request)
    except Exception as e:
        logger.error(f"Error in mail_automation view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while processing your request: {str(e)}")
        return redirect('/mail/')

def _mail_automation_impl(request: HttpRequest) -> HttpResponse:
    """Main mail automation logic."""
    context = {"step": "form"}
    
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
        # Handle smoke test action
        if request.POST.get("action") == "attach_smoke_test":
            return _handle_attachment_smoke_test(request)
        
        form = MailAutomationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Read Excel content
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
                    content = base64.b64decode(request.session["mail_excel_b64"])
                    df = pd.read_excel(BytesIO(content))
                    logger.debug(f"Excel loaded from session, {len(df)} rows")
                else:
                    raise ValueError("Please upload an Excel file.")

                # Handle attachment file
                attachment_file = request.FILES.get('attachment')
                uploaded_files = []
                
                if attachment_file:
                    logger.debug(f"Processing attachment: {attachment_file.name}, Size: {attachment_file.size}")
                    
                    if attachment_file.name.lower().endswith('.zip'):
                        # ZIP file - extract and collect files
                        from automation.services.attach_matcher import collect_files_from_upload
                        import tempfile as tf
                        
                        base_temp_dir = Path(getattr(settings, 'FILE_UPLOAD_TEMP_DIR', tf.gettempdir()))
                        uploaded_files, temp_files_dir = collect_files_from_upload([attachment_file], base_temp_dir)
                        logger.debug(f"Extracted ZIP: {len(uploaded_files)} files")
                        
                        request.session["uploaded_files"] = uploaded_files
                        request.session["temp_files_dir"] = temp_files_dir
                    else:
                        # Single file
                        attachment_data = build_graph_attachment(attachment_file)
                        uploaded_files = [{
                            "name": attachment_file.name,
                            "graph_data": attachment_data
                        }]
                        request.session["uploaded_files"] = uploaded_files
                        logger.debug(f"Stored single file: {attachment_file.name}")
                else:
                    uploaded_files = request.session.get("uploaded_files", [])
                    if uploaded_files:
                        logger.debug(f"Retrieved {len(uploaded_files)} files from session")

                # Template selection
                template_name = form.cleaned_data["template"]
                templates = load_email_templates()
                template_obj = templates.get(template_name, {"subject": "", "body": ""})
                subject = template_obj.get("subject", "")
                template_body = template_obj.get("body", "")
                dry_run = bool(form.cleaned_data.get("dry_run"))

                # Normalize column names
                df.columns = df.columns.str.strip().str.lower()

                # Find email column
                email_column = None
                for col in ["email", "e-mail", "mail"]:
                    if col in df.columns:
                        email_column = col
                        break
                
                if not email_column:
                    raise ValueError("Excel file must contain an 'email' column")

                # Add attachment preview
                df_preview = df.head(5).copy()
                company_column = "companyname"
                
                def get_matching_attachments(company_name):
                    if not uploaded_files:
                        return "None"
                    
                    if company_column not in df.columns:
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

                # Preview
                try:
                    preview = df_preview.to_html(classes=["table"], index=False, escape=False)
                except Exception:
                    preview = "<p>Preview not available</p>"

                context.update({
                    "preview": preview,
                    "total_rows": len(df),
                    "step": "preview"
                })

                if dry_run:
                    # Dry run logic
                    logs = []
                    attachment_summary = {"with_attachments": 0, "without_attachments": 0}
                    
                    for _, row in df.iterrows():
                        try:
                            to_addr = str(row[email_column])
                            _sub, body = render_subject_body(subject, template_body, row.to_dict())
                            
                            # Company name matching
                            company_name = row.get(company_column, "") if company_column in df.columns else ""
                            matching_files = []
                            
                            if uploaded_files:
                                if company_column not in df.columns:
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
                            
                            logs.append(f"[DRY] {to_addr}{attachment_info}")
                        except Exception as e:
                            logs.append(f"[DRY][ERROR] Row render failed: {e}")
                    
                    logs.append(f"\n[SUMMARY] {attachment_summary['with_attachments']} emails will have attachments, {attachment_summary['without_attachments']} will have no attachments")
                    context["logs"] = logs
                    context["step"] = "dry_run"
                else:
                    # Actual sending
                    try:
                        access_token = acquire_token_silent_or_fail()
                    except NeedsLoginError:
                        messages.error(request, "Please sign in via Device Code first.")
                        return redirect("automation:mail_automation")
                    
                    logs = []
                    results = []
                    
                    for _, row in df.iterrows():
                        try:
                            to_addr = str(row[email_column])
                            sub, body = render_subject_body(subject, template_body, row.to_dict())
                            
                            # Company name matching for attachments
                            company_name = row.get(company_column, "") if company_column in df.columns else ""
                            attachments = []
                            
                            if uploaded_files:
                                if company_column not in df.columns:
                                    # Attach all files
                                    for file_info in uploaded_files:
                                        if "graph_data" in file_info:
                                            attachments.append(file_info["graph_data"])
                                        else:
                                            attachment_data = build_graph_file_attachment_from_path(file_info["path"], file_info["content_type"])
                                            attachments.append(attachment_data)
                                elif pd.notna(company_name) and str(company_name).strip():
                                    company_lower = str(company_name).strip().lower()
                                    for file_info in uploaded_files:
                                        filename_lower = file_info["name"].lower()
                                        if company_lower in filename_lower:
                                            if "graph_data" in file_info:
                                                attachments.append(file_info["graph_data"])
                                            else:
                                                attachment_data = build_graph_file_attachment_from_path(file_info["path"], file_info["content_type"])
                                                attachments.append(attachment_data)

                            # Build message payload
                            message_payload = {
                                "subject": sub,
                                "body": {"contentType": "HTML", "content": body},
                                "toRecipients": [{"emailAddress": {"address": to_addr}}],
                            }
                            if attachments:
                                message_payload["attachments"] = attachments

                            # Track result
                            attachment_filenames = []
                            if uploaded_files:
                                if company_column not in df.columns:
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
                        try:
                            report_path = generate_excel_report(results)
                            request.session["report_path"] = report_path
                            logs.append(f"\nReport generated: {report_path}")
                        except Exception as e:
                            logs.append(f"ERROR generating report: {e}")

                    context["logs"] = logs
                    context["step"] = "done"
                    
                    # Cleanup
                    temp_files_dir = request.session.get("temp_files_dir")
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
    try:
        return _template_manager_impl(request)
    except Exception as e:
        logger.error(f"Error in template_manager view: {e}", exc_info=True)
        messages.error(request, f"An error occurred while managing templates: {str(e)}")
        return redirect('/templates/')

def _template_manager_impl(request: HttpRequest) -> HttpResponse:
    """Main template manager logic."""
    templates = load_email_templates()
    context = {"templates": templates}
    
    if request.method == "POST":
        if "delete_template" in request.POST:
            template_name = request.POST.get("template_name")
            if template_name and template_name in templates:
                del templates[template_name]
                save_email_templates(templates)
                messages.success(request, f"Template '{template_name}' deleted successfully.")
                return redirect("automation:template_manager")
        
        elif "upload_templates" in request.POST:
            form = TemplateUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    uploaded_file = form.cleaned_data["template_file"]
                    content = uploaded_file.read().decode('utf-8')
                    import json
                    new_templates = json.loads(content)
                    templates.update(new_templates)
                    save_email_templates(templates)
                    context["templates"] = templates
                    context["success"] = "Templates file uploaded and replaced."
                except Exception as e:
                    context["error"] = f"Failed to parse JSON: {e}"
            else:
                context["upload_form"] = form
    
    context["upload_form"] = TemplateUploadForm()
    return render(request, "automation/template_manager.html", context)

@login_required
def template_edit(request: HttpRequest, template_name: str) -> HttpResponse:
    """Edit template view."""
    templates = load_email_templates()
    
    if request.method == "POST":
        form = TemplateEditForm(request.POST)
        if form.is_valid():
            templates[template_name] = {
                "subject": form.cleaned_data["subject"],
                "body": form.cleaned_data["body"]
            }
            save_email_templates(templates)
            messages.success(request, f"Template '{template_name}' updated successfully.")
            return redirect("automation:template_manager")
    else:
        template_data = templates.get(template_name, {"subject": "", "body": ""})
        form = TemplateEditForm(initial=template_data)
    
    return render(request, "automation/template_edit.html", {"form": form, "template_name": template_name})

@login_required
def template_delete(request: HttpRequest, template_name: str) -> HttpResponse:
    """Delete template view."""
    templates = load_email_templates()
    
    if template_name in templates:
        if request.method == "POST":
            del templates[template_name]
            save_email_templates(templates)
            messages.success(request, f"Template '{template_name}' deleted successfully.")
            return redirect("automation:template_manager")
        
        return render(request, "automation/template_delete.html", {"template_name": template_name})
    else:
        messages.error(request, f"Template '{template_name}' not found.")
        return redirect("automation:template_manager")

@login_required
def template_upload(request: HttpRequest) -> HttpResponse:
    """Upload templates from JSON file."""
    if request.method == "POST":
        form = TemplateUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                uploaded_file = form.cleaned_data["template_file"]
                content = uploaded_file.read().decode('utf-8')
                import json
                new_templates = json.loads(content)
                templates = load_email_templates()
                templates.update(new_templates)
                save_email_templates(templates)
                messages.success(request, "Templates uploaded successfully.")
            except Exception as e:
                messages.error(request, f"Failed to upload templates: {e}")
            return redirect("automation:template_manager")
    else:
        form = TemplateUploadForm()
    
    return render(request, "automation/template_upload.html", {"form": form})

@login_required
def template_download(request: HttpRequest) -> HttpResponse:
    """Download templates as JSON file."""
    templates = load_email_templates()
    import json
    content = json.dumps(templates, indent=2)
    
    response = HttpResponse(content, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="email_templates.json"'
    return response

def health_check(request: HttpRequest) -> HttpResponse:
    """Simple health check endpoint."""
    return HttpResponse("ok", status=200)

@login_required
def report_download(request: HttpRequest) -> HttpResponse:
    """Download Excel report."""
    try:
        report_path = request.session.get("report_path")
        if not report_path or not os.path.exists(report_path):
            return HttpResponse("No report available", status=404)
        
        with open(report_path, "rb") as f:
            response = HttpResponse(f.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response["Content-Disposition"] = "attachment; filename=mail_report.xlsx"
            return response
            
    except Exception as e:
        return HttpResponse(f"Error serving report: {e}", status=500)

def _handle_attachment_smoke_test(request: HttpRequest) -> HttpResponse:
    """Handle attachment smoke test."""
    try:
        # Try to get access token
        try:
            access_token = acquire_token_silent_or_fail()
        except NeedsLoginError:
            messages.error(request, "Sign-in required. Please use Device Code first.")
            return redirect("automation:mail_automation")
        
        # Create or find test file
        test_path = os.path.join(settings.BASE_DIR, "tests", "fixtures", "hello.pdf")
        os.makedirs(os.path.dirname(test_path), exist_ok=True)
        
        if not os.path.exists(test_path):
            # Create a simple PDF file
            with open(test_path, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000136 00000 n \n0000000301 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n395\n%%EOF")
        
        # Get test email from session Excel or use default
        test_email = "test@example.com"
        if request.session.get("mail_excel_b64"):
            try:
                import pandas as pd
                from io import BytesIO
                content = base64.b64decode(request.session["mail_excel_b64"])
                df = pd.read_excel(BytesIO(content))
                if len(df) > 0 and 'email' in df.columns:
                    test_email = str(df.iloc[0]['email'])
                    logger.debug(f"Using email from Excel: {test_email}")
            except Exception as e:
                logger.warning(f"Could not read email from session Excel: {e}")
        
        # Build test message
        message_payload = {
            "subject": "Smoke Test - Attachment",
            "body": {"contentType": "HTML", "content": "<p>This is a smoke test with attachment.</p>"},
            "toRecipients": [{"emailAddress": {"address": test_email}}],
        }
        
        # Build attachment
        attachment_data = build_graph_file_attachment_from_path(test_path, "application/pdf")
        attachments = [attachment_data]
        message_payload["attachments"] = attachments
        
        # Send test email
        logger.info(f"SMOKE: sending 1 attachment: {test_path}")
        response = send_mail_with_attachments(access_token, message_payload, attachments, timeout=15)
        logger.info(f"SMOKE response = {response}")
        
        if response:
            messages.success(request, f"Smoke test sent successfully with 1 attachment to {test_email}")
        else:
            messages.error(request, "Smoke test failed - no response received")
            
    except Exception as e:
        logger.error(f"Smoke test failed: {e}", exc_info=True)
        messages.error(request, f"Smoke test failed: {str(e)}")
    
    return redirect("automation:mail_automation")

def signup(request: HttpRequest) -> HttpResponse:
    """User signup view."""
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("automation:dashboard")
    else:
        form = SignupForm()
    
    return render(request, "automation/signup.html", {"form": form})

@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Dashboard view."""
    return render(request, "automation/dashboard.html")

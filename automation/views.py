from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import base64
import os
import logging
import pandas as pd
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional

from .forms import SignupForm, MailAutomationForm, TemplateEditForm
from .exceptions import MailSendError, TemplateNotFoundError, FileProcessingError, ReportGenerationError
from .services.mailer import send_single_mail, encode_attachment
from .services.templates import template_service
from .services.reporting import reporting_service
from .services.file_processor import file_processor
from .services.graph_client import (
    acquire_token_silent_or_fail,
    send_mail_with_attachments,
    NeedsLoginError
)
from .services.template_render import render_subject_body
from .services.attach_matcher import build_graph_file_attachment_from_path
from django.conf import settings

logger = logging.getLogger(__name__)


def _process_excel_file(request: HttpRequest) -> tuple[pd.DataFrame, str]:
    """Process Excel file from form or session."""
    uploaded = request.FILES.get("excel_file")
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
    
    return df, email_column


def _process_attachments(request: HttpRequest) -> List[Dict[str, Any]]:
    """Process attachment files."""
    attachment_file = request.FILES.get('attachment')
    uploaded_files = []
    
    if attachment_file:
        logger.debug(f"Processing attachment: {attachment_file.name}, Size: {attachment_file.size}")
        
        if attachment_file.name.lower().endswith('.zip'):
            # ZIP file - extract and collect files
            from django.conf import settings
            import tempfile as tf
            
            base_temp_dir = Path(getattr(settings, 'FILE_UPLOAD_TEMP_DIR', tf.gettempdir()))
            uploaded_files, temp_files_dir = file_processor.process_uploaded_files([attachment_file])
            logger.debug(f"Extracted ZIP: {len(uploaded_files)} files")
            
            request.session["uploaded_files"] = uploaded_files
            request.session["temp_files_dir"] = temp_files_dir
        else:
            # Single file
            attachment_data = encode_attachment(attachment_file)
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
    
    return uploaded_files


def _get_matching_attachments(company_name: str, uploaded_files: List[Dict[str, Any]], df: pd.DataFrame) -> str:
    """Get matching attachments for a company."""
    if not uploaded_files:
        return "None"
    
    company_column = "companyname"
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


def _perform_dry_run(
    df: pd.DataFrame,
    email_column: str,
    company_column: str,
    subject: str,
    template_body: str,
    uploaded_files: List[Dict[str, Any]]
) -> tuple[List[str], Dict[str, int]]:
    """Perform dry run and return logs and attachment summary."""
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
    return logs, attachment_summary


def _send_emails(
    df: pd.DataFrame,
    email_column: str,
    company_column: str,
    subject: str,
    template_body: str,
    uploaded_files: List[Dict[str, Any]]
) -> tuple[List[str], List[Dict[str, Any]]]:
    """Send emails and return logs and results."""
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
                # Send email using service
                send_single_mail(to_addr, sub, body, attachments, timeout=15)
                
                if attachments:
                    attachment_info = f" (with {len(attachments)} attachments: {'; '.join(attachment_filenames)})"
                else:
                    attachment_info = " (no attachment)"
                
                logs.append(f"Sent to {to_addr}{attachment_info}")
                
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
    
    return logs, results


def _cleanup_session_files(request: HttpRequest) -> None:
    """Clean up temporary files and session data."""
    temp_files_dir = request.session.get("temp_files_dir")
    if temp_files_dir and os.path.exists(temp_files_dir):
        try:
            file_processor.cleanup_temp_files(temp_files_dir)
            logger.debug(f"Cleaned up temp directory: {temp_files_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {temp_files_dir}: {e}")
    
    # Clean up session data
    if "uploaded_files" in request.session:
        del request.session["uploaded_files"]
    if "temp_files_dir" in request.session:
        del request.session["temp_files_dir"]

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
                # Process Excel file
                df, email_column = _process_excel_file(request)
                
                # Process attachments
                uploaded_files = _process_attachments(request)

                # Get template
                template_name = form.cleaned_data["template"]
                try:
                    template_obj = template_service.get_template(template_name)
                    subject = template_obj["subject"]
                    template_body = template_obj["body"]
                except TemplateNotFoundError:
                    raise ValueError(f"Template '{template_name}' not found")
                
                dry_run = bool(form.cleaned_data.get("dry_run"))

                # Add attachment preview
                df_preview = df.head(5).copy()
                company_column = "companyname"
                df_preview['Attachment'] = df_preview[company_column].apply(
                    lambda x: _get_matching_attachments(x, uploaded_files, df)
                )

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
                    logs, attachment_summary = _perform_dry_run(
                        df, email_column, company_column, subject, template_body, uploaded_files
                    )
                    context["logs"] = logs
                    context["step"] = "dry_run"
                else:
                    # Actual sending
                    try:
                        logs, results = _send_emails(
                            df, email_column, company_column, subject, template_body, uploaded_files
                        )
                        
                        # Generate Excel report
                        if results:
                            try:
                                report_path = reporting_service.save_report_to_file(results, "mail_report.xlsx")
                                request.session["report_path"] = report_path
                                request.session["mail_results"] = results
                                logs.append(f"\nReport generated: {report_path}")
                            except ReportGenerationError as e:
                                logs.append(f"ERROR generating report: {e}")

                        context["logs"] = logs
                        context["step"] = "done"
                        
                        # Cleanup
                        _cleanup_session_files(request)
                        
                    except NeedsLoginError:
                        messages.error(request, "Please sign in via Device Code first.")
                        return redirect("automation:mail_automation")
                    except MailSendError as e:
                        messages.error(request, f"Mail sending failed: {e}")
                        return redirect("automation:mail_automation")

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
    templates = template_service.get_templates()
    context = {"templates": templates}
    
    # Handle edit parameter
    edit_template_name = request.GET.get('edit')
    if edit_template_name and edit_template_name in templates:
        edit_form = TemplateEditForm(initial={
            'name': edit_template_name,
            'subject': templates[edit_template_name]['subject'],
            'body': templates[edit_template_name]['body']
        })
    else:
        edit_form = TemplateEditForm()
    
    context["edit_form"] = edit_form
    
    if request.method == "POST":
        if "delete_template" in request.POST:
            template_name = request.POST.get("template_name")
            if template_name:
                try:
                    template_service.delete_template(template_name)
                    messages.success(request, f"Template '{template_name}' deleted successfully.")
                    return redirect("automation:template_manager")
                except TemplateNotFoundError:
                    messages.error(request, f"Template '{template_name}' not found.")
                    return redirect("automation:template_manager")
        
        elif "action" in request.POST and request.POST["action"] == "save_template":
            form = TemplateEditForm(request.POST)
            if form.is_valid():
                try:
                    template_name = form.cleaned_data["name"]
                    subject = form.cleaned_data["subject"]
                    body = form.cleaned_data["body"]
                    logger.info(f"Saving template: {template_name}")
                    template_service.save_template(template_name, subject, body)
                    messages.success(request, f"Template '{template_name}' saved successfully.")
                    return redirect("automation:template_manager")
                except Exception as e:
                    logger.error(f"Failed to save template: {e}")
                    messages.error(request, f"Failed to save template: {e}")
            else:
                # Form validation errors
                logger.error(f"Form validation failed: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                context["edit_form"] = form
        
    return render(request, "automation/template_manager.html", context)

@login_required
def template_edit(request: HttpRequest, template_name: str) -> HttpResponse:
    """Edit template view."""
    try:
        template_data = template_service.get_template(template_name)
    except TemplateNotFoundError:
        messages.error(request, f"Template '{template_name}' not found.")
        return redirect("automation:template_manager")
    
    if request.method == "POST":
        form = TemplateEditForm(request.POST)
        if form.is_valid():
            try:
                template_service.save_template(
                    template_name,
                    form.cleaned_data["subject"],
                    form.cleaned_data["body"]
                )
                messages.success(request, f"Template '{template_name}' updated successfully.")
                return redirect("automation:template_manager")
            except Exception as e:
                messages.error(request, f"Failed to update template: {e}")
    else:
        form = TemplateEditForm(initial=template_data)
    
    return render(request, "automation/template_edit.html", {"form": form, "template_name": template_name})

@login_required
def template_delete(request: HttpRequest, template_name: str) -> HttpResponse:
    """Delete template view."""
    try:
        template_service.get_template(template_name)
    except TemplateNotFoundError:
        messages.error(request, f"Template '{template_name}' not found.")
        return redirect("automation:template_manager")
    
    if request.method == "POST":
        try:
            template_service.delete_template(template_name)
            messages.success(request, f"Template '{template_name}' deleted successfully.")
            return redirect("automation:template_manager")
        except TemplateNotFoundError:
            messages.error(request, f"Template '{template_name}' not found.")
            return redirect("automation:template_manager")
    
    return render(request, "automation/template_delete.html", {"template_name": template_name})


@login_required
def template_download(request: HttpRequest) -> HttpResponse:
    """Download templates as JSON file."""
    try:
        content = template_service.export_templates_to_json()
        response = HttpResponse(content, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="email_templates.json"'
        return response
    except Exception as e:
        messages.error(request, f"Failed to download templates: {e}")
        return redirect("automation:template_manager")

def health_check(request: HttpRequest) -> HttpResponse:
    """Simple health check endpoint."""
    return HttpResponse("ok", status=200)

def landing(request: HttpRequest) -> HttpResponse:
    """Landing page view."""
    return render(request, "landing.html")

def mail_signin_start(request: HttpRequest) -> HttpResponse:
    """Start Microsoft Graph sign-in process."""
    from .services.graph_client import start_device_code_flow
    try:
        device_code_info = start_device_code_flow()
        request.session['device_code'] = device_code_info['device_code']
        request.session['user_code'] = device_code_info['user_code']
        request.session['verification_uri'] = device_code_info['verification_uri']
        request.session['expires_in'] = device_code_info['expires_in']
        return render(request, "automation/device_code.html", {
            'user_code': device_code_info['user_code'],
            'verification_uri': device_code_info['verification_uri']
        })
    except Exception as e:
        messages.error(request, f"Failed to start sign-in: {str(e)}")
        return redirect("automation:mail_automation")

def mail_signin_poll(request: HttpRequest) -> HttpResponse:
    """Poll for device code completion."""
    from .services.graph_client import poll_device_code
    device_code = request.session.get('device_code')
    if not device_code:
        return HttpResponse("No device code found", status=400)
    
    try:
        result = poll_device_code(device_code)
        if result:
            messages.success(request, "Successfully signed in!")
            return redirect("automation:mail_automation")
        else:
            return HttpResponse("Still waiting...", status=202)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

def download_templates(request: HttpRequest) -> HttpResponse:
    """Download templates as JSON file."""
    return template_download(request)

def delete_template(request: HttpRequest, name: str) -> HttpResponse:
    """Delete a template."""
    try:
        template_service.delete_template(name)
        messages.success(request, f"Template '{name}' deleted successfully.")
    except TemplateNotFoundError:
        messages.error(request, f"Template '{name}' not found.")
    except Exception as e:
        messages.error(request, f"Failed to delete template: {e}")
    
    return redirect("automation:template_manager")

def download_report(request: HttpRequest) -> HttpResponse:
    """Download Excel report."""
    return report_download(request)

def healthcheck(request: HttpRequest) -> HttpResponse:
    """Health check endpoint."""
    return health_check(request)

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
        logger.error(f"Error serving report: {e}")
        return HttpResponse(f"Error serving report: {e}", status=500)

@login_required
def download_report_direct(request: HttpRequest) -> HttpResponse:
    """Download Excel report directly from session data using new utility."""
    try:
        # Get results from session (if available)
        results = request.session.get("mail_results", [])
        if not results:
            return HttpResponse("No report data available", status=404)
        
        # Generate Excel content directly using reporting service
        content = reporting_service.generate_report_bytes(results)
        
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="mail_report.xlsx"'
        return response
        
    except ReportGenerationError as e:
        logger.error(f"Report generation error: {e}")
        return HttpResponse(f"Error generating report: {e}", status=500)
    except Exception as e:
        logger.error(f"Unexpected error in download_report_direct: {e}")
        return HttpResponse(f"Error generating report: {e}", status=500)

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
    
    return render(request, "registration/signup.html", {"form": form})

@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Dashboard view."""
    return render(request, "automation/dashboard.html")

import logging
from django.core.exceptions import RequestDataTooBig
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseBadRequest, HttpResponseServerError

logger = logging.getLogger(__name__)


class UploadSizeMiddleware:
    """
    Middleware to handle RequestDataTooBig exceptions gracefully and log request details.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request details for /mail requests
        if request.path == '/mail/' or request.path.startswith('/mail'):
            content_length = request.META.get('CONTENT_LENGTH', 'unknown')
            logger.info(f"Mail request: {request.method} {request.path}, Content-Length: {content_length}, User: {request.user.username if hasattr(request, 'user') else 'anonymous'}")
        
        try:
            response = self.get_response(request)
            return response
        except RequestDataTooBig as e:
            logger.warning(f"Request data too big for {request.path}: {e}")
            
            # Handle specific paths with user-friendly messages
            if request.path == '/mail/' or request.path.startswith('/mail'):
                messages.error(
                    request, 
                    "Your upload exceeded 100 MB. Please zip or reduce size and try again."
                )
                return redirect('/mail/')
            
            # Generic error for other paths
            return HttpResponseBadRequest(
                "Request data too large. Maximum 100 MB allowed.",
                content_type="text/plain"
            )
        except Exception as e:
            logger.error(f"Unexpected error in middleware for {request.path}: {e}", exc_info=True)
            
            # Don't crash the server - return a friendly error page
            if request.path == '/mail/' or request.path.startswith('/mail'):
                messages.error(
                    request,
                    "An unexpected error occurred. Please try again or contact support."
                )
                return redirect('/mail/')
            
            return HttpResponseServerError(
                "An unexpected error occurred. Please try again.",
                content_type="text/plain"
            )

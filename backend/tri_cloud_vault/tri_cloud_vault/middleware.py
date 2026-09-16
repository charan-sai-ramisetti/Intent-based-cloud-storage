from django.utils.deprecation import MiddlewareMixin

# UserEmailHeaderMiddleware has been removed.
#
# The previous implementation attached request.user.email to every API response
# as an X-User-Email header. This exposed PII (email addresses) in response
# headers with no legitimate purpose — the frontend already has the email from
# the JWT payload / login response and does not need it echoed back on every call.
#
# This file is kept as a placeholder so the import in settings.py does not need
# to be changed if other middleware is added here in the future.
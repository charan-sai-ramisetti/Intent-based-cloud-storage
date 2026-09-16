import time
from django.db import connection, OperationalError
from django.http import JsonResponse
from django.views import View


class HealthCheckView(View):

    def get(self, request):
        start = time.monotonic()

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_status = "ok"
            db_ok = True
        except OperationalError as e:
            db_status = f"error: {str(e)}"
            db_ok = False

        elapsed_ms = round((time.monotonic() - start) * 1000, 1)

        payload = {
            "status": "ok" if db_ok else "degraded",
            "checks": {
                "database": db_status,
            },
            "response_ms": elapsed_ms,
        }

        status_code = 200 if db_ok else 503
        return JsonResponse(payload, status=status_code)
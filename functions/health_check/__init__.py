import logging
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Lightweight health-check endpoint for the Azure Function App.

    Used by Application Insights Availability tests to verify:
    - The Function App is running
    - HTTP routing and the Python worker are working

    It does NOT call Azure Document Intelligence or any external services.
    """
    logging.info("Health check ping received.")
    return func.HttpResponse(
        "OK",
        status_code=200,
        mimetype="text/plain",
    )
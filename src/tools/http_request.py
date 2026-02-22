
import httpx
from src.tools.base import Tool
from src.core.logger import logger


class HttpRequestTool(Tool):
    """Allows agents to make HTTP requests to APIs and web services."""

    def __init__(self):
        super().__init__(
            "http_request",
            "Make an HTTP request to any URL. Supports GET, POST, PUT, DELETE. "
            "Use this to call APIs, fetch data from URLs, or interact with web services. "
            "Returns the response body (truncated to 4000 chars) and status code.",
            args_schema={
                "url": "The full URL to request (e.g. https://api.example.com/data)",
                "method": "HTTP method: GET, POST, PUT, DELETE (default: GET)",
                "body": "Optional JSON body for POST/PUT requests, as a string",
                "headers": "Optional headers as a JSON string, e.g. '{\"Authorization\": \"Bearer xxx\"}'",
            }
        )

    async def run(self, url: str, method: str = "GET", body: str = "", headers: str = "", **kwargs) -> str:
        method = method.upper()
        if method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"):
            return f"Unsupported HTTP method: {method}"

        try:
            import json as _json

            # Parse optional headers
            req_headers = {}
            if headers and headers.strip():
                try:
                    req_headers = _json.loads(headers)
                except _json.JSONDecodeError:
                    return "Error: 'headers' must be a valid JSON string."

            # Parse optional body
            req_body = None
            if body and body.strip():
                try:
                    req_body = _json.loads(body)
                except _json.JSONDecodeError:
                    # Send as raw string if not valid JSON
                    req_body = body

            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                if method in ("POST", "PUT", "PATCH") and isinstance(req_body, dict):
                    response = await client.request(
                        method, url, json=req_body, headers=req_headers
                    )
                elif method in ("POST", "PUT", "PATCH") and isinstance(req_body, str):
                    response = await client.request(
                        method, url, content=req_body, headers=req_headers
                    )
                else:
                    response = await client.request(method, url, headers=req_headers)

            status = response.status_code
            content_type = response.headers.get("content-type", "")
            body_text = response.text

            # Truncate large responses
            if len(body_text) > 4000:
                body_text = body_text[:4000] + "\n\n... [TRUNCATED — response was " + str(len(response.text)) + " chars]"

            logger.info(f"HTTP {method} {url} → {status} ({len(response.text)} chars)")
            return f"HTTP {status}\nContent-Type: {content_type}\n\n{body_text}"

        except httpx.TimeoutException:
            return f"Error: Request to {url} timed out after 30 seconds."
        except httpx.ConnectError as e:
            return f"Error: Could not connect to {url}: {e}"
        except Exception as e:
            logger.error(f"HTTP request error: {e}")
            return f"Error making HTTP request: {e}"

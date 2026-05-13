import time
import httpx

from .secret_loader import get_api_key


def _get_provider_settings(provider_name: str) -> dict:
    try:
        from ..database import SessionLocal
        from ..models import ProviderConfig
        db = SessionLocal()
        prov = db.query(ProviderConfig).filter(
            ProviderConfig.name == provider_name,
            ProviderConfig.enabled == True,
        ).first()
        db.close()
        if prov:
            return {
                "base_url": prov.base_url,
                "timeout_seconds": prov.timeout_seconds,
                "app_name": prov.app_name or "",
                "site_url": prov.site_url or "",
            }
    except Exception:
        pass
    return {"base_url": "http://localhost:4000/v1", "timeout_seconds": 180, "app_name": "", "site_url": ""}


class GenericOpenAIClient:
    """Client OpenAI-compatible generico per provider configurati nel DB (es. LiteLLM)."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        settings = _get_provider_settings(provider_name)
        self.base_url = settings["base_url"].rstrip("/")
        self.timeout = settings["timeout_seconds"]
        self.app_name = settings["app_name"]
        self.site_url = settings["site_url"]

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.0,
        top_p: float = 0.9,
        max_tokens: int = 1024,
        response_format: str | None = None,
        extra: dict | None = None,
    ) -> dict:
        result = {
            "provider": self.provider_name,
            "model": model,
            "text": "",
            "raw": {},
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "timing": {"latency_ms": 0, "tokens_per_second": 0},
            "error": None,
        }

        api_key = get_api_key(self.provider_name) or "no-key"
        start = time.time()

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if self.app_name:
            headers["X-Title"] = self.app_name
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}
        if extra:
            payload.update(extra)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                latency = (time.time() - start) * 1000
                result["timing"]["latency_ms"] = round(latency, 2)

                if response.status_code in (401, 403):
                    result["error"] = "Authentication error: Invalid or missing API key"
                    return result
                if response.status_code == 429:
                    result["error"] = "Rate limit exceeded"
                    return result
                if response.status_code != 200:
                    result["error"] = f"{self.provider_name} returned status {response.status_code}: {response.text[:500]}"
                    return result

                data = response.json()
                result["raw"] = data
                choices = data.get("choices", [])
                if choices:
                    result["text"] = choices[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                result["usage"]["prompt_tokens"] = usage.get("prompt_tokens", 0)
                result["usage"]["completion_tokens"] = usage.get("completion_tokens", 0)
                result["usage"]["total_tokens"] = usage.get("total_tokens", 0)
                if usage.get("completion_tokens", 0) > 0 and latency > 0:
                    result["timing"]["tokens_per_second"] = round(usage["completion_tokens"] / (latency / 1000), 2)

        except httpx.TimeoutException:
            result["error"] = f"Timeout: {self.provider_name} request exceeded time limit"
            result["timing"]["latency_ms"] = (time.time() - start) * 1000
        except httpx.ConnectError:
            result["error"] = f"Cannot connect to {self.provider_name} at {self.base_url}"
            result["timing"]["latency_ms"] = (time.time() - start) * 1000
        except Exception as e:
            result["error"] = f"{self.provider_name} error: {str(e)}"
            result["timing"]["latency_ms"] = (time.time() - start) * 1000

        return result

    async def probe(self, model: str) -> dict:
        return await self.chat(
            model=model,
            messages=[{"role": "user", "content": "Rispondi solo con: OK"}],
            max_tokens=10,
        )

import time
import httpx

from .config_loader import get_provider_config as _get_cfg


def _get_provider_settings(provider_name: str) -> dict:
    try:
        from ..database import SessionLocal
        from ..models import ProviderConfig
        db = SessionLocal()
        prov = db.query(ProviderConfig).filter(ProviderConfig.name == provider_name, ProviderConfig.enabled == True).first()
        db.close()
        if prov:
            return {
                "base_url": prov.base_url,
                "timeout_seconds": prov.timeout_seconds,
                "app_name": prov.app_name,
                "site_url": prov.site_url,
            }
    except Exception:
        pass
    cfg = _get_cfg(provider_name)
    return {
        "base_url": cfg.get("base_url", "http://localhost:11434"),
        "timeout_seconds": cfg.get("timeout_seconds", 180),
        "app_name": cfg.get("app_name", ""),
        "site_url": cfg.get("site_url", ""),
    }


class OllamaClient:
    def __init__(self):
        settings = _get_provider_settings("ollama")
        self.base_url = settings["base_url"]
        self.timeout = settings["timeout_seconds"]
        self.is_openai_compat = self.base_url.rstrip("/").endswith("/v1")

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
            "provider": "ollama",
            "model": model,
            "text": "",
            "raw": {},
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "timing": {"latency_ms": 0, "tokens_per_second": 0},
            "error": None,
        }

        start = time.time()

        if self.is_openai_compat:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            }
            if response_format and response_format == "json":
                payload["response_format"] = {"type": "json_object"}
            ep = f"{self.base_url}/chat/completions"
        else:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_predict": max_tokens,
                },
            }
            if response_format and response_format == "json":
                payload["format"] = "json"
            ep = f"{self.base_url}/api/chat"

        if extra:
            payload.update(extra)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(ep, json=payload)
                latency = (time.time() - start) * 1000
                result["timing"]["latency_ms"] = round(latency, 2)

                if response.status_code != 200:
                    result["error"] = f"Ollama returned status {response.status_code}: {response.text[:500]}"
                    return result

                data = response.json()
                result["raw"] = data

                if self.is_openai_compat:
                    choices = data.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        result["text"] = msg.get("content", "")
                    usage = data.get("usage", {})
                    result["usage"]["prompt_tokens"] = usage.get("prompt_tokens", 0)
                    result["usage"]["completion_tokens"] = usage.get("completion_tokens", 0)
                    result["usage"]["total_tokens"] = usage.get("total_tokens", 0)
                    if usage.get("completion_tokens", 0) > 0 and latency > 0:
                        result["timing"]["tokens_per_second"] = round(usage["completion_tokens"] / (latency / 1000), 2)
                else:
                    message = data.get("message", {})
                    result["text"] = message.get("content", "")
                    prompt_eval = data.get("prompt_eval_count", 0)
                    eval_count = data.get("eval_count", 0)
                    result["usage"]["prompt_tokens"] = prompt_eval
                    result["usage"]["completion_tokens"] = eval_count
                    result["usage"]["total_tokens"] = prompt_eval + eval_count
                    if eval_count > 0 and latency > 0:
                        result["timing"]["tokens_per_second"] = round(eval_count / (latency / 1000), 2)

        except httpx.TimeoutException:
            result["error"] = "Timeout: Ollama request exceeded time limit"
            result["timing"]["latency_ms"] = (time.time() - start) * 1000
        except httpx.ConnectError:
            result["error"] = "Cannot connect to Ollama. Is it running?"
            result["timing"]["latency_ms"] = (time.time() - start) * 1000
        except Exception as e:
            result["error"] = f"Ollama error: {str(e)}"
            result["timing"]["latency_ms"] = (time.time() - start) * 1000

        return result

    async def probe(self, model: str) -> dict:
        return await self.chat(
            model=model,
            messages=[{"role": "user", "content": "Rispondi solo con: OK"}],
            max_tokens=10,
        )

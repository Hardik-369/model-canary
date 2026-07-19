from __future__ import annotations

from abc import abstractmethod
from typing import Any

import httpx

from model_canary.core.exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from model_canary.core.interfaces import Provider
from model_canary.core.models import (
    CostMetrics,
    ProviderConfig,
    TokenUsage,
)


class BaseProvider(Provider):
    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def config(self) -> ProviderConfig:
        return self._config

    @property
    def name(self) -> str:
        return self._config.name

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            timeout = httpx.Timeout(
                self._config.timeout,
                connect=10.0,
            )
            headers = self._get_headers()
            self._client = httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                follow_redirects=True,
            )
        return self._client

    @abstractmethod
    def _get_headers(self) -> dict[str, str]:
        ...

    @abstractmethod
    def _get_api_url(self) -> str:
        ...

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        url = f"{self._get_api_url()}{endpoint}"

        for attempt in range(self._config.max_retries):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                )

                if response.status_code == 401:
                    raise ProviderAuthError(
                        f"Authentication failed for provider '{self.name}': {response.text}"
                    )
                if response.status_code == 429:
                    raise ProviderRateLimitError(
                        f"Rate limited by provider '{self.name}': {response.text}"
                    )
                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                if attempt == self._config.max_retries - 1:
                    raise ProviderTimeoutError(
                        f"Provider '{self.name}' timed out: {e}"
                    )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < self._config.max_retries - 1:
                    import asyncio

                    await asyncio.sleep(self._config.retry_delay * (2**attempt))
                    continue
                raise ProviderError(
                    f"HTTP error from provider '{self.name}': {e}"
                )
            except httpx.RequestError as e:
                if attempt == self._config.max_retries - 1:
                    raise ProviderError(
                        f"Request failed for provider '{self.name}': {e}"
                    )

        raise ProviderError(f"Max retries exceeded for provider '{self.name}'")

    async def check_health(self) -> bool:
        try:
            await self.list_models()
            return True
        except ProviderError:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _extract_token_usage(self, data: dict[str, Any]) -> TokenUsage:
        usage = data.get("usage", {})
        return TokenUsage(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            reasoning_tokens=usage.get("reasoning_tokens"),
        )

    def _calculate_cost(
        self, token_usage: TokenUsage, model: str
    ) -> CostMetrics:
        from model_canary.utils.costs import estimate_cost

        cost = estimate_cost(
            model=model,
            prompt_tokens=token_usage.prompt_tokens,
            completion_tokens=token_usage.completion_tokens,
            provider=self.provider_type,
        )
        return CostMetrics(
            total_cost=cost,
            cost_per_prompt_token=cost / max(token_usage.prompt_tokens, 1),
            cost_per_completion_token=cost / max(token_usage.completion_tokens, 1),
        )

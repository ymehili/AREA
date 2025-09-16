"""Project-specific Python startup adjustments.

Ensures third-party dependencies missing optional typing backports
still expose the attributes expected by our toolchain."""

from __future__ import annotations

import inspect

try:
    import typing_extensions as _typing_extensions
except Exception:  # pragma: no cover - defensive guard for partial envs
    _typing_extensions = None  # type: ignore[assignment]
else:
    if _typing_extensions is not None and not hasattr(_typing_extensions, "TypeIs"):
        from typing import Any, TypeVar, Generic

        _T_co = TypeVar("_T_co", covariant=True)

        class _TypeIs(Generic[_T_co]):
            """Fallback implementation matching typing_extensions API surface."""

            def __class_getitem__(cls, item: Any) -> "_TypeIs[_T_co]":
                return cls  # runtime semantics unused; return class for compatibility

        _typing_extensions.TypeIs = _TypeIs  # type: ignore[attr-defined]

try:
    import httpx as _httpx
except Exception:  # pragma: no cover - optional dependency
    _httpx = None
else:
    if _httpx is not None:
        client_signature = inspect.signature(_httpx.Client.__init__)
        if "app" not in client_signature.parameters:
            original_client_init = _httpx.Client.__init__

            def _patched_client_init(self, *args, app=None, transport=None, **kwargs):
                if app is not None and transport is None:
                    transport = _httpx.ASGITransport(app=app)
                return original_client_init(self, *args, transport=transport, **kwargs)

            _httpx.Client.__init__ = _patched_client_init  # type: ignore[assignment]

        async_client_signature = inspect.signature(_httpx.AsyncClient.__init__)
        if "app" not in async_client_signature.parameters:
            original_async_init = _httpx.AsyncClient.__init__

            def _patched_async_client_init(self, *args, app=None, transport=None, **kwargs):
                if app is not None and transport is None:
                    transport = _httpx.ASGITransport(app=app)
                return original_async_init(self, *args, transport=transport, **kwargs)

            _httpx.AsyncClient.__init__ = _patched_async_client_init  # type: ignore[assignment]

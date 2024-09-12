# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Any, Callable, List, Tuple, Dict, Awaitable

plantuml_logger = logging.getLogger("PlantUML")
plantuml_logger.setLevel(logging.INFO)
plantuml_logger.setLevel(logging.DEBUG)


# Code based on https://stackoverflow.com/a/23036785/156169
def async_test(f: Callable[..., Any]) -> Callable[..., None]:
    def wrapper(*args: Any, **kwargs: Any):
        loop = asyncio.get_event_loop()
        t = loop.create_task(f(*args, **kwargs))
        loop.run_until_complete(t)
    return wrapper


class Mock:
    def __init__(self) -> None:
        self._calls: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []
        self._return_values: Dict[str, Any] = {}

    def __getattr__(self, name: str) -> Callable[..., Any]:
        if name.startswith('async_'):
            async def async_method(*args: Any, **kwargs: Any) -> Any:
                self._calls.append((name, args, kwargs))
                return self._return_values.get(name, None)
            return async_method
        else:
            def method(*args: Any, **kwargs: Any) -> Any:
                self._calls.append((name, args, kwargs))
                return self._return_values.get(name, None)
            return method

    def set_return_value(self, name: str, value: Any) -> None:
        self._return_values[name] = value

    def assert_called_with(self, name: str, *args: Any, **kwargs: Any) -> None:
        for call in self._calls:
            if call[0] == name and call[1] == args and call[2] == kwargs:
                return
        raise AssertionError(f"Expected call not found: {name} with args {args} and kwargs {kwargs}")

    def assert_called_once(self, name: str, *args: Any, **kwargs: Any) -> None:
        calls = [call for call in self._calls if call[0] == name and call[1] == args and call[2] == kwargs]

        if len(calls) == 1:
            self.reset_calls_for(name)
            return

        raise AssertionError(
            f"Expected {name} to be called once with args {args} and kwargs {kwargs}, "
            f"but was called {len(calls)} times"
        )

    def reset_calls_for(self, name: str) -> None:
        self._calls = [call for call in self._calls if call[0] != name]


def plantuml_logging(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        plantuml_logger.debug("\n@startuml %s", func.__name__)
        try:
            return await func(*args, **kwargs)
        finally:
            plantuml_logger.debug("@enduml")
    return wrapper

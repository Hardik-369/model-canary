from __future__ import annotations

import importlib
import importlib.metadata
import logging
from typing import Any

from model_canary.core.exceptions import PluginLoadError, PluginNotFoundError
from model_canary.core.interfaces import Plugin, PluginType

logger = logging.getLogger("model_canary.plugins")


class PluginManager:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._plugin_metadata: dict[str, dict[str, Any]] = {}

    def discover(self, group: str = "model_canary.plugins") -> list[str]:
        discovered = []
        try:
            for ep in importlib.metadata.entry_points(group=group):
                try:
                    plugin_cls = ep.load()
                    discovered.append(ep.name)
                    self._plugin_metadata[ep.name] = {
                        "entry_point": ep.name,
                        "module": ep.value,
                        "group": group,
                    }
                    logger.debug("Discovered plugin: %s (%s)", ep.name, ep.value)
                except Exception as e:
                    logger.warning("Failed to load plugin entry point '%s': %s", ep.name, e)
        except Exception as e:
            logger.warning("Failed to discover plugins: %s", e)
        return discovered

    def register(self, name: str, plugin: Plugin) -> None:
        self._plugins[name] = plugin

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)

    def get(self, name: str) -> Plugin:
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' not found")
        return self._plugins[name]

    def list_plugins(self) -> dict[str, dict[str, Any]]:
        result = {}
        for name, plugin in self._plugins.items():
            result[name] = {
                "name": plugin.name,
                "type": plugin.plugin_type.value,
                "version": plugin.version,
            }
        return result

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[Plugin]:
        return [
            p for p in self._plugins.values() if p.plugin_type == plugin_type
        ]

    def load_and_register(
        self,
        module_path: str,
        config: dict[str, Any] | None = None,
    ) -> Plugin:
        try:
            module_name, class_name = module_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            plugin_cls: type[Plugin] = getattr(module, class_name)

            plugin = plugin_cls()
            plugin.initialize(config or {})
            self._plugins[plugin.name] = plugin

            logger.info("Loaded plugin: %s (type: %s, version: %s)", plugin.name, plugin.plugin_type.value, plugin.version)
            return plugin
        except ImportError as e:
            raise PluginLoadError(f"Failed to import plugin module '{module_path}': {e}")
        except AttributeError as e:
            raise PluginLoadError(f"Plugin class not found in '{module_path}': {e}")
        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin '{module_path}': {e}")

    def load_all(self, plugin_paths: list[str]) -> list[Plugin]:
        loaded = []
        for path in plugin_paths:
            try:
                plugin = self.load_and_register(path)
                loaded.append(plugin)
            except PluginLoadError as e:
                logger.error("Failed to load plugin '%s': %s", path, e)
        return loaded

    def shutdown_all(self) -> None:
        for name, plugin in self._plugins.items():
            try:
                plugin.shutdown()
                logger.debug("Shut down plugin: %s", name)
            except Exception as e:
                logger.warning("Error shutting down plugin '%s': %s", name, e)
        self._plugins.clear()

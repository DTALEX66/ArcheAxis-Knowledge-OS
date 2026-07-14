"""Canonical service identities and versioned compatibility aliases."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

_SERVICE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_PYTHON_PACKAGE_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class NamingRegistryError(ValueError):
    """Base error for invalid registries and unresolved service names."""


class UnknownServiceNameError(NamingRegistryError):
    """Raised when a value is neither canonical nor a registered alias."""


class AmbiguousServiceAliasError(NamingRegistryError):
    """Raised when one normalized alias identifies multiple services."""


@dataclass(frozen=True)
class ServiceIdentity:
    service_id: str
    python_package: str
    api_prefix: str
    display: dict[str, str]
    compatibility_path: str | None = None
    deprecated_alias: bool = False


class NamingRegistry:
    """Validated canonical service identities with explicit legacy aliases."""

    def __init__(
        self,
        services: dict[str, ServiceIdentity],
        aliases: dict[str, str],
    ) -> None:
        self._services = services
        self._aliases = aliases

    @staticmethod
    def _alias_key(value: str) -> str:
        return unicodedata.normalize("NFC", value).casefold()

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> NamingRegistry:
        if payload.get("version") != 1:
            raise NamingRegistryError("naming registry version must be 1")
        required_locales = payload.get("required_locales")
        if not isinstance(required_locales, list) or not all(
            isinstance(locale, str) and locale for locale in required_locales
        ):
            raise NamingRegistryError("required_locales must be a non-empty string list")
        raw_services = payload.get("services")
        if not isinstance(raw_services, dict) or not raw_services:
            raise NamingRegistryError("services must be a non-empty mapping")

        services: dict[str, ServiceIdentity] = {}
        aliases: dict[str, str] = {}
        for service_id, raw in raw_services.items():
            if not isinstance(service_id, str) or not _SERVICE_ID_RE.fullmatch(service_id):
                raise NamingRegistryError(f"invalid canonical service id: {service_id!r}")
            if not isinstance(raw, dict):
                raise NamingRegistryError(f"service {service_id!r} must be a mapping")
            python_package = raw.get("python_package")
            if not isinstance(python_package, str) or not _PYTHON_PACKAGE_RE.fullmatch(
                python_package
            ):
                raise NamingRegistryError(
                    f"invalid python package for {service_id!r}: {python_package!r}"
                )
            api_prefix = raw.get("api_prefix")
            if not isinstance(api_prefix, str) or not api_prefix.startswith("/"):
                raise NamingRegistryError(f"invalid API prefix for {service_id!r}")
            display = raw.get("display")
            if not isinstance(display, dict) or any(
                not isinstance(display.get(locale), str) or not display[locale]
                for locale in required_locales
            ):
                raise NamingRegistryError(
                    f"service {service_id!r} is missing required locale labels"
                )
            compatibility_path = raw.get("compatibility_path")
            if compatibility_path is not None and not isinstance(compatibility_path, str):
                raise NamingRegistryError(
                    f"compatibility_path for {service_id!r} must be a string"
                )
            services[service_id] = ServiceIdentity(
                service_id=service_id,
                python_package=python_package,
                api_prefix=api_prefix,
                display={str(key): str(value) for key, value in display.items()},
                compatibility_path=compatibility_path,
            )

            raw_aliases = raw.get("deprecated_aliases", [])
            if not isinstance(raw_aliases, list) or not all(
                isinstance(alias, str) and alias for alias in raw_aliases
            ):
                raise NamingRegistryError(
                    f"deprecated_aliases for {service_id!r} must be a string list"
                )
            for alias in raw_aliases:
                key = cls._alias_key(alias)
                owner = aliases.get(key)
                if owner is not None and owner != service_id:
                    raise AmbiguousServiceAliasError(
                        f"alias {key!r} resolves to both {owner!r} and {service_id!r}"
                    )
                aliases[key] = service_id

        for service_id in services:
            key = cls._alias_key(service_id)
            owner = aliases.get(key)
            if owner is not None and owner != service_id:
                raise AmbiguousServiceAliasError(
                    f"canonical id {service_id!r} collides with alias for {owner!r}"
                )

        return cls(services, aliases)

    def resolve_service(self, value: str) -> ServiceIdentity:
        normalized = unicodedata.normalize("NFC", value)
        canonical = self._services.get(normalized)
        if canonical is not None:
            return canonical
        service_id = self._aliases.get(self._alias_key(normalized))
        if service_id is None:
            raise UnknownServiceNameError(f"unknown service name: {value!r}")
        return replace(self._services[service_id], deprecated_alias=True)

    @property
    def services(self) -> tuple[ServiceIdentity, ...]:
        return tuple(self._services[key] for key in sorted(self._services))


def load_naming_registry(path: Path) -> NamingRegistry:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise NamingRegistryError("naming registry root must be a mapping")
    return NamingRegistry.from_mapping(payload)

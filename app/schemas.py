"""Esquemas Pydantic de entrada (request). Las respuestas se arman a mano
como dict en app/main.py, igual que GET /states: no hay response_model
porque no hay una capa ORM/declarativa que lo justifique todavía.
"""

import unicodedata
from datetime import UTC, datetime

from pydantic import BaseModel, field_validator

# Categorías Unicode que no dejan ningún carácter visible (docs/contrato-api.md,
# sección Convenciones, "Normalización de texto"). No basta con str.strip():
# hay invisibles, como U+200B, que lo atraviesan.
CATEGORIAS_INVISIBLES = {"Cc", "Cf", "Zl", "Zp", "Zs"}


def normalizar_titulo(value: str) -> str:
    """Recorta el espacio de los extremos y rechaza un título sin ningún
    carácter visible, por categoría Unicode."""
    recortado = value.strip()
    if all(unicodedata.category(c) in CATEGORIAS_INVISIBLES for c in recortado):
        raise ValueError("El título no puede quedar vacío")
    return recortado


def normalizar_due_at(value: datetime | None) -> datetime | None:
    """Rechaza una fecha sin zona horaria (es ambigua, docs/contrato-api.md,
    sección Tareas v2) y normaliza el resto a UTC antes de guardar."""
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("due_at debe incluir zona horaria")
    return value.astimezone(UTC)


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    project_id: int
    state_id: int
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def _normalizar_title(cls, value: str) -> str:
        return normalizar_titulo(value)

    @field_validator("due_at")
    @classmethod
    def _normalizar_due_at(cls, value: datetime | None) -> datetime | None:
        return normalizar_due_at(value)


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    project_id: int | None = None
    state_id: int | None = None
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def _normalizar_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalizar_titulo(value)

    @field_validator("due_at")
    @classmethod
    def _normalizar_due_at(cls, value: datetime | None) -> datetime | None:
        return normalizar_due_at(value)

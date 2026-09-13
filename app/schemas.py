"""Esquemas Pydantic de entrada (request). Las respuestas se arman a mano
como dict en app/main.py, igual que GET /states: no hay response_model
porque no hay una capa ORM/declarativa que lo justifique todavía.
"""

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

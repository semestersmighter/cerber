"""Modèles de requêtes (validation automatique par Pydantic)."""
from decimal import Decimal

from pydantic import BaseModel, Field

NIF = Field(pattern=r"^\d{13}$", description="Numéro fiscal (13 chiffres)")
CODE = Field(pattern=r"^\d{6}$", description="Code TOTP à 6 chiffres")
PASSWORD = Field(min_length=1, max_length=256)
EMAIL = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
ADDRESS = Field(default="", max_length=500)


class LoginIn(BaseModel):
    nif: str = NIF
    password: str = PASSWORD


class CodeIn(BaseModel):
    code: str = CODE


class ForgotPasswordIn(BaseModel):
    nif: str = NIF
    code: str = CODE
    new_password: str = PASSWORD


class ProfileIn(BaseModel):
    email: str = EMAIL
    address: str = ADDRESS


class ChangePasswordIn(BaseModel):
    current_password: str = PASSWORD
    new_password: str = PASSWORD


class PasswordIn(BaseModel):
    password: str = PASSWORD


class UserCreateIn(BaseModel):
    nif: str = NIF
    email: str = EMAIL
    address: str = ADDRESS
    password: str = PASSWORD
    role_ids: list[int] = Field(min_length=1)


class ResourceIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,50}$")
    name: str = Field(min_length=1, max_length=100)
    # Chemin local (/intranet/) ou URL http(s) externe.
    # Refuse javascript:, data: et les URL "//hote" (redirection vers un autre site).
    url: str = Field(pattern=r"^(https?://\S+|/|/[^/\s]\S*)$", max_length=500)
    role_ids: list[int] = []


class RoleIdsIn(BaseModel):
    role_ids: list[int]


class TaxRateIn(BaseModel):
    # Taux du prélèvement à la source, en %, une décimale (ex. 7.5)
    rate: Decimal = Field(ge=0, le=60, max_digits=3, decimal_places=1)

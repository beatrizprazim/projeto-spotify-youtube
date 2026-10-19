"""Configuração central do pipeline: variáveis de ambiente e logging."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")


def _env(nome: str, padrao: str = ""):
    # lê o ambiente no momento em que o Config é criado (não na importação)
    return field(default_factory=lambda: os.getenv(nome, padrao).strip())


@dataclass
class Config:
    modo: str = _env("MODO", "simulado")
    # sem DATABASE_URL usa um SQLite local (prático para testar sem Docker)
    database_url: str = _env("DATABASE_URL", f"sqlite:///{RAIZ / 'data' / 'tendencias.db'}")
    spotify_client_id: str = _env("SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = _env("SPOTIFY_CLIENT_SECRET")
    youtube_api_key: str = _env("YOUTUBE_API_KEY")
    paises: list[str] = field(
        default_factory=lambda: [
            p.strip().upper()
            for p in os.getenv("PAISES", "BR,US,MX,AR,ES,JP").split(",")
            if p.strip()
        ]
    )
    charts_dir: Path = field(default_factory=lambda: RAIZ / os.getenv("CHARTS_DIR", "data/charts"))
    intervalo_requisicoes: float = field(
        default_factory=lambda: float(os.getenv("INTERVALO_REQUISICOES", "0.2")))

    def validar(self) -> None:
        self.modo = self.modo.lower()
        if self.modo not in {"simulado", "real"}:
            raise ValueError("MODO deve ser 'simulado' ou 'real'")
        if self.modo == "real":
            faltando = [
                nome
                for nome, valor in [
                    ("SPOTIFY_CLIENT_ID", self.spotify_client_id),
                    ("SPOTIFY_CLIENT_SECRET", self.spotify_client_secret),
                    ("YOUTUBE_API_KEY", self.youtube_api_key),
                ]
                if not valor
            ]
            if faltando:
                raise ValueError(
                    "Modo real exige as variáveis: " + ", ".join(faltando)
                )


def configurar_logging() -> None:
    pasta = RAIZ / "logs"
    pasta.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(pasta / "pipeline.log", encoding="utf-8"),
        ],
        force=True,
    )
    # bibliotecas barulhentas
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

"""Funções auxiliares compartilhadas: normalização de texto e controle de requisições."""
from __future__ import annotations

import re
import threading
import time

from unidecode import unidecode

# termos que aparecem em títulos de vídeo mas não fazem parte do nome da música
RUIDO_TITULO = [
    "official music video", "official video", "official audio", "music video",
    "video oficial", "clipe oficial", "videoclipe oficial", "videoclipe", "clipe",
    "lyric video", "lyrics", "letra", "visualizer", "audio oficial", "audio",
    "official", "oficial", "ao vivo", "live", "4k", "hd", "mv", "dvd",
]
_RE_RUIDO = re.compile(r"\b(" + "|".join(re.escape(t) for t in RUIDO_TITULO) + r")\b")
_RE_FEAT = re.compile(r"\b(feat|ft|featuring|part|participacao especial)\b\.?")
_RE_NAO_ALNUM = re.compile(r"[^a-z0-9 ]+")
_RE_ESPACOS = re.compile(r"\s+")


def normalizar_nome(texto: str | None) -> str:
    """Minúsculas, sem acentos, sem pontuação. Usado para artistas e faixas."""
    if not texto:
        return ""
    t = unidecode(str(texto)).lower()
    t = t.replace("&", " ")
    t = _RE_NAO_ALNUM.sub(" ", t)
    return _RE_ESPACOS.sub(" ", t).strip()


def normalizar_titulo_video(titulo: str | None) -> str:
    """Remove ruído típico de títulos do YouTube: (Clipe Oficial), ft., | Lyrics, hashtags..."""
    if not titulo:
        return ""
    t = unidecode(str(titulo)).lower()
    t = re.sub(r"#\w+", " ", t)                 # hashtags
    t = re.sub(r"[\(\[\{]", " ", t)             # mantém o conteúdo dos parênteses
    t = t.replace("&", " ")
    t = _RE_NAO_ALNUM.sub(" ", t)
    t = _RE_RUIDO.sub(" ", t)
    t = _RE_FEAT.sub(" ", t)
    return _RE_ESPACOS.sub(" ", t).strip()


def separar_artistas(texto: str | None) -> list[str]:
    """'A, B; C' -> ['A', 'B', 'C'] (mantém a grafia original).

    Não separa por '&' ou ' e ' de propósito: duplas como 'Henrique & Juliano'
    são UM artista no Spotify. A lista oficial de artistas vem da API.
    """
    if not texto:
        return []
    partes = re.split(r"[,;]", str(texto))
    return [p.strip() for p in partes if p.strip()]


class LimitadorRequisicoes:
    """Garante um intervalo mínimo entre chamadas (rate limiting do lado do cliente)."""

    def __init__(self, intervalo_s: float):
        self.intervalo = max(0.0, intervalo_s)
        self._ultimo = 0.0
        self._trava = threading.Lock()

    def aguardar(self) -> None:
        with self._trava:
            espera = self._ultimo + self.intervalo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.monotonic()

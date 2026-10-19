"""Validação da qualidade dos dados transformados (etapa 3 do enunciado)."""
from __future__ import annotations

import logging

import pandas as pd

log = logging.getLogger("qualidade")


class ErroQualidade(ValueError):
    pass


def validar(df: pd.DataFrame, nome: str, chaves: list[str],
            obrigatorias: list[str] | None = None,
            intervalos: dict[str, tuple[float | None, float | None]] | None = None,
            minimo_linhas: int = 1) -> pd.DataFrame:
    """Checa: volume mínimo, chave única, campos obrigatórios e faixas de valores.

    Erros graves (chave duplicada, obrigatório nulo, tabela vazia) interrompem a carga.
    Valores fora da faixa são registrados como aviso.
    """
    problemas = []
    if len(df) < minimo_linhas:
        problemas.append(f"apenas {len(df)} linhas (mínimo {minimo_linhas})")
    dup = df.duplicated(subset=chaves).sum()
    if dup:
        problemas.append(f"{dup} chaves duplicadas em {chaves}")
    for col in obrigatorias or []:
        nulos = df[col].isna().sum()
        if nulos:
            problemas.append(f"{nulos} nulos na coluna obrigatória '{col}'")
    for col, (mn, mx) in (intervalos or {}).items():
        serie = pd.to_numeric(df[col], errors="coerce").dropna()
        fora = ((serie < mn).sum() if mn is not None else 0) + \
               ((serie > mx).sum() if mx is not None else 0)
        if fora:
            log.warning("[%s] %d valores de '%s' fora de [%s, %s]", nome, fora, col, mn, mx)
    if problemas:
        raise ErroQualidade(f"[{nome}] " + "; ".join(problemas))
    log.info("[%s] qualidade ok: %d linhas", nome, len(df))
    return df

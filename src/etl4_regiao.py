"""ETL 4 - Análise de Engajamento por Região.
Responsável: Beatriz Prazim

Compara países em cada semana:
  - Spotify: % de faixas "locais" (só aparecem naquele país), duração média,
    gênero e artista mais fortes, streams totais.
  - YouTube: quantidade de vídeos de música em alta, engajamento médio, views medianas.
  - Semelhança entre países: índice de Jaccard dos Top 50
    (faixas em comum / faixas na união; 0 = nada em comum, 1 = idênticos).
"""
from __future__ import annotations

import logging
from itertools import combinations

import pandas as pd

from src import db
from src.config import Config
from src.qualidade import validar

log = logging.getLogger("etl4")


def jaccard(a: set, b: set) -> float:
    uniao = a | b
    return len(a & b) / len(uniao) if uniao else 0.0


def resumo_regioes(chart: pd.DataFrame, faixas: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    base = chart.merge(faixas[["track_id", "artista_principal", "genero_principal", "duracao_min"]],
                       on="track_id", how="left")
    # em quantos países cada faixa aparece naquela semana
    n_paises = base.groupby(["snapshot_date", "track_id"])["country"].transform("nunique")
    base["local"] = n_paises == 1

    linhas = []
    for (dia, pais), g in base.groupby(["snapshot_date", "country"]):
        v = videos[(videos["snapshot_date"] == dia) & (videos["country"] == pais)]
        artista = g.groupby("artista_principal")["streams"].sum()
        generos = g["genero_principal"].dropna()
        linhas.append({
            "snapshot_date": dia, "country": pais, "n_faixas": len(g),
            "pct_faixas_locais": round(100 * g["local"].mean(), 1),
            "duracao_media_min": round(g["duracao_min"].mean(), 2),
            "genero_top": generos.mode().iloc[0] if not generos.empty else None,
            "artista_top": artista.idxmax() if not artista.empty else None,
            "streams_total": int(g["streams"].sum()),
            "n_videos_musica": len(v),
            "engajamento_medio_yt": round(v["taxa_engajamento"].mean(), 3) if len(v) else None,
            "views_medianas_yt": float(v["views"].median()) if len(v) else None,
        })
    return pd.DataFrame(linhas)


def sobreposicao(chart: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for dia, g in chart.groupby("snapshot_date"):
        conjuntos = {p: set(s["track_id"]) for p, s in g.groupby("country")}
        for a, b in combinations(sorted(conjuntos), 2):
            linhas.append({"snapshot_date": dia, "pais_a": a, "pais_b": b,
                           "jaccard": round(jaccard(conjuntos[a], conjuntos[b]), 3)})
    return pd.DataFrame(linhas, columns=["snapshot_date", "pais_a", "pais_b", "jaccard"])


def executar(cfg: Config, engine) -> dict:
    chart = db.ler(engine, "SELECT snapshot_date, country, track_id, streams FROM spotify_chart")
    faixas = db.ler(engine, "SELECT track_id, artista_principal, genero_principal, duracao_min "
                            "FROM spotify_faixa")
    videos = db.ler(engine, "SELECT snapshot_date, country, views, taxa_engajamento FROM youtube_video")
    for df in (chart, videos):
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.date

    resumo = validar(resumo_regioes(chart, faixas, videos), "regiao_resumo",
                     chaves=["snapshot_date", "country"],
                     intervalos={"pct_faixas_locais": (0, 100)})
    overlap = validar(sobreposicao(chart), "regiao_overlap",
                      chaves=["snapshot_date", "pais_a", "pais_b"],
                      intervalos={"jaccard": (0, 1)}, minimo_linhas=0)
    n = db.upsert(engine, "regiao_resumo", resumo)
    if not overlap.empty:
        n += db.upsert(engine, "regiao_overlap", overlap)
    ultimo = resumo[resumo["snapshot_date"] == resumo["snapshot_date"].max()]
    for r in ultimo.itertuples():
        log.info("ETL4 %s: %.0f%% faixas locais | top: %s | engajamento YT %.2f%%",
                 r.country, r.pct_faixas_locais, r.artista_top, r.engajamento_medio_yt or 0)
    return {"linhas": n}

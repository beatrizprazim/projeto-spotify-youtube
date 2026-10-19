"""ETL 3 - Correlação entre Música e Vídeos Populares.
Responsável: Gabrielle Mendes

Cruza as faixas do Spotify com os vídeos em alta do YouTube. Não existe um ID
em comum entre as plataformas, então o vínculo é feito por similaridade de texto:

  1. normaliza o título do vídeo (tira "Clipe Oficial", "ft.", acentos, hashtags...)
  2. compara com o nome da faixa e com os artistas (rapidfuzz.token_set_ratio)
  3. score = 0,6 * similaridade da música + 0,4 * similaridade do artista
     >= 85 -> 'match'   |   70-84 -> 'revisar' (conferência manual)

Depois mede, por país e semana: quantas faixas do Top 50 também estão em alta
em vídeo, a correlação de Spearman entre posição no chart e views, e a defasagem
entre lançamento da faixa e publicação do vídeo.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from scipy.stats import spearmanr

from src import db
from src.config import Config
from src.qualidade import validar
from src.utils import normalizar_nome, normalizar_titulo_video

log = logging.getLogger("etl3")

LIMIAR_MATCH = 85
LIMIAR_REVISAR = 70
PESO_MUSICA, PESO_ARTISTA = 0.6, 0.4


def score_par(nome_musica: str, artistas: list[str], titulo_norm: str, canal_norm: str) -> float:
    """Similaridade 0-100 entre uma faixa (já normalizada) e um vídeo (já normalizado)."""
    if not nome_musica or not titulo_norm:
        return 0.0
    s_musica = fuzz.token_set_ratio(nome_musica, titulo_norm)
    if s_musica < 80:          # o nome da música precisa estar no título
        return s_musica * PESO_MUSICA
    alvo = f"{titulo_norm} {canal_norm}"
    s_artista = max((fuzz.token_set_ratio(a, alvo) for a in artistas if a), default=0)
    return PESO_MUSICA * s_musica + PESO_ARTISTA * s_artista


def casar(faixas: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    """Para cada vídeo, encontra a faixa mais parecida. Retorna pares acima de 70."""
    cat = [
        (r.track_id, normalizar_nome(r.nome),
         [normalizar_nome(a) for a in str(r.artistas).split(";")])
        for r in faixas.itertuples()
    ]
    unicos = videos.drop_duplicates("video_id")
    pares = []
    for v in unicos.itertuples():
        titulo = v.titulo_normalizado or normalizar_titulo_video(v.titulo)
        canal = normalizar_nome(v.canal)
        melhor_id, melhor, desempate = None, 0.0, 0
        for tid, nome, artistas in cat:
            s = score_par(nome, artistas, titulo, canal)
            # empate (ex.: "Sol" e "Sol Neon" do mesmo artista): vence o nome mais específico
            if s > melhor or (s == melhor and s > 0 and len(nome) > desempate):
                melhor_id, melhor, desempate = tid, s, len(nome)
        if melhor >= LIMIAR_REVISAR:
            pares.append({"track_id": melhor_id, "video_id": v.video_id,
                          "score": round(melhor, 1),
                          "status": "match" if melhor >= LIMIAR_MATCH else "revisar"})
    return pd.DataFrame(pares, columns=["track_id", "video_id", "score", "status"])


def resumir(chart: pd.DataFrame, faixas: pd.DataFrame, videos: pd.DataFrame,
            pares: pd.DataFrame) -> pd.DataFrame:
    confirmados = pares[pares["status"] == "match"]
    v = videos.merge(confirmados[["track_id", "video_id"]], on="video_id")
    # um vídeo por faixa/país/semana: o de mais views
    v = (v.sort_values("views", ascending=False)
          .drop_duplicates(["track_id", "country", "snapshot_date"]))
    base = chart.merge(v[["track_id", "country", "snapshot_date", "views", "publicado_em"]],
                       on=["track_id", "country", "snapshot_date"], how="left")
    base = base.merge(faixas[["track_id", "data_lancamento"]], on="track_id", how="left")

    linhas = []
    for (dia, pais), g in base.groupby(["snapshot_date", "country"]):
        com_video = g.dropna(subset=["views"])
        rho = p = np.nan
        if len(com_video) >= 5:
            rho, p = spearmanr(com_video["position"], com_video["views"])
        defas = (pd.to_datetime(com_video["publicado_em"]) -
                 pd.to_datetime(com_video["data_lancamento"])).dt.days
        linhas.append({
            "snapshot_date": dia, "country": pais,
            "n_faixas_chart": len(g), "n_faixas_com_video": len(com_video),
            "pct_faixas_com_video": round(100 * len(com_video) / len(g), 1) if len(g) else None,
            "spearman_rho": None if np.isnan(rho) else round(float(rho), 3),
            "spearman_p": None if np.isnan(p) else float(p),
            "defasagem_mediana_dias": None if defas.dropna().empty else float(defas.median()),
        })
    return pd.DataFrame(linhas)


def executar(cfg: Config, engine) -> dict:
    faixas = db.ler(engine, "SELECT track_id, nome, artistas, data_lancamento FROM spotify_faixa")
    videos = db.ler(engine, "SELECT video_id, country, snapshot_date, titulo, titulo_normalizado, "
                            "canal, views, publicado_em FROM youtube_video")
    chart = db.ler(engine, "SELECT snapshot_date, country, position, track_id FROM spotify_chart")
    for df in (videos, chart):
        df["snapshot_date"] = pd.to_datetime(df["snapshot_date"]).dt.date

    pares = validar(casar(faixas, videos), "musica_video", chaves=["track_id", "video_id"],
                    intervalos={"score": (LIMIAR_REVISAR, 100)}, minimo_linhas=0)
    resumo = validar(resumir(chart, faixas, videos, pares), "correlacao_resumo",
                     chaves=["snapshot_date", "country"],
                     intervalos={"spearman_rho": (-1, 1), "pct_faixas_com_video": (0, 100)})
    n = db.upsert(engine, "musica_video", pares) + db.upsert(engine, "correlacao_resumo", resumo)
    log.info("ETL3: %d pares (%d match, %d para revisar); %.1f%% do Top 50 com vídeo em alta; "
             "Spearman médio %.2f", len(pares), (pares["status"] == "match").sum(),
             (pares["status"] == "revisar").sum(), resumo["pct_faixas_com_video"].mean(),
             resumo["spearman_rho"].astype(float).mean())
    return {"linhas": n}

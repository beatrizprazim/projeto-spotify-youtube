"""Testes unitários das transformações (rodam sem internet e sem chaves)."""
import json
from datetime import date

import pandas as pd
import pytest

from src.etl1_spotify import transformar_chart, transformar_faixas
from src.etl2_youtube import duracao_segundos, transformar_videos
from src.etl3_correlacao import score_par
from src.etl4_regiao import jaccard, sobreposicao
from src.qualidade import ErroQualidade, validar
from src.utils import normalizar_nome, normalizar_titulo_video


# ---------------- normalização ----------------
def test_normalizar_nome_tira_acentos_e_pontuacao():
    assert normalizar_nome("Coração, Ação & Fé!") == "coracao acao fe"


@pytest.mark.parametrize("titulo, esperado", [
    ("MC Lule - Noite Fogo ft. Doka (Clipe Oficial)", "mc lule noite fogo doka"),
    ("NEON - Gozeto | Videoclipe", "neon gozeto"),
    ("Sol - Mitale (Ao Vivo) #shorts", "sol mitale"),
    ("Mitale • Lua (Official Music Video)", "mitale lua"),
])
def test_normalizar_titulo_remove_ruido(titulo, esperado):
    assert normalizar_titulo_video(titulo) == esperado


# ---------------- ETL 1 ----------------
def _raw_track(tid, nome, artistas, duracao=180000, lanc="2026-05-01", prec="day", generos=None):
    payload = {"track": {"id": tid, "name": nome, "duration_ms": duracao,
                         "album": {"name": "Álbum", "release_date": lanc,
                                   "release_date_precision": prec},
                         "artists": [{"id": a, "name": a} for a in artistas]},
               "artists_detail": [{"id": a, "name": a, "genres": generos or []} for a in artistas]}
    return {"track_id": tid, "payload": json.dumps(payload)}


def test_transformar_faixas_campos_derivados():
    raw = pd.DataFrame([_raw_track("t1", "Música", ["A", "B"], 150000, "2019", "year", ["Funk"])])
    chart = pd.DataFrame({"track_id": ["t1"], "track_name": ["Música"], "artist_names": ["A, B"]})
    f = transformar_faixas(raw, chart).iloc[0]
    assert f["artista_principal"] == "A" and f["n_artistas"] == 2 and f["tem_feat"]
    assert f["duracao_min"] == 2.5
    assert str(f["data_lancamento"]) == "2019-01-01"     # precisão de ano tratada
    assert f["genero_principal"] == "funk"                # padronizado em minúsculas


def test_faixa_sem_metadados_usa_dados_do_chart():
    raw = pd.DataFrame([_raw_track("t1", "X", ["A"])])
    chart = pd.DataFrame({"track_id": ["t1", "t2"], "track_name": ["X", "Y"],
                          "artist_names": ["A", "B, C"]})
    f = transformar_faixas(raw, chart).set_index("track_id")
    assert f.loc["t2", "artista_principal"] == "B"
    assert f.loc["t2", "n_artistas"] == 2


def test_indice_popularidade_entre_0_e_100_e_ordenado():
    raw = pd.DataFrame({"snapshot_date": [date(2026, 1, 1)] * 3, "country": ["BR"] * 3,
                        "position": [1, 2, 50], "track_id": ["a", "b", "c"],
                        "streams": [1000, 600, 100], "weeks_on_chart": [3, 1, 1]})
    c = transformar_chart(raw)
    assert c["indice_popularidade"].between(0, 100).all()
    assert c["indice_popularidade"].is_monotonic_decreasing
    assert c.loc[0, "indice_popularidade"] == 100.0


# ---------------- ETL 2 ----------------
@pytest.mark.parametrize("iso, seg", [("PT3M45S", 225), ("PT1H2M", 3720), ("P0D", None),
                                      (None, None), ("lixo", None)])
def test_duracao_iso8601(iso, seg):
    assert duracao_segundos(iso) == seg


def test_engajamento_e_likes_ocultos():
    item_ok = {"id": "v1", "_posicao": 1,
               "snippet": {"title": "A - B (Clipe Oficial)", "channelTitle": "A",
                           "categoryId": "10", "publishedAt": "2026-10-01T00:00:00Z"},
               "contentDetails": {"duration": "PT3M"},
               "statistics": {"viewCount": "1000", "likeCount": "40", "commentCount": "10"}}
    item_oculto = json.loads(json.dumps(item_ok)) | {"id": "v2"}
    del item_oculto["statistics"]["likeCount"]
    raw = pd.DataFrame([{"video_id": i["id"], "country": "BR", "snapshot_date": date(2026, 10, 11),
                         "payload": json.dumps(i)} for i in (item_ok, item_oculto)])
    cat = pd.DataFrame({"category_id": ["10"], "nome": ["Music"]})
    v = transformar_videos(raw, cat).set_index("video_id")
    assert v.loc["v1", "taxa_engajamento"] == pytest.approx(5.0)   # (40+10)/1000
    assert v.loc["v1", "views_por_dia"] == 100                     # 1000 views / 10 dias
    assert pd.isna(v.loc["v2", "likes"])                           # oculto != zero
    assert v.loc["v1", "categoria"] == "Music"


# ---------------- ETL 3 ----------------
def test_score_reconhece_mesma_musica():
    titulo = normalizar_titulo_video("MC Lule - Noite Fogo (Clipe Oficial)")
    assert score_par("noite fogo", ["mc lule"], titulo, "mc lule") >= 85


def test_score_rejeita_musica_diferente():
    titulo = normalizar_titulo_video("MC Lule - Noite Fogo (Clipe Oficial)")
    assert score_par("verao azul", ["mc lule"], titulo, "mc lule") < 70


# ---------------- ETL 4 ----------------
def test_jaccard():
    assert jaccard({1, 2, 3}, {2, 3, 4}) == 0.5
    assert jaccard(set(), set()) == 0.0


def test_sobreposicao_um_par_por_combinacao():
    chart = pd.DataFrame({"snapshot_date": [1] * 6, "country": list("AABBCC"),
                          "track_id": ["x", "y", "x", "z", "y", "z"]})
    assert len(sobreposicao(chart)) == 3


# ---------------- qualidade ----------------
def test_validar_bloqueia_chave_duplicada():
    with pytest.raises(ErroQualidade):
        validar(pd.DataFrame({"id": [1, 1]}), "t", chaves=["id"])


def test_validar_bloqueia_obrigatorio_nulo():
    with pytest.raises(ErroQualidade):
        validar(pd.DataFrame({"id": [1, 2], "nome": ["a", None]}), "t", chaves=["id"],
                obrigatorias=["nome"])


# ---------------- leitura dos CSVs do Spotify Charts (modo real) ----------------
def test_ler_csvs_charts_tira_pais_e_data_do_nome(tmp_path):
    from src.extract.spotify import ler_csvs_charts
    csv = ("rank,uri,artist_names,track_name,source,peak_rank,previous_rank,weeks_on_chart,streams\n"
           "1,spotify:track:abc,\"Ana, Bia\",Canção,Label,1,2,5,1000\n")
    (tmp_path / "regional-br-weekly-2026-10-16.csv").write_text(csv, encoding="utf-8")
    (tmp_path / "regional-jp-weekly-2026-10-16.csv").write_text(csv, encoding="utf-8")
    df = ler_csvs_charts(tmp_path, ["BR"])          # JP fora da lista de países
    assert list(df["country"].unique()) == ["BR"]
    assert str(df.loc[0, "snapshot_date"]) == "2026-10-16"


def test_sem_csvs_da_erro_explicativo(tmp_path):
    from src.extract.spotify import ler_csvs_charts
    with pytest.raises(FileNotFoundError, match="charts.spotify.com"):
        ler_csvs_charts(tmp_path, ["BR"])


def test_modo_real_sem_chaves_e_recusado(monkeypatch):
    from src.config import Config
    for v in ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "YOUTUBE_API_KEY"]:
        monkeypatch.setenv(v, "")
    cfg = Config()
    cfg.modo = "real"
    with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
        cfg.validar()

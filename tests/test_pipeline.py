"""Teste de ponta a ponta: roda o pipeline inteiro com dados simulados num banco temporário."""
import random

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from src import pipeline
from src.mock_data import Simulador, _id


@pytest.fixture(scope="module")
def banco(tmp_path_factory, monkeypatch_module):
    caminho = tmp_path_factory.mktemp("db") / "teste.db"
    url = f"sqlite:///{caminho}"
    monkeypatch_module.setenv("DATABASE_URL", url)
    assert pipeline.main(["--modo", "simulado"]) == 0
    return create_engine(url)


@pytest.fixture(scope="module")
def monkeypatch_module():
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def contar(engine, tabela):
    with engine.connect() as con:
        return con.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()


def test_todas_as_tabelas_foram_carregadas(banco):
    for t in ["raw_spotify_chart", "raw_spotify_track", "raw_youtube_video", "spotify_faixa",
              "spotify_chart", "youtube_video", "musica_video", "correlacao_resumo",
              "regiao_resumo", "regiao_overlap"]:
        assert contar(banco, t) > 0, t


def test_extraido_igual_carregado(banco):
    # cada linha bruta do chart vira exatamente uma linha tratada
    assert contar(banco, "raw_spotify_chart") == contar(banco, "spotify_chart")
    assert contar(banco, "raw_youtube_video") == contar(banco, "youtube_video")


def test_pipeline_idempotente(banco):
    antes = contar(banco, "spotify_chart")
    assert pipeline.main(["--modo", "simulado", "--etapas", "1"]) == 0
    assert contar(banco, "spotify_chart") == antes          # upsert não duplica


def test_execucoes_auditadas(banco):
    with banco.connect() as con:
        status = {r[0] for r in con.execute(text("SELECT status FROM pipeline_execucao"))}
    assert status == {"ok"}


def test_precisao_do_matching_contra_gabarito(banco):
    """Nos dados simulados sabemos qual vídeo é de qual faixa: medimos a precisão."""
    sim = Simulador(["BR", "US", "MX", "AR", "ES", "JP"])
    gabarito = {}
    for f in sim.faixas:
        r = random.Random(f["id"])
        sim._titulo_video(r, f)
        gabarito[_id(r, 11)] = f["id"]
    with banco.connect() as con:
        mv = pd.read_sql(text("SELECT * FROM musica_video WHERE status = 'match'"), con)
    acertos = sum(gabarito.get(v) == t for v, t in zip(mv["video_id"], mv["track_id"]))
    assert acertos / len(mv) >= 0.95


def test_modo_real_cruza_youtube_de_hoje_com_chart_da_semana(tmp_path, monkeypatch):
    """No modo real a coleta do YouTube é de HOJE e o CSV do chart é de dias antes.
    O pipeline precisa alinhar as datas, senão o ETL 3 não encontra nenhum par."""
    from datetime import timedelta
    from src.config import Config
    from src.extract import spotify as ext_sp, youtube as ext_yt

    url = f"sqlite:///{tmp_path / 'real.db'}"
    for k, v in {"DATABASE_URL": url, "SPOTIFY_CLIENT_ID": "x", "SPOTIFY_CLIENT_SECRET": "x",
                 "YOUTUBE_API_KEY": "x"}.items():
        monkeypatch.setenv(k, v)

    sim_cfg = Config()
    sim_cfg.modo = "simulado"
    raw_chart, raw_track = ext_sp.extrair(sim_cfg)
    ultima = raw_chart["snapshot_date"].max()
    raw_chart = raw_chart[raw_chart["snapshot_date"] == ultima]      # 1 CSV por país
    raw_yt, cat = ext_yt.extrair(sim_cfg)
    raw_yt = raw_yt[raw_yt["snapshot_date"] == ultima].copy()
    raw_yt["snapshot_date"] = ultima + timedelta(days=2)              # coletado 2 dias depois

    monkeypatch.setattr(ext_sp, "extrair", lambda cfg: (raw_chart, raw_track))
    monkeypatch.setattr(ext_yt, "extrair", lambda cfg: (raw_yt, cat))
    assert pipeline.main(["--modo", "real"]) == 0

    eng = create_engine(url)
    with eng.connect() as con:
        datas_yt = {r[0] for r in con.execute(text("SELECT DISTINCT snapshot_date FROM youtube_video"))}
        com_video = con.execute(text("SELECT SUM(n_faixas_com_video) FROM correlacao_resumo")).scalar()
        msg = con.execute(text("SELECT mensagem FROM pipeline_execucao ORDER BY inicio DESC")).first()[0]
    assert {str(d) for d in datas_yt} == {str(ultima)}   # alinhado à semana do chart
    assert com_video > 0                                  # houve cruzamento
    assert msg == "modo=real"                             # dashboard sabe que é real

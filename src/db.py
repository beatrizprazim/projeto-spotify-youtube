"""Acesso ao banco: criação do esquema, upsert idempotente e auditoria."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

log = logging.getLogger("db")
SCHEMA_SQL = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

# chave primária de cada tabela -> usada no ON CONFLICT
CHAVES = {
    "raw_spotify_chart": ["snapshot_date", "country", "track_id"],
    "raw_spotify_track": ["track_id"],
    "raw_youtube_video": ["video_id", "country", "snapshot_date"],
    "raw_youtube_categoria": ["category_id"],
    "spotify_faixa": ["track_id"],
    "spotify_chart": ["snapshot_date", "country", "track_id"],
    "youtube_video": ["video_id", "country", "snapshot_date"],
    "musica_video": ["track_id", "video_id"],
    "correlacao_resumo": ["snapshot_date", "country"],
    "regiao_resumo": ["snapshot_date", "country"],
    "regiao_overlap": ["snapshot_date", "pais_a", "pais_b"],
}


def criar_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        Path(url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, future=True)


def criar_esquema(engine: Engine) -> None:
    # remove comentários "-- ..." antes de separar os comandos por ";"
    sem_comentarios = "\n".join(
        linha.split("--", 1)[0] for linha in SCHEMA_SQL.read_text(encoding="utf-8").splitlines()
    )
    with engine.begin() as con:
        for cmd in sem_comentarios.split(";"):
            if cmd.strip():
                con.execute(text(cmd))
    log.info("Esquema verificado/criado")


def upsert(engine: Engine, tabela: str, df: pd.DataFrame) -> int:
    """Insere ou atualiza linhas pela chave primária (idempotente: rodar 2x não duplica)."""
    if df.empty:
        log.warning("upsert em %s com DataFrame vazio", tabela)
        return 0
    chaves = CHAVES[tabela]
    df = df.drop_duplicates(subset=chaves, keep="last")
    colunas = list(df.columns)
    atualizar = [c for c in colunas if c not in chaves]
    set_sql = ", ".join(f"{c} = excluded.{c}" for c in atualizar)
    acao = f"DO UPDATE SET {set_sql}" if atualizar else "DO NOTHING"
    sql = text(
        f"INSERT INTO {tabela} ({', '.join(colunas)}) "
        f"VALUES ({', '.join(':' + c for c in colunas)}) "
        f"ON CONFLICT ({', '.join(chaves)}) {acao}"
    )
    registros = [{k: _python(v) for k, v in linha.items()}
                 for linha in df.astype(object).to_dict("records")]
    with engine.begin() as con:
        con.execute(sql, registros)
    log.info("%s: %d linhas gravadas (upsert)", tabela, len(registros))
    return len(registros)


def _python(v):
    """Converte tipos do pandas/numpy para tipos que qualquer driver aceita."""
    if v is None or v is pd.NaT or v is pd.NA:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return None if np.isnan(v) else float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def ler(engine: Engine, sql: str, **params) -> pd.DataFrame:
    with engine.connect() as con:
        return pd.read_sql(text(sql), con, params=params)


@contextmanager
def auditar(engine: Engine, etapa: str, info: str | None = None):
    """Registra início, fim, linhas e erro de cada etapa na tabela pipeline_execucao."""
    inicio = datetime.now()
    estado = {"linhas": 0}
    try:
        yield estado
        status, msg = "ok", info
    except Exception as exc:  # registra e propaga
        status, msg = "erro", f"{type(exc).__name__}: {exc}"[:2000]
        log.exception("Falha na etapa %s", etapa)
        raise
    finally:
        with engine.begin() as con:
            con.execute(
                text(
                    "INSERT INTO pipeline_execucao (etapa, inicio, fim, linhas, status, mensagem) "
                    "VALUES (:e, :i, :f, :l, :s, :m)"
                ),
                dict(e=etapa, i=inicio, f=datetime.now(), l=estado["linhas"], s=status, m=msg),
            )

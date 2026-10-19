-- Esquema do banco "tendencias"
-- Camada RAW: dados como vieram das fontes (reprocessáveis)
-- Camada TRATADA: dados limpos, com métricas derivadas, prontos para análise
-- Compatível com PostgreSQL (produção/Docker) e SQLite (testes automatizados).

-- ============ RAW ============
CREATE TABLE IF NOT EXISTS raw_spotify_chart (
    snapshot_date   DATE        NOT NULL,
    country         VARCHAR(2)  NOT NULL,
    position        INTEGER     NOT NULL,
    track_id        VARCHAR(40) NOT NULL,
    track_name      TEXT,
    artist_names    TEXT,
    streams         BIGINT,
    weeks_on_chart  INTEGER,
    extracted_at    TIMESTAMP   NOT NULL,
    PRIMARY KEY (snapshot_date, country, track_id)
);

CREATE TABLE IF NOT EXISTS raw_spotify_track (
    track_id      VARCHAR(40) PRIMARY KEY,
    payload       TEXT        NOT NULL,   -- JSON bruto da API
    extracted_at  TIMESTAMP   NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_youtube_video (
    video_id      VARCHAR(20) NOT NULL,
    country       VARCHAR(2)  NOT NULL,
    snapshot_date DATE        NOT NULL,
    payload       TEXT        NOT NULL,   -- JSON bruto da API
    extracted_at  TIMESTAMP   NOT NULL,
    PRIMARY KEY (video_id, country, snapshot_date)
);

CREATE TABLE IF NOT EXISTS raw_youtube_categoria (
    category_id   VARCHAR(10) PRIMARY KEY,
    nome          TEXT        NOT NULL
);

-- ============ TRATADA ============
-- ETL 1
CREATE TABLE IF NOT EXISTS spotify_faixa (
    track_id          VARCHAR(40) PRIMARY KEY,
    nome              TEXT    NOT NULL,
    artista_principal TEXT    NOT NULL,
    artistas          TEXT    NOT NULL,     -- separados por "; "
    n_artistas        INTEGER NOT NULL,
    tem_feat          BOOLEAN NOT NULL,
    duracao_ms        INTEGER,
    duracao_min       REAL,
    album             TEXT,
    data_lancamento   DATE,
    generos           TEXT,                 -- separados por "; " (pode ser nulo)
    genero_principal  TEXT
);

CREATE TABLE IF NOT EXISTS spotify_chart (
    snapshot_date        DATE        NOT NULL,
    country              VARCHAR(2)  NOT NULL,
    position             INTEGER     NOT NULL,
    track_id             VARCHAR(40) NOT NULL,
    streams              BIGINT,
    weeks_on_chart       INTEGER,
    indice_popularidade  REAL,              -- 0-100, substitui o campo popularity removido da API
    PRIMARY KEY (snapshot_date, country, track_id)
);

-- ETL 2
CREATE TABLE IF NOT EXISTS youtube_video (
    video_id            VARCHAR(20) NOT NULL,
    country             VARCHAR(2)  NOT NULL,
    snapshot_date       DATE        NOT NULL,
    posicao_trending    INTEGER,
    titulo              TEXT        NOT NULL,
    titulo_normalizado  TEXT        NOT NULL,
    canal               TEXT,
    category_id         VARCHAR(10),
    categoria           TEXT,
    publicado_em        TIMESTAMP,
    duracao_s           INTEGER,
    views               BIGINT,
    likes               BIGINT,             -- nulo quando o canal oculta likes
    comentarios         BIGINT,             -- nulo quando comentários estão desativados
    taxa_engajamento    REAL,               -- (likes + comentários) / views * 100
    likes_por_mil       REAL,
    views_por_dia       REAL,
    PRIMARY KEY (video_id, country, snapshot_date)
);

-- ETL 3
CREATE TABLE IF NOT EXISTS musica_video (
    track_id   VARCHAR(40) NOT NULL,
    video_id   VARCHAR(20) NOT NULL,
    score      REAL        NOT NULL,        -- 0-100 (rapidfuzz)
    status     VARCHAR(10) NOT NULL,        -- 'match' (>=85) ou 'revisar' (70-84)
    PRIMARY KEY (track_id, video_id)
);

CREATE TABLE IF NOT EXISTS correlacao_resumo (
    snapshot_date          DATE       NOT NULL,
    country                VARCHAR(2) NOT NULL,
    n_faixas_chart         INTEGER,
    n_faixas_com_video     INTEGER,
    pct_faixas_com_video   REAL,
    spearman_rho           REAL,          -- posição no chart x views do vídeo
    spearman_p             REAL,
    defasagem_mediana_dias REAL,          -- publicação do vídeo - lançamento da faixa
    PRIMARY KEY (snapshot_date, country)
);

-- ETL 4
CREATE TABLE IF NOT EXISTS regiao_resumo (
    snapshot_date           DATE       NOT NULL,
    country                 VARCHAR(2) NOT NULL,
    n_faixas                INTEGER,
    pct_faixas_locais       REAL,         -- faixas que só aparecem neste país
    duracao_media_min       REAL,
    genero_top              TEXT,
    artista_top             TEXT,
    streams_total           BIGINT,
    n_videos_musica         INTEGER,
    engajamento_medio_yt    REAL,
    views_medianas_yt       REAL,
    PRIMARY KEY (snapshot_date, country)
);

CREATE TABLE IF NOT EXISTS regiao_overlap (
    snapshot_date DATE       NOT NULL,
    pais_a        VARCHAR(2) NOT NULL,
    pais_b        VARCHAR(2) NOT NULL,
    jaccard       REAL       NOT NULL,     -- interseção / união dos Top 50
    PRIMARY KEY (snapshot_date, pais_a, pais_b)
);

-- Auditoria do pipeline
CREATE TABLE IF NOT EXISTS pipeline_execucao (
    etapa       VARCHAR(40) NOT NULL,
    inicio      TIMESTAMP   NOT NULL,
    fim         TIMESTAMP,
    linhas      INTEGER,
    status      VARCHAR(10) NOT NULL,
    mensagem    TEXT,
    PRIMARY KEY (etapa, inicio)
);

-- Índices para os filtros do dashboard
CREATE INDEX IF NOT EXISTS ix_chart_pais_data  ON spotify_chart (country, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_video_pais_data  ON youtube_video (country, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_mv_video         ON musica_video (video_id);

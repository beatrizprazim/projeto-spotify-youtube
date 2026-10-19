# Dicionário de dados (camada tratada)

## spotify_faixa — uma linha por faixa
| Coluna | Tipo | Descrição |
|---|---|---|
| track_id | texto (PK) | ID da faixa no Spotify |
| nome | texto | nome da faixa |
| artista_principal | texto | primeiro artista creditado |
| artistas | texto | todos os artistas, separados por "; " |
| n_artistas / tem_feat | inteiro / bool | quantidade de artistas / se tem participação |
| duracao_ms / duracao_min | inteiro / real | duração |
| album, data_lancamento | texto, data | álbum e lançamento (precisão de ano ou mês vira o dia 1) |
| generos / genero_principal | texto | gêneros dos artistas (podem ser nulos) |

## spotify_chart — faixa × país × semana
| Coluna | Descrição |
|---|---|
| snapshot_date, country, track_id (PK) | semana, país (ISO-2), faixa |
| position | posição no Top 50 (1 = primeiro) |
| streams, weeks_on_chart | streams na semana e semanas consecutivas no chart |
| indice_popularidade | 0–100, ver `decisoes_tecnicas.md` |

## youtube_video — vídeo × país × coleta
| Coluna | Descrição |
|---|---|
| video_id, country, snapshot_date (PK) | vídeo, país da lista de em alta, data da coleta |
| posicao_trending | posição na lista de em alta |
| titulo / titulo_normalizado | título original e título limpo, usado no matching |
| canal, categoria | canal e nome da categoria |
| publicado_em, duracao_s | data de publicação e duração em segundos |
| views, likes, comentarios | estatísticas (likes e comentários nulos quando ocultos) |
| taxa_engajamento | (likes + comentários) / views × 100 |
| likes_por_mil, views_por_dia | métricas derivadas |

## musica_video — vínculo faixa ↔ vídeo
| Coluna | Descrição |
|---|---|
| track_id, video_id (PK) | par encontrado |
| score | similaridade 0–100 |
| status | `match` (≥ 85) ou `revisar` (70–84) |

## correlacao_resumo — país × semana
`n_faixas_chart`, `n_faixas_com_video`, `pct_faixas_com_video`, `spearman_rho` e `spearman_p` (posição × views), `defasagem_mediana_dias` (publicação do vídeo − lançamento da faixa).

## regiao_resumo — país × semana
`n_faixas`, `pct_faixas_locais`, `duracao_media_min`, `genero_top`, `artista_top`, `streams_total`, `n_videos_musica`, `engajamento_medio_yt`, `views_medianas_yt`.

## regiao_overlap — par de países × semana
`pais_a`, `pais_b`, `jaccard` (0 = nada em comum, 1 = Top 50 idênticos).

## Camada RAW
`raw_spotify_chart`, `raw_spotify_track`, `raw_youtube_video` e `raw_youtube_categoria` guardam o dado como veio da fonte (JSON no campo `payload`), com `extracted_at`.

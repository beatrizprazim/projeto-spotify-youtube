# Arquitetura e uso do sistema

## Fluxo

1. **`src/pipeline.py`** lê o `.env`, cria o esquema se necessário e roda as etapas em ordem. Cada etapa fica registrada em `pipeline_execucao`.
2. **ETL 1 – Spotify**
   - Extract: lê os CSVs do Spotify Charts (real) ou o simulador. Para cada faixa única, chama `sp.track()` e `sp.artist()`, com cache de artistas.
   - Raw: grava em `raw_spotify_chart` e `raw_spotify_track` (JSON).
   - Transform: separa artista principal e participações, padroniza gêneros, converte a duração para minutos, trata datas com precisão de ano ou mês e calcula o índice de popularidade.
   - Load: grava em `spotify_faixa` e `spotify_chart`.
3. **ETL 2 – YouTube**
   - Extract: chama `videos.list` com mostPopular e categoria Música, por país, paginando. Também busca `videoCategories.list`.
   - Raw: grava em `raw_youtube_video` e `raw_youtube_categoria`.
   - Transform: converte a duração ISO 8601 em segundos, trata likes e comentários ocultos como nulos, normaliza o título e calcula engajamento, likes por mil e views por dia.
   - Load: grava em `youtube_video`.
4. **ETL 3 – Correlação**: lê as tabelas tratadas, faz o matching por similaridade e grava `musica_video`. Calcula `correlacao_resumo` por país e semana.
5. **ETL 4 – Região**: grava `regiao_resumo` (faixas locais, gênero e artista nº 1, engajamento do YT) e `regiao_overlap` (Jaccard entre países).
6. **ETL 5 – Dashboard**: lê as tabelas tratadas (com cache de 10 min) e aplica os filtros de período, país, gênero, artista e engajamento. Tem 5 abas:
   - **Spotify**: barras de top artistas, gêneros, linha da evolução de posição e ranking.
   - **YouTube**: dispersão views × engajamento, engajamento por semana e top vídeos.
   - **Música × Vídeo**: posição × views, % do Top 50 com vídeo e tabela de músicas nas duas plataformas.
   - **Regiões**: mapa coroplético, matriz de Jaccard e tabela por país.
   - **Pipeline**: auditoria das execuções.

## Tratamento de erros, logs e limites

| Situação | O que o pipeline faz |
|---|---|
| 429 do Spotify | o Spotipy respeita o `Retry-After`; tenacity tenta de novo com espera exponencial |
| 5xx em qualquer API | até 4 tentativas com espera exponencial (máx. 30 s) |
| Cota do YouTube esgotada | para a extração, mantém o que já foi coletado e registra no log |
| Falha numa faixa ou num país | registra no log e segue com os demais |
| Ritmo de chamadas | `LimitadorRequisicoes`: intervalo mínimo entre chamadas (`INTERVALO_REQUISICOES`) |
| Dado inválido | `qualidade.validar` bloqueia a carga quando há chave duplicada, obrigatório nulo ou tabela vazia, e avisa sobre valores fora da faixa |
| Rastreabilidade | logs em `logs/pipeline.log` e tabela `pipeline_execucao` |

## Comandos

```bash
python -m src.pipeline                      # tudo, no MODO do .env
python -m src.pipeline --modo simulado      # força o simulado
python -m src.pipeline --etapas 3 4         # só correlação e região (reaproveita o banco)
streamlit run dashboard/app.py              # dashboard
pytest -q                                   # testes
```

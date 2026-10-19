# Decisões técnicas

## 1. A API do Spotify mudou, então usamos uma fonte híbrida

Entre novembro de 2024 e fevereiro/março de 2026, o Spotify restringiu bastante a Web API para apps em **Development Mode**, que é o modo de qualquer projeto acadêmico:

- foram removidos os campos `popularity` (de faixas e artistas) e `followers`;
- saíram os endpoints de categorias, novos lançamentos, top tracks de artista, playlists editoriais e playlists de outros usuários;
- saíram os endpoints em lote (`/tracks?ids=`, `/artists?ids=`);
- a busca passou a devolver no máximo 10 resultados por chamada;
- o dono do app precisa ter Spotify Premium.

O enunciado pede "playlists populares" e "popularidade". Para cumprir isso sem depender do que foi removido:

| Necessidade | Fonte usada |
|---|---|
| O que está em alta, por país | CSVs do **Spotify Charts**, Top 50 semanal (posição, streams, semanas no chart) |
| Popularidade | **Índice próprio 0–100** = 60% streams relativos + 40% posição |
| Duração, álbum, lançamento, artistas | Web API via Spotipy, uma requisição por faixa |
| Gênero | `genres` do artista, quando a API devolve. Quando não devolve, fica "(sem gênero)" |

Referência: guia oficial de migração do Spotify (fevereiro de 2026).

## 2. YouTube: `videos.list` em vez de `search.list`

`videos.list(chart="mostPopular", regionCode=..., videoCategoryId="10")` traz os vídeos de **música** em alta de cada país e custa **1 unidade** de cota. Uma busca (`search.list`) custaria 100. Com a cota padrão de 10.000 unidades por dia, sobra muita margem.

Quando a cota acaba (`403 quotaExceeded`), o extrator para e salva o que já coletou. Erros 5xx são repetidos com espera exponencial.

## 3. Cruzamento por similaridade de texto (ETL 3)

Spotify e YouTube não compartilham nenhum ID. O cruzamento funciona assim:

1. Normalizamos o título do vídeo: minúsculas, sem acento, sem "(Clipe Oficial)", "ft.", "Lyric Video", hashtags etc.
2. Calculamos `rapidfuzz.token_set_ratio` contra o nome da faixa e contra os artistas.
3. O score é **0,6 × música + 0,4 × artista**. A partir de 85 o par é *match*. Entre 70 e 84 fica como *revisar*, para conferência manual.
4. Em caso de empate (ex.: "Sol" e "Sol Neon" do mesmo artista), vence o nome mais específico.

Nos dados simulados, onde conhecemos o gabarito, a precisão foi de 98,6%. Nos dados reais, a equipe confere manualmente uma amostra para medir.

## 4. Banco em duas camadas

- **RAW**: guarda o JSON exatamente como veio. Se uma regra de transformação mudar, dá para reprocessar sem chamar as APIs de novo.
- **TRATADA**: tabelas limpas com métricas, que alimentam o dashboard.
- **Upsert** (`INSERT ... ON CONFLICT DO UPDATE`) pela chave natural deixa o pipeline idempotente.
- A tabela `pipeline_execucao` audita cada etapa: início, fim, linhas e erro.
- O mesmo SQL roda em PostgreSQL (Docker) e em SQLite (testes e uso local sem Docker).

## 5. Dados simulados

O enunciado pede testes com dados reais **e simulados**. O módulo `src/mock_data.py` gera, com semente fixa, um catálogo **fictício** de artistas e músicas, charts de 6 países em 4 semanas e vídeos com títulos "sujos", como os de verdade. Assim o pipeline inteiro roda sem chaves, e o matching pode ser medido contra um gabarito.

## 6. Métricas definidas

| Métrica | Fórmula |
|---|---|
| Taxa de engajamento (YT) | (likes + comentários) / views × 100 |
| Likes por mil views | likes / views × 1000 |
| Views por dia | views / dias desde a publicação |
| Índice de popularidade (Spotify) | 100 × (0,6 × streams/streams do 1º + 0,4 × (51 − posição)/50) |
| % faixas locais | faixas do Top 50 que não aparecem em nenhum outro país analisado |
| Jaccard entre países | faixas em comum / faixas na união |
| Correlação | Spearman entre posição no chart e views do clipe |

Likes ocultos e comentários desativados ficam **nulos**, não zero, para não puxar as médias para baixo.

## Melhorias futuras

- Agendar o pipeline (Airflow ou cron/GitHub Actions) para coletar toda semana e montar a série histórica.
- Pedir Extended Quota ao Spotify, ou usar datasets públicos, para ter de volta atributos de áudio (BPM, energia).
- Fazer análise de sentimento dos comentários dos clipes.
- Incluir uma terceira fonte de viralização (TikTok, Shazam).
- Publicar o dashboard (Streamlit Community Cloud) ligado a um PostgreSQL gerenciado.

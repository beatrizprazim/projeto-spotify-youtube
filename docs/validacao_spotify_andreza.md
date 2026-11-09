# Andreza — ETL 1 / Spotify

Execução em 08/11/2026, horário de Brasília. Repositório gabriellemnunes/projeto-spotify-youtube, commit 4a17e9e45078b5417051c2ed66118b9b1bd93cf3. Usada a versão com checkpoint em projeto_spotify_validado, que reutiliza o extrator e as transformações do projeto e salva cada resposta no banco.

## Resultado desta sessão

Situação: **coleta parcial**. Autenticação e consulta diagnóstica retornaram HTTP 200. Credenciais do aplicativo existente configuradas no .env local do projeto aberto no VS Code; nenhum segredo está neste relatório.

- 30 CSVs, 6000 linhas; todos sem problemas estruturais na auditoria.
- Países: Argentina, Brasil, Espanha, Japão, México e Estados Unidos. Semanas: 01, 08, 15, 22 e 29/10/2026.
- Regra do projeto: Top 50 por arquivo, total de 1500 posições e 400 IDs únicos. As outras 4.500 linhas não entram nessa regra.
- 301 respostas completas de faixas persistidas e 297 consultas bem-sucedidas de artistas.
- 99 IDs sem resposta completa persistida; lista em faixas_pendentes.csv.
- HTTP 404 registrados: 0. Falhas HTTP por código: {'429': 1}.
- Pausa por HTTP 429: True.
- Duplicidades: 0 nos Charts e 0 nas faixas.
- 64 testes passaram, incluindo pausa e retomada com API falsa. Esses testes são distintos da coleta real.

## Metadados recebidos

As contagens abaixo se referem às 301 respostas da API, sem contar os nomes de fallback dos CSVs.

| Verificação | Respostas que passaram |
|---|---:|
| id_confere | 301 / 301 |
| nome_preenchido | 301 / 301 |
| artistas_com_id_e_nome | 301 / 301 |
| album_com_id_e_nome | 301 / 301 |
| duracao_positiva | 301 / 301 |
| lancamento_preenchido | 301 / 301 |
| precisao_lancamento_valida | 301 / 301 |
| isrc_preenchido | 301 / 301 |
| url_spotify_preenchida | 301 / 301 |
| explicit_booleano | 301 / 301 |
| numero_faixa_positivo | 301 / 301 |
| generos_disponiveis | 0 / 301 |

Duração mínima/máxima tratada: 1.85 / 10.4 minutos. Fora do intervalo de 0,5 a 15 minutos: 0.

Divergências de nome ou ID entre API e CSV: 9; detalhes em spotify_validacao_real.json. Divergência de nome não comprova associação errada: o ID e os artistas devem ser analisados em conjunto. A validação dos artistas nesta auditoria verifica presença de IDs e nomes oficiais, não equivalência semântica com a separação por vírgulas dos CSVs.

Gêneros ausentes não foram inventados. O extrator normaliza tanto campo ausente quanto lista vazia para lista vazia. A documentação do Spotify marca genres como descontinuado: https://developer.spotify.com/documentation/web-api/reference/get-an-artist . Portanto, as listas normalizadas não distinguem essas duas situações na resposta original do artista.

As datas com precisão de ano/mês são normalizadas pelo projeto para o primeiro dia do período. O índice de popularidade dos Charts é calculado pelo projeto, não é popularidade oficial da API. Esta auditoria não compara os streams com o portal Charts.

## Evidências

- spotify_andreza_real.db: RAW das respostas recebidas e tabelas tratadas; carga parcial com fallback dos CSVs para IDs pendentes.
- spotify_validacao_real.json: cobertura, falhas, divergências e pendências.
- spotify_eventos_api.json: chamadas lógicas; não contém cada tentativa HTTP interna.
- spotify_cache_artistas.json: cache para retomada.
- auditoria_etl1.json: inventário dos 30 arquivos com SHA-256 e idempotência da carga CSV.
- validacao_metadados.json: verificações adicionais dos payloads recebidos.
- testes_etl1.txt: resultado dos 64 testes.

O histórico incluído no repositório, de 300 respostas sem payloads persistidos, é uma execução anterior e não foi somado às respostas desta sessão. O banco desta entrega é isolado; não substituiu o banco do projeto em Downloads.

## Limite e retomada

Uma consulta diagnóstica adicional confirmou HTTP 429, com Retry-After de 85645 segundos. Aguardar até **09/11/2026, após 23h06min36s, horário de Brasília**, antes de retomar. O servidor pode impor novo limite. Essa consulta é separada dos eventos do coletor.

O log registra 302 consultas de faixa bem-sucedidas, mas somente 301 payloads completos foram persistidos: a consulta do artista da 302ª faixa recebeu HTTP 429 antes do checkpoint. Essa faixa integra as 99 pendentes e será consultada novamente na retomada.

O processo terminou com erro de codificação do console ao imprimir nomes japoneses, depois de gravar o JSON de validação e concluir a carga parcial. Os arquivos e o banco foram conferidos após esse erro. A cópia preparada para retomada usa saída UTF-8 para evitar essa falha de impressão.

As nove divergências de nome mantêm o mesmo ID: oito são títulos em japonês em vez da versão romanizada/traduzida no CSV; uma é “Dreams - 2004 Remaster” no CSV e “Dreams - 2001 Remaster” na API. A API foi preservada como fonte dos metadados atuais; a diferença de edição merece revisão do CSV.

O arquivo .env está listado no .gitignore do projeto aberto. Ele não integra as evidências entregues. O registro desta execução é este relatório e as evidências versionadas. O banco parcial e o cache de retomada ficam no pacote local entregue, fora do GitHub.


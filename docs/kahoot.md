# Kahoot — conceito extra (10 perguntas)

Importação rápida: `docs/kahoot_importar.xlsx` (kahoot.com → Create → Add question → Import spreadsheet). 20 segundos por pergunta. ✅ = resposta certa (as posições variam de propósito).

1. **O que significa ETL?**
   - Export, Test, Launch
   - Extract, Transform, Load ✅
   - Encrypt, Transfer, Log
   - Evaluate, Train, Learn

2. **Qual fonte usamos para saber as músicas mais tocadas em cada país?**
   - Campo popularity da API
   - Playlists editoriais via API
   - Google Trends
   - Spotify Charts (CSV do Top 50 semanal) ✅

3. **Por que não usamos o campo popularity do Spotify?**
   - Foi removido da API em 2026 para apps em modo de testes ✅
   - Ele é pago
   - Só existe para podcasts
   - É igual ao número de streams

4. **Qual chamada da API do YouTube traz os vídeos em alta?**
   - search.list com q = trending
   - channels.list
   - videos.list com chart = mostPopular ✅
   - comments.list

5. **Por que evitamos search.list no YouTube?**
   - Não retorna vídeos de música
   - Custa 100 unidades de cota; videos.list custa 1 ✅
   - Precisa de login do usuário
   - Só funciona nos EUA

6. **Como calculamos a taxa de engajamento de um vídeo?**
   - views ÷ likes
   - likes − dislikes
   - comentários × 100
   - (likes + comentários) ÷ views × 100 ✅

7. **Spotify e YouTube não têm ID em comum. Como ligamos música e clipe?**
   - Pelo código ISRC
   - Similaridade de texto entre título, música e artista ✅
   - Pela duração exata
   - Manualmente, um por um

8. **Spearman negativo entre posição no Spotify e views significa…**
   - Música famosa tem menos views
   - Não existe relação
   - Melhor posição (número menor) vem com mais views ✅
   - O cálculo deu erro

9. **O índice de Jaccard entre dois países mede…**
   - Quanto os Top 50 se parecem (comum ÷ união) ✅
   - A diferença de streams
   - O engajamento médio
   - A população de cada país

10. **Para que serve a camada RAW no banco?**
   - Deixar o dashboard bonito
   - Apagar dados antigos
   - Guardar as senhas das APIs
   - Guardar o original e reprocessar sem chamar a API ✅

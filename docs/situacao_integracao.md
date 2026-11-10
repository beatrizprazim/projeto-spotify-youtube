# Situação da integração e do dashboard

Atualizado em 09/11/2026. O banco `deploy/tendencias.db` contém resultados de
coletas reais dos ETLs 1–4 e é selecionado automaticamente pelo dashboard quando
`DATABASE_URL` não estiver configurada.

## Cobertura disponível

- **Spotify:** 1.500 posições em seis países e cinco semanas (01–29/10/2026).
  A API respondeu para 301 de 400 faixas; 99 mantêm os nomes presentes nos Charts,
  sem metadados inferidos. Gêneros não estão disponíveis.
- **YouTube:** coleta real de 09/11 alinhada ao Chart de 29/10 (11 dias de diferença).
  Foram tratados 165 vídeos de música, correspondentes a 153 IDs distintos em seis
  países, com mediana de engajamento de 1,90%. O alinhamento não representa uma
  coleta histórica da mesma semana.
- **Cruzamento:** 9 vínculos automáticos classificados como `match` e 8 como
  `revisar`; estes últimos não entram nos indicadores que exigem vínculo confirmado.
  Spearman não pôde ser calculado por falta de amostra suficiente.
- **Regiões:** métricas de vídeos e engajamento existem para os seis países. Métricas
  baseadas em gênero não estão disponíveis.

As cinco abas apresentam os dados do banco e os filtros de período e países; filtros
de gênero e artista limitam os rankings e os vínculos relacionados. Os avisos no app
informam cobertura parcial e a distância entre a coleta do YouTube e a semana do
Spotify. Os números acima são da carga real identificada no banco, não de testes
simulados.

## Abrir e validar

```powershell
streamlit run dashboard/app.py
```

O dashboard lê `deploy/tendencias.db` por padrão. Para selecionar outro banco, defina
`DATABASE_URL` antes de iniciar. O dashboard é somente leitura: ele não coleta dados
nem executa os ETLs.

O arquivo `deploy/validacao_youtube_2026-11-09.json` registra a integridade, as
contagens por país, os avisos de cobertura e a validação do dashboard. Credenciais não
fazem parte do banco nem do relatório.

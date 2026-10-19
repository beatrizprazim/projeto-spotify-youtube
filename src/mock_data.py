"""Gerador de dados SIMULADOS no mesmo formato das fontes reais.

Serve para testar o pipeline inteiro sem credenciais (o enunciado pede testes
com dados reais e simulados). Todos os artistas e músicas são FICTÍCIOS.
A semente é fixa, então duas execuções geram exatamente os mesmos dados.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

SEMENTE = 42

PAISES_INFO = {
    # país: (fator de tamanho do mercado, gêneros locais)
    "BR": (1.0, ["funk brasileiro", "sertanejo", "piseiro", "trap"]),
    "US": (2.4, ["hip hop", "pop", "country"]),
    "MX": (0.9, ["regional mexicano", "reggaeton", "corridos"]),
    "AR": (0.45, ["cuarteto", "trap latino", "reggaeton"]),
    "ES": (0.5, ["pop espanhol", "reggaeton", "flamenco pop"]),
    "JP": (0.7, ["j-pop", "anime", "j-rock"]),
}
GENEROS_GLOBAIS = ["pop", "reggaeton", "hip hop", "dance pop"]

SILABAS = ["ka", "lu", "mi", "ro", "ze", "na", "vi", "to", "sa", "le", "ju", "pa",
           "ri", "do", "ma", "be", "ni", "ta", "go", "fe"]
PALAVRAS_MUSICA = [
    "Noite", "Saudade", "Fogo", "Coração", "Verão", "Lua", "Céu", "Ritmo", "Baile",
    "Sonho", "Estrela", "Mar", "Calor", "Destino", "Promessa", "Segredo", "Volta",
    "Midnight", "Gold", "Dreams", "Fire", "Neon", "Echo", "Wild", "Heart", "City",
    "Amor", "Bailando", "Corazón", "Fuego", "Luna", "Sol", "Hikari", "Sakura", "Yume",
]


def _nome_artista(rnd: random.Random) -> str:
    estilo = rnd.random()
    nome = "".join(rnd.choice(SILABAS) for _ in range(rnd.randint(2, 3))).capitalize()
    if estilo < 0.25:
        return f"MC {nome}"
    if estilo < 0.45:
        sobrenome = "".join(rnd.choice(SILABAS) for _ in range(2)).capitalize()
        return f"{nome} {sobrenome}"
    if estilo < 0.55:
        outro = "".join(rnd.choice(SILABAS) for _ in range(2)).capitalize()
        return f"{nome} & {outro}"
    return nome


def _nome_musica(rnd: random.Random) -> str:
    n = rnd.choice([1, 1, 2, 2, 3])
    palavras = rnd.sample(PALAVRAS_MUSICA, n)
    return " ".join(palavras)


def _id(rnd: random.Random, tamanho: int) -> str:
    alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(rnd.choice(alfabeto) for _ in range(tamanho))


def _snapshots(n: int = 4, fim: date = date(2026, 10, 15)) -> list[date]:
    return [fim - timedelta(weeks=i) for i in reversed(range(n))]


class Simulador:
    """Gera catálogo, charts semanais por país e vídeos em alta coerentes entre si."""

    def __init__(self, paises: list[str], semente: int = SEMENTE):
        self.rnd = random.Random(semente)
        self.paises = [p for p in paises if p in PAISES_INFO] or ["BR"]
        self.datas = _snapshots()
        self._criar_catalogo()

    # ---------- catálogo ----------
    def _criar_catalogo(self) -> None:
        rnd = self.rnd
        self.artistas = []
        usados = set()
        for pais in PAISES_INFO:
            for _ in range(12):
                nome = _nome_artista(rnd)
                while nome in usados:
                    nome = _nome_artista(rnd)
                usados.add(nome)
                generos = rnd.sample(PAISES_INFO[pais][1], k=rnd.randint(1, 2))
                self.artistas.append({"id": _id(rnd, 22), "name": nome, "origem": pais,
                                      "genres": generos})
        for _ in range(10):  # artistas globais
            nome = _nome_artista(rnd)
            while nome in usados:
                nome = _nome_artista(rnd)
            usados.add(nome)
            self.artistas.append({"id": _id(rnd, 22), "name": nome, "origem": "GLOBAL",
                                  "genres": rnd.sample(GENEROS_GLOBAIS, k=2)})
        # ~8% dos artistas sem gênero (simula campo vazio na API)
        for a in rnd.sample(self.artistas, k=len(self.artistas) // 12):
            a["genres"] = []

        self.faixas = []
        for art in self.artistas:
            for _ in range(rnd.randint(2, 4)):
                participantes = [art]
                if rnd.random() < 0.3:
                    convidado = rnd.choice(self.artistas)
                    if convidado is not art:
                        participantes.append(convidado)
                lanc = date(2026, 10, 15) - timedelta(days=rnd.randint(5, 400))
                self.faixas.append({
                    "id": _id(rnd, 22),
                    "name": _nome_musica(rnd),
                    "duration_ms": rnd.randint(105_000, 290_000),
                    "album": {"name": _nome_musica(rnd), "release_date": lanc.isoformat(),
                              "release_date_precision": "day"},
                    "artists": [{"id": a["id"], "name": a["name"]} for a in participantes],
                    "_origem": art["origem"],
                    "_forca": rnd.lognormvariate(0, 0.8),  # "qualidade de hit"
                })
        self._artista_por_id = {a["id"]: a for a in self.artistas}
        self._faixa_por_id = {f["id"]: f for f in self.faixas}

    # ---------- Spotify ----------
    def charts(self) -> list[dict]:
        """Linhas no formato do CSV do Spotify Charts (Top 50 semanal por país)."""
        rnd = random.Random(SEMENTE + 1)
        linhas = []
        semanas = {}
        for pais in self.paises:
            tamanho = PAISES_INFO[pais][0]
            for i, dia in enumerate(self.datas):
                pontuacoes = []
                for f in self.faixas:
                    if f["_origem"] == pais:
                        peso = 3.0
                    elif f["_origem"] == "GLOBAL":
                        peso = 1.6
                    else:
                        peso = 0.12
                    # deriva semanal: algumas sobem, outras caem
                    deriva = 1 + 0.15 * i * (1 if sum(map(ord, f["id"])) % 2 else -1)
                    pontuacoes.append((peso * f["_forca"] * deriva * rnd.uniform(0.7, 1.3), f))
                top = sorted(pontuacoes, key=lambda x: x[0], reverse=True)[:50]
                for pos, (_, f) in enumerate(top, start=1):
                    chave = (pais, f["id"])
                    semanas[chave] = semanas.get(chave, 0) + 1
                    streams = int(tamanho * 9_000_000 / (pos ** 0.75) * rnd.uniform(0.9, 1.1))
                    linhas.append({
                        "snapshot_date": dia, "country": pais, "rank": pos,
                        "uri": f"spotify:track:{f['id']}", "track_name": f["name"],
                        "artist_names": ", ".join(a["name"] for a in f["artists"]),
                        "streams": streams, "weeks_on_chart": semanas[chave],
                    })
        return linhas

    def track_payload(self, track_id: str) -> dict:
        """Mesmo formato que o extrator real grava: faixa + detalhes dos artistas."""
        f = self._faixa_por_id[track_id]
        track = {k: v for k, v in f.items() if not k.startswith("_")}
        detalhes = [{"id": a["id"], "name": a["name"],
                     "genres": self._artista_por_id[a["id"]]["genres"]}
                    for a in f["artists"]]
        return {"track": track, "artists_detail": detalhes}

    # ---------- YouTube ----------
    def categorias(self) -> list[dict]:
        return [{"id": "10", "snippet": {"title": "Music"}},
                {"id": "24", "snippet": {"title": "Entertainment"}},
                {"id": "22", "snippet": {"title": "People & Blogs"}}]

    def _titulo_video(self, rnd: random.Random, f: dict) -> tuple[str, str]:
        art = f["artists"][0]["name"]
        musica = f["name"]
        convidado = f["artists"][1]["name"] if len(f["artists"]) > 1 else None
        feat = f" ft. {convidado}" if convidado else ""
        formatos = [
            f"{art} - {musica}{feat} (Clipe Oficial)",
            f"{art} - {musica} (Official Music Video)",
            f"{musica.upper()} - {art}{feat} | Videoclipe",
            f"{art}{' & ' + convidado if convidado else ''} - {musica} [Lyric Video]",
            f"{musica} - {art} (Ao Vivo) #shorts",
            f"{art.upper()} • {musica} (Visualizer)",
        ]
        canal = rnd.choice([art, f"{art} Oficial", f"{art}VEVO", "GR6 Explode"
                            if f["_origem"] == "BR" else f"{art} - Topic"])
        return rnd.choice(formatos), canal

    def videos_em_alta(self, pais: str, dia: date) -> list[dict]:
        """Itens no formato de videos.list(chart='mostPopular', videoCategoryId=10)."""
        rnd = random.Random(f"{SEMENTE}-{pais}-{dia.isoformat()}")
        charts = [c for c in self._charts_cache() if c["country"] == pais
                  and c["snapshot_date"] == dia]
        itens = []
        # ~60% dos vídeos em alta são clipes de faixas do Top 50 daquele país
        for c in charts:
            if rnd.random() > 0.62:
                continue
            tid = c["uri"].split(":")[-1]
            f = self._faixa_por_id[tid]
            itens.append(self._video_de_faixa(f, pais, dia, c["rank"]))
        # o restante: covers, sessões ao vivo e vídeos de música fora dos charts
        while len(itens) < 50:
            r = random.Random(f"{pais}-{dia}-{len(itens)}")
            nome_canal = _nome_artista(r)
            titulo = r.choice([
                f"{_nome_musica(r)} (Cover Acústico) - {nome_canal}",
                f"Sessão ao vivo: {nome_canal} | {_nome_musica(r)}",
                f"TOP 10 músicas mais tocadas da semana #{r.randint(1, 50)}",
                f"{nome_canal} - {_nome_musica(r)} (Official Video)",
            ])
            vid = "x" + _id(r, 10)
            views = int(r.lognormvariate(12.2, 1.0))
            itens.append(self._item(vid, titulo, nome_canal, dia, views, r,
                                    publicado=dia - timedelta(days=r.randint(1, 30))))
        itens.sort(key=lambda it: int(it["statistics"]["viewCount"]), reverse=True)
        return itens[:50]

    def _video_de_faixa(self, f: dict, pais: str, dia: date, posicao: int) -> dict:
        r = random.Random(f["id"])           # mesmo vídeo em todos os países/semanas
        titulo, canal = self._titulo_video(r, f)
        vid = _id(r, 11)
        lanc = date.fromisoformat(f["album"]["release_date"])
        publicado = lanc + timedelta(days=r.choice([0, 0, 0, 1, 3, 7, 14, 30]))
        if publicado > dia:
            publicado = dia - timedelta(days=1)
        idade = max(1, (dia - publicado).days)
        r2 = random.Random(f"{f['id']}-{pais}-{dia}")
        base = PAISES_INFO[pais][0] * 6_000_000 / (posicao ** 0.8)
        views = int(base * (idade ** 0.35) * r2.lognormvariate(0, 0.45))
        return self._item(vid, titulo, canal, dia, views, r2, publicado=publicado)

    def _item(self, vid, titulo, canal, dia, views, r, publicado) -> dict:
        likes = int(views * r.uniform(0.015, 0.07))
        comentarios = int(views * r.uniform(0.0008, 0.006))
        stats = {"viewCount": str(views), "likeCount": str(likes),
                 "commentCount": str(comentarios)}
        if r.random() < 0.05:   # canal ocultou likes
            stats.pop("likeCount")
        if r.random() < 0.04:   # comentários desativados
            stats.pop("commentCount")
        seg = r.randint(95, 300)
        duracao = f"PT{seg // 60}M{seg % 60}S" if seg % 60 else f"PT{seg // 60}M"
        return {
            "id": vid,
            "snippet": {"title": titulo, "channelTitle": canal, "categoryId": "10",
                        "publishedAt": datetime.combine(publicado, datetime.min.time())
                        .isoformat() + "Z"},
            "contentDetails": {"duration": duracao},
            "statistics": stats,
        }

    def _charts_cache(self) -> list[dict]:
        if not hasattr(self, "_cache"):
            self._cache = self.charts()
        return self._cache

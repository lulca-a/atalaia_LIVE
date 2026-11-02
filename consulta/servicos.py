from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any


class Formatador:
    @staticmethod
    def parser_API(dados: dict[str, Any]) -> list[dict[str, Any]]:
        """Transforma a resposta da API Redemet em uma lista por radar.

        Cada item da lista representa um radar e contém:
        - nome
        - sigla
        - imagem: todas as imagens disponíveis daquele radar
        - data: todos os horários disponíveis daquele radar
        """
        grupos_horarios = dados.get("data", {}).get("radar", [])
        radares: dict[str, dict[str, Any]] = {}

        for grupo in grupos_horarios:
            for radar in grupo:
                if not isinstance(radar, dict):
                    continue

                sigla = radar.get("localidade") or radar.get("sigla")
                if not sigla:
                    continue

                item = radares.setdefault(
                    sigla,
                    {
                        # "id": radar.get("id"),
                        "nome": radar.get("nome"),
                        "sigla": sigla,
                        "imagem": [],
                        "data": [],
                    },
                )

                data_radar = radar.get("data")
                if data_radar and data_radar not in item["data"]:
                    item["data"].append(data_radar)

                imagem = radar.get("path")
                if imagem and imagem not in item["imagem"]:
                    item["imagem"].append(imagem)

        return list(radares.values())

    @staticmethod
    def parser_WEB(response: str) -> list[dict[str, Any]]:
        """Transforma a resposta do site Redemet em uma lista por radar."""
        padrao =re.compile(
        r"carrega_radar\("
        r"400000,\s*"
        r"'(?P<sigla>[^']+)',\s*"
        r"'(?P<imagem>[^']+)',\s*"
        r"-?\d+\.?\d*,\s*"
        r"-?\d+\.?\d*,\s*"
        r"-?\d+\.?\d*,\s*"
        r"-?\d+\.?\d*,\s*"
        r"(?P<lat>-?\d+\.?\d*),\s*"
        r"(?P<long>-?\d+\.?\d*),\s*"
        r"mapaGoogle,\s*"
        r"'Radar de (?P<nome>[^']+)',\s*"
        r"'.*?(?P<data>\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'"
    )
        radares = []
        
        for m in padrao.finditer(response.text):
            radares.append({
                "nome": m.group("nome"),
                "sigla": m.group("sigla"),
                "imagem": m.group("imagem"),
                # "lat": float(m.group("lat")),
                # "lon": float(m.group("long")),
                "data": str(datetime.strptime(
                    m.group("data"),
                    "%d/%m/%Y %H:%M"
                ))
            })
        return radares

    @staticmethod
    def analisar_indisponibilidades(
        online: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        formato = "%Y-%m-%d %H:%M:%S"
        resultado = {}

        for nome, animas in online.items():
            horarios = sorted(
                datetime.strptime(anima, formato)
                for anima in animas
            )
            intervalos = []

            for inicio, fim in zip(horarios, horarios[1:]):
                if fim - inicio > timedelta(hours=1):
                    intervalos.append(
                        f"indisponivel entre "
                        f"({inicio.strftime(formato)} - {fim.strftime(formato)})"
                    )

            resultado[nome] = intervalos

        return resultado
    
    @staticmethod
    def atualizar_dicionario(dicionario,
                             itens ) -> None: 
        for i,j in itens.items():
            dicionario.setdefault(i,list()).extend(j)

    @staticmethod
    def recortar_disponibilidades(
        frames: dict[str, list[str]],
        delta: timedelta = timedelta(hours=1),
    ) -> dict[str, dict[str, dict[str, list[dict[str, str]]]]]:
        """Agrupa os períodos disponíveis por mês, radar e dia.

        Uma diferença maior que ``delta`` entre frames encerra um período
        disponível. Cada dia contém uma lista de períodos com ``inicio`` e
        ``fim``, permitindo representar mais de uma indisponibilidade no dia.
        """
        formato = "%Y-%m-%d %H:%M:%S"
        disponibilidades: dict[
            str, dict[str, dict[str, list[dict[str, str]]]]
        ] = {}

        for radar, frames_radar in frames.items():
            horarios = sorted(
                {
                    datetime.strptime(frame, formato)
                    for frame in frames_radar
                }
            )
            if not horarios:
                continue

            inicio_periodo = horarios[0]
            ultimo_frame = horarios[0]
            periodos: list[tuple[datetime, datetime]] = []

            for horario in horarios[1:]:
                if (
                    horario.date() != ultimo_frame.date()
                    or horario - ultimo_frame > delta
                ):
                    periodos.append((inicio_periodo, ultimo_frame))
                    inicio_periodo = horario
                ultimo_frame = horario

            periodos.append((inicio_periodo, ultimo_frame))

            for inicio, fim in periodos:
                mes = inicio.strftime("%Y-%m")
                dia = inicio.strftime("%d")
                periodos_do_dia = (
                    disponibilidades
                    .setdefault(mes, {})
                    .setdefault(radar, {})
                    .setdefault(dia, [])
                )
                periodos_do_dia.append(
                    {
                        "inicio": inicio.strftime(formato),
                        "fim": fim.strftime(formato),
                    }
                )

        return disponibilidades

    @staticmethod
    def salvar_disponibilidades_json(
        frames: dict[str, list[str]],
        diretorio: Path | None = None,
        delta: timedelta = timedelta(hours=1),
    ) -> list[Path]:
        """Atualiza os arquivos mensais de disponibilidade sem perder histórico."""
        if diretorio is None:
            diretorio = Path(__file__).resolve().parent.parent / "banco"

        disponibilidades = Formatador.recortar_disponibilidades(frames, delta)
        if not disponibilidades:
            return []

        diretorio.mkdir(parents=True, exist_ok=True)
        arquivos_salvos = []
        formato = "%Y-%m-%d %H:%M:%S"

        for mes, dados_mes in disponibilidades.items():
            arquivo = diretorio / f"{mes}.json"
            if arquivo.exists():
                with arquivo.open("r", encoding="utf-8") as json_existente:
                    dados_existentes = json.load(json_existente)
                dados_mes_existentes = dados_existentes.get(mes, {})
            else:
                dados_mes_existentes = {}

            for radar, dias in dados_mes.items():
                dias_existentes = (
                    dados_mes_existentes
                    .setdefault(radar, {})
                )
                for dia, periodos in dias.items():
                    todos_periodos = dias_existentes.setdefault(dia, []) + periodos
                    todos_periodos.sort(
                        key=lambda periodo: datetime.strptime(
                            periodo["inicio"], formato
                        )
                    )

                    periodos_mesclados: list[dict[str, str]] = []
                    for periodo in todos_periodos:
                        inicio = datetime.strptime(periodo["inicio"], formato)
                        fim = datetime.strptime(periodo["fim"], formato)
                        if not periodos_mesclados:
                            periodos_mesclados.append(
                                {
                                    "inicio": inicio.strftime(formato),
                                    "fim": fim.strftime(formato),
                                }
                            )
                            continue

                        ultimo = periodos_mesclados[-1]
                        fim_ultimo = datetime.strptime(ultimo["fim"], formato)
                        if inicio - fim_ultimo <= delta:
                            ultimo["fim"] = max(fim_ultimo, fim).strftime(formato)
                        else:
                            periodos_mesclados.append(
                                {
                                    "inicio": inicio.strftime(formato),
                                    "fim": fim.strftime(formato),
                                }
                            )

                    dias_existentes[dia] = periodos_mesclados

            with arquivo.open("w", encoding="utf-8") as json_saida:
                json.dump(
                    {mes: dados_mes_existentes},
                    json_saida,
                    ensure_ascii=False,
                    indent=2,
                )
                json_saida.write("\n")
            arquivos_salvos.append(arquivo)

        return arquivos_salvos

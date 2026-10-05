from datetime import datetime, timedelta
import re
from typing import Any
from datetime import datetime
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
    def agrupar_dia(radares_web,radares_api):
        ...
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
                if fim - inicio >= timedelta(minutes=60):
                    intervalos.append(
                        f"indisponivel entre "
                        f"({inicio.strftime(formato)} - {fim.strftime(formato)})"
                    )

            resultado[nome] = intervalos

        return resultado
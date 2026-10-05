from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from servicos import Formatador
from time import sleep
from pprint import pprint

todos_radares = {
    "Almenara/MG", "Belém/PA","Boa Vista/RR", "Canguçu/RS","Cruzeiro do Sul/AC","Gama/DF", "Jaraguari/MS","Morro da Igreja/SC", "Manaus/AM",
    "Maceió/AL","Macapá/AP", "Natal/RN","Pico do Couto/RJ","Petrolina/PE","Porto Velho/RO", "São Francisco/MG",
    "Santiago/RS","São Luís/MA","Santarém/PA","São Roque/SP","Santa Teresa/ES","Salvador/BA","Tefé/AM",
    "Três Marias/MG","Tabatinga/AM", "São Gabriel da Cachoeira/AM", "Vilhena/RO", "Rio Branco/AC"
}

class Radar:
    class WEB:
        """
        Consulta a redemet via web scraping. Esta classe é útil para
        obter dados de radares que estão visíveis para o usuário da rede, 
        porém não estão na API.
        """
        _URL = "https://redemet.decea.mil.br/old/produtos/radares-meteorologicos/plota_radar.php"
        _SESSION = requests.Session()
        _SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
        _INICIADO = False
        _TENTATIVA = 3
        
        @classmethod
        def consulta(
            cls,
            data_hora: datetime | None = None,
            tipo_radar: str = "maxcappi"
        ) -> list[dict]:

            # Validação do tipo_radar
            if not isinstance(tipo_radar, str):
                raise TypeError("tipo_radar deve ser uma string.")

            tipo_radar = tipo_radar.lower()

            if tipo_radar not in ("maxcappi", "10km", "07km", "05km", "03km"):
                raise ValueError(
                    "tipo_radar deve ser 'maxcappi', '10km', '07km', '05km' ou '03km'."
                )

            # Validação da data
            if data_hora is not None and not isinstance(data_hora, datetime):
                raise TypeError("data_hora deve ser um objeto datetime ou None.")

            if not cls._INICIADO:
                cls._SESSION.get(cls._URL, timeout=30)
                cls._INICIADO = True

            payload = [
                ("radar[]", tipo_radar),
                (
                    "datahora",
                    data_hora.strftime("%d/%m/%Y %H:%M")
                    if data_hora is not None
                    else None
                ),
            ]
            for i in range(cls._TENTATIVA + 1):
                try:
                    response = cls._SESSION.post(
                        cls._URL,
                        data=payload,
                        timeout=30
                    )
                    response.raise_for_status()
                    break

                except requests.exceptions.RequestException:
                    if i == cls._TENTATIVA:
                        raise
                
            return Formatador.parser_WEB(response)

        def busca_binaria():
            ...
        def analisar_consulta(radares):
            online = set()
            for radar in radares:
                online.add(radar["nome"])
            offline = todos_radares - online
            return online
    class API:
        load_dotenv()
        _URL = "https://api-redemet.decea.mil.br/produtos/radar/maxcappi"
        _API_KEY = os.getenv("RADAR_API_KEY")
        _SESSION = requests.Session()
        _SLEEP_TIME = 1.0
        _MAX_TENTATIVAS = 4

        @classmethod
        def consulta(cls,data_hora: datetime | None = None,
                    anima = None, 
                    area = None,) -> list[dict]:
            params = {
                    "api_key": cls._API_KEY,
                    "data": f"{data_hora.strftime('%Y%m%d%H') if data_hora is not None else ''}",
                    "area": area,
                    "anima": anima
            }  
            for tentativa in range(1, cls._MAX_TENTATIVAS + 1):
                try:
                    response = cls._SESSION.get(
                        url=cls._URL,
                        params=params,
                        timeout=30,
                    )
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException:
                    if tentativa == cls._MAX_TENTATIVAS:
                        raise
                    sleep(cls._SLEEP_TIME * (2 ** (tentativa - 1)))

            sleep(cls._SLEEP_TIME)
            r = response.json()
            return (Formatador.parser_API(r))
        @classmethod
        def analisar_consulta(cls,radares):
            online =  []
            for radar in radares:
                if not radar["data"]:
                    pass
                else:
                    online.append((radar["nome"],radar["data"]))
            return online
if __name__ == "__main__":
    # Exemplo de uso da classe Radar
    radar_web = Radar.WEB.consulta(data_hora=datetime.now())
    radar_api = Radar.API.consulta(data_hora=datetime(2026,9,1,5),anima=15) 
    pprint(Radar.API.analisar_consulta(radar_api))
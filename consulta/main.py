#github actions com cron de todo dia as 0400Z############

#consulta 24hrs passadas pela API########################

#analisa consulta passada################################

#relaciona as disponibilidades###########################

#salva em ano_mes.json###################################

from datetime import datetime, timedelta, timezone
from pprint import pprint

from radar import Radar
from servicos import Formatador


def main() -> None:
    ontem = datetime.now(timezone.utc).date() - timedelta(days=1)
    frames_por_radar: dict[str, list[str]] = {}

    for hora in (0, 5, 10, 15, 20, 23):
        consulta = Radar.API(
            datetime(
                ontem.year,
                ontem.month,
                ontem.day,
                hora,
                tzinfo=timezone.utc,
            ),
            anima=9 if hora == 23 else 15 if hora else None,
        )
        Formatador.atualizar_dicionario(frames_por_radar, consulta.frames)
        print(f"Consulta da hora {hora:02d}Z concluída.")

    indisponibilidades = Formatador.analisar_indisponibilidades(
        frames_por_radar
    )
    print("Indisponibilidades identificadas:")
    pprint(indisponibilidades)

    arquivos = Formatador.salvar_disponibilidades_json(frames_por_radar)
    if not arquivos:
        raise RuntimeError("A consulta não retornou frames para salvar.")

    print("Arquivos mensais atualizados:")
    pprint([str(arquivo) for arquivo in arquivos])


if __name__ == "__main__":
    main()

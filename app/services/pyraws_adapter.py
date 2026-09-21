import importlib.util


def status_pyraws():
    spec = importlib.util.find_spec("pyraws")
    return {
        "disponivel": spec is not None,
        "modo": "opcional",
        "mensagem": (
            "PyRawS está instalado e pode ser usado para cenas Sentinel-2 RAW locais."
            if spec
            else "PyRawS não está instalado. A aplicação principal continua usando STAC/COG do Brazil Data Cube."
        ),
    }

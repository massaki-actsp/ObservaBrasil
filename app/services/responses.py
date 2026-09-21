from datetime import datetime, timezone


def api_response(dados=None, erro=None, sucesso=True, fonte=None, atualizado_em=None, status=200):
    payload = {
        "sucesso": sucesso,
        "dados": dados if dados is not None else {},
        "erro": erro,
        "fonte": fonte,
        "atualizado_em": atualizado_em or datetime.now(timezone.utc).isoformat(),
    }
    return payload, status

from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g, request, session

from app.extensions import db
from app.models.area import AreaInteresse
from app.models.alerta import HistoricoNotificacao
from app.services import bdqueimadas
from app.services.brazil_data_cube import buscar_produtos, status_stac
from app.services.geoprocessamento import GeoJSONInvalido, foco_dentro_geojson, normalizar_geojson
from app.services.pyraws_adapter import status_pyraws
from app.services.responses import api_response


api_bp = Blueprint("api", __name__)


def _user_id():
    return session.get("user_id")


def _queimadas_payload():
    return bdqueimadas.obter_focos(
        current_app.config["INPE_QUEIMADAS_URL"],
        current_app.config["CACHE_DIR"],
        data=request.args.get("data"),
        timeout=current_app.config["REQUEST_TIMEOUT"],
    )


def _serializar_foco(foco):
    foco = dict(foco)
    if foco.get("data_hora_gmt") and hasattr(foco["data_hora_gmt"], "isoformat"):
        foco["data_hora_gmt"] = foco["data_hora_gmt"].isoformat()
    return foco


@api_bp.get("/health")
def health():
    return api_response(
        {"status": "ok", "servico": "Observa Brasil", "dispositivo": g.device},
        fonte="Observa Brasil",
    )


@api_bp.get("/fontes/status")
def fontes_status():
    inpe = {"online": False, "url": current_app.config["INPE_QUEIMADAS_URL"]}
    try:
        csv_url = bdqueimadas.csv_mais_recente(
            current_app.config["INPE_QUEIMADAS_URL"], timeout=current_app.config["REQUEST_TIMEOUT"]
        )
        inpe.update({"online": True, "csv_mais_recente": csv_url})
    except Exception as exc:
        inpe["erro"] = str(exc)
    bdc = status_stac(current_app.config["BDC_STAC_URL"], timeout=current_app.config["REQUEST_TIMEOUT"])
    return api_response({"inpe_bdqueimadas": inpe, "brazil_data_cube": bdc}, fonte="INPE/BDC")


@api_bp.get("/queimadas")
def queimadas():
    try:
        payload = _queimadas_payload()
        filtros = request.args.to_dict()
        focos = bdqueimadas.aplicar_filtros(payload["focos"], filtros)
        if request.args.get("limite"):
            focos = focos[: min(int(request.args["limite"]), 5000)]
        return api_response(
            {
                "total": len(focos),
                "focos": [_serializar_foco(foco) for foco in focos],
                "origem": payload["origem"],
                "url": payload["url"],
            },
            fonte="INPE BDQueimadas",
            atualizado_em=payload["atualizado_em"],
        )
    except Exception as exc:
        return api_response({}, erro=str(exc), sucesso=False, fonte="INPE BDQueimadas", status=502)


@api_bp.get("/queimadas/resumo")
def queimadas_resumo():
    try:
        payload = _queimadas_payload()
        focos = bdqueimadas.aplicar_filtros(payload["focos"], request.args.to_dict())
        agora = datetime.now(timezone.utc)
        ultimas_24h = [
            f for f in focos if f.get("data_hora_gmt") and f["data_hora_gmt"] >= agora - timedelta(hours=24)
        ]
        def contar(campo):
            out = {}
            for foco in focos:
                chave = foco.get(campo) or "Não informado"
                out[chave] = out.get(chave, 0) + 1
            return out
        frps = [f["frp"] for f in focos if f.get("frp") is not None]
        resumo = {
            "total_focos": len(focos),
            "por_estado": contar("estado"),
            "por_bioma": contar("bioma"),
            "por_satelite": contar("satelite"),
            "frp_medio": sum(frps) / len(frps) if frps else None,
            "focos_ultimas_24h": len(ultimas_24h),
            "ultima_atualizacao": payload["atualizado_em"],
            "observacao": "Foco de calor não equivale automaticamente a incêndio confirmado ou área queimada.",
        }
        return api_response(resumo, fonte="INPE BDQueimadas", atualizado_em=payload["atualizado_em"])
    except Exception as exc:
        return api_response({}, erro=str(exc), sucesso=False, fonte="INPE BDQueimadas", status=502)


@api_bp.get("/vegetacao")
def vegetacao():
    return api_response(
        {
            "indices": {
                "NDVI": "(B08 - B04) / (B08 + B04)",
                "NBR": "(B08 - B12) / (B08 + B12)",
                "dNBR": "NBR antes - NBR depois",
            },
            "classificacao_ndvi": [
                {"intervalo": "< 0", "classe": "água, sombra ou superfície não vegetada"},
                {"intervalo": "0 a 0,2", "classe": "solo exposto ou vegetação muito baixa"},
                {"intervalo": "0,2 a 0,4", "classe": "vegetação esparsa"},
                {"intervalo": "0,4 a 0,6", "classe": "vegetação moderada"},
                {"intervalo": "> 0,6", "classe": "vegetação densa"},
            ],
        },
        fonte="Brazil Data Cube",
    )


@api_bp.get("/sentinel/produtos")
def sentinel_produtos():
    bbox = request.args.get("bbox")
    bbox_values = bbox.split(",") if bbox else None
    try:
        produtos = buscar_produtos(
            current_app.config["BDC_STAC_URL"],
            current_app.config["BDC_COLLECTION"],
            bbox=bbox_values,
            datetime_range=request.args.get("datetime"),
            limit=request.args.get("limit", 20),
            timeout=current_app.config["REQUEST_TIMEOUT"],
        )
        return api_response(produtos, fonte="Brazil Data Cube")
    except Exception as exc:
        return api_response({}, erro=str(exc), sucesso=False, fonte="Brazil Data Cube", status=502)


@api_bp.get("/areas")
def listar_areas():
    query = AreaInteresse.query
    if _user_id():
        query = query.filter_by(usuario_id=_user_id())
    else:
        query = query.filter_by(usuario_id=None)
    return api_response([area.to_dict() for area in query.order_by(AreaInteresse.criado_em.desc()).all()])


@api_bp.post("/areas")
def criar_area():
    if request.content_length and request.content_length > current_app.config["GEOJSON_MAX_BYTES"]:
        return api_response({}, erro="GeoJSON excede o tamanho máximo permitido.", sucesso=False, status=413)
    payload = request.get_json(silent=True) or {}
    try:
        geometria = normalizar_geojson(payload.get("geometria") or payload.get("geojson") or payload)
    except (GeoJSONInvalido, ValueError, TypeError) as exc:
        return api_response({}, erro=str(exc), sucesso=False, status=400)
    area = AreaInteresse(
        nome=payload.get("nome") or "Área sem nome",
        descricao=payload.get("descricao"),
        geometria=geometria,
        filtros=payload.get("filtros") or {},
        canais_alerta=payload.get("canais_alerta") or [],
        usuario_id=_user_id(),
    )
    db.session.add(area)
    db.session.commit()
    return api_response(area.to_dict(), status=201)


@api_bp.put("/areas/<int:area_id>")
def atualizar_area(area_id):
    area = AreaInteresse.query.get_or_404(area_id)
    payload = request.get_json(silent=True) or {}
    if "geometria" in payload:
        try:
            area.geometria = normalizar_geojson(payload["geometria"])
        except (GeoJSONInvalido, ValueError, TypeError) as exc:
            return api_response({}, erro=str(exc), sucesso=False, status=400)
    for campo in ("nome", "descricao", "filtros", "canais_alerta", "ativa"):
        if campo in payload:
            setattr(area, campo, payload[campo])
    db.session.commit()
    return api_response(area.to_dict())


@api_bp.delete("/areas/<int:area_id>")
def deletar_area(area_id):
    area = AreaInteresse.query.get_or_404(area_id)
    db.session.delete(area)
    db.session.commit()
    return api_response({"removida": True})


@api_bp.post("/alertas/verificar")
def verificar_alertas():
    return api_response(
        {
            "processados": 0,
            "mensagem": "Estrutura preparada. Configure canais e agendador para envio automático.",
        }
    )


@api_bp.get("/alertas/historico")
def alertas_historico():
    itens = HistoricoNotificacao.query.order_by(HistoricoNotificacao.criado_em.desc()).limit(100).all()
    return api_response(
        [
            {
                "id": item.id,
                "alerta_id": item.alerta_id,
                "foco_id": item.foco_id,
                "status": item.status,
                "tentativas": item.tentativas,
                "erro": item.erro,
                "criado_em": item.criado_em.isoformat(),
                "enviado_em": item.enviado_em.isoformat() if item.enviado_em else None,
            }
            for item in itens
        ]
    )


@api_bp.get("/pyraws/status")
def pyraws_status():
    return api_response(status_pyraws(), fonte="PyRawS")

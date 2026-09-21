from datetime import datetime, timezone

import requests


class BrazilDataCubeError(RuntimeError):
    pass


def status_stac(stac_url, timeout=20):
    try:
        response = requests.get(stac_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        return {"online": True, "titulo": payload.get("title"), "url": stac_url}
    except requests.RequestException as exc:
        return {"online": False, "erro": str(exc), "url": stac_url}


def buscar_produtos(stac_url, collection, bbox=None, datetime_range=None, limit=20, timeout=20):
    endpoint = stac_url.rstrip("/") + "/search"
    body = {"collections": [collection], "limit": min(int(limit), 100)}
    if bbox:
        body["bbox"] = [float(v) for v in bbox]
    if datetime_range:
        body["datetime"] = datetime_range

    response = requests.post(endpoint, json=body, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    produtos = []
    for feature in payload.get("features", []):
        assets = feature.get("assets", {})
        produtos.append(
            {
                "id": feature.get("id"),
                "datetime": feature.get("properties", {}).get("datetime"),
                "bbox": feature.get("bbox"),
                "assets": {k: v.get("href") for k, v in assets.items() if k in {
                    "NDVI", "EVI", "NBR", "B04", "B08", "B11", "B12", "SCL", "thumbnail", "CLEAROB", "TOTALOB"
                }},
            }
        )
    return {"produtos": produtos, "consultado_em": datetime.now(timezone.utc).isoformat()}

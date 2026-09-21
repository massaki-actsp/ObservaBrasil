from shapely.geometry import GeometryCollection, shape
from shapely.validation import explain_validity


class GeoJSONInvalido(ValueError):
    pass


def normalizar_geojson(obj):
    if not isinstance(obj, dict):
        raise GeoJSONInvalido("GeoJSON deve ser um objeto JSON.")

    tipo = obj.get("type")
    try:
        if tipo == "FeatureCollection":
            geometries = [shape(feature.get("geometry")) for feature in obj.get("features", [])]
            geom = GeometryCollection([g for g in geometries if not g.is_empty])
        elif tipo == "Feature":
            if not obj.get("geometry"):
                raise GeoJSONInvalido("Feature GeoJSON precisa conter uma geometria.")
            geom = shape(obj.get("geometry"))
        else:
            geom = shape(obj)
    except (AttributeError, TypeError, ValueError) as exc:
        raise GeoJSONInvalido("GeoJSON inválido ou incompleto.") from exc

    if geom.is_empty:
        raise GeoJSONInvalido("A geometria informada está vazia.")
    if not geom.is_valid:
        raise GeoJSONInvalido(f"GeoJSON inválido: {explain_validity(geom)}")

    return geom.__geo_interface__


def foco_dentro_geojson(foco, geojson):
    from shapely.geometry import Point

    geom = shape(normalizar_geojson(geojson))
    return geom.contains(Point(float(foco["lon"]), float(foco["lat"])))

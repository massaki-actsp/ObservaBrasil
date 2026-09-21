import numpy as np

from app.extensions import db
from app.models.area import AreaInteresse
from app.services import bdqueimadas
from app.services.alertas import registrar_foco_processado
from app.services.brazil_data_cube import buscar_produtos
from app.services.geoprocessamento import foco_dentro_geojson, normalizar_geojson
from app.services.indices import calcular_dnbr, calcular_nbr, calcular_ndvi, estatisticas_indice


def test_ler_csv_e_filtrar():
    focos = bdqueimadas.ler_csv(
        "id;lat;lon;data_hora_gmt;satelite;municipio;estado;bioma;risco_fogo;precipitacao;numero_dias_sem_chuva;frp\n"
        "1;-1,5;-50,2;2026-09-19 10:00:00;S;A;PA;Amazônia;0,7;0;10;22,5\n"
    )
    assert len(focos) == 1
    assert focos[0]["lat"] == -1.5
    assert bdqueimadas.aplicar_filtros(focos, {"bioma": "Amazônia"})[0]["id"] == "1"


def test_resolver_csv_url_aceita_url_completa():
    url = "https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/focos_diario_br_20260919.csv"
    assert bdqueimadas.resolver_csv_url("https://example.test/base/", data=url) == url


def test_resolver_csv_url_aceita_nome_com_ou_sem_extensao():
    base_url = "https://example.test/Brasil/"
    assert (
        bdqueimadas.resolver_csv_url(base_url, data="focos_diario_br_20260919")
        == "https://example.test/Brasil/focos_diario_br_20260919.csv"
    )
    assert (
        bdqueimadas.resolver_csv_url(base_url, data="focos_diario_br_20260919.csv")
        == "https://example.test/Brasil/focos_diario_br_20260919.csv"
    )


def test_obter_focos_usa_cache_recente_quando_inpe_falha_sem_data(tmp_path, monkeypatch):
    url = "https://example.test/focos_diario_br_20260919.csv"
    cache_path = bdqueimadas._cache_path(tmp_path, url)
    cache_path.write_text(
        "id,lat,lon,data_hora_gmt,satelite,municipio,estado,bioma,risco_fogo,precipitacao,numero_dias_sem_chuva,frp\n"
        "1,-23.1,-46.6,2026-09-19 10:00:00,S,Campinas,SÃO PAULO,Mata Atlântica,0.7,0,10,22.5\n",
        encoding="utf-8",
    )
    bdqueimadas._registrar_cache(cache_path, url)
    monkeypatch.setattr(
        bdqueimadas,
        "resolver_csv_url",
        lambda *args, **kwargs: (_ for _ in ()).throw(bdqueimadas.BDQueimadasError("timeout")),
    )

    resultado = bdqueimadas.obter_focos("https://example.test/", tmp_path, data=None)

    assert resultado["origem"] == "cache_recente"
    assert resultado["url"] == url
    assert resultado["focos"][0]["estado"] == "SÃO PAULO"


def test_obter_focos_com_data_nao_usa_cache_de_outro_csv(tmp_path, monkeypatch):
    monkeypatch.setattr(
        bdqueimadas,
        "baixar_csv",
        lambda *args, **kwargs: (_ for _ in ()).throw(bdqueimadas.BDQueimadasError("timeout")),
    )

    try:
        bdqueimadas.obter_focos("https://example.test/", tmp_path, data="focos_diario_br_20260919")
    except bdqueimadas.BDQueimadasError as exc:
        assert "timeout" in str(exc)
    else:
        raise AssertionError("A consulta com data explícita não deve cair em cache genérico.")


def test_geojson_contains_point():
    geojson = {
        "type": "Polygon",
        "coordinates": [[[-56, -11], [-54, -11], [-54, -9], [-56, -9], [-56, -11]]],
    }
    normalizado = normalizar_geojson(geojson)
    assert foco_dentro_geojson({"lat": -10, "lon": -55}, normalizado) is True


def test_indices():
    nir = np.array([0.8, 0.4])
    red = np.array([0.2, 0.4])
    swir = np.array([0.3, 0.2])
    ndvi = calcular_ndvi(nir, red)
    nbr = calcular_nbr(nir, swir)
    dnbr = calcular_dnbr(nbr, nbr - 0.1)
    assert np.isclose(ndvi[0], 0.6)
    assert np.isclose(dnbr[0], 0.1, atol=1e-6)
    assert estatisticas_indice(ndvi)["pixels_validos"] == 2


def test_stac_mock(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "features": [
                    {
                        "id": "S2",
                        "bbox": [-56, -11, -54, -9],
                        "properties": {"datetime": "2026-09-19T00:00:00Z"},
                        "assets": {"NDVI": {"href": "https://example.test/ndvi.tif"}, "B08": {"href": "x"}},
                    }
                ]
            }

    monkeypatch.setattr("app.services.brazil_data_cube.requests.post", lambda *a, **k: Response())
    result = buscar_produtos("https://data.inpe.br/bdc/stac/v1/", "S2-16D-2", bbox=[-56, -11, -54, -9])
    assert result["produtos"][0]["assets"]["NDVI"].endswith("ndvi.tif")


def test_prevenir_alerta_duplicado(app):
    with app.app_context():
        area = AreaInteresse(nome="A", geometria={"type": "Point", "coordinates": [0, 0]})
        db.session.add(area)
        db.session.commit()
        assert registrar_foco_processado("foco-1", area.id) is True
        assert registrar_foco_processado("foco-1", area.id) is False

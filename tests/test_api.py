from app.models.foco import FocoCalor
from app.services import bdqueimadas


CSV = """id,lat,lon,data_hora_gmt,satelite,municipio,estado,bioma,risco_fogo,precipitacao,numero_dias_sem_chuva,frp
abc,-10.1,-55.2,2026-09-19 12:00:00,AQUA_M-T,Sinop,Mato Grosso,Amazônia,0.9,0,12,34.5
def,-15.0,-47.9,2026-09-19 13:00:00,NOAA-20,Brasília,Distrito Federal,Cerrado,0.4,1,3,8.0
"""


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["sucesso"] is True
    assert response.json["dados"]["status"] == "ok"
    assert response.json["dados"]["dispositivo"]["tipo"] == "desktop"


def test_health_detecta_celular(client):
    response = client.get(
        "/api/health",
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            "Sec-CH-UA-Mobile": "?1",
        },
    )
    assert response.json["dados"]["dispositivo"]["tipo"] == "mobile"


def test_health_detecta_tablet(client):
    response = client.get(
        "/api/health",
        headers={
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Safari/604.1",
        },
    )
    assert response.json["dados"]["dispositivo"]["tipo"] == "tablet"


def test_queimadas_com_mock(client, monkeypatch):
    def fake_obter_focos(*args, **kwargs):
        return {
            "url": "https://example.test/focos.csv",
            "origem": "rede",
            "focos": bdqueimadas.ler_csv(CSV),
            "atualizado_em": "2026-09-19T12:00:00+00:00",
        }

    monkeypatch.setattr(bdqueimadas, "obter_focos", fake_obter_focos)
    response = client.get("/api/queimadas?estado=Mato%20Grosso")
    assert response.status_code == 200
    assert response.json["dados"]["total"] == 1
    assert response.json["dados"]["focos"][0]["municipio"] == "Sinop"


def test_resumo_por_bioma(client, monkeypatch):
    monkeypatch.setattr(
        bdqueimadas,
        "obter_focos",
        lambda *args, **kwargs: {
            "url": "x",
            "origem": "rede",
            "focos": bdqueimadas.ler_csv(CSV),
            "atualizado_em": "2026-09-19T12:00:00+00:00",
        },
    )
    response = client.get("/api/queimadas/resumo")
    assert response.status_code == 200
    assert response.json["dados"]["por_bioma"]["Amazônia"] == 1
    assert response.json["dados"]["por_bioma"]["Cerrado"] == 1


def test_criar_foco_manual(client, app):
    response = client.post(
        "/api/focos/manual",
        json={
            "lat": -23.55052,
            "lon": -46.633308,
            "municipio": "São Paulo",
            "estado": "São Paulo",
            "bioma": "Mata Atlântica",
            "frp": 12.5,
        },
    )

    assert response.status_code == 201
    assert response.json["dados"]["foco"]["fonte"] == "Coleta manual por geolocalização"
    with app.app_context():
        assert FocoCalor.query.count() == 1


def test_resumo_inclui_foco_manual_sem_quebrar_data(client, monkeypatch):
    monkeypatch.setattr(
        bdqueimadas,
        "obter_focos",
        lambda *args, **kwargs: {
            "url": "x",
            "origem": "rede",
            "focos": bdqueimadas.ler_csv(CSV),
            "atualizado_em": "2026-09-19T12:00:00+00:00",
        },
    )
    client.post(
        "/api/focos/manual",
        json={
            "lat": -23.55052,
            "lon": -46.633308,
            "municipio": "São Paulo",
            "estado": "São Paulo",
            "bioma": "Mata Atlântica",
        },
    )

    response = client.get("/api/queimadas/resumo")

    assert response.status_code == 200
    assert response.json["dados"]["por_estado"]["São Paulo"] == 1


def test_criar_foco_manual_exige_lat_lon(client):
    response = client.post("/api/focos/manual", json={"estado": "São Paulo"})

    assert response.status_code == 400
    assert response.json["sucesso"] is False


def test_clonar_base_queimadas(client, app, monkeypatch):
    monkeypatch.setattr(
        bdqueimadas,
        "obter_focos",
        lambda *args, **kwargs: {
            "url": "x",
            "origem": "rede",
            "focos": bdqueimadas.ler_csv(CSV),
            "atualizado_em": "2026-09-19T12:00:00+00:00",
        },
    )

    response = client.post("/api/queimadas/clonar-base?estado=Mato%20Grosso")

    assert response.status_code == 201
    assert response.json["dados"]["criados"] == 1
    with app.app_context():
        assert FocoCalor.query.count() == 1
        assert FocoCalor.query.first().municipio == "Sinop"


def test_criar_area_geojson(client):
    geojson = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-56, -11], [-54, -11], [-54, -9], [-56, -9], [-56, -11]]],
        },
    }
    response = client.post("/api/areas", json={"nome": "Teste", "geometria": geojson})
    assert response.status_code == 201
    assert response.json["dados"]["nome"] == "Teste"


def test_geojson_invalido(client):
    response = client.post("/api/areas", json={"type": "Feature", "geometry": None})
    assert response.status_code == 400
    assert response.json["sucesso"] is False

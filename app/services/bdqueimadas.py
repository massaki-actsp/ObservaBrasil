import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


CSV_RE = re.compile(r'href="([^"]+\.csv)"', re.IGNORECASE)


class BDQueimadasError(RuntimeError):
    pass


def _cache_path(cache_dir, url):
    return Path(cache_dir) / hashlib.sha256(url.encode("utf-8")).hexdigest()


def _metadata_path(cache_path):
    return cache_path.with_suffix(".json")


def _registrar_cache(cache_path, url):
    metadata = {
        "url": url,
        "salvo_em": datetime.now(timezone.utc).isoformat(),
    }
    _metadata_path(cache_path).write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")


def csv_cache_mais_recente(cache_dir):
    cache_dir = Path(cache_dir)
    candidatos = [path for path in cache_dir.glob("*") if path.is_file() and path.suffix != ".json"]
    if not candidatos:
        raise BDQueimadasError("INPE indisponível e nenhum CSV foi encontrado no cache local.")

    cache_path = max(candidatos, key=lambda path: path.stat().st_mtime)
    metadata_path = _metadata_path(cache_path)
    metadata = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    return {
        "texto": cache_path.read_text(encoding="utf-8-sig"),
        "url": metadata.get("url", f"cache://{cache_path.name}"),
        "salvo_em": metadata.get("salvo_em"),
    }


def _float_or_none(value):
    if value in (None, "", "null", "None"):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _int_or_none(value):
    number = _float_or_none(value)
    return int(number) if number is not None else None


def _parse_datetime(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def listar_csvs(base_url, timeout=20):
    response = requests.get(base_url, timeout=timeout)
    response.raise_for_status()
    arquivos = sorted(set(CSV_RE.findall(response.text)))
    return [urljoin(base_url, arquivo) for arquivo in arquivos]


def csv_mais_recente(base_url, timeout=20):
    arquivos = listar_csvs(base_url, timeout=timeout)
    if not arquivos:
        raise BDQueimadasError("Nenhum CSV foi encontrado no diretório do INPE.")
    return arquivos[-1]


def resolver_csv_url(base_url, data=None, timeout=20):
    if not data:
        return csv_mais_recente(base_url, timeout=timeout)

    data = str(data).strip()
    parsed = urlparse(data)
    if parsed.scheme in ("http", "https"):
        return data

    arquivo = data if data.lower().endswith(".csv") else f"{data}.csv"
    return urljoin(base_url, arquivo)


def baixar_csv(url, cache_dir, timeout=20):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_path(cache_dir, url)
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        cache_path.write_bytes(response.content)
        _registrar_cache(cache_path, url)
        return response.content.decode("utf-8-sig"), "rede"
    except requests.RequestException as exc:
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8-sig"), "cache"
        raise BDQueimadasError(f"Falha ao baixar CSV do INPE: {exc}") from exc


def normalizar_linha(row):
    lat = row.get("lat") or row.get("latitude")
    lon = row.get("lon") or row.get("longitude")
    data = row.get("data_hora_gmt") or row.get("datahora") or row.get("data_hora")
    foco_id = row.get("id")
    if not foco_id:
        foco_id = hashlib.sha1(f"{lat}|{lon}|{data}|{row.get('satelite')}".encode()).hexdigest()

    return {
        "id": str(foco_id),
        "lat": _float_or_none(lat),
        "lon": _float_or_none(lon),
        "data_hora_gmt": _parse_datetime(data),
        "satelite": row.get("satelite"),
        "municipio": row.get("municipio"),
        "estado": row.get("estado") or row.get("uf"),
        "bioma": row.get("bioma"),
        "risco_fogo": _float_or_none(row.get("risco_fogo")),
        "precipitacao": _float_or_none(row.get("precipitacao")),
        "numero_dias_sem_chuva": _int_or_none(row.get("numero_dias_sem_chuva")),
        "frp": _float_or_none(row.get("frp")),
    }


def ler_csv(texto_csv):
    sample = texto_csv[:4096]
    dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    reader = csv.DictReader(io.StringIO(texto_csv), dialect=dialect)
    focos = []
    for row in reader:
        foco = normalizar_linha({(k or "").strip().lower(): (v or "").strip() for k, v in row.items()})
        if foco["lat"] is not None and foco["lon"] is not None:
            focos.append(foco)
    return focos


def aplicar_filtros(focos, filtros):
    filtrados = focos
    for campo in ("estado", "municipio", "bioma", "satelite"):
        valor = filtros.get(campo)
        if valor:
            filtrados = [f for f in filtrados if (f.get(campo) or "").lower() == valor.lower()]
    risco = filtros.get("risco_fogo")
    if risco:
        filtrados = [f for f in filtrados if f.get("risco_fogo") is not None and f["risco_fogo"] >= float(risco)]
    frp_min = filtros.get("frp_min")
    if frp_min:
        filtrados = [f for f in filtrados if f.get("frp") is not None and f["frp"] >= float(frp_min)]
    return filtrados


def obter_focos(base_url, cache_dir, data=None, timeout=20):
    try:
        url = resolver_csv_url(base_url, data=data, timeout=timeout)
        texto, origem = baixar_csv(url, cache_dir=cache_dir, timeout=timeout)
    except Exception:
        if data:
            raise
        cached = csv_cache_mais_recente(cache_dir)
        url = cached["url"]
        texto = cached["texto"]
        origem = "cache_recente"
    return {
        "url": url,
        "origem": origem,
        "focos": ler_csv(texto),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }

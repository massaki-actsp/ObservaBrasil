import numpy as np


def _safe_divide(numerador, denominador):
    numerador = np.asarray(numerador, dtype="float32")
    denominador = np.asarray(denominador, dtype="float32")
    out = np.full(numerador.shape, np.nan, dtype="float32")
    return np.divide(numerador, denominador, out=out, where=denominador != 0)


def calcular_ndvi(nir, red):
    return _safe_divide(np.asarray(nir) - np.asarray(red), np.asarray(nir) + np.asarray(red))


def calcular_nbr(nir, swir):
    return _safe_divide(np.asarray(nir) - np.asarray(swir), np.asarray(nir) + np.asarray(swir))


def calcular_dnbr(nbr_antes, nbr_depois):
    return np.asarray(nbr_antes, dtype="float32") - np.asarray(nbr_depois, dtype="float32")


def estatisticas_indice(array):
    valores = np.asarray(array, dtype="float32")
    validos = valores[~np.isnan(valores)]
    if validos.size == 0:
        return {"media": None, "minimo": None, "maximo": None, "desvio_padrao": None, "pixels_validos": 0}
    return {
        "media": float(np.mean(validos)),
        "minimo": float(np.min(validos)),
        "maximo": float(np.max(validos)),
        "desvio_padrao": float(np.std(validos)),
        "pixels_validos": int(validos.size),
    }


def classificar_ndvi(valor):
    if valor < 0:
        return "agua_sombra_ou_nao_vegetado"
    if valor < 0.2:
        return "solo_exposto_ou_vegetacao_muito_baixa"
    if valor < 0.4:
        return "vegetacao_esparsa"
    if valor < 0.6:
        return "vegetacao_moderada"
    return "vegetacao_densa"

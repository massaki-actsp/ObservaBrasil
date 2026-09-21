from datetime import datetime, timezone

from app.extensions import db


class FocoCalor(db.Model):
    __tablename__ = "focos_calor"

    id = db.Column(db.String(120), primary_key=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    data_hora_gmt = db.Column(db.DateTime, nullable=True, index=True)
    satelite = db.Column(db.String(80), index=True)
    municipio = db.Column(db.String(160), index=True)
    estado = db.Column(db.String(80), index=True)
    bioma = db.Column(db.String(120), index=True)
    risco_fogo = db.Column(db.Float)
    precipitacao = db.Column(db.Float)
    numero_dias_sem_chuva = db.Column(db.Integer)
    frp = db.Column(db.Float)
    fonte = db.Column(db.String(80), nullable=False, default="INPE BDQueimadas")
    atualizado_em = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "lat": self.lat,
            "lon": self.lon,
            "data_hora_gmt": self.data_hora_gmt.isoformat() if self.data_hora_gmt else None,
            "satelite": self.satelite,
            "municipio": self.municipio,
            "estado": self.estado,
            "bioma": self.bioma,
            "risco_fogo": self.risco_fogo,
            "precipitacao": self.precipitacao,
            "numero_dias_sem_chuva": self.numero_dias_sem_chuva,
            "frp": self.frp,
            "fonte": self.fonte,
            "atualizado_em": self.atualizado_em.isoformat(),
        }

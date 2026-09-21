from datetime import datetime, timezone

from app.extensions import db


class AreaInteresse(db.Model):
    __tablename__ = "areas_interesse"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.Text)
    geometria = db.Column(db.JSON, nullable=False)
    filtros = db.Column(db.JSON, nullable=True)
    canais_alerta = db.Column(db.JSON, nullable=True)
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    usuario = db.relationship("User", back_populates="areas")
    alertas = db.relationship("Alerta", back_populates="area", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "geometria": self.geometria,
            "filtros": self.filtros or {},
            "canais_alerta": self.canais_alerta or [],
            "ativa": self.ativa,
            "criado_em": self.criado_em.isoformat(),
            "atualizado_em": self.atualizado_em.isoformat(),
        }

from datetime import datetime, timezone

from app.extensions import db


class Alerta(db.Model):
    __tablename__ = "alertas"

    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey("areas_interesse.id"), nullable=False)
    canal = db.Column(db.String(40), nullable=False)
    destino = db.Column(db.String(255), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    area = db.relationship("AreaInteresse", back_populates="alertas")


class FocoProcessado(db.Model):
    __tablename__ = "focos_processados"

    id = db.Column(db.Integer, primary_key=True)
    foco_id = db.Column(db.String(120), nullable=False, index=True)
    area_id = db.Column(db.Integer, db.ForeignKey("areas_interesse.id"), nullable=False)
    processado_em = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("foco_id", "area_id", name="uq_foco_area_processado"),)


class HistoricoNotificacao(db.Model):
    __tablename__ = "historico_notificacoes"

    id = db.Column(db.Integer, primary_key=True)
    alerta_id = db.Column(db.Integer, db.ForeignKey("alertas.id"), nullable=False)
    foco_id = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="pendente")
    tentativas = db.Column(db.Integer, nullable=False, default=0)
    erro = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    enviado_em = db.Column(db.DateTime)

from app.extensions import db
from app.models.alerta import FocoProcessado, HistoricoNotificacao


def registrar_foco_processado(foco_id, area_id):
    existente = FocoProcessado.query.filter_by(foco_id=foco_id, area_id=area_id).first()
    if existente:
        return False
    db.session.add(FocoProcessado(foco_id=foco_id, area_id=area_id))
    db.session.commit()
    return True


def criar_historico(alerta_id, foco_id, status="pendente", erro=None):
    historico = HistoricoNotificacao(alerta_id=alerta_id, foco_id=foco_id, status=status, erro=erro)
    db.session.add(historico)
    db.session.commit()
    return historico

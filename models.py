from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Orcamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bimestre = db.Column(db.String(20), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)  # NOVO
    data_fim = db.Column(db.Date, nullable=False)     # NOVO
    diarias = db.Column(db.Float, default=0.0)
    derso = db.Column(db.Float, default=0.0)
    diarias_pav = db.Column(db.Float, default=0.0)
    derso_pav = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='ativo')  # NOVO: ativo, finalizado
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_finalizacao = db.Column(db.DateTime)  # NOVO

class RecolhimentoSaldo(db.Model):
    """Modelo para registrar recolhimentos de saldo"""
    __tablename__ = 'recolhimento_saldo'
    
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    unidade_origem = db.Column(db.String(50), nullable=False)  # Ex: "7º BPM"
    unidade_destino = db.Column(db.String(50), default='CRPIV')  # Sempre CRPIV
    tipo_orcamento = db.Column(db.String(50), nullable=False)  # DIÁRIAS, DERSO, etc.
    valor_recolhido = db.Column(db.Numeric(10, 2), nullable=False)
    motivo = db.Column(db.Text)
    usuario_responsavel = db.Column(db.String(100), default='Sistema')
    data_recolhimento = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    orcamento = db.relationship('Orcamento', backref='recolhimentos')
    
    def __repr__(self):
        return f'<RecolhimentoSaldo {self.unidade_origem} -> {self.unidade_destino}: R$ {self.valor_recolhido}>'


class ComplementacaoOrcamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    processo_sei = db.Column(db.String(50), nullable=False)
    tipo_orcamento = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    orcamento = db.relationship('Orcamento', backref='complementacoes')

class Distribuicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=False)
    unidade = db.Column(db.String(20), nullable=False)
    tipo_orcamento = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_distribuicao = db.Column(db.DateTime, default=datetime.utcnow)

class Missao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fonte_dinheiro = db.Column(db.String(20), nullable=False)
    opm_destino = db.Column(db.String(20), nullable=False)
    processo_sei = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    periodo = db.Column(db.String(50), nullable=False)
    mes = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    numero_autorizacao = db.Column(db.String(50))
    status = db.Column(db.String(20), default='previsao')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_autorizacao = db.Column(db.DateTime)
    observacoes = db.Column(db.Text)

class MovimentacaoOrcamentaria(db.Model):
    """Modelo para registrar todas as movimentações orçamentárias"""
    __tablename__ = 'movimentacao_orcamentaria'
    
    id = db.Column(db.Integer, primary_key=True)
    data_movimentacao = db.Column(db.DateTime, default=datetime.utcnow)
    tipo = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text)
    unidade_origem = db.Column(db.String(50), nullable=True)
    unidade_destino = db.Column(db.String(50), nullable=True)
    tipo_orcamento = db.Column(db.String(50), nullable=True)
    valor = db.Column(db.Numeric(10,2), nullable=True)
    usuario = db.Column(db.String(100), default="Sistema")
    
    # Referências opcionais
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamento.id'), nullable=True)
    missao_id = db.Column(db.Integer, db.ForeignKey('missao.id'), nullable=True)
    
    # Relacionamentos
    orcamento = db.relationship('Orcamento', backref='movimentacoes')
    missao = db.relationship('Missao', backref='movimentacoes')
    
    def __repr__(self):
        return f'<MovimentacaoOrcamentaria {self.tipo} - {self.valor}>'


class ResolucaoSemSaldo(db.Model):
    """Modelo para registrar resoluções quando não há saldo suficiente"""
    __tablename__ = 'resolucao_sem_saldo'
    
    id = db.Column(db.Integer, primary_key=True)
    data_resolucao = db.Column(db.DateTime, default=datetime.utcnow)
    missao_id = db.Column(db.Integer, db.ForeignKey('missao.id'), nullable=False)
    tipo_resolucao = db.Column(db.String(50))  # "transferencia", "nova_distribuicao", "cancelamento"
    valor_necessario = db.Column(db.Numeric(10,2))
    unidade_origem_transferencia = db.Column(db.String(50), nullable=True)
    valor_transferido = db.Column(db.Numeric(10,2), nullable=True)
    observacoes = db.Column(db.Text)
    usuario_responsavel = db.Column(db.String(100), default="Sistema")
    
    # Relacionamento
    missao = db.relationship('Missao', backref='resolucoes_saldo')


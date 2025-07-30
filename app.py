from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, Response, abort
from models import db, Orcamento, Distribuicao, Missao, ComplementacaoOrcamento, MovimentacaoOrcamentaria, ResolucaoSemSaldo, RecolhimentoSaldo
from config import Config
import sqlite3
from datetime import datetime, date
import calendar
import pandas as pd
import io
import csv  
from werkzeug.utils import secure_filename
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from sqlalchemy import or_ 
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env na variável de ambiente do sistema
load_dotenv()


app = Flask(__name__)
app.config.from_object(Config)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB máximo

# Criar pasta de uploads se não existir
if not os.path.exists('uploads'):
    os.makedirs('uploads')


@app.route('/exportar_movimentacoes_pdf')
def exportar_movimentacoes_pdf():
    """Exportar movimentações para PDF"""
    try:
        # Buscar movimentações
        movimentacoes = MovimentacaoOrcamentaria.query.order_by(
            MovimentacaoOrcamentaria.data_movimentacao.desc()
        ).all()
        
        # Criar buffer para o PDF
        buffer = io.BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f4e79')
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        
        # Elementos do documento
        elements = []
        
        # Cabeçalho
        elements.append(Paragraph("RELATÓRIO DE MOVIMENTAÇÕES ORÇAMENTÁRIAS", title_style))
        elements.append(Paragraph(f"CRPIV - Comando Regional de Polícia IV", subtitle_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", subtitle_style))
        elements.append(Spacer(1, 20))
        
        # Resumo estatístico
        total_movimentacoes = len(movimentacoes)
        valor_total = sum([m.valor for m in movimentacoes if m.valor])
        
        resumo_data = [
            ['RESUMO EXECUTIVO', ''],
            ['Total de Movimentações:', f'{total_movimentacoes:,}'],
            ['Valor Total Movimentado:', f'R$ {valor_total:,.2f}'.replace('.', ',')],
            ['Período:', f'{movimentacoes[-1].data_movimentacao.strftime("%d/%m/%Y") if movimentacoes else "N/A"} a {movimentacoes[0].data_movimentacao.strftime("%d/%m/%Y") if movimentacoes else "N/A"}']
        ]
        
        resumo_table = Table(resumo_data, colWidths=[3*inch, 2*inch])
        resumo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        
        elements.append(resumo_table)
        elements.append(Spacer(1, 30))
        
        # Tabela principal de movimentações
        if movimentacoes:
            # Cabeçalho da tabela
            data = [['Data', 'Tipo', 'Descrição', 'Origem', 'Destino', 'Tipo Orç.', 'Valor', 'Usuário']]
            
            # Dados das movimentações
            for mov in movimentacoes:
                data.append([
                    mov.data_movimentacao.strftime('%d/%m/%Y\n%H:%M'),
                    mov.tipo.replace('_', ' ').title(),
                    (mov.descricao or '')[:30] + ('...' if len(mov.descricao or '') > 30 else ''),
                    mov.unidade_origem or '-',
                    mov.unidade_destino or '-',
                    mov.tipo_orcamento or '-',
                    f'R$ {mov.valor:,.2f}'.replace('.', ',') if mov.valor else '-',
                    mov.usuario[:10] + ('...' if len(mov.usuario) > 10 else '')
                ])
            
            # Criar tabela
            table = Table(data, colWidths=[0.8*inch, 1.2*inch, 1.8*inch, 0.8*inch, 0.8*inch, 0.7*inch, 0.9*inch, 0.8*inch])
            
            # Estilo da tabela
            table.setStyle(TableStyle([
                # Cabeçalho
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Corpo da tabela
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Zebrar linhas
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ]))
            
            # Aplicar zebra nas linhas
            for i in range(1, len(data)):
                if i % 2 == 0:
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
                    ]))
            
            elements.append(Paragraph("DETALHAMENTO DAS MOVIMENTAÇÕES", styles['Heading2']))
            elements.append(Spacer(1, 10))
            elements.append(table)
            
        else:
            elements.append(Paragraph("Nenhuma movimentação encontrada.", styles['Normal']))
        
        # Rodapé
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("___" * 30, styles['Normal']))
        elements.append(Paragraph(
            f"Relatório gerado automaticamente pelo Sistema CRPIV em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))
        
        # Gerar PDF
        doc.build(elements)
        
        # Preparar resposta
        buffer.seek(0)
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=relatorio_movimentacoes_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro na exportação PDF: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao exportar relatório em PDF', 'error')
        return redirect(url_for('relatorio_movimentacoes'))


@app.route('/exportar_pdf')
def exportar_pdf():
    """Exportar relatórios em PDF - VERSÃO UNIFICADA"""
    try:
        tipo = request.args.get('tipo', 'orcamento')
        
        print(f"🔍 Exportando PDF - Tipo: {tipo}")
        
        # ✅ ROTEAMENTO POR TIPO DE RELATÓRIO
        if tipo == 'orcamento':
            return exportar_relatorio_orcamentario_pdf()
        elif tipo == 'missoes':
            return exportar_missoes_pdf()
        elif tipo == 'movimentacoes':
            return exportar_movimentacoes_pdf()
        elif tipo == 'unidade':
            return exportar_relatorio_unidade_pdf()
        else:
            flash(f'Tipo de relatório "{tipo}" não reconhecido', 'error')
            return redirect(url_for('relatorios'))
            
    except Exception as e:
        print(f"❌ Erro na exportação: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao exportar relatório', 'error')
        return redirect(url_for('relatorios'))

def exportar_relatorio_orcamentario_pdf():
    """Exportar relatório orçamentário em PDF - SEU CÓDIGO ATUAL"""
    try:
        unidade_filtro = request.args.get('unidade', '')
        
        # Buscar dados para o relatório
        dados = preparar_dados_relatorio(unidade_filtro)
        
        # Criar buffer para o PDF
        buffer = io.BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f4e79')
        )
        
        elements.append(Paragraph("RELATÓRIO ORÇAMENTÁRIO CONSOLIDADO", title_style))
        elements.append(Paragraph(f"CRPIV - Comando Regional de Polícia IV", 
                                ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)))
        
        if unidade_filtro:
            elements.append(Paragraph(f"Filtro aplicado: {unidade_filtro}", 
                                    ParagraphStyle('Filter', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.red)))
        
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", 
                                ParagraphStyle('Date', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.grey)))
        elements.append(Spacer(1, 30))
        
        # Resumo Financeiro
        resumo_data = [
            ['RESUMO FINANCEIRO', ''],
            ['Total Orçamento:', f'R$ {sum(dados["tipos_valores"]):,.2f}'.replace('.', ',')],
            ['Total Previsões:', f'R$ {dados["status_valores"][0]:,.2f}'.replace('.', ',')],
            ['Total Autorizadas:', f'R$ {dados["status_valores"][1]:,.2f}'.replace('.', ',')],
            ['Disponível:', f'R$ {(sum(dados["tipos_valores"]) - dados["status_valores"][1]):,.2f}'.replace('.', ',')]
        ]
        
        resumo_table = Table(resumo_data, colWidths=[3*inch, 2*inch])
        resumo_table.setStyle(get_table_style_header())  # ✅ Usar função helper
        
        elements.append(resumo_table)
        elements.append(Spacer(1, 30))
        
        # Orçamento por Tipo
        tipo_data = [['ORÇAMENTO POR TIPO', 'VALOR']]
        for i, tipo in enumerate(dados['tipos_orcamento']):
            tipo_data.append([tipo, f'R$ {dados["tipos_valores"][i]:,.2f}'.replace('.', ',')])
        
        tipo_table = Table(tipo_data, colWidths=[3*inch, 2*inch])
        tipo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
        ]))
        
        elements.append(tipo_table)
        elements.append(Spacer(1, 30))
        
        # Gastos por Unidade
        if dados['unidades']:
            unidade_data = [['GASTOS POR UNIDADE', 'VALOR']]
            for i, unidade in enumerate(dados['unidades']):
                unidade_data.append([unidade, f'R$ {dados["gastos_unidade"][i]:,.2f}'.replace('.', ',')])
            
            unidade_table = Table(unidade_data, colWidths=[3*inch, 2*inch])
            unidade_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ]))
            
            elements.append(unidade_table)
        
        # Rodapé
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("___" * 30, styles['Normal']))
        elements.append(Paragraph(
            f"Relatório gerado automaticamente pelo Sistema CRPIV em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        filtro_nome = f"_{unidade_filtro.replace(' ', '_')}" if unidade_filtro else "_geral"
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=relatorio_orcamentario{filtro_nome}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro na exportação PDF orçamentário: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao exportar relatório orçamentário em PDF', 'error')
        return redirect(url_for('relatorios'))

def exportar_missoes_pdf():
    """Exportar missões para PDF separadas por unidades"""
    try:
        # Buscar filtros
        omp_filtro = request.args.get('omp_filtro', '')
        fonte_filtro = request.args.get('fonte_filtro', '')
        
        print(f"🔍 Exportando PDF de missões - Filtros: OMP='{omp_filtro}', Fonte='{fonte_filtro}'")
        
        # Buscar missões com filtros
        query = Missao.query
        
        if omp_filtro:
            query = query.filter(Missao.opm_destino == omp_filtro)
        
        if fonte_filtro:
            query = query.filter(Missao.fonte_dinheiro == fonte_filtro)
        
        missoes = query.order_by(Missao.fonte_dinheiro, Missao.status.desc(), Missao.data_criacao.desc()).all()
        
        print(f"📋 {len(missoes)} missões encontradas para exportação")
        
        # Organizar missões por unidade
        missoes_por_unidade = {}
        for missao in missoes:
            unidade = missao.fonte_dinheiro
            if unidade not in missoes_por_unidade:
                missoes_por_unidade[unidade] = {
                    'previsao': [],
                    'autorizada': [],
                    'total_previsao': 0,
                    'total_autorizada': 0,
                    'total_geral': 0
                }
            
            missoes_por_unidade[unidade][missao.status].append(missao)
            
            if missao.status == 'previsao':
                missoes_por_unidade[unidade]['total_previsao'] += missao.valor
            else:
                missoes_por_unidade[unidade]['total_autorizada'] += missao.valor
            
            missoes_por_unidade[unidade]['total_geral'] += missao.valor
        
        # Criar buffer para o PDF
        buffer = io.BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=72,
            bottomMargin=18
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f4e79'),
            fontName='Helvetica-Bold'
        )
        
        elements.append(Paragraph("RELATÓRIO DE MISSÕES POR UNIDADE", title_style))
        elements.append(Paragraph("CRPIV - Comando Regional de Polícia IV", 
                                ParagraphStyle('Sub', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, textColor=colors.grey)))
        
        # Informações dos filtros
        filtro_info = []
        if omp_filtro:
            filtro_info.append(f"OPM Destino: {omp_filtro}")
        if fonte_filtro:
            filtro_info.append(f"Fonte: {fonte_filtro}")
        
        if filtro_info:
            elements.append(Paragraph(f"Filtros aplicados: {' | '.join(filtro_info)}", 
                                    ParagraphStyle('Filter', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, textColor=colors.grey)))
        
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", 
                                ParagraphStyle('Date', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, textColor=colors.grey)))
        elements.append(Spacer(1, 20))
        
        # Resumo executivo
        total_missoes = len(missoes)
        total_previsoes = sum([m.valor for m in missoes if m.status == 'previsao'])
        total_autorizadas = sum([m.valor for m in missoes if m.status == 'autorizada'])
        total_geral = total_previsoes + total_autorizadas
        
        resumo_data = [
            ['RESUMO EXECUTIVO', ''],
            ['Total de Missões:', f'{total_missoes:,}'],
            ['Total em Previsão:', f'R$ {total_previsoes:,.2f}'.replace('.', ',')],
            ['Total Autorizada:', f'R$ {total_autorizadas:,.2f}'.replace('.', ',')],
            ['Valor Total Geral:', f'R$ {total_geral:,.2f}'.replace('.', ',')],
            ['Unidades Envolvidas:', f'{len(missoes_por_unidade)} unidade(s)']
        ]
        
        resumo_table = Table(resumo_data, colWidths=[3.5*inch, 2.5*inch])
        resumo_table.setStyle(get_table_style_header())  # ✅ Usar função helper
        
        elements.append(resumo_table)
        elements.append(Spacer(1, 30))
        
        # Missões por unidade
        unidade_style = ParagraphStyle(
            'UnidadeTitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.HexColor('#2c5aa0'),
            fontName='Helvetica-Bold'
        )
        
        for unidade, dados in missoes_por_unidade.items():
            # Título da unidade
            elements.append(Paragraph(f"📍 {unidade}", unidade_style))
            
            # Resumo da unidade
            unidade_resumo = [
                ['Resumo da Unidade', 'Quantidade', 'Valor Total'],
                ['Missões em Previsão', f"{len(dados['previsao'])}", f"R$ {dados['total_previsao']:,.2f}".replace('.', ',')],
                ['Missões Autorizadas', f"{len(dados['autorizada'])}", f"R$ {dados['total_autorizada']:,.2f}".replace('.', ',')],
                ['TOTAL DA UNIDADE', f"{len(dados['previsao']) + len(dados['autorizada'])}", f"R$ {dados['total_geral']:,.2f}".replace('.', ',')]
            ]
            
            unidade_resumo_table = Table(unidade_resumo, colWidths=[3*inch, 1.5*inch, 2*inch])
            unidade_resumo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            
            elements.append(unidade_resumo_table)
            elements.append(Spacer(1, 15))
            
            # Tabelas de missões (autorizadas e previsões)
            if dados['autorizada']:
                elements.append(Paragraph(f"✅ Missões Autorizadas ({len(dados['autorizada'])})", 
                                       ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12, 
                                                    textColor=colors.HexColor('#28a745'), fontName='Helvetica-Bold')))
                
                auth_data = [['OPM Destino', 'Descrição', 'Tipo', 'Período', 'Valor']]
                
                for missao in dados['autorizada']:
                    auth_data.append([
                        missao.opm_destino,
                        (missao.descricao or '')[:35] + ('...' if len(missao.descricao or '') > 35 else ''),
                        missao.tipo,
                        missao.periodo or '-',
                        f'R$ {missao.valor:,.2f}'.replace('.', ',')
                    ])
                
                auth_table = Table(auth_data, colWidths=[1.2*inch, 2.3*inch, 1*inch, 1*inch, 1*inch])
                auth_table.setStyle(create_missoes_table_style('#28a745', colors.lightgreen))
                
                elements.append(auth_table)
                elements.append(Spacer(1, 10))
            
            if dados['previsao']:
                elements.append(Paragraph(f"⏳ Missões em Previsão ({len(dados['previsao'])})", 
                                       ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12, 
                                                    textColor=colors.HexColor('#ffc107'), fontName='Helvetica-Bold')))
                
                prev_data = [['OPM Destino', 'Descrição', 'Tipo', 'Período', 'Valor']]
                
                for missao in dados['previsao']:
                    prev_data.append([
                        missao.opm_destino,
                        (missao.descricao or '')[:35] + ('...' if len(missao.descricao or '') > 35 else ''),
                        missao.tipo,
                        missao.periodo or '-',
                        f'R$ {missao.valor:,.2f}'.replace('.', ',')
                    ])
                
                prev_table = Table(prev_data, colWidths=[1.2*inch, 2.3*inch, 1*inch, 1*inch, 1*inch])
                prev_table.setStyle(create_missoes_table_style('#ffc107', colors.lightyellow))
                
                elements.append(prev_table)
                elements.append(Spacer(1, 10))
            
            elements.append(Spacer(1, 20))
        
        # Rodapé
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("_" * 80, ParagraphStyle('Line', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)))
        elements.append(Paragraph(
            f"Relatório gerado automaticamente pelo Sistema CRPIV em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Nome do arquivo com filtros
        nome_arquivo = "missoes_por_unidade"
        if fonte_filtro:
            nome_arquivo += f"_{fonte_filtro.replace(' ', '_')}"
        if omp_filtro:
            nome_arquivo += f"_destino_{omp_filtro.replace(' ', '_')}"
        nome_arquivo += f"_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        
        print(f"✅ PDF gerado: {nome_arquivo}")
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename={nome_arquivo}'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro na exportação PDF de missões: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao exportar relatório de missões em PDF', 'error')
        return redirect(url_for('missoes'))


def preparar_dados_relatorio(unidade_filtro=''):
    """Prepara dados para o relatório"""
    try:
        # Usar orçamento total de todos os bimestres
        totais_geral = calcular_orcamento_total_todos_bimestres()
        tipos_valores = [
            totais_geral['diarias'],
            totais_geral['derso'],
            totais_geral['diarias_pav'],
            totais_geral['derso_pav']
        ]
        
        # Gráfico por unidade (gastos autorizados) - com filtro
        gastos_unidade = {}
        for unidade in UNIDADES:
            if unidade_filtro and unidade != unidade_filtro:
                continue
                
            total_gasto = db.session.query(Missao).filter_by(
                fonte_dinheiro=unidade, 
                status='autorizada'
            ).with_entities(db.func.sum(Missao.valor)).scalar() or 0
            gastos_unidade[unidade] = total_gasto
        
        # Gráfico por status - considerando filtro de unidade
        query_previsoes = db.session.query(Missao).filter_by(status='previsao')
        query_autorizadas = db.session.query(Missao).filter_by(status='autorizada')
        
        if unidade_filtro:
            query_previsoes = query_previsoes.filter(Missao.fonte_dinheiro == unidade_filtro)
            query_autorizadas = query_autorizadas.filter(Missao.fonte_dinheiro == unidade_filtro)
        
        total_previsoes = query_previsoes.with_entities(db.func.sum(Missao.valor)).scalar() or 0
        total_autorizadas = query_autorizadas.with_entities(db.func.sum(Missao.valor)).scalar() or 0
        
        return {
            'tipos_orcamento': TIPOS_ORCAMENTO,
            'tipos_valores': tipos_valores,
            'unidades': list(gastos_unidade.keys()),
            'gastos_unidade': list(gastos_unidade.values()),
            'status_labels': ['Previsões', 'Autorizadas'],
            'status_valores': [total_previsoes, total_autorizadas],
            'unidade_filtro': unidade_filtro
        }
        
    except Exception as e:
        print(f"❌ Erro ao preparar dados: {e}")
        return {
            'tipos_orcamento': TIPOS_ORCAMENTO,
            'tipos_valores': [0, 0, 0, 0],
            'unidades': [],
            'gastos_unidade': [],
            'status_labels': ['Previsões', 'Autorizadas'],
            'status_valores': [0, 0],
            'unidade_filtro': unidade_filtro
        }
    

def verificar_saldo_disponivel_missao(missao):
    """Verifica se há saldo disponível para autorizar uma missão - VERSÃO CORRIGIDA"""
    try:
        print(f"🔍 Verificando saldo para missão: {missao.fonte_dinheiro} - {missao.tipo} - R$ {missao.valor:,.2f}")
        
        if missao.fonte_dinheiro == 'CRPIV':
            # ✅ MISSÃO DO CRPIV - Verificar saldo não distribuído
            saldo_crpiv = calcular_saldo_disponivel_crpiv(missao.tipo)
            
            print(f"💰 Saldo CRPIV disponível para {missao.tipo}: R$ {saldo_crpiv:,.2f}")
            
            if saldo_crpiv >= missao.valor:
                return {
                    'pode_autorizar': True,
                    'saldo_disponivel': saldo_crpiv,
                    'deficit': 0
                }
            else:
                return {
                    'pode_autorizar': False,
                    'saldo_disponivel': saldo_crpiv,
                    'deficit': missao.valor - saldo_crpiv
                }
        else:
            # ✅ MISSÃO DE SUBUNIDADE - Verificar saldo distribuído
            # Total distribuído para esta unidade/tipo
            distribuido = db.session.query(
                db.func.sum(Distribuicao.valor)
            ).filter(
                Distribuicao.unidade == missao.fonte_dinheiro,
                Distribuicao.tipo_orcamento == missao.tipo
            ).scalar() or 0
            
            # Total já autorizado para esta unidade/tipo
            autorizado = db.session.query(
                db.func.sum(Missao.valor)
            ).filter(
                Missao.fonte_dinheiro == missao.fonte_dinheiro,
                Missao.tipo == missao.tipo,
                Missao.status == 'autorizada'
            ).scalar() or 0
            
            saldo_disponivel = distribuido - autorizado
            
            print(f"📊 Análise de saldo {missao.fonte_dinheiro} - {missao.tipo}:")
            print(f"   Distribuído: R$ {distribuido:,.2f}")
            print(f"   Já autorizado: R$ {autorizado:,.2f}")
            print(f"   Disponível: R$ {saldo_disponivel:,.2f}")
            print(f"   Necessário: R$ {missao.valor:,.2f}")
            
            if saldo_disponivel >= missao.valor:
                return {
                    'pode_autorizar': True,
                    'saldo_disponivel': saldo_disponivel,
                    'deficit': 0
                }
            else:
                return {
                    'pode_autorizar': False,
                    'saldo_disponivel': saldo_disponivel,
                    'deficit': missao.valor - saldo_disponivel
                }
                
    except Exception as e:
        print(f"❌ Erro ao verificar saldo: {e}")
        return {
            'pode_autorizar': False,
            'saldo_disponivel': 0,
            'deficit': missao.valor
        }



def buscar_opcoes_transferencia(missao, deficit):
    """Busca opções de transferência de outras unidades/tipos"""
    try:
        opcoes = []
        
        # Buscar saldos disponíveis em outras unidades do mesmo tipo
        for unidade in UNIDADES:  # Excluir CRPIV
            if unidade == missao.fonte_dinheiro:
                continue
                
            # Calcular saldo desta unidade no mesmo tipo
            distribuido = db.session.query(
                db.func.sum(Distribuicao.valor)
            ).filter(
                Distribuicao.unidade == unidade,
                Distribuicao.tipo_orcamento == missao.tipo
            ).scalar() or 0
            
            autorizado = db.session.query(
                db.func.sum(Missao.valor)
            ).filter(
                Missao.fonte_dinheiro == unidade,
                Missao.tipo == missao.tipo,
                Missao.status == 'autorizada'
            ).scalar() or 0
            
            saldo_disponivel = distribuido - autorizado
            
            if saldo_disponivel >= deficit:
                opcoes.append({
                    'unidade': unidade,
                    'tipo': missao.tipo,
                    'saldo_disponivel': saldo_disponivel,
                    'valor_transferir': deficit,
                    'saldo_restante': saldo_disponivel - deficit
                })
        
        # Verificar se CRPIV tem saldo para nova distribuição
        saldos_crpiv = calcular_saldos_para_distribuir()
        tipo_crpiv_map = {
            'DIÁRIAS': 'diarias',
            'DERSO': 'derso',
            'DIÁRIAS PAV': 'diarias_pav',
            'DERSO PAV': 'derso_pav'
        }
        
        saldo_crpiv = saldos_crpiv.get(tipo_crpiv_map.get(missao.tipo, ''), 0)
        
        opcoes_crpiv = {
            'tem_saldo': saldo_crpiv >= deficit,
            'saldo_disponivel': saldo_crpiv,
            'valor_necessario': deficit
        }
        
        return {
            'opcoes_transferencia': opcoes,
            'opcoes_crpiv': opcoes_crpiv,
            'total_opcoes': len(opcoes) + (1 if opcoes_crpiv['tem_saldo'] else 0)
        }
        
    except Exception as e:
        print(f"❌ Erro ao buscar opções: {e}")
        return {'opcoes_transferencia': [], 'opcoes_crpiv': {'tem_saldo': False}, 'total_opcoes': 0}

def executar_transferencia_entre_unidades(unidade_origem, unidade_destino, tipo_orcamento, valor):
    """Executa transferência de saldo entre unidades - VERSÃO CORRIGIDA"""
    try:
        print(f"🔄 Executando transferência: {unidade_origem} → {unidade_destino} - {tipo_orcamento} - R$ {valor:,.2f}")
        
        # ✅ VALIDAÇÕES INICIAIS
        if valor <= 0:
            return {'sucesso': False, 'erro': 'Valor deve ser maior que zero'}
        
        if unidade_origem == unidade_destino:
            return {'sucesso': False, 'erro': 'Unidade origem não pode ser igual à unidade destino'}
        
        # ✅ BUSCAR DISTRIBUIÇÃO DA UNIDADE ORIGEM
        distribuicao_origem = db.session.query(Distribuicao).filter_by(
            unidade=unidade_origem,
            tipo_orcamento=tipo_orcamento
        ).order_by(Distribuicao.data_distribuicao.desc()).first()
        
        if not distribuicao_origem:
            return {'sucesso': False, 'erro': f'Nenhuma distribuição encontrada para {unidade_origem} - {tipo_orcamento}'}
        
        if distribuicao_origem.valor < valor:
            return {'sucesso': False, 'erro': f'Saldo insuficiente. Disponível: R$ {distribuicao_origem.valor:,.2f}, Solicitado: R$ {valor:,.2f}'}
        
        print(f"✅ Distribuição origem encontrada: R$ {distribuicao_origem.valor:,.2f}")
        
        # ✅ VERIFICAR SALDO REAL DISPONÍVEL (Distribuído - Autorizado)
        autorizado_origem = db.session.query(
            db.func.sum(Missao.valor)
        ).filter(
            Missao.fonte_dinheiro == unidade_origem,
            Missao.tipo == tipo_orcamento,
            Missao.status == 'autorizada'
        ).scalar() or 0
        
        saldo_real_origem = distribuicao_origem.valor - autorizado_origem
        
        if saldo_real_origem < valor:
            return {'sucesso': False, 'erro': f'Saldo real insuficiente. Disponível: R$ {saldo_real_origem:,.2f} (R$ {autorizado_origem:,.2f} já autorizados)'}
        
        print(f"✅ Saldo real verificado: R$ {saldo_real_origem:,.2f}")
        
        # ✅ REDUZIR VALOR DA UNIDADE ORIGEM
        valor_original_origem = distribuicao_origem.valor
        distribuicao_origem.valor -= valor
        
        print(f"📉 Reduzindo distribuição de {unidade_origem}:")
        print(f"   De: R$ {valor_original_origem:,.2f}")
        print(f"   Para: R$ {distribuicao_origem.valor:,.2f}")
        
        # ✅ BUSCAR OU CRIAR DISTRIBUIÇÃO NA UNIDADE DESTINO
        distribuicao_destino = db.session.query(Distribuicao).filter_by(
            unidade=unidade_destino,
            tipo_orcamento=tipo_orcamento,
            orcamento_id=distribuicao_origem.orcamento_id
        ).first()
        
        if distribuicao_destino:
            valor_original_destino = distribuicao_destino.valor
            distribuicao_destino.valor += valor
            print(f"📈 Aumentando distribuição de {unidade_destino}:")
            print(f"   De: R$ {valor_original_destino:,.2f}")
            print(f"   Para: R$ {distribuicao_destino.valor:,.2f}")
        else:
            # Criar nova distribuição
            distribuicao_destino = Distribuicao(
                orcamento_id=distribuicao_origem.orcamento_id,
                unidade=unidade_destino,
                tipo_orcamento=tipo_orcamento,
                valor=valor,
                data_distribuicao=datetime.utcnow()
            )
            db.session.add(distribuicao_destino)
            print(f"✅ Criando nova distribuição para {unidade_destino}: R$ {valor:,.2f}")
        
        # ✅ REGISTRAR MOVIMENTAÇÃO DE LOG
        registrar_movimentacao(
            tipo='transferencia_entre_unidades',
            descricao=f'Transferência: {unidade_origem} → {unidade_destino} ({tipo_orcamento})',
            unidade_origem=unidade_origem,
            unidade_destino=unidade_destino,
            tipo_orcamento=tipo_orcamento,
            valor=valor,
            orcamento_id=distribuicao_origem.orcamento_id
        )
        
        print(f"✅ Transferência preparada com sucesso!")
        
        return {
            'sucesso': True,
            'valor_transferido': valor,
            'saldo_origem_anterior': valor_original_origem,
            'saldo_origem_atual': distribuicao_origem.valor,
            'saldo_destino_anterior': valor_original_destino if distribuicao_destino else 0,
            'saldo_destino_atual': distribuicao_destino.valor
        }
        
    except Exception as e:
        print(f"❌ Erro na transferência: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}


def executar_nova_distribuicao_crpiv(unidade_destino, tipo_orcamento, valor):
    """Executa nova distribuição do CRPIV para uma unidade"""
    try:
        print(f"📤 Nova distribuição: CRPIV → {unidade_destino} - {tipo_orcamento} - R$ {valor:,.2f}")
        
        # Verificar se CRPIV tem saldo
        saldos_crpiv = calcular_saldos_para_distribuir()
        tipo_map = {
            'DIÁRIAS': 'diarias',
            'DERSO': 'derso',
            'DIÁRIAS PAV': 'diarias_pav',
            'DERSO PAV': 'derso_pav'
        }
        
        saldo_disponivel = saldos_crpiv.get(tipo_map.get(tipo_orcamento, ''), 0)
        
        if saldo_disponivel < valor:
            return {'sucesso': False, 'erro': f'CRPIV não tem saldo suficiente. Disponível: R$ {saldo_disponivel:,.2f}'}
        
        # Buscar orçamento mais recente (ou usar lógica específica)
        orcamento_atual = Orcamento.query.order_by(Orcamento.data_criacao.desc()).first()
        
        if not orcamento_atual:
            return {'sucesso': False, 'erro': 'Nenhum orçamento encontrado'}
        
        # Buscar ou criar distribuição
        distribuicao = Distribuicao.query.filter_by(
            orcamento_id=orcamento_atual.id,
            unidade=unidade_destino,
            tipo_orcamento=tipo_orcamento
        ).first()
        
        if distribuicao:
            distribuicao.valor += valor
        else:
            distribuicao = Distribuicao(
                orcamento_id=orcamento_atual.id,
                unidade=unidade_destino,
                tipo_orcamento=tipo_orcamento,
                valor=valor
            )
            db.session.add(distribuicao)
        
        # Registrar movimentação
        registrar_movimentacao(
            tipo='nova_distribuicao_crpiv',
            descricao=f'Nova distribuição do CRPIV para viabilizar autorização de missão',
            unidade_origem='CRPIV',
            unidade_destino=unidade_destino,
            tipo_orcamento=tipo_orcamento,
            valor=valor,
            orcamento_id=orcamento_atual.id
        )
        
        return {'sucesso': True}
        
    except Exception as e:
        print(f"❌ Erro na nova distribuição: {e}")
        return {'sucesso': False, 'erro': str(e)}

def registrar_movimentacao(tipo, descricao="", unidade_origem=None, unidade_destino=None, 
                          tipo_orcamento=None, valor=None, usuario=None, orcamento_id=None, missao_id=None):
    """Registra todas as movimentações orçamentárias - VERSÃO COM DEBUG"""
    try:
        print(f"🔍 TENTANDO REGISTRAR MOVIMENTAÇÃO:")
        print(f"   Tipo: {tipo}")
        print(f"   Descrição: {descricao}")
        print(f"   Valor: {valor}")
        
        # ✅ VERIFICAR SE A CLASSE EXISTE
        try:
            movimento = MovimentacaoOrcamentaria(
                tipo=tipo,
                descricao=descricao,
                unidade_origem=unidade_origem,
                unidade_destino=unidade_destino,
                tipo_orcamento=tipo_orcamento,
                valor=valor,
                usuario=usuario or "Sistema",
                orcamento_id=orcamento_id,
                missao_id=missao_id
            )
            print(f"✅ Objeto MovimentacaoOrcamentaria criado com sucesso")
            
            db.session.add(movimento)
            print(f"✅ Movimento adicionado à sessão")
            
            db.session.commit()
            print(f"✅ Movimento commitado no banco")
            
            # Verificar se foi salvo
            total_after = MovimentacaoOrcamentaria.query.count()
            print(f"📊 Total de registros após insert: {total_after}")
            
            print(f"📝 Log registrado com sucesso: {tipo} - {descricao}")
            
        except Exception as db_error:
            print(f"❌ Erro ao salvar no banco: {db_error}")
            print(f"   Fazendo rollback...")
            db.session.rollback()
            
            # Tentar verificar o erro específico
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Erro geral ao registrar log: {e}")
        import traceback
        traceback.print_exc()


def debug_distribuicao_completo():
    """Função para diagnosticar todos os problemas de distribuição"""
    print("=" * 60)
    print("🔍 DIAGNÓSTICO COMPLETO DO SISTEMA DE DISTRIBUIÇÃO")
    print("=" * 60)
    
    try:
        # 1. Verificar orçamentos
        orcamentos = Orcamento.query.all()
        print(f"📊 Total de orçamentos: {len(orcamentos)}")
        
        total_geral = {'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0}
        for orc in orcamentos:
            total_geral['diarias'] += orc.diarias or 0
            total_geral['derso'] += orc.derso or 0
            total_geral['diarias_pav'] += orc.diarias_pav or 0
            total_geral['derso_pav'] += orc.derso_pav or 0
        
        print("💰 Orçamento total base:")
        for tipo, valor in total_geral.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        # 2. Verificar complementações
        complementacoes = ComplementacaoOrcamento.query.all()
        print(f"📈 Total de complementações: {len(complementacoes)}")
        
        # 3. Verificar distribuições
        distribuicoes = Distribuicao.query.all()
        print(f"📤 Total de distribuições: {len(distribuicoes)}")
        
        total_distribuido = sum([d.valor for d in distribuicoes])
        print(f"💸 Total distribuído: R$ {total_distribuido:,.2f}")
        
        # 4. Verificar missões
        missoes_prev = Missao.query.filter_by(status='previsao').all()
        missoes_aut = Missao.query.filter_by(status='autorizada').all()
        
        print(f"📋 Missões em previsão: {len(missoes_prev)}")
        print(f"✅ Missões autorizadas: {len(missoes_aut)}")
        
        total_prev = sum([m.valor for m in missoes_prev])
        total_aut = sum([m.valor for m in missoes_aut])
        
        print(f"💰 Valor previsões: R$ {total_prev:,.2f}")
        print(f"💰 Valor autorizadas: R$ {total_aut:,.2f}")
        
        print("=" * 60)
        
        return {
            'status': 'OK',
            'orcamentos': len(orcamentos),
            'distribuicoes': len(distribuicoes),
            'missoes_autorizadas': len(missoes_aut)
        }
        
    except Exception as e:
        print(f"❌ Erro no diagnóstico: {e}")
        return {'status': 'ERRO', 'erro': str(e)}


@app.route('/autorizar_missao/<int:missao_id>')
def autorizar_missao(missao_id):
    """Autorizar missão com validação de saldo e registro de distribuição"""
    try:
        missao = db.session.get(Missao, missao_id)
        if not missao:
            flash('Missão não encontrada', 'error')
            return redirect(url_for('missoes'))
        
        if missao.status == 'autorizada':
            flash('Missão já está autorizada', 'info')
            return redirect(url_for('missoes'))
        
        print(f"🔍 Autorizando missão {missao_id}: {missao.fonte_dinheiro} → {missao.opm_destino} - R$ {missao.valor:,.2f}")
        
        # ✅ VERIFICAR SALDO DISPONÍVEL
        analise_saldo = verificar_saldo_disponivel_missao(missao)
        
        if analise_saldo['pode_autorizar']:
            # ✅ HÁ SALDO SUFICIENTE - AUTORIZAR E REGISTRAR DISTRIBUIÇÃO
            
            # 1. Autorizar a missão
            missao.status = 'autorizada'
            missao.data_autorizacao = datetime.utcnow()
            
            # 2. ✅ REGISTRAR DISTRIBUIÇÃO AUTOMÁTICA (NOVO)
            # Buscar orçamento mais recente para vincular
            orcamento_recente = Orcamento.query.order_by(Orcamento.data_criacao.desc()).first()
            
            if orcamento_recente:
                # Verificar se já existe distribuição para essa fonte/tipo
                distribuicao_existente = Distribuicao.query.filter_by(
                    orcamento_id=orcamento_recente.id,
                    unidade=missao.fonte_dinheiro,  # ✅ Pode ser CRPIV ou subunidade
                    tipo_orcamento=missao.tipo
                ).first()
                
                if distribuicao_existente:
                    # Aumentar valor da distribuição existente
                    valor_anterior = distribuicao_existente.valor
                    distribuicao_existente.valor += missao.valor
                    distribuicao_existente.data_distribuicao = datetime.utcnow()
                    
                    print(f"📈 Atualizando distribuição existente {missao.fonte_dinheiro}:")
                    print(f"   De: R$ {valor_anterior:,.2f}")
                    print(f"   Para: R$ {distribuicao_existente.valor:,.2f}")
                else:
                    # Criar nova distribuição
                    nova_distribuicao = Distribuicao(
                        orcamento_id=orcamento_recente.id,
                        unidade=missao.fonte_dinheiro,  # ✅ CRPIV ou subunidade
                        tipo_orcamento=missao.tipo,
                        valor=missao.valor,
                        data_distribuicao=datetime.utcnow()
                    )
                    db.session.add(nova_distribuicao)
                    
                    print(f"✅ Criando nova distribuição {missao.fonte_dinheiro}: R$ {missao.valor:,.2f}")
                
                # 3. ✅ REGISTRAR LOG DE DISTRIBUIÇÃO
                registrar_movimentacao(
                    tipo='distribuicao',
                    descricao=f'Distribuição automática: Missão {missao.id} - {missao.fonte_dinheiro} → {missao.omp_destino}',
                    unidade_origem='CRPIV' if missao.fonte_dinheiro != 'CRPIV' else 'Sistema',
                    unidade_destino=missao.fonte_dinheiro,
                    tipo_orcamento=missao.tipo,
                    valor=missao.valor,
                    orcamento_id=orcamento_recente.id,
                    missao_id=missao.id
                )
            
            # 4. ✅ REGISTRAR LOG DE AUTORIZAÇÃO
            registrar_movimentacao(
                tipo='autorizacao_missao',
                descricao=f'Missão autorizada: {missao.descricao[:50]}...',
                unidade_origem=missao.fonte_dinheiro,
                unidade_destino=missao.omp_destino,
                tipo_orcamento=missao.tipo,
                valor=missao.valor,
                missao_id=missao.id
            )
            
            db.session.commit()
            flash('✅ Missão autorizada com sucesso! Saldo ajustado automaticamente.', 'success')
            return redirect(url_for('missoes'))
            
        else:
            # ❌ NÃO HÁ SALDO SUFICIENTE - BUSCAR OPÇÕES
            opcoes = buscar_opcoes_transferencia(missao, analise_saldo['deficit'])
            
            if opcoes['total_opcoes'] == 0:
                # Não há nenhuma opção disponível
                flash(f'❌ Não é possível autorizar esta missão. Déficit: R$ {analise_saldo["deficit"]:,.2f}. '
                      f'Não há saldo suficiente em nenhuma unidade ou no CRPIV.', 'error')
                return redirect(url_for('missoes'))
            
            # Há opções - redirecionar para tela de resolução
            return render_template('resolver_sem_saldo.html',
                                 missao=missao,
                                 analise_saldo=analise_saldo,
                                 opcoes=opcoes)
                                 
    except Exception as e:
        print(f"❌ Erro ao autorizar missão: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()  # ✅ ADICIONAR ROLLBACK
        flash(f'Erro ao autorizar missão: {str(e)}', 'error')
        return redirect(url_for('missoes'))

def calcular_saldo_disponivel_crpiv(tipo_orcamento):
    """Calcula saldo disponível do CRPIV (não distribuído) - VERSÃO CORRIGIDA"""
    try:
        print(f"🔍 Calculando saldo CRPIV não distribuído para {tipo_orcamento}")
        
        # ✅ TOTAL ORÇAMENTÁRIO (COTA + COMPLEMENTAÇÕES)
        total_orcamentario = 0
        
        # Somar orçamento base de todos os bimestres
        orcamentos = Orcamento.query.all()
        for orc in orcamentos:
            if tipo_orcamento == 'DIÁRIAS':
                total_orcamentario += orc.diarias or 0
            elif tipo_orcamento == 'DERSO':
                total_orcamentario += orc.derso or 0
            elif tipo_orcamento == 'DIÁRIAS PAV':
                total_orcamentario += orc.diarias_pav or 0
            elif tipo_orcamento == 'DERSO PAV':
                total_orcamentario += orc.derso_pav or 0
        
        # Somar complementações
        complementacoes_total = db.session.query(
            db.func.sum(ComplementacaoOrcamento.valor)
        ).filter(
            ComplementacaoOrcamento.tipo_orcamento == tipo_orcamento
        ).scalar() or 0
        
        total_orcamentario += complementacoes_total
        
        # ✅ TOTAL DISTRIBUÍDO (PARA SUBUNIDADES + USADO PELO CRPIV)
        total_distribuido = db.session.query(
            db.func.sum(Distribuicao.valor)
        ).filter(
            Distribuicao.tipo_orcamento == tipo_orcamento
            # ✅ INCLUIR TODAS as distribuições (subunidades E CRPIV)
        ).scalar() or 0
        
        # ✅ SALDO DISPONÍVEL = ORÇAMENTO TOTAL - DISTRIBUÍDO
        saldo_disponivel = total_orcamentario - total_distribuido
        
        print(f"📊 CRPIV - {tipo_orcamento}:")
        print(f"   Total orçamentário: R$ {total_orcamentario:,.2f}")
        print(f"   Total distribuído: R$ {total_distribuido:,.2f}")
        print(f"   Saldo não distribuído: R$ {saldo_disponivel:,.2f}")
        
        return max(0, saldo_disponivel)  # Nunca retornar negativo
        
    except Exception as e:
        print(f"❌ Erro ao calcular saldo CRPIV: {e}")
        return 0

def executar_distribuicao_crpiv_para_unidade(unidade_destino, tipo_orcamento, valor):
    """Executa nova distribuição do CRPIV para uma unidade"""
    try:
        print(f"📤 Distribuindo do CRPIV: {unidade_destino} - {tipo_orcamento} - R$ {valor:,.2f}")
        
        # ✅ VALIDAÇÕES
        if valor <= 0:
            return {'sucesso': False, 'erro': 'Valor deve ser maior que zero'}
        
        if unidade_destino == 'CRPIV':
            return {'sucesso': False, 'erro': 'Não é possível distribuir do CRPIV para o próprio CRPIV'}
        
        # ✅ VERIFICAR SALDO DISPONÍVEL DO CRPIV
        saldo_crpiv = calcular_saldo_disponivel_crpiv(tipo_orcamento)
        
        if saldo_crpiv < valor:
            return {'sucesso': False, 'erro': f'CRPIV não possui saldo suficiente. Disponível: R$ {saldo_crpiv:,.2f}'}
        
        # ✅ BUSCAR ORÇAMENTO MAIS RECENTE PARA VINCULAR
        orcamento_recente = Orcamento.query.order_by(Orcamento.data_criacao.desc()).first()
        
        if not orcamento_recente:
            return {'sucesso': False, 'erro': 'Nenhum orçamento encontrado para vincular a distribuição'}
        
        # ✅ CRIAR OU ATUALIZAR DISTRIBUIÇÃO
        distribuicao_existente = Distribuicao.query.filter_by(
            orcamento_id=orcamento_recente.id,
            unidade=unidade_destino,
            tipo_orcamento=tipo_orcamento
        ).first()
        
        if distribuicao_existente:
            valor_anterior = distribuicao_existente.valor
            distribuicao_existente.valor += valor
            distribuicao_existente.data_distribuicao = datetime.utcnow()
            
            print(f"📈 Atualizando distribuição existente:")
            print(f"   De: R$ {valor_anterior:,.2f}")
            print(f"   Para: R$ {distribuicao_existente.valor:,.2f}")
        else:
            nova_distribuicao = Distribuicao(
                orcamento_id=orcamento_recente.id,
                unidade=unidade_destino,
                tipo_orcamento=tipo_orcamento,
                valor=valor,
                data_distribuicao=datetime.utcnow()
            )
            db.session.add(nova_distribuicao)
            
            print(f"✅ Criando nova distribuição: R$ {valor:,.2f}")
        
        # ✅ REGISTRAR LOG
        registrar_movimentacao(
            tipo='nova_distribuicao_crpiv',
            descricao=f'Nova distribuição CRPIV → {unidade_destino} ({tipo_orcamento})',
            unidade_origem='CRPIV',
            unidade_destino=unidade_destino,
            tipo_orcamento=tipo_orcamento,
            valor=valor,
            orcamento_id=orcamento_recente.id
        )
        
        return {'sucesso': True, 'valor_transferido': valor}
        
    except Exception as e:
        print(f"❌ Erro na distribuição CRPIV: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}

def executar_recolhimento_unidade_para_crpiv(unidade_origem, tipo_orcamento, valor):
    """Executa recolhimento de saldo de uma unidade para o CRPIV"""
    try:
        print(f"📥 Recolhendo para CRPIV: {unidade_origem} - {tipo_orcamento} - R$ {valor:,.2f}")
        
        # ✅ VALIDAÇÕES
        if valor <= 0:
            return {'sucesso': False, 'erro': 'Valor deve ser maior que zero'}
        
        if unidade_origem == 'CRPIV':
            return {'sucesso': False, 'erro': 'Não é possível recolher do próprio CRPIV'}
        
        # ✅ BUSCAR DISTRIBUIÇÃO DA UNIDADE ORIGEM
        distribuicao_origem = db.session.query(Distribuicao).filter_by(
            unidade=unidade_origem,
            tipo_orcamento=tipo_orcamento
        ).order_by(Distribuicao.data_distribuicao.desc()).first()
        
        if not distribuicao_origem:
            return {'sucesso': False, 'erro': f'Nenhuma distribuição encontrada para {unidade_origem} - {tipo_orcamento}'}
        
        # ✅ VERIFICAR SALDO DISPONÍVEL
        autorizado_origem = db.session.query(
            db.func.sum(Missao.valor)
        ).filter(
            Missao.fonte_dinheiro == unidade_origem,
            Missao.tipo == tipo_orcamento,
            Missao.status == 'autorizada'
        ).scalar() or 0
        
        saldo_real_origem = distribuicao_origem.valor - autorizado_origem
        
        if saldo_real_origem < valor:
            return {'sucesso': False, 'erro': f'Saldo insuficiente. Disponível: R$ {saldo_real_origem:,.2f}'}
        
        # ✅ REDUZIR DISTRIBUIÇÃO DA UNIDADE
        valor_original = distribuicao_origem.valor
        distribuicao_origem.valor -= valor
        
        print(f"📉 Reduzindo distribuição de {unidade_origem}:")
        print(f"   De: R$ {valor_original:,.2f}")
        print(f"   Para: R$ {distribuicao_origem.valor:,.2f}")
        
        # ✅ CRIAR REGISTRO DE RECOLHIMENTO
        recolhimento = RecolhimentoSaldo(
            orcamento_id=distribuicao_origem.orcamento_id,
            unidade_origem=unidade_origem,
            unidade_destino='CRPIV',
            tipo_orcamento=tipo_orcamento,
            valor_recolhido=valor,
            motivo=f'Recolhimento de saldo não utilizado',
            usuario_responsavel='Sistema'
        )
        db.session.add(recolhimento)
        
        # ✅ REGISTRAR LOG
        registrar_movimentacao(
            tipo='recolhimento',
            descricao=f'Recolhimento {unidade_origem} → CRPIV ({tipo_orcamento})',
            unidade_origem=unidade_origem,
            unidade_destino='CRPIV',
            tipo_orcamento=tipo_orcamento,
            valor=valor,
            orcamento_id=distribuicao_origem.orcamento_id
        )
        
        return {'sucesso': True, 'valor_transferido': valor}
        
    except Exception as e:
        print(f"❌ Erro no recolhimento: {e}")
        import traceback
        traceback.print_exc()
        return {'sucesso': False, 'erro': str(e)}

@app.route('/transferir_saldo', methods=['GET', 'POST'])
def transferir_saldo():
    """Interface para transferir saldo entre unidades - INCLUINDO CRPIV"""
    if request.method == 'POST':
        try:
            unidade_origem = request.form['unidade_origem']
            unidade_destino = request.form['unidade_destino']
            tipo_orcamento = request.form['tipo_orcamento']
            valor = float(request.form['valor'])
            
            print(f"🔄 Solicitação de transferência recebida:")
            print(f"   Origem: {unidade_origem}")
            print(f"   Destino: {unidade_destino}")
            print(f"   Tipo: {tipo_orcamento}")
            print(f"   Valor: R$ {valor:,.2f}")
            
            # ✅ EXECUTAR TRANSFERÊNCIA (agora suporta CRPIV)
            if unidade_origem == 'CRPIV':
                resultado = executar_distribuicao_crpiv_para_unidade(
                    unidade_destino, tipo_orcamento, valor
                )
            elif unidade_destino == 'CRPIV':
                resultado = executar_recolhimento_unidade_para_crpiv(
                    unidade_origem, tipo_orcamento, valor
                )
            else:
                resultado = executar_transferencia_entre_unidades(
                    unidade_origem, unidade_destino, tipo_orcamento, valor
                )
            
            if resultado['sucesso']:
                # Commit da transação
                db.session.commit()
                
                flash(f'✅ Transferência realizada com sucesso! '
                      f'R$ {valor:,.2f} transferidos de {unidade_origem} para {unidade_destino}', 'success')
                
                print(f"✅ Transferência commitada no banco!")
                
            else:
                # Rollback em caso de erro
                db.session.rollback()
                flash(f'❌ Erro na transferência: {resultado["erro"]}', 'error')
                print(f"❌ Transferência falhou: {resultado['erro']}")
            
            return redirect(url_for('transferir_saldo'))
            
        except ValueError as e:
            flash('❌ Valor inválido inserido', 'error')
            return redirect(url_for('transferir_saldo'))
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro geral na transferência: {e}")
            flash(f'❌ Erro ao processar transferência: {str(e)}', 'error')
            return redirect(url_for('transferir_saldo'))
    
    # GET - Mostrar formulário
    try:
        # ✅ BUSCAR SALDOS DISPONÍVEIS POR UNIDADE (INCLUINDO CRPIV)
        saldos_disponiveis = {}
        
        # ✅ INCLUIR TODAS AS UNIDADES (inclusive CRPIV)
        for unidade in UNIDADES:  # AGORA INCLUI CRPIV
            saldos_disponiveis[unidade] = {}
            
            for tipo in TIPOS_ORCAMENTO:
                if unidade == 'CRPIV':
                    # ✅ CÁLCULO ESPECIAL PARA CRPIV
                    saldo_crpiv = calcular_saldo_disponivel_crpiv(tipo)
                    if saldo_crpiv > 0:
                        saldos_disponiveis[unidade][tipo] = {
                            'distribuido': 0,  # CRPIV não recebe distribuições
                            'autorizado': 0,   # CRPIV não autoriza missões
                            'disponivel': saldo_crpiv
                        }
                else:
                    # ✅ CÁLCULO PARA SUBUNIDADES
                    # Total distribuído
                    distribuido = db.session.query(
                        db.func.sum(Distribuicao.valor)
                    ).filter(
                        Distribuicao.unidade == unidade,
                        Distribuicao.tipo_orcamento == tipo
                    ).scalar() or 0
                    
                    # Total autorizado
                    autorizado = db.session.query(
                        db.func.sum(Missao.valor)
                    ).filter(
                        Missao.fonte_dinheiro == unidade,
                        Missao.tipo == tipo,
                        Missao.status == 'autorizada'
                    ).scalar() or 0
                    
                    saldo_disponivel = distribuido - autorizado
                    
                    if saldo_disponivel > 0:
                        saldos_disponiveis[unidade][tipo] = {
                            'distribuido': distribuido,
                            'autorizado': autorizado,
                            'disponivel': saldo_disponivel
                        }
        
        return render_template('transferir_saldo.html',
                             unidades=UNIDADES,  # ✅ AGORA INCLUI CRPIV
                             tipos=TIPOS_ORCAMENTO,
                             saldos_disponiveis=saldos_disponiveis)
                             
    except Exception as e:
        print(f"❌ Erro ao carregar página de transferência: {e}")
        flash('Erro ao carregar dados de saldos', 'error')
        return render_template('transferir_saldo.html',
                             unidades=UNIDADES,
                             tipos=TIPOS_ORCAMENTO,
                             saldos_disponiveis={})

@app.route('/resolver_sem_saldo/<int:missao_id>', methods=['POST'])
def resolver_sem_saldo(missao_id):
    """Resolver situação de saldo insuficiente"""
    try:
        missao = db.session.get(Missao, missao_id)
        if not missao:
            flash('Missão não encontrada', 'error')
            return redirect(url_for('missoes'))
        
        tipo_resolucao = request.form.get('tipo_resolucao')
        
        if tipo_resolucao == 'transferencia':
            # Transferir de outra unidade
            unidade_origem = request.form.get('unidade_origem')
            valor_transferir = float(request.form.get('valor_transferir', 0))
            
            # Executar transferência
            resultado = executar_transferencia_entre_unidades(
                unidade_origem, missao.fonte_dinheiro, missao.tipo, valor_transferir
            )
            
            if resultado['sucesso']:
                # Autorizar missão após transferência
                missao.status = 'autorizada'
                missao.data_autorizacao = datetime.utcnow()
                
                # Registrar resolução
                resolucao = ResolucaoSemSaldo(
                    missao_id=missao.id,
                    tipo_resolucao='transferencia',
                    valor_necessario=valor_transferir,
                    unidade_origem_transferencia=unidade_origem,
                    valor_transferido=valor_transferir,
                    observacoes=f'Transferência de {unidade_origem} para {missao.fonte_dinheiro}'
                )
                db.session.add(resolucao)
                
                registrar_movimentacao(
                    tipo='autorizacao_com_transferencia',
                    descricao=f'Missão autorizada após transferência de {unidade_origem}',
                    unidade_origem=missao.fonte_dinheiro,
                    tipo_orcamento=missao.tipo,
                    valor=missao.valor,
                    missao_id=missao.id
                )
                
                db.session.commit()
                flash(f'✅ Transferência realizada e missão autorizada! '
                      f'R$ {valor_transferir:,.2f} transferidos de {unidade_origem}.', 'success')
                      
            else:
                flash(f'❌ Erro na transferência: {resultado["erro"]}', 'error')
                
        elif tipo_resolucao == 'nova_distribuicao':
            # Solicitar nova distribuição do CRPIV
            valor_solicitar = float(request.form.get('valor_solicitar', 0))
            
            resultado = executar_nova_distribuicao_crpiv(
                missao.fonte_dinheiro, missao.tipo, valor_solicitar
            )
            
            if resultado['sucesso']:
                # Autorizar missão após nova distribuição
                missao.status = 'autorizada'
                missao.data_autorizacao = datetime.utcnow()
                
                # Registrar resolução
                resolucao = ResolucaoSemSaldo(
                    missao_id=missao.id,
                    tipo_resolucao='nova_distribuicao',
                    valor_necessario=valor_solicitar,
                    observacoes=f'Nova distribuição do CRPIV para {missao.fonte_dinheiro}'
                )
                db.session.add(resolucao)
                
                registrar_movimentacao(
                    tipo='autorizacao_com_nova_distribuicao',
                    descricao=f'Missão autorizada após nova distribuição do CRPIV',
                    unidade_origem='CRPIV',
                    unidade_destino=missao.fonte_dinheiro,
                    tipo_orcamento=missao.tipo,
                    valor=valor_solicitar,
                    missao_id=missao.id
                )
                
                db.session.commit()
                flash(f'✅ Nova distribuição realizada e missão autorizada! '
                      f'R$ {valor_solicitar:,.2f} distribuídos do CRPIV.', 'success')
                      
            else:
                flash(f'❌ Erro na nova distribuição: {resultado["erro"]}', 'error')
                
        else:
            flash('Tipo de resolução inválido', 'error')
        
        return redirect(url_for('missoes'))
        
    except Exception as e:
        print(f"❌ Erro ao resolver sem saldo: {e}")
        flash(f'Erro ao resolver situação: {str(e)}', 'error')
        return redirect(url_for('missoes'))

@app.route('/verificar_recolhimento/<int:orcamento_id>')
def verificar_recolhimento(orcamento_id):
    """Debug: Verificar o resultado do recolhimento"""
    try:
        print(f"🔍 VERIFICANDO RESULTADO DO RECOLHIMENTO - Orçamento {orcamento_id}")
        
        # Distribuições atuais
        distribuicoes = Distribuicao.query.filter_by(orcamento_id=orcamento_id).all()
        
        print("📊 DISTRIBUIÇÕES ATUAIS:")
        for dist in distribuicoes:
            print(f"  {dist.unidade} - {dist.tipo_orcamento}: R$ {dist.valor:,.2f}")
        
        # Verificar se CRPIV tem valores
        crpiv_distribuicoes = [d for d in distribuicoes if d.unidade == 'CRPIV']
        
        print("🏛️ DISTRIBUIÇÕES DO CRPIV:")
        total_crpiv = 0
        for dist in crpiv_distribuicoes:
            print(f"  {dist.tipo_orcamento}: R$ {dist.valor:,.2f}")
            total_crpiv += dist.valor
        
        print(f"💰 TOTAL NO CRPIV: R$ {total_crpiv:,.2f}")
        
        # Calcular novos saldos
        saldos_atuais = calcular_saldos_para_recolher_bimestre_corrigido(orcamento_id)
        
        print("📊 SALDOS APÓS RECOLHIMENTO:")
        for unidade, tipos in saldos_atuais.items():
            if tipos:
                print(f"  {unidade}:")
                for tipo, dados in tipos.items():
                    if dados['saldo_disponivel'] > 0:
                        print(f"    {tipo}: R$ {dados['saldo_disponivel']:,.2f}")
        
        return {
            "status": "OK",
            "distribuicoes_totais": len(distribuicoes),
            "distribuicoes_crpiv": len(crpiv_distribuicoes),
            "total_crpiv": total_crpiv,
            "saldos_restantes": saldos_atuais
        }
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return {"erro": str(e)}


def calcular_saldos_para_recolher_bimestre(orcamento_id):
    """Versão corrigida com validações"""
    orcamento = db.session.get(Orcamento, orcamento_id) or abort(404)
    saldos_recolhimento = {}
    
    for unidade in ['7º BPM', '8º BPM', 'CIPO']:
        saldos_recolhimento[unidade] = {}
        
        for tipo in TIPOS_ORCAMENTO:
            # Total distribuído
            distribuido = db.session.query(Distribuicao).filter_by(
                orcamento_id=orcamento_id,
                unidade=unidade,
                tipo_orcamento=tipo
            ).with_entities(db.func.sum(Distribuicao.valor)).scalar() or 0
            
            # ✅ VALIDAÇÃO MELHORADA
            if distribuido <= 0:
                continue  # Pula se não há distribuição
            
            # Total autorizado
            autorizadas_unidade_tipo = db.session.query(Missao).filter(
                Missao.fonte_dinheiro == unidade,
                Missao.tipo == tipo,
                Missao.status == 'autorizada'
            ).with_entities(db.func.sum(Missao.valor)).scalar() or 0
            
            # Total distribuído da unidade
            total_distribuido_unidade = db.session.query(Distribuicao).filter_by(
                orcamento_id=orcamento_id,
                unidade=unidade
            ).with_entities(db.func.sum(Distribuicao.valor)).scalar() or 0
            
            # ✅ VALIDAÇÃO SEGURA
            if total_distribuido_unidade > 0:
                proporcao_tipo = distribuido / total_distribuido_unidade
                autorizado_proporcional = autorizadas_unidade_tipo * proporcao_tipo
            else:
                autorizado_proporcional = 0
            
            # Saldo disponível
            saldo_disponivel = max(0, distribuido - autorizado_proporcional)
            
            if saldo_disponivel > 0:
                saldos_recolhimento[unidade][tipo] = {
                    'distribuido': distribuido,
                    'autorizado': autorizado_proporcional,
                    'saldo_disponivel': saldo_disponivel
                }
    
    return saldos_recolhimento


@app.route('/visualizar_recolhimento/<int:orcamento_id>')
def visualizar_recolhimento(orcamento_id):
    """Visualizar saldos disponíveis para recolhimento - CORRIGIDO"""
    try:
        orcamento = db.session.get(Orcamento, orcamento_id)
        if not orcamento:
            flash('Orçamento não encontrado', 'error')
            return redirect(url_for('saldos_bimestre'))
        
        print(f"🔍 Visualizando recolhimento para orçamento {orcamento_id}")
        
        # Verificar se pode recolher
        pode_recolher = True
        erro = None
        
        # Verificar se bimestre já foi finalizado (se campo existir)
        if hasattr(orcamento, 'status') and getattr(orcamento, 'status') == 'finalizado':
            erro = "Este bimestre já foi finalizado"
            pode_recolher = False
        
        # ✅ CALCULAR SALDOS DETALHADOS
        saldos_detalhados = calcular_saldos_para_recolher_bimestre_corrigido(orcamento_id)
        
        print("💰 Saldos detalhados calculados:")
        for unidade, tipos in saldos_detalhados.items():
            print(f"  {unidade}:")
            for tipo, dados in tipos.items():
                if dados['saldo_disponivel'] > 0:
                    print(f"    {tipo}: R$ {dados['saldo_disponivel']:,.2f}")
        
        # Verificar se tem saldo para recolher
        tem_saldo = any(
            any(dados['saldo_disponivel'] > 0 for dados in tipos.values()) 
            for tipos in saldos_detalhados.values() if tipos
        )
        
        if not tem_saldo:
            erro = "Não há saldos disponíveis para recolher neste bimestre"
            pode_recolher = False
        
        if not pode_recolher:
            flash(erro, 'warning')
            return redirect(url_for('saldos_bimestre'))
        
        # Verificar recolhimentos existentes (se tabela existir)
        recolhimentos_existentes = []
        try:
            # Se você tiver a tabela RecolhimentoSaldo, descomente:
            # recolhimentos_existentes = RecolhimentoSaldo.query.filter_by(orcamento_id=orcamento_id).all()
            pass
        except:
            pass
        
        return render_template('recolher_saldos.html',
                             orcamento=orcamento,
                             saldos_detalhados=saldos_detalhados,  # ✅ NOME CORRETO
                             recolhimentos_existentes=recolhimentos_existentes)
                             
    except Exception as e:
        print(f"❌ Erro em visualizar_recolhimento: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao calcular saldos para recolhimento', 'error')
        return redirect(url_for('saldos_bimestre'))


def calcular_saldos_para_recolher_bimestre_corrigido(orcamento_id):
    """Versão corrigida do cálculo de saldos para recolhimento"""
    try:
        orcamento = db.session.get(Orcamento, orcamento_id)
        if not orcamento:
            return {}
        
        print(f"🔍 Calculando saldos para recolhimento - Orçamento {orcamento_id}")
        
        saldos_detalhados = {}
        
        # Para cada unidade (exceto CRPIV)
        for unidade in ['7º BPM', '8º BPM', 'CIPO']:
            saldos_detalhados[unidade] = {}
            
            for tipo in TIPOS_ORCAMENTO:
                print(f"  Calculando {unidade} - {tipo}")
                
                # Total distribuído para esta unidade/tipo neste bimestre
                distribuido = db.session.query(
                    db.func.sum(Distribuicao.valor)
                ).filter(
                    Distribuicao.orcamento_id == orcamento_id,
                    Distribuicao.unidade == unidade,
                    Distribuicao.tipo_orcamento == tipo
                ).scalar() or 0
                
                print(f"    Distribuído: R$ {distribuido:,.2f}")
                
                # Total autorizado desta unidade/tipo
                autorizado = db.session.query(
                    db.func.sum(Missao.valor)
                ).filter(
                    Missao.fonte_dinheiro == unidade,
                    Missao.tipo == tipo,
                    Missao.status == 'autorizada'
                ).scalar() or 0
                
                print(f"    Autorizado: R$ {autorizado:,.2f}")
                
                # ✅ CÁLCULO SIMPLES E DIRETO
                saldo_disponivel = max(0, distribuido - autorizado)
                
                print(f"    Saldo disponível: R$ {saldo_disponivel:,.2f}")
                
                # Só adicionar se houver saldo ou distribuição
                if distribuido > 0 or autorizado > 0:
                    saldos_detalhados[unidade][tipo] = {
                        'distribuido': distribuido,
                        'autorizado': autorizado,
                        'saldo_disponivel': saldo_disponivel
                    }
        
        return saldos_detalhados
        
    except Exception as e:
        print(f"❌ Erro em calcular_saldos_para_recolher_bimestre_corrigido: {e}")
        import traceback
        traceback.print_exc()
        return {}

@app.route('/confirmar_recolhimento_simples/<int:orcamento_id>', methods=['POST'])

def confirmar_recolhimento_simples(orcamento_id):
    """Executar recolhimento com transferência real de valores - VERSÃO COMPLETA"""    
    try:
        orcamento = db.session.get(Orcamento, orcamento_id)
        if not orcamento:
            flash('Orçamento não encontrado', 'error')
            return redirect(url_for('saldos_bimestre'))
        
        print(f"🔍 Confirmando recolhimento com transferência - Orçamento {orcamento_id}")
        
        # Verificar se bimestre já foi finalizado
        if hasattr(orcamento, 'status') and getattr(orcamento, 'status') == 'finalizado':
            flash('Este bimestre já foi finalizado', 'error')
            return redirect(url_for('saldos_bimestre'))
        
        saldos_detalhados = calcular_saldos_para_recolher_bimestre_corrigido(orcamento_id)
        motivo = request.form.get('motivo', f'Recolhimento automático de saldo final do bimestre {orcamento.bimestre}/{orcamento.ano}')
        
        recolhimentos_realizados = 0
        valor_total_recolhido = 0
        recolhimentos_detalhados = []
        transferencias_realizadas = []
        
        print("📋 Dados do formulário recebidos:")
        for key, value in request.form.items():
            print(f"  {key} = {value}")
        
        # ✅ INICIAR TRANSAÇÃO PARA GARANTIR CONSISTÊNCIA
        from sqlalchemy.exc import SQLAlchemyError
        
        try:
            # Processar recolhimentos selecionados
            for unidade in ['7º BPM', '8º BPM', 'CIPO']:
                for tipo in TIPOS_ORCAMENTO:
                    campo_checkbox = f"recolher_{unidade}_{tipo}"
                    print(f"🔍 Verificando campo: {campo_checkbox}")
                    
                    if request.form.get(campo_checkbox):
                        print(f"✅ Campo marcado: {campo_checkbox}")
                        
                        if unidade in saldos_detalhados and tipo in saldos_detalhados[unidade]:
                            valor_recolher = saldos_detalhados[unidade][tipo]['saldo_disponivel']
                            
                            if valor_recolher > 0:
                                print(f"💰 Processando recolhimento: {unidade} - {tipo} - R$ {valor_recolher:,.2f}")
                                
                                # ✅ PASSO 1: ENCONTRAR E REDUZIR A DISTRIBUIÇÃO
                                distribuicao_existente = Distribuicao.query.filter_by(
                                    orcamento_id=orcamento_id,
                                    unidade=unidade,
                                    tipo_orcamento=tipo
                                ).first()
                                
                                if distribuicao_existente:
                                    valor_original = distribuicao_existente.valor
                                    novo_valor = valor_original - valor_recolher
                                    
                                    print(f"📉 Reduzindo distribuição de {unidade}:")
                                    print(f"   Valor original: R$ {valor_original:,.2f}")
                                    print(f"   Valor recolhido: R$ {valor_recolher:,.2f}")
                                    print(f"   Novo valor: R$ {novo_valor:,.2f}")
                                    
                                    if novo_valor <= 0:
                                        # Se recolheu tudo, remove a distribuição
                                        print(f"🗑️ Removendo distribuição completamente (valor <= 0)")
                                        db.session.delete(distribuicao_existente)
                                    else:
                                        # Se ainda resta algo, atualiza o valor
                                        distribuicao_existente.valor = novo_valor
                                        print(f"📝 Atualizando distribuição para R$ {novo_valor:,.2f}")
                                    
                                    # ✅ PASSO 2: CRIAR NOVA DISTRIBUIÇÃO PARA O CRPIV
                                    # Isso efetivamente "devolve" o valor ao CRPIV
                                    distribuicao_crpiv = Distribuicao(
                                        orcamento_id=orcamento_id,
                                        unidade='CRPIV',
                                        tipo_orcamento=tipo,
                                        valor=valor_recolher
                                    )
                                    db.session.add(distribuicao_crpiv)
                                    
                                    print(f"✅ Criando nova distribuição para CRPIV:")
                                    print(f"   Unidade: CRPIV")
                                    print(f"   Tipo: {tipo}")
                                    print(f"   Valor: R$ {valor_recolher:,.2f}")
                                    
                                    # ✅ PASSO 3: REGISTRAR O RECOLHIMENTO (se tabela existir)
                                    # TODO: Descomente se tiver tabela RecolhimentoSaldo
                                    """
                                    recolhimento = RecolhimentoSaldo(
                                        orcamento_id=orcamento_id,
                                        unidade_origem=unidade,
                                        unidade_destino='CRPIV',
                                        tipo_orcamento=tipo,
                                        valor_recolhido=valor_recolher,
                                        motivo=motivo,
                                        data_recolhimento=datetime.utcnow()
                                    )
                                    db.session.add(recolhimento)
                                    """
                                    
                                    # Registrar para relatório
                                    transferencias_realizadas.append({
                                        'de': unidade,
                                        'para': 'CRPIV',
                                        'tipo': tipo,
                                        'valor': valor_recolher,
                                        'valor_original': valor_original,
                                        'novo_valor': max(0, novo_valor)
                                    })
                                    
                                    recolhimentos_detalhados.append({
                                        'unidade': unidade,
                                        'tipo': tipo,
                                        'valor': valor_recolher,
                                        'motivo': motivo
                                    })
                                    
                                    recolhimentos_realizados += 1
                                    valor_total_recolhido += valor_recolher
                                
                                else:
                                    print(f"⚠️ Distribuição não encontrada para {unidade} - {tipo}")
            
            # ✅ PASSO 4: COMMIT DAS ALTERAÇÕES
            try:
                recolhimento_historico = RecolhimentoSaldo(
                    orcamento_id=orcamento_id,
                    unidade_origem=unidade,
                    unidade_destino='CRPIV',
                    tipo_orcamento=tipo,
                    valor_recolhido=valor_recolher,
                    motivo=motivo,
                    usuario_responsavel='Sistema',  # ou pegar do login
                    data_recolhimento=datetime.utcnow()
                )
                db.session.add(recolhimento_historico)
                print(f"📝 Histórico salvo: {unidade} → CRPIV - R$ {valor_recolher:,.2f}")
            except Exception as e:
                print(f"⚠️ Erro ao salvar histórico: {e}")

            if transferencias_realizadas:
                db.session.commit()
                print(f"✅ TRANSAÇÃO COMMITADA - {len(transferencias_realizadas)} transferências realizadas")
                
                # Log detalhado das transferências
                print("📊 RESUMO DAS TRANSFERÊNCIAS:")
                for transfer in transferencias_realizadas:
                    print(f"  🔄 {transfer['de']} → {transfer['para']}")
                    print(f"     Tipo: {transfer['tipo']}")
                    print(f"     Valor transferido: R$ {transfer['valor']:,.2f}")
                    print(f"     Saldo restante em {transfer['de']}: R$ {transfer['novo_valor']:,.2f}")
                    print(f"     Valor adicionado ao CRPIV: R$ {transfer['valor']:,.2f}")
                    print("-" * 40)
            
            # Finalizar bimestre se solicitado
            if request.form.get('finalizar_bimestre'):
                print("🏁 Finalizando bimestre...")
                # TODO: Implementar lógica de finalização
                # orcamento.status = 'finalizado'
                # orcamento.data_finalizacao = datetime.utcnow()
                # db.session.commit()
            
            # ✅ RESULTADO FINAL
            if recolhimentos_realizados > 0:
                print(f"🎉 RECOLHIMENTO CONCLUÍDO COM SUCESSO!")
                print(f"   Itens processados: {recolhimentos_realizados}")
                print(f"   Valor total recolhido: R$ {valor_total_recolhido:,.2f}")
                print(f"   Transferências realizadas: {len(transferencias_realizadas)}")
                
                flash(f'✅ Recolhimento realizado com sucesso! '
                      f'{recolhimentos_realizados} itens processados. '
                      f'Valor total transferido de volta ao CRPIV: R$ {valor_total_recolhido:,.2f}', 'success')
                
                # Mensagem detalhada sobre as transferências
                for transfer in transferencias_realizadas:
                    flash(f'🔄 {transfer["de"]} → CRPIV: '
                          f'{transfer["tipo"]} - R$ {transfer["valor"]:,.2f}', 'info')
                
            else:
                flash('⚠️ Nenhum item foi selecionado para recolhimento.', 'warning')
            
            return redirect(url_for('saldos_bimestre'))
            
        except SQLAlchemyError as e:
            # Rollback em caso de erro na transação
            db.session.rollback()
            print(f"❌ ERRO NA TRANSAÇÃO - Rollback realizado")
            print(f"   Erro: {str(e)}")
            flash(f'❌ Erro ao processar recolhimento: {str(e)}', 'error')
            return redirect(url_for('visualizar_recolhimento', orcamento_id=orcamento_id))
        
    except Exception as e:
        print(f"❌ Erro geral em confirmar_recolhimento_simples: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        flash(f'❌ Erro ao processar recolhimento: {str(e)}', 'error')
        return redirect(url_for('saldos_bimestre'))

@app.route('/orcamento', methods=['GET', 'POST'])
def orcamento():
    if request.method == 'POST':
        # Converter strings de data para objetos date
        data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date()
        data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date()
        
        # Validar datas
        if data_inicio >= data_fim:
            flash('Data de início deve ser anterior à data de fim', 'error')
            return redirect(request.url)
        
        novo_orcamento = Orcamento(
            bimestre=request.form['bimestre'],
            ano=int(request.form['ano']),
            data_inicio=data_inicio,
            data_fim=data_fim,
            diarias=float(request.form['diarias']),
            derso=float(request.form['derso']),
            diarias_pav=float(request.form['diarias_pav']),
            derso_pav=float(request.form['derso_pav'])
        )
        
        db.session.add(novo_orcamento)
        db.session.commit()
        registrar_movimentacao(
            tipo='orcamento_criado',
            descricao=f'Orçamento criado: {novo_orcamento.bimestre}/{novo_orcamento.ano}',
            valor=sum([novo_orcamento.diarias, novo_orcamento.derso, 
                      novo_orcamento.diarias_pav, novo_orcamento.derso_pav]),
            orcamento_id=novo_orcamento.id
        )
        
        flash('Orçamento cadastrado com sucesso!', 'success')
        return redirect(url_for('orcamento'))
    
    orcamentos = Orcamento.query.order_by(Orcamento.data_criacao.desc()).all()
    return render_template('orcamento.html', orcamentos=orcamentos, bimestres=BIMESTRES)


@app.route('/historico_recolhimentos')
def historico_recolhimentos():
    """Visualizar histórico de recolhimentos - ERRO CORRIGIDO"""
    try:
        print("🔍 Carregando histórico de recolhimentos...")
        
        # ✅ OPÇÃO 1: Se você tem tabela RecolhimentoSaldo
        recolhimentos = []
        try:
            # Descomente se tiver a tabela criada:
            """
            recolhimentos = db.session.query(RecolhimentoSaldo).join(Orcamento).order_by(
                RecolhimentoSaldo.data_recolhimento.desc()
            ).all()
            """
            pass
        except Exception as e:
            print(f"⚠️ Tabela RecolhimentoSaldo não existe ainda: {e}")
        
        # ✅ OPÇÃO 2: Simular dados baseados nas distribuições do CRPIV - CORRIGIDA
        if not recolhimentos:
            print("📊 Criando histórico simulado baseado em distribuições do CRPIV...")
            
            # ✅ CORREÇÃO: Usar JOIN ou buscar orçamento separadamente
            distribuicoes_crpiv = db.session.query(Distribuicao).filter(
                Distribuicao.unidade == 'CRPIV'
            ).order_by(Distribuicao.data_distribuicao.desc()).all()
            
            print(f"📋 Encontradas {len(distribuicoes_crpiv)} distribuições do CRPIV")
            
            # Criar objetos simulados para o template
            recolhimentos_simulados = []
            for dist in distribuicoes_crpiv:
                # ✅ BUSCAR ORÇAMENTO USANDO O ID
                orcamento = db.session.get(Orcamento, dist.orcamento_id)
                
                if orcamento:  # Só processar se orçamento existir
                    # Simular um objeto recolhimento
                    class RecolhimentoSimulado:
                        def __init__(self, distribuicao, orcamento_obj):
                            self.data_recolhimento = distribuicao.data_distribuicao
                            self.orcamento = orcamento_obj  # ✅ USAR OBJETO BUSCADO
                            self.unidade_origem = "Subunidade"  # Simulado (não sabemos qual)
                            self.tipo_orcamento = distribuicao.tipo_orcamento  
                            self.valor_recolhido = distribuicao.valor
                            self.motivo = f"Recolhimento de saldo não utilizado do {orcamento_obj.bimestre}/{orcamento_obj.ano}"
                            self.usuario_responsavel = "Sistema"
                    
                    recolhimento_obj = RecolhimentoSimulado(dist, orcamento)
                    recolhimentos_simulados.append(recolhimento_obj)
                    
                    print(f"✅ Recolhimento simulado: {orcamento.bimestre}/{orcamento.ano} - {dist.tipo_orcamento} - R$ {dist.valor:,.2f}")
                else:
                    print(f"⚠️ Orçamento ID {dist.orcamento_id} não encontrado para distribuição")
            
            recolhimentos = recolhimentos_simulados
            print(f"✅ {len(recolhimentos)} recolhimentos simulados criados")
        
        print(f"📋 Total de recolhimentos para exibir: {len(recolhimentos)}")
        
        return render_template('historico_recolhimentos.html', 
                             recolhimentos=recolhimentos)
                             
    except Exception as e:
        print(f"❌ Erro em historico_recolhimentos: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar histórico de recolhimentos', 'error')
        return render_template('historico_recolhimentos.html', 
                             recolhimentos=[])

# Atualizar a função de cálculo de saldos por bimestre
def calcular_saldo_por_bimestre():
    """Calcula saldos por bimestre - FÓRMULA CORRIGIDA"""
    try:
        print("🔍 Calculando saldos por bimestre...")
        
        orcamentos = Orcamento.query.order_by(Orcamento.data_criacao.desc()).all()
        saldos_lista = []
        
        for orcamento in orcamentos:
            print(f"📊 Processando {orcamento.bimestre}/{orcamento.ano}")
            
            # ✅ 1. TOTAL DISPONIBILIZADO (Cota + Complementações)
            total_base = sum([
                orcamento.diarias or 0,
                orcamento.derso or 0, 
                orcamento.diarias_pav or 0,
                orcamento.derso_pav or 0
            ])
            
            # Somar complementações deste orçamento
            complementacoes = ComplementacaoOrcamento.query.filter_by(orcamento_id=orcamento.id).all()
            total_complementacoes = sum([comp.valor for comp in complementacoes])
            
            total_disponibilizado = total_base + total_complementacoes
            
            # ✅ 2. TOTAL DISTRIBUÍDO (para subunidades)
            total_distribuido = db.session.query(
                db.func.sum(Distribuicao.valor)
            ).filter(
                Distribuicao.orcamento_id == orcamento.id,
                Distribuicao.unidade != 'CRPIV'  # Excluir distribuições para CRPIV
            ).scalar() or 0
            
            # ✅ 3. TOTAL AUTORIZADO (todas as missões autorizadas deste bimestre)
            # Considerando que missões são vinculadas ao bimestre pelo período ou data
            total_autorizado = db.session.query(
                db.func.sum(Missao.valor)
            ).filter(
                Missao.status == 'autorizada'
                # ✅ AQUI você pode adicionar filtro por período se tiver
                # Por exemplo: Missao.data_autorizacao entre data_inicio e data_fim do bimestre
            ).scalar() or 0
            
            # ✅ 4. SALDO CORRETO = Disponibilizado - Autorizado
            # NÃO consideramos distribuições, apenas o que foi realmente gasto
            saldo = total_disponibilizado - total_autorizado
            
            # Verificar se pode recolher (tem distribuições não utilizadas)
            pode_recolher = total_distribuido > total_autorizado
            
            # Total recolhido (se implementado)
            total_recolhido = 0
            if hasattr(orcamento, 'recolhimentos'):
                total_recolhido = sum([r.valor_recolhido for r in orcamento.recolhimentos])
            
            print(f"  📈 Disponibilizado: R$ {total_disponibilizado:,.2f}")
            print(f"  📤 Distribuído: R$ {total_distribuido:,.2f}")
            print(f"  ✅ Autorizado: R$ {total_autorizado:,.2f}")
            print(f"  💰 Saldo: R$ {saldo:,.2f}")
            
            saldos_lista.append({
                'orcamento': orcamento,
                'complementacoes': complementacoes,
                'total_disponibilizado': total_disponibilizado,
                'total_distribuido': total_distribuido,
                'total_autorizado': total_autorizado,
                'saldo': saldo,  # ✅ FÓRMULA CORRIGIDA
                'pode_recolher': pode_recolher,
                'total_recolhido': total_recolhido
            })
        
        print(f"✅ Calculados saldos para {len(saldos_lista)} bimestres")
        return saldos_lista
        
    except Exception as e:
        print(f"❌ Erro ao calcular saldos por bimestre: {e}")
        import traceback
        traceback.print_exc()
        return []


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def validar_dados_missao(row, linha_num):
    """Valida uma linha de dados da importação - VERSÃO CORRIGIDA"""
    erros = []
    
    # Campos obrigatórios
    campos_obrigatorios = ['fonte_dinheiro', 'opm_destino', 'processo_sei', 
                          'descricao', 'periodo', 'mes', 'tipo', 'valor']
    
    for campo in campos_obrigatorios:
        valor_campo = str(row.get(campo, '')).strip()
        if pd.isna(row.get(campo)) or valor_campo == '' or valor_campo == '*********':
            # Permitir processo_sei vazio ou com asteriscos
            if campo == 'processo_sei' and valor_campo == '*********':
                continue
            erros.append(f"Linha {linha_num}: Campo '{campo}' é obrigatório")
    
    # Validar unidades
    if row.get('fonte_dinheiro') not in UNIDADES:
        erros.append(f"Linha {linha_num}: Fonte '{row.get('fonte_dinheiro')}' inválida. Use: {', '.join(UNIDADES)}")
    
    if row.get('opm_destino') not in UNIDADES:
        erros.append(f"Linha {linha_num}: OPM destino '{row.get('opm_destino')}' inválida. Use: {', '.join(UNIDADES)}")
    
    # Validar tipo de orçamento
    if row.get('tipo') not in TIPOS_ORCAMENTO:
        erros.append(f"Linha {linha_num}: Tipo '{row.get('tipo')}' inválido. Use: {', '.join(TIPOS_ORCAMENTO)}")
    
    # Validar mês
    if row.get('mes') not in MESES:
        erros.append(f"Linha {linha_num}: Mês '{row.get('mes')}' inválido. Use: {', '.join(MESES)}")
    
    # Validar valor - MELHORADO para aceitar vírgula
    try:
        valor_str = str(row.get('valor', '')).strip()
        # Aceitar vírgula e ponto, remover espaços
        valor_str = valor_str.replace(',', '.').replace(' ', '')
        valor = float(valor_str)
        if valor <= 0:
            erros.append(f"Linha {linha_num}: Valor deve ser maior que zero")
    except (ValueError, TypeError):
        erros.append(f"Linha {linha_num}: Valor '{row.get('valor')}' deve ser um número válido")
    
    # Validar status se fornecido
    if row.get('status') and row.get('status') not in ['previsao', 'autorizada']:
        erros.append(f"Linha {linha_num}: Status deve ser 'previsao' ou 'autorizada'")
    
    return erros

@app.route('/importar_missoes', methods=['GET', 'POST'])
def importar_missoes():
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        arquivo = request.files['arquivo']
        
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(request.url)
        
        if arquivo and allowed_file(arquivo.filename):
            try:
                # Ler arquivo CSV
                df = pd.read_csv(arquivo, encoding='utf-8', sep='\t')  # Usar TAB como separador
                
                # Se não funcionar com TAB, tentar outros
                if len(df.columns) == 1:
                    arquivo.seek(0)
                    df = pd.read_csv(arquivo, encoding='utf-8', sep=';')
                
                if len(df.columns) == 1:
                    arquivo.seek(0)
                    df = pd.read_csv(arquivo, encoding='utf-8', sep=',')
                
                # Limpar nomes das colunas
                df.columns = df.columns.str.strip()
                
                # Log para debug
                print("Colunas encontradas:", list(df.columns))
                print("Primeiras linhas:", df.head())
                
                # Verificar colunas obrigatórias
                colunas_esperadas = ['fonte_dinheiro', 'opm_destino', 'processo_sei', 
                                   'descricao', 'periodo', 'mes', 'tipo', 'valor']
                
                colunas_faltantes = [col for col in colunas_esperadas if col not in df.columns]
                if colunas_faltantes:
                    flash(f'Colunas obrigatórias faltando: {", ".join(colunas_faltantes)}', 'error')
                    flash(f'Colunas encontradas: {", ".join(df.columns)}', 'info')
                    return redirect(request.url)
                
                # Processar dados
                erros_validacao = []
                missoes_validas = []
                
                for index, row in df.iterrows():
                    linha_num = index + 2
                    
                    # Pular linhas vazias
                    if pd.isna(row['fonte_dinheiro']) or str(row['fonte_dinheiro']).strip() == '':
                        continue
                    
                    erros_linha = validar_dados_missao(row, linha_num)
                    erros_validacao.extend(erros_linha)
                    
                    if not erros_linha:
                        # Limpar e converter dados
                        valor_str = str(row['valor']).strip().replace(',', '.').replace(' ', '')
                        valor = float(valor_str)
                        status = str(row.get('status', 'previsao')).strip().lower()
                        
                        # Tratar processo SEI especial
                        processo_sei = str(row['processo_sei']).strip()
                        if processo_sei == '*********':
                            processo_sei = f"TEMP-{datetime.now().strftime('%Y%m%d')}-{index}"
                        
                        # Tratar número de autorização
                        num_auth = str(row.get('numero_autorizacao', '')).strip()
                        if num_auth == '0':
                            num_auth = ''
                        
                        missao_data = {
                            'fonte_dinheiro': str(row['fonte_dinheiro']).strip(),
                            'opm_destino': str(row['opm_destino']).strip(),
                            'processo_sei': processo_sei,
                            'descricao': str(row['descricao']).strip(),
                            'periodo': str(row['periodo']).strip(),
                            'mes': str(row['mes']).strip(),
                            'tipo': str(row['tipo']).strip(),
                            'valor': valor,
                            'numero_autorizacao': num_auth,
                            'status': status if status in ['previsao', 'autorizada'] else 'previsao'
                        }
                        missoes_validas.append(missao_data)
                
                # Mostrar erros se houver
                if erros_validacao:
                    flash(f'Encontrados {len(erros_validacao)} erros:', 'error')
                    for erro in erros_validacao[:10]:
                        flash(erro, 'error')
                    if len(erros_validacao) > 10:
                        flash(f'... e mais {len(erros_validacao) - 10} erros', 'error')
                    
                    # Mostrar quantas missões seriam importadas mesmo com erros
                    flash(f'Missões válidas encontradas: {len(missoes_validas)}', 'info')
                    return redirect(request.url)
                
                # Importar missões válidas
                missoes_importadas = 0
                for missao_data in missoes_validas:
                    nova_missao = Missao(**missao_data)
                    
                    if nova_missao.status == 'autorizada':
                        nova_missao.data_autorizacao = datetime.utcnow()
                    
                    db.session.add(nova_missao)
                    missoes_importadas += 1
                
                db.session.commit()
                flash(f'Sucesso! {missoes_importadas} missões importadas.', 'success')
                return redirect(url_for('missoes'))
                
            except Exception as e:
                flash(f'Erro ao processar arquivo: {str(e)}', 'error')
                print(f"Erro detalhado: {e}")
                import traceback
                traceback.print_exc()
        else:
            flash('Tipo de arquivo não permitido. Use apenas .csv', 'error')
    
    return render_template('importar_missoes.html', 
                         unidades=UNIDADES,
                         tipos=TIPOS_ORCAMENTO,
                         meses=MESES)


@app.route('/download_modelo_csv')
def download_modelo_csv():
    """Gera um arquivo CSV modelo para importação"""
    dados_exemplo = [
        {
            'fonte_dinheiro': 'CRPIV',
            'opm_destino': '7º BPM',
            'processo_sei': '23.000.001/2024-01',
            'descricao': 'Operação exemplo - Patrulhamento rural',
            'periodo': '01/01/2024 a 05/01/2024',
            'mes': 'Janeiro',
            'tipo': 'DIÁRIAS',
            'valor': '1500.00',
            'numero_autorizacao': 'AUT-001/2024',
            'status': 'previsao'
        },
        {
            'fonte_dinheiro': '7º BPM',
            'opm_destino': '8º BPM',
            'processo_sei': '23.000.002/2024-01',
            'descricao': 'Apoio operacional - Eventos especiais',
            'periodo': '10/01/2024 a 15/01/2024',
            'mes': 'Janeiro',
            'tipo': 'DERSO',
            'valor': '2000.50',
            'numero_autorizacao': '',
            'status': 'autorizada'
        }
    ]
    
    # Criar DataFrame
    df = pd.DataFrame(dados_exemplo)
    
    # Criar arquivo CSV em memória
    output = io.StringIO()
    df.to_csv(output, index=False, sep=';', encoding='utf-8')
    output.seek(0)
    
    # Retornar arquivo para download
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=modelo_importacao_missoes.csv'}
    )

# Adicionar import do Response no topo do arquivo
from flask import Response


db.init_app(app)

UNIDADES = ['CRPIV', '7º BPM', '8º BPM', 'CIPO']
TIPOS_ORCAMENTO = ['DIÁRIAS', 'DERSO', 'DIÁRIAS PAV', 'DERSO PAV']
BIMESTRES = ['1º Bimestre', '2º Bimestre', '3º Bimestre', '4º Bimestre', '5º Bimestre', '6º Bimestre']
MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

@app.template_filter('currency')
def currency_filter(value):
    if value is None:
        return "0,00"
    try:
        return f"{float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "0,00"


def create_tables():
    with app.app_context():
        db.create_all()


def calcular_saldos_para_distribuir():
    """Calcula quanto ainda pode ser distribuído pelo CRPIV - VERSÃO CORRIGIDA"""
    try:
        # Orçamento total de todos os bimestres (Cota + Complementações)
        totais_geral = calcular_orcamento_total_todos_bimestres()
        
        # ✅ CORREÇÃO: Total já distribuído APENAS PARA SUBUNIDADES
        distribuido_por_tipo = {
            'DIÁRIAS': 0,
            'DERSO': 0,
            'DIÁRIAS PAV': 0,
            'DERSO PAV': 0
        }
        
        # Somar apenas distribuições para subunidades (excluindo CRPIV)
        distribuicoes_agregadas = db.session.query(
            Distribuicao.tipo_orcamento,
            db.func.sum(Distribuicao.valor).label('total')
        ).filter(
            Distribuicao.unidade != 'CRPIV'  # ✅ EXCLUIR CRPIV
        ).group_by(Distribuicao.tipo_orcamento).all()
        
        for tipo, total in distribuicoes_agregadas:
            if tipo in distribuido_por_tipo:
                distribuido_por_tipo[tipo] = total or 0
        
        print("💰 Cálculo de saldos para distribuir (CORRIGIDO):")
        print("📊 Total geral disponível (Cota + Complementações):")
        for tipo, valor in totais_geral.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        print("📤 Total distribuído para subunidades:")
        for tipo, valor in distribuido_por_tipo.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        # Calcular saldos disponíveis para distribuir
        saldos_para_distribuir = {
            'diarias': max(0, totais_geral['diarias'] - distribuido_por_tipo['DIÁRIAS']),
            'derso': max(0, totais_geral['derso'] - distribuido_por_tipo['DERSO']),
            'diarias_pav': max(0, totais_geral['diarias_pav'] - distribuido_por_tipo['DIÁRIAS PAV']),
            'derso_pav': max(0, totais_geral['derso_pav'] - distribuido_por_tipo['DERSO PAV'])
        }
        
        print("✅ Saldos disponíveis para nova distribuição:")
        for tipo, valor in saldos_para_distribuir.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        return saldos_para_distribuir
        
    except Exception as e:
        print(f"❌ Erro em calcular_saldos_para_distribuir: {e}")
        return {'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0}


def calcular_orcamento_total_todos_bimestres():
    """Calcula o orçamento total de TODOS os bimestres incluindo complementações - CORRIGIDO"""
    try:
        # ✅ CORREÇÃO: Usar agregação no banco
        orcamentos_totais = db.session.query(
            db.func.sum(Orcamento.diarias).label('diarias'),
            db.func.sum(Orcamento.derso).label('derso'),
            db.func.sum(Orcamento.diarias_pav).label('diarias_pav'),
            db.func.sum(Orcamento.derso_pav).label('derso_pav')
        ).first()
        
        totais = {
            'diarias': orcamentos_totais.diarias or 0,
            'derso': orcamentos_totais.derso or 0,
            'diarias_pav': orcamentos_totais.diarias_pav or 0,
            'derso_pav': orcamentos_totais.derso_pav or 0
        }
        
        # ✅ CORREÇÃO: Somar complementações usando agregação
        complementacoes_agregadas = db.session.query(
            ComplementacaoOrcamento.tipo_orcamento,
            db.func.sum(ComplementacaoOrcamento.valor).label('total')
        ).group_by(ComplementacaoOrcamento.tipo_orcamento).all()
        
        for tipo, total in complementacoes_agregadas:
            if tipo == 'DIÁRIAS':
                totais['diarias'] += total or 0
            elif tipo == 'DERSO':
                totais['derso'] += total or 0
            elif tipo == 'DIÁRIAS PAV':
                totais['diarias_pav'] += total or 0
            elif tipo == 'DERSO PAV':
                totais['derso_pav'] += total or 0
        
        return totais
        
    except Exception as e:
        print(f"❌ Erro em calcular_orcamento_total_todos_bimestres: {e}")
        return {'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0}


def calcular_saldo_por_bimestre():
    """Calcula saldos por bimestre - FLUXO CORRETO DO CRPIV"""
    try:
        print("🔍 Calculando saldos por bimestre...")
        
        orcamentos = Orcamento.query.order_by(Orcamento.data_criacao.desc()).all()
        saldos_lista = []
        
        for orcamento in orcamentos:
            print(f"📊 Processando {orcamento.bimestre}/{orcamento.ano}")
            
            # ✅ 1. TOTAL DISPONIBILIZADO (Cota + Complementações para CRPIV)
            total_base = sum([
                orcamento.diarias or 0,
                orcamento.derso or 0, 
                orcamento.diarias_pav or 0,
                orcamento.derso_pav or 0
            ])
            
            # Complementações para este orçamento
            complementacoes = ComplementacaoOrcamento.query.filter_by(orcamento_id=orcamento.id).all()
            total_complementacoes = sum([comp.valor for comp in complementacoes])
            
            total_disponibilizado = total_base + total_complementacoes
            
            # ✅ 2. TOTAL DISTRIBUÍDO (apenas para subunidades, NÃO conta CRPIV)
            total_distribuido = db.session.query(
                db.func.sum(Distribuicao.valor)
            ).filter(
                Distribuicao.orcamento_id == orcamento.id,
                Distribuicao.unidade != 'CRPIV'  # ✅ EXCLUIR CRPIV
            ).scalar() or 0
            
            # ✅ 3. TOTAL AUTORIZADO (todas as missões autorizadas, independente da fonte)
            # Isso inclui missões pagas pelo CRPIV e pelas subunidades
            total_autorizado = db.session.query(
                db.func.sum(Missao.valor)
            ).filter(
                Missao.status == 'autorizada'
                # ✅ Aqui você pode filtrar por período do bimestre se necessário
            ).scalar() or 0
            
            # ✅ 4. SALDO CORRETO = Total Disponibilizado - Total Autorizado
            # Representa quanto ainda resta do orçamento original
            saldo = total_disponibilizado - total_autorizado
            
            # ✅ 5. SALDO CRPIV (não distribuído) = Disponibilizado - Distribuído
            saldo_crpiv_disponivel = total_disponibilizado - total_distribuido
            
            # ✅ 6. SALDO SUBUNIDADES = Distribuído - Autorizado por subunidades
            autorizado_subunidades = db.session.query(
                db.func.sum(Missao.valor)
            ).filter(
                Missao.status == 'autorizada',
                Missao.fonte_dinheiro != 'CRPIV'  # Apenas subunidades
            ).scalar() or 0
            
            autorizado_crpiv = db.session.query(
                db.func.sum(Missao.valor)
            ).filter(
                Missao.status == 'autorizada',
                Missao.fonte_dinheiro == 'CRPIV'  # Apenas CRPIV
            ).scalar() or 0
            
            saldo_subunidades = total_distribuido - autorizado_subunidades
            
            print(f"  💰 Total Disponibilizado (Cota + Complementações): R$ {total_disponibilizado:,.2f}")
            print(f"  📤 Distribuído para Subunidades: R$ {total_distribuido:,.2f}")
            print(f"  🏛️  Saldo CRPIV (não distribuído): R$ {saldo_crpiv_disponivel:,.2f}")
            print(f"  ✅ Total Autorizado (TODAS as missões): R$ {total_autorizado:,.2f}")
            print(f"     - Autorizado por CRPIV: R$ {autorizado_crpiv:,.2f}")
            print(f"     - Autorizado por Subunidades: R$ {autorizado_subunidades:,.2f}")
            print(f"  💸 Saldo Subunidades: R$ {saldo_subunidades:,.2f}")
            print(f"  📊 SALDO FINAL: R$ {saldo:,.2f}")
            
            saldos_lista.append({
                'orcamento': orcamento,
                'complementacoes': complementacoes,
                'total_disponibilizado': total_disponibilizado,
                'total_distribuido': total_distribuido,
                'total_autorizado': total_autorizado,
                'autorizado_crpiv': autorizado_crpiv,
                'autorizado_subunidades': autorizado_subunidades,
                'saldo_crpiv_disponivel': saldo_crpiv_disponivel,
                'saldo_subunidades': saldo_subunidades,
                'saldo': saldo,  # ✅ SALDO CORRETO
                'pode_recolher': saldo_subunidades > 0,
                'total_recolhido': 0
            })
        
        return saldos_lista
        
    except Exception as e:
        print(f"❌ Erro ao calcular saldos por bimestre: {e}")
        import traceback
        traceback.print_exc()
        return []

def calcular_orcamento_total_com_complementacao(orcamento):
    """Calcula o orçamento DISPONÍVEL de um bimestre (considerando distribuições já feitas)"""
    if not orcamento:
        return {'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0}
    
    try:
        print(f"🔍 Calculando saldo disponível para orçamento {orcamento.bimestre}/{orcamento.ano}")
        
        # ✅ PASSO 1: Total base + complementações
        totais_base = {
            'diarias': float(orcamento.diarias or 0),
            'derso': float(orcamento.derso or 0),
            'diarias_pav': float(orcamento.diarias_pav or 0),
            'derso_pav': float(orcamento.derso_pav or 0)
        }
        
        print(f"📊 Orçamento base:")
        for tipo, valor in totais_base.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        # Somar complementações
        complementacoes_agregadas = db.session.query(
            ComplementacaoOrcamento.tipo_orcamento,
            db.func.sum(ComplementacaoOrcamento.valor).label('total')
        ).filter(ComplementacaoOrcamento.orcamento_id == orcamento.id).group_by(
            ComplementacaoOrcamento.tipo_orcamento
        ).all()
        
        for tipo, total in complementacoes_agregadas:
            if tipo == 'DIÁRIAS':
                totais_base['diarias'] += total or 0
            elif tipo == 'DERSO':
                totais_base['derso'] += total or 0
            elif tipo == 'DIÁRIAS PAV':
                totais_base['diarias_pav'] += total or 0
            elif tipo == 'DERSO PAV':
                totais_base['derso_pav'] += total or 0
        
        print(f"📈 Após complementações:")
        for tipo, valor in totais_base.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        # ✅ PASSO 2: Subtrair distribuições já feitas PARA SUBUNIDADES
        distribuicoes_agregadas = db.session.query(
            Distribuicao.tipo_orcamento,
            db.func.sum(Distribuicao.valor).label('total')
        ).filter(
            Distribuicao.orcamento_id == orcamento.id,
            Distribuicao.unidade != 'CRPIV'  # ✅ EXCLUIR CRPIV (recolhimentos)
        ).group_by(Distribuicao.tipo_orcamento).all()
        
        # Calcular saldos disponíveis
        saldos_disponiveis = totais_base.copy()
        
        for tipo, total_distribuido in distribuicoes_agregadas:
            if tipo == 'DIÁRIAS':
                saldos_disponiveis['diarias'] -= total_distribuido or 0
            elif tipo == 'DERSO':
                saldos_disponiveis['derso'] -= total_distribuido or 0
            elif tipo == 'DIÁRIAS PAV':
                saldos_disponiveis['diarias_pav'] -= total_distribuido or 0
            elif tipo == 'DERSO PAV':
                saldos_disponiveis['derso_pav'] -= total_distribuido or 0
        
        print(f"📤 Após subtrair distribuições:")
        for tipo, valor in saldos_disponiveis.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        # ✅ Garantir que não há valores negativos
        for tipo in saldos_disponiveis:
            saldos_disponiveis[tipo] = max(0, saldos_disponiveis[tipo])
        
        print(f"✅ Saldos disponíveis finais:")
        for tipo, valor in saldos_disponiveis.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        return saldos_disponiveis
        
    except Exception as e:
        print(f"❌ Erro em calcular_orcamento_total_com_complementacao: {e}")
        import traceback
        traceback.print_exc()
        return {'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0}



@app.route('/')
def index():
    try:
        # Calcular orçamento total de todos os bimestres
        totais_geral = calcular_orcamento_total_todos_bimestres()
        total_disponibilizado = sum(totais_geral.values())
        
        # Calcular saldos disponíveis para distribuir
        saldos_para_distribuir = calcular_saldos_para_distribuir()
        total_para_distribuir = sum(saldos_para_distribuir.values())
        
        # Total de missões
        total_previsoes = db.session.query(
            db.func.sum(Missao.valor)
        ).filter(Missao.status == 'previsao').scalar() or 0
        
        total_autorizadas = db.session.query(
            db.func.sum(Missao.valor)
        ).filter(Missao.status == 'autorizada').scalar() or 0
        
        disponivel = max(0, total_disponibilizado - total_autorizadas)
        
        # ✅ NOVO: Calcular saldos detalhados por unidade e tipo
        saldos_unidades_detalhados = calcular_saldos_unidades_por_tipo()
        
        # Calcular saldos totais por unidade (para compatibilidade)
        saldos_unidades = {}
        distribuicoes_unidades = {}
        
        for unidade in UNIDADES[1:]:  # Excluir CRPIV
            total_unidade = 0
            distribuido_unidade = 0
            
            if unidade in saldos_unidades_detalhados:
                for tipo_data in saldos_unidades_detalhados[unidade].values():
                    total_unidade += tipo_data['saldo']
                    distribuido_unidade += tipo_data['distribuido']
            
            saldos_unidades[unidade] = total_unidade
            distribuicoes_unidades[unidade] = distribuido_unidade
        
        # Calcular saldos por bimestre
        saldos_bimestre = calcular_saldo_por_bimestre()
        
        # Logs para debug
        print("📊 DASHBOARD - Resumo dos cálculos:")
        print(f"💰 Total disponibilizado (Cota + Complementações): R$ {total_disponibilizado:,.2f}")
        print(f"📤 Total distribuído para subunidades: R$ {sum(distribuicoes_unidades.values()):,.2f}")
        print(f"✅ Total autorizado: R$ {total_autorizadas:,.2f}")
        print(f"📊 Disponível restante: R$ {disponivel:,.2f}")
        print(f"🔄 Total para distribuir (CRPIV): R$ {total_para_distribuir:,.2f}")
        
        dashboard_data = {
            'total_disponibilizado': total_disponibilizado,
            'total_previsoes': total_previsoes,
            'total_autorizadas': total_autorizadas,
            'disponivel': disponivel,
            'distribuicoes_unidades': distribuicoes_unidades
        }
        # Saldo não distribuído do CRPIV - pode ser usado pelo CRPIV ou redistribuído
        saldo_crpiv = sum([saldos_para_distribuir.get(k, 0) for k in ['diarias', 'derso', 'diarias_pav', 'derso_pav']])
        dashboard_data['saldo_crpiv'] = saldo_crpiv
        dashboard_data['saldo_crpiv_detalhado'] = {
            'diarias': saldos_para_distribuir.get('diarias', 0),
            'derso': saldos_para_distribuir.get('derso', 0),
            'diarias_pav': saldos_para_distribuir.get('diarias_pav', 0),
            'derso_pav': saldos_para_distribuir.get('derso_pav', 0),
        }


        dashboard_data['saldo_crpiv'] = saldo_crpiv
        dashboard_data['saldo_crpiv_detalhado'] = {
            'diarias': saldos_para_distribuir.get('diarias', 0),
            'derso': saldos_para_distribuir.get('derso', 0),
            'diarias_pav': saldos_para_distribuir.get('diarias_pav', 0),
            'derso_pav': saldos_para_distribuir.get('derso_pav', 0)
        }
        
        return render_template('index.html', 
                             totais_geral=totais_geral,
                             saldos_para_distribuir=saldos_para_distribuir,
                             total_para_distribuir=total_para_distribuir,
                             dashboard_data=dashboard_data,
                             saldos_unidades=saldos_unidades,
                             saldos_unidades_detalhados=saldos_unidades_detalhados,  # ✅ NOVO
                             saldos_bimestre=saldos_bimestre)
                             
    except Exception as e:
        print(f"❌ Erro na rota index: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar dados do dashboard', 'error')
        return render_template('index.html', 
                             totais_geral={'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0},
                             saldos_para_distribuir={'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0},
                             total_para_distribuir=0,
                             dashboard_data={},
                             saldos_unidades={},
                             saldos_unidades_detalhados={},  # ✅ NOVO
                             saldos_bimestre=[])


def calcular_saldos_unidades_por_tipo():
    """Calcula saldos detalhados por unidade e tipo orçamentário"""
    try:
        print("🔍 Calculando saldos detalhados por unidade e tipo...")
        
        saldos_detalhados = {}
        
        # Para cada unidade (exceto CRPIV)
        for unidade in UNIDADES[1:]:
            saldos_detalhados[unidade] = {}
            
            # Para cada tipo orçamentário
            for tipo in TIPOS_ORCAMENTO:
                print(f"  Calculando {unidade} - {tipo}")
                
                # Total distribuído para esta unidade/tipo
                distribuido = db.session.query(
                    db.func.sum(Distribuicao.valor)
                ).filter(
                    Distribuicao.unidade == unidade,
                    Distribuicao.tipo_orcamento == tipo
                ).scalar() or 0
                
                # Total autorizado para esta unidade/tipo
                autorizado = db.session.query(
                    db.func.sum(Missao.valor)
                ).filter(
                    Missao.fonte_dinheiro == unidade,
                    Missao.tipo == tipo,
                    Missao.status == 'autorizada'
                ).scalar() or 0
                
                # Saldo = Distribuído - Autorizado
                saldo = distribuido - autorizado
                
                print(f"    Distribuído: R$ {distribuido:,.2f}")
                print(f"    Autorizado: R$ {autorizado:,.2f}")
                print(f"    Saldo: R$ {saldo:,.2f}")
                
                # Armazenar dados detalhados
                saldos_detalhados[unidade][tipo] = {
                    'distribuido': distribuido,
                    'autorizado': autorizado,
                    'saldo': saldo
                }
        
        print(f"✅ Saldos detalhados calculados para {len(saldos_detalhados)} unidades")
        return saldos_detalhados
        
    except Exception as e:
        print(f"❌ Erro em calcular_saldos_unidades_por_tipo: {e}")
        import traceback
        traceback.print_exc()
        return {}

@app.route('/exportar_missoes_pdf')
def exportar_missoes_pdf():
    """Exportar missões para PDF separadas por unidades"""
    try:
        # Buscar filtros
        omp_filtro = request.args.get('opm_filtro', '')
        fonte_filtro = request.args.get('fonte_filtro', '')
        
        print(f"🔍 Exportando PDF de missões - Filtros: OMP='{omp_filtro}', Fonte='{fonte_filtro}'")
        
        # Buscar missões com filtros
        query = Missao.query
        
        if omp_filtro:
            query = query.filter(Missao.opm_destino == omp_filtro)
        
        if fonte_filtro:
            query = query.filter(Missao.fonte_dinheiro == fonte_filtro)
        
        missoes = query.order_by(Missao.fonte_dinheiro, Missao.status.desc(), Missao.data_criacao.desc()).all()
        
        print(f"📋 {len(missoes)} missões encontradas para exportação")
        
        # Organizar missões por unidade
        missoes_por_unidade = {}
        for missao in missoes:
            unidade = missao.fonte_dinheiro
            if unidade not in missoes_por_unidade:
                missoes_por_unidade[unidade] = {
                    'previsao': [],
                    'autorizada': [],
                    'total_previsao': 0,
                    'total_autorizada': 0,
                    'total_geral': 0
                }
            
            missoes_por_unidade[unidade][missao.status].append(missao)
            
            if missao.status == 'previsao':
                missoes_por_unidade[unidade]['total_previsao'] += missao.valor
            else:
                missoes_por_unidade[unidade]['total_autorizada'] += missao.valor
            
            missoes_por_unidade[unidade]['total_geral'] += missao.valor
        
        # Criar buffer para o PDF
        buffer = io.BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=72,
            bottomMargin=18
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # ✅ ESTILOS CUSTOMIZADOS
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f4e79'),
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        
        unidade_style = ParagraphStyle(
            'UnidadeTitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            spaceBefore=20,
            textColor=colors.HexColor('#2c5aa0'),
            fontName='Helvetica-Bold'
        )
        
        # ✅ CABEÇALHO
        elements.append(Paragraph("RELATÓRIO DE MISSÕES POR UNIDADE", title_style))
        elements.append(Paragraph("CRPIV - Comando Regional de Polícia IV", subtitle_style))
        
        # Informações dos filtros
        filtro_info = []
        if omp_filtro:
            filtro_info.append(f"OPM Destino: {omp_filtro}")
        if fonte_filtro:
            filtro_info.append(f"Fonte: {fonte_filtro}")
        
        if filtro_info:
            elements.append(Paragraph(f"Filtros aplicados: {' | '.join(filtro_info)}", subtitle_style))
        
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}", subtitle_style))
        elements.append(Spacer(1, 20))
        
        # ✅ RESUMO EXECUTIVO
        total_missoes = len(missoes)
        total_previsoes = sum([m.valor for m in missoes if m.status == 'previsao'])
        total_autorizadas = sum([m.valor for m in missoes if m.status == 'autorizada'])
        total_geral = total_previsoes + total_autorizadas
        
        resumo_data = [
            ['RESUMO EXECUTIVO', ''],
            ['Total de Missões:', f'{total_missoes:,}'],
            ['Total em Previsão:', f'R$ {total_previsoes:,.2f}'.replace('.', ',')],
            ['Total Autorizada:', f'R$ {total_autorizadas:,.2f}'.replace('.', ',')],
            ['Valor Total Geral:', f'R$ {total_geral:,.2f}'.replace('.', ',')],
            ['Unidades Envolvidas:', f'{len(missoes_por_unidade)} unidade(s)']
        ]
        
        resumo_table = Table(resumo_data, colWidths=[3.5*inch, 2.5*inch])
        resumo_table.setStyle(get_table_style_header())
        
        elements.append(resumo_table)
        elements.append(Spacer(1, 30))
        
        # ✅ MISSÕES POR UNIDADE
        for unidade, dados in missoes_por_unidade.items():
            # Título da unidade
            elements.append(Paragraph(f"📍 {unidade}", unidade_style))
            
            # Resumo da unidade
            unidade_resumo = [
                ['Resumo da Unidade', 'Quantidade', 'Valor Total'],
                ['Missões em Previsão', f"{len(dados['previsao'])}", f"R$ {dados['total_previsao']:,.2f}".replace('.', ',')],
                ['Missões Autorizadas', f"{len(dados['autorizada'])}", f"R$ {dados['total_autorizada']:,.2f}".replace('.', ',')],
                ['TOTAL DA UNIDADE', f"{len(dados['previsao']) + len(dados['autorizada'])}", f"R$ {dados['total_geral']:,.2f}".replace('.', ',')]
            ]
            
            unidade_resumo_table = Table(unidade_resumo, colWidths=[3*inch, 1.5*inch, 2*inch])
            unidade_resumo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            
            elements.append(unidade_resumo_table)
            elements.append(Spacer(1, 15))
            
            # ✅ MISSÕES AUTORIZADAS
            if dados['autorizada']:
                elements.append(Paragraph(f"✅ Missões Autorizadas ({len(dados['autorizada'])})", 
                                       ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12, 
                                                    textColor=colors.HexColor('#28a745'), fontName='Helvetica-Bold')))
                
                auth_data = [['OPM Destino', 'Descrição', 'Tipo', 'Período', 'Valor']]
                
                for missao in dados['autorizada']:
                    auth_data.append([
                        missao.opm_destino,
                        (missao.descricao or '')[:35] + ('...' if len(missao.descricao or '') > 35 else ''),
                        missao.tipo,
                        missao.periodo or '-',
                        f'R$ {missao.valor:,.2f}'.replace('.', ',')
                    ])
                
                auth_table = Table(auth_data, colWidths=[1.2*inch, 2.3*inch, 1*inch, 1*inch, 1*inch])
                auth_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),  # Última coluna à direita
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                elements.append(auth_table)
                elements.append(Spacer(1, 10))
            
            # ✅ MISSÕES EM PREVISÃO
            if dados['previsao']:
                elements.append(Paragraph(f"⏳ Missões em Previsão ({len(dados['previsao'])})", 
                                       ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12, 
                                                    textColor=colors.HexColor('#ffc107'), fontName='Helvetica-Bold')))
                
                prev_data = [['OPM Destino', 'Descrição', 'Tipo', 'Período', 'Valor']]
                
                for missao in dados['previsao']:
                    prev_data.append([
                        missao.opm_destino,
                        (missao.descricao or '')[:35] + ('...' if len(missao.descricao or '') > 35 else ''),
                        missao.tipo,
                        missao.periodo or '-',
                        f'R$ {missao.valor:,.2f}'.replace('.', ',')
                    ])
                
                prev_table = Table(prev_data, colWidths=[1.2*inch, 2.3*inch, 1*inch, 1*inch, 1*inch])
                prev_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ffc107')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                elements.append(prev_table)
                elements.append(Spacer(1, 10))
            
            # Se não há missões na unidade
            if not dados['autorizada'] and not dados['previsao']:
                elements.append(Paragraph("ℹ️ Nenhuma missão encontrada para esta unidade", 
                                       ParagraphStyle('Info', parent=styles['Normal'], fontSize=10, 
                                                    textColor=colors.grey, alignment=TA_CENTER)))
            
            elements.append(Spacer(1, 20))
        
        # ✅ RODAPÉ
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("_" * 80, ParagraphStyle('Line', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)))
        elements.append(Paragraph(
            f"Relatório gerado automaticamente pelo Sistema CRPIV em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        ))
        
        # Gerar PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Nome do arquivo com filtros
        nome_arquivo = "missoes_por_unidade"
        if fonte_filtro:
            nome_arquivo += f"_{fonte_filtro.replace(' ', '_')}"
        if omp_filtro:
            nome_arquivo += f"_destino_{omp_filtro.replace(' ', '_')}"
        nome_arquivo += f"_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        
        print(f"✅ PDF gerado: {nome_arquivo}")
        
        return Response(
            buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename={nome_arquivo}'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro na exportação PDF de missões: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao exportar relatório de missões em PDF', 'error')
        return redirect(url_for('missoes'))


def get_table_style_header():
    """Estilo padrão para tabelas com cabeçalho"""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ])


def create_missoes_table_style(header_color, body_color):
    """Criar estilo específico para tabelas de missões"""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black if header_color == '#ffc107' else colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),  # Última coluna à direita
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), body_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])


@app.route('/salvar_distribuicao', methods=['POST'])
def salvar_distribuicao():
    """VERSÃO CORRIGIDA - Compatível com HTML"""
    print("=" * 50)
    print("🔍 INICIANDO DISTRIBUIÇÃO - DEBUG ATIVO")
    print("=" * 50)
    
    try:
        # Debug: Mostrar TODOS os dados recebidos
        print("📋 TODOS OS DADOS DO FORMULÁRIO:")
        for key, value in request.form.items():
            print(f"  '{key}' = '{value}'")
        print("-" * 30)
        
        orcamento_id = request.form['orcamento_id']
        print(f"📊 Orçamento ID: {orcamento_id}")
        
        orcamento = db.session.get(Orcamento, orcamento_id)
        if not orcamento:
            flash('Orçamento não encontrado', 'error')
            return redirect(url_for('orcamento'))
        
        print(f"✅ Orçamento encontrado: {orcamento.bimestre}/{orcamento.ano}")
        
        # Verificar saldos disponíveis
        saldos_para_distribuir = calcular_saldos_para_distribuir()
        print("💰 Saldos disponíveis:")
        for tipo, valor in saldos_para_distribuir.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        # ✅ MAPEAMENTO CORRETO - HTML usa nomes sem acento
        mapeamento_html_para_python = {
            'DIARIAS': 'DIÁRIAS',
            'DERSO': 'DERSO', 
            'DIARIAS_PAV': 'DIÁRIAS PAV',
            'DERSO_PAV': 'DERSO PAV'
        }
        
        # Processar dados do formulário
        totais_por_tipo = {
            'DIÁRIAS': 0,
            'DERSO': 0,
            'DIÁRIAS PAV': 0,
            'DERSO PAV': 0
        }
        
        distribuicoes_para_salvar = []
        
        for unidade in ['7º BPM', '8º BPM', 'CIPO']:
            for tipo_html in ['DIARIAS', 'DERSO', 'DIARIAS_PAV', 'DERSO_PAV']:
                # ✅ USAR O NOME EXATO DO HTML
                campo_nome = f"{unidade}_{tipo_html}"
                valor_str = request.form.get(campo_nome, '0').strip()
                
                print(f"🔍 {unidade} - {tipo_html}: '{valor_str}'")
                
                if not valor_str or valor_str == '0' or valor_str == '':
                    continue
                
                try:
                    valor_limpo = valor_str.replace(',', '.').replace(' ', '').replace('R$', '')
                    valor_float = float(valor_limpo)
                    
                    if valor_float > 0:
                        # ✅ CONVERTER PARA O TIPO PYTHON CORRETO
                        tipo_python = mapeamento_html_para_python[tipo_html]
                        
                        print(f"✅ Valor válido: {campo_nome} = R$ {valor_float:,.2f}")
                        print(f"   Convertido para: {tipo_python}")
                        
                        totais_por_tipo[tipo_python] += valor_float
                        distribuicoes_para_salvar.append({
                            'unidade': unidade,
                            'tipo': tipo_python,  # Usar tipo Python
                            'valor': valor_float
                        })
                    else:
                        print(f"⚠️ Valor zero ignorado")
                        
                except (ValueError, TypeError) as e:
                    print(f"❌ Erro ao converter valor '{valor_str}': {e}")
                    flash(f'Valor inválido para {unidade} - {tipo_html}: {valor_str}', 'error')
                    return redirect(url_for('distribuir', orcamento_id=orcamento_id))
        
        print("📊 Totais por tipo a distribuir:")
        for tipo, total in totais_por_tipo.items():
            print(f"  {tipo}: R$ {total:,.2f}")
        
        # Verificar se há distribuições para salvar
        if not distribuicoes_para_salvar:
            print("⚠️ NENHUMA DISTRIBUIÇÃO VÁLIDA ENCONTRADA!")
            flash('⚠️ Nenhum valor válido foi encontrado para distribuir. Verifique se preencheu os campos.', 'warning')
            return redirect(url_for('distribuir', orcamento_id=orcamento_id))
        
        # Validação de saldos
        print("🔍 Validando saldos...")
        erros_validacao = []
        
        mapeamento_tipos_saldo = {
            'DIÁRIAS': 'diarias',
            'DERSO': 'derso', 
            'DIÁRIAS PAV': 'diarias_pav',
            'DERSO PAV': 'derso_pav'
        }
        
        for tipo_orcamento, tipo_saldo in mapeamento_tipos_saldo.items():
            disponivel = saldos_para_distribuir[tipo_saldo]
            solicitado = totais_por_tipo[tipo_orcamento]
            
            print(f"  {tipo_orcamento}: Solicitado R$ {solicitado:,.2f} / Disponível R$ {disponivel:,.2f}")
            
            if solicitado > disponivel:
                erro_msg = (f"{tipo_orcamento}: Tentando distribuir R$ {solicitado:,.2f}, "
                           f"mas só há R$ {disponivel:,.2f} disponível")
                erros_validacao.append(erro_msg)
                print(f"❌ {erro_msg}")
        
        if erros_validacao:
            print(f"❌ {len(erros_validacao)} erros de validação encontrados")
            for erro in erros_validacao:
                flash(erro, 'error')
            return redirect(url_for('distribuir', orcamento_id=orcamento_id))
        
        print("✅ Validação passou - Salvando distribuições...")
        
        # Limpar distribuições anteriores
        distribuicoes_anteriores = Distribuicao.query.filter_by(orcamento_id=orcamento_id).count()
        print(f"🗑️ Removendo {distribuicoes_anteriores} distribuições anteriores")
        
        Distribuicao.query.filter_by(orcamento_id=orcamento_id).delete()
        
        # Salvar novas distribuições
        distribuicoes_salvas = 0
        for item in distribuicoes_para_salvar:
            distribuicao = Distribuicao(
                orcamento_id=orcamento_id,
                unidade=item['unidade'],
                tipo_orcamento=item['tipo'],  # Já está no formato Python correto
                valor=item['valor']
            )
            db.session.add(distribuicao)
            distribuicoes_salvas += 1
            print(f"💾 Salvando: {item['unidade']} - {item['tipo']} - R$ {item['valor']:,.2f}")
        
        print(f"💾 Commitando {distribuicoes_salvas} distribuições...")
        db.session.commit()
        # ✅ REGISTRAR LOGS DAS DISTRIBUIÇÕES
        for item in distribuicoes_para_salvar:
            registrar_movimentacao(
                tipo='distribuicao',
                descricao=f'Distribuição para {item["unidade"]}',
                unidade_origem='CRPIV',
                unidade_destino=item['unidade'],
                tipo_orcamento=item['tipo'],
                valor=item['valor'],
                orcamento_id=orcamento_id
            )
        
        print("✅ DISTRIBUIÇÃO CONCLUÍDA COM SUCESSO!")
        flash(f'✅ Distribuição salva com sucesso! {distribuicoes_salvas} itens distribuídos.', 'success')
        
        return redirect(url_for('distribuir', orcamento_id=orcamento_id))
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        
        import traceback
        traceback.print_exc()
        
        db.session.rollback()
        flash(f'❌ Erro ao salvar distribuição: {str(e)}', 'error')
        return redirect(url_for('distribuir', orcamento_id=orcamento_id))

@app.route('/relatorio_movimentacoes')
def relatorio_movimentacoes():
    """Relatório geral de movimentações - VERSÃO CORRIGIDA"""
    try:
        filtro_unidade = request.args.get('unidade_filtro', '')
        filtro_tipo = request.args.get('tipo_filtro', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        
        print(f"🔍 Carregando relatório de movimentações...")
        print(f"   Filtros: unidade='{filtro_unidade}', tipo='{filtro_tipo}', inicio='{data_inicio}', fim='{data_fim}'")
        
        # ✅ VERIFICAR SE A TABELA EXISTE E TEM DADOS
        try:
            total_registros = MovimentacaoOrcamentaria.query.count()
            print(f"📊 Total de registros na tabela MovimentacaoOrcamentaria: {total_registros}")
        except Exception as e:
            print(f"❌ Erro ao acessar tabela MovimentacaoOrcamentaria: {e}")
            # Se a tabela não existe, usar dados simulados
            return relatorio_movimentacoes_simulado(filtro_unidade, filtro_tipo, data_inicio, data_fim)
        
        # ✅ CONSTRUIR QUERY COM FILTROS
        query = MovimentacaoOrcamentaria.query
        
        # Aplicar filtros
        if filtro_unidade:
            query = query.filter(
                or_(
                    MovimentacaoOrcamentaria.unidade_origem == filtro_unidade,
                    MovimentacaoOrcamentaria.unidade_destino == filtro_unidade
                )
            )
            print(f"   Aplicado filtro de unidade: {filtro_unidade}")
        
        if filtro_tipo:
            query = query.filter(MovimentacaoOrcamentaria.tipo == filtro_tipo)
            print(f"   Aplicado filtro de tipo: {filtro_tipo}")
        
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(MovimentacaoOrcamentaria.data_movimentacao >= data_inicio_obj)
                print(f"   Aplicado filtro data início: {data_inicio}")
            except ValueError:
                print(f"   Erro ao converter data início: {data_inicio}")
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
                query = query.filter(MovimentacaoOrcamentaria.data_movimentacao <= data_fim_obj)
                print(f"   Aplicado filtro data fim: {data_fim}")
            except ValueError:
                print(f"   Erro ao converter data fim: {data_fim}")
        
        # ✅ EXECUTAR QUERY E BUSCAR DADOS
        movimentacoes = query.order_by(MovimentacaoOrcamentaria.data_movimentacao.desc()).all()
        print(f"📋 Movimentações encontradas: {len(movimentacoes)}")
        
        # ✅ LOG DETALHADO DAS MOVIMENTAÇÕES
        if movimentacoes:
            print("📋 Primeiras 5 movimentações:")
            for i, mov in enumerate(movimentacoes[:5]):
                print(f"  {i+1}. {mov.data_movimentacao} - {mov.tipo} - {mov.unidade_origem} → {mov.unidade_destino} - R$ {mov.valor or 0:,.2f}")
        else:
            print("⚠️ Nenhuma movimentação encontrada!")
        
        # Estatísticas
        total_movimentacoes = len(movimentacoes)
        valor_total = sum([m.valor for m in movimentacoes if m.valor])
        
        print(f"📊 Estatísticas calculadas:")
        print(f"   Total de movimentações: {total_movimentacoes}")
        print(f"   Valor total: R$ {valor_total:,.2f}")
        
        tipos_movimento = ['orcamento_criado', 'distribuicao', 'autorizacao_missao', 
                          'transferencia_entre_unidades', 'nova_distribuicao_crpiv', 'recolhimento']
        
        filtros_retorno = {
            'unidade_filtro': filtro_unidade,
            'tipo_filtro': filtro_tipo,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }
        
        print(f"🎯 Renderizando template com {len(movimentacoes)} movimentações")
        
        return render_template('relatorio_movimentacoes.html',
                             movimentacoes=movimentacoes,
                             total_movimentacoes=total_movimentacoes,
                             valor_total=valor_total,
                             unidades=UNIDADES,
                             tipos_movimento=tipos_movimento,
                             filtros=filtros_retorno)
                             
    except Exception as e:
        print(f"❌ Erro no relatório: {e}")
        import traceback
        traceback.print_exc()
        flash('Erro ao carregar relatório de movimentações', 'error')
        
        # Retornar template vazio em caso de erro
        return render_template('relatorio_movimentacoes.html', 
                             movimentacoes=[],
                             total_movimentacoes=0,
                             valor_total=0,
                             unidades=UNIDADES,
                             tipos_movimento=[],
                             filtros={
                                 'unidade_filtro': '',
                                 'tipo_filtro': '',
                                 'data_inicio': '',
                                 'data_fim': ''
                             })


def relatorio_movimentacoes_simulado(filtro_unidade='', filtro_tipo='', data_inicio='', data_fim=''):
    """Função auxiliar para dados simulados quando tabela não existe"""
    print("📊 Gerando dados simulados para movimentações...")
    
    try:
        # Simular movimentações baseadas em dados existentes
        movimentacoes_simuladas = []
        
        # 1. Simular criação de orçamentos
        orcamentos = Orcamento.query.all()
        for orc in orcamentos:
            class MovimentacaoSimulada:
                def __init__(self, data, tipo, descricao, origem=None, destino=None, tipo_orc=None, valor=None, usuario="Sistema"):
                    self.data_movimentacao = data
                    self.tipo = tipo
                    self.descricao = descricao  
                    self.unidade_origem = origem
                    self.unidade_destino = destino
                    self.tipo_orcamento = tipo_orc
                    self.valor = valor
                    self.usuario = usuario
            
            mov = MovimentacaoSimulada(
                data=orc.data_criacao,
                tipo='orcamento_criado',
                descricao=f'Orçamento criado: {orc.bimestre}/{orc.ano}',
                valor=sum([orc.diarias, orc.derso, orc.diarias_pav, orc.derso_pav])
            )
            movimentacoes_simuladas.append(mov)
        
        # 2. Simular distribuições
        distribuicoes = Distribuicao.query.all()
        for dist in distribuicoes:
            mov = MovimentacaoSimulada(
                data=dist.data_distribuicao,
                tipo='distribuicao',
                descricao=f'Distribuição para {dist.unidade}',
                origem='CRPIV',
                destino=dist.unidade,
                tipo_orc=dist.tipo_orcamento,
                valor=dist.valor
            )
            movimentacoes_simuladas.append(mov)
        
        # 3. Simular autorizações
        missoes = Missao.query.filter_by(status='autorizada').all()
        for missao in missoes:
            mov = MovimentacaoSimulada(
                data=missao.data_autorizacao or missao.data_criacao,
                tipo='autorizacao_missao',
                descricao=f'Missão autorizada: {missao.descricao[:30]}...',
                origem=missao.fonte_dinheiro,
                destino=missao.omp_destino,
                tipo_orc=missao.tipo,
                valor=missao.valor
            )
            movimentacoes_simuladas.append(mov)
        
        # Ordenar por data
        movimentacoes_simuladas.sort(key=lambda x: x.data_movimentacao, reverse=True)
        
        # Aplicar filtros
        if filtro_unidade:
            movimentacoes_simuladas = [
                m for m in movimentacoes_simuladas 
                if m.unidade_origem == filtro_unidade or m.unidade_destino == filtro_unidade
            ]
        
        if filtro_tipo:
            movimentacoes_simuladas = [
                m for m in movimentacoes_simuladas 
                if m.tipo == filtro_tipo
            ]
        
        total_movimentacoes = len(movimentacoes_simuladas)
        valor_total = sum([m.valor for m in movimentacoes_simuladas if m.valor])
        
        print(f"✅ Dados simulados: {total_movimentacoes} movimentações, valor total: R$ {valor_total:,.2f}")
        
        tipos_movimento = ['orcamento_criado', 'distribuicao', 'autorizacao_missao']
        
        return render_template('relatorio_movimentacoes.html',
                             movimentacoes=movimentacoes_simuladas,
                             total_movimentacoes=total_movimentacoes,
                             valor_total=valor_total,
                             unidades=UNIDADES,
                             tipos_movimento=tipos_movimento,
                             filtros={
                                 'unidade_filtro': filtro_unidade,
                                 'tipo_filtro': filtro_tipo,
                                 'data_inicio': data_inicio,
                                 'data_fim': data_fim
                             })
                             
    except Exception as e:
        print(f"❌ Erro ao gerar dados simulados: {e}")
        return render_template('relatorio_movimentacoes.html', 
                             movimentacoes=[],
                             total_movimentacoes=0,
                             valor_total=0,
                             unidades=UNIDADES,
                             tipos_movimento=[],
                             filtros={})


@app.route('/exportar_movimentacoes_csv')
def exportar_movimentacoes_csv():
    """Exportar movimentações para CSV"""
    try:
        movimentacoes = MovimentacaoOrcamentaria.query.order_by(
            MovimentacaoOrcamentaria.data_movimentacao.desc()
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Cabeçalho
        writer.writerow([
            'Data', 'Tipo', 'Descrição', 'Unidade Origem', 'Unidade Destino',
            'Tipo Orçamento', 'Valor', 'Usuário', 'Orçamento ID', 'Missão ID'
        ])
        
        # Dados
        for mov in movimentacoes:
            writer.writerow([
                mov.data_movimentacao.strftime('%d/%m/%Y %H:%M'),
                mov.tipo,
                mov.descricao or '',
                mov.unidade_origem or '',
                mov.unidade_destino or '',
                mov.tipo_orcamento or '',
                f"{mov.valor:,.2f}".replace('.', ',') if mov.valor else '',
                mov.usuario,
                mov.orcamento_id or '',
                mov.missao_id or ''
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': 'attachment; filename=movimentacoes_orcamentarias.csv'
            }
        )
        
    except Exception as e:
        print(f"❌ Erro na exportação: {e}")
        flash('Erro ao exportar relatório', 'error')
        return redirect(url_for('relatorio_movimentacoes'))

# ✅ FUNÇÃO DE DEBUG MELHORADA
def debug_distribuicao_completo():
    """Função para diagnosticar todos os problemas de distribuição"""
    print("=" * 60)
    print("🔍 DIAGNÓSTICO COMPLETO DO SISTEMA DE DISTRIBUIÇÃO")
    print("=" * 60)
    
    try:
        # 1. Verificar orçamentos
        orcamentos = Orcamento.query.all()
        print(f"📊 Total de orçamentos: {len(orcamentos)}")
        
        total_geral = {'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0}
        for orc in orcamentos:
            total_geral['diarias'] += orc.diarias or 0
            total_geral['derso'] += orc.derso or 0
            total_geral['diarias_pav'] += orc.diarias_pav or 0
            total_geral['derso_pav'] += orc.derso_pav or 0
        
        print("💰 Orçamento total base:")
        for tipo, valor in total_geral.items():
            print(f"  {tipo}: R$ {valor:,.2f}")
        
        # 2. Verificar complementações
        complementacoes = ComplementacaoOrcamento.query.all()
        print(f"📈 Total de complementações: {len(complementacoes)}")
        
        # 3. Verificar distribuições
        distribuicoes = Distribuicao.query.all()
        print(f"📤 Total de distribuições: {len(distribuicoes)}")
        
        total_distribuido = sum([d.valor for d in distribuicoes])
        print(f"💸 Total distribuído: R$ {total_distribuido:,.2f}")
        
        # 4. Verificar missões
        missoes_prev = Missao.query.filter_by(status='previsao').all()
        missoes_aut = Missao.query.filter_by(status='autorizada').all()
        
        print(f"📋 Missões em previsão: {len(missoes_prev)}")
        print(f"✅ Missões autorizadas: {len(missoes_aut)}")
        
        total_prev = sum([m.valor for m in missoes_prev])
        total_aut = sum([m.valor for m in missoes_aut])
        
        print(f"💰 Valor previsões: R$ {total_prev:,.2f}")
        print(f"💰 Valor autorizadas: R$ {total_aut:,.2f}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erro no diagnóstico: {e}")


@app.route('/saldos_bimestre')
def saldos_bimestre():
    try:
        saldos = calcular_saldo_por_bimestre()
        totais_geral = calcular_orcamento_total_todos_bimestres()
        return render_template('saldos_bimestre.html', 
                             saldos_bimestre=saldos,
                             totais_geral=totais_geral)
    except Exception as e:
        print(f"❌ Erro em saldos_bimestre: {e}")
        flash('Erro ao carregar saldos por bimestre', 'error')
        return render_template('saldos_bimestre.html', 
                             saldos_bimestre=[],
                             totais_geral={'diarias': 0, 'derso': 0, 'diarias_pav': 0, 'derso_pav': 0})


@app.route('/complementacao', methods=['GET', 'POST'])
def complementacao():
    if request.method == 'POST':
        nova_complementacao = ComplementacaoOrcamento(
            orcamento_id=int(request.form['orcamento_id']),
            processo_sei=request.form['processo_sei'],
            tipo_orcamento=request.form['tipo_orcamento'],
            valor=float(request.form['valor']),
            descricao=request.form.get('descricao', '')
        )
        
        db.session.add(nova_complementacao)
        db.session.commit()
        
        # Registrar log
        registrar_movimentacao(
            tipo='complementacao_orcamento',
            descricao=f'Complementação orçamentária: {nova_complementacao.tipo_orcamento}',
            tipo_orcamento=nova_complementacao.tipo_orcamento,
            valor=nova_complementacao.valor,
            orcamento_id=nova_complementacao.orcamento_id
        )
        
        flash('Complementação orçamentária cadastrada com sucesso!', 'success')
        return redirect(url_for('complementacao'))
    
    orcamentos = Orcamento.query.order_by(Orcamento.data_criacao.desc()).all()
    complementacoes = ComplementacaoOrcamento.query.order_by(ComplementacaoOrcamento.data_criacao.desc()).all()
    
    return render_template('complementacao.html', 
                         orcamentos=orcamentos,
                         complementacoes=complementacoes,
                         tipos=TIPOS_ORCAMENTO)

@app.route('/editar_complementacao/<int:comp_id>', methods=['GET', 'POST'])
def editar_complementacao(comp_id):
    complementacao = db.session.get(ComplementacaoOrcamento, comp_id) or abort(404)
    
    if request.method == 'POST':
        complementacao.orcamento_id = int(request.form['orcamento_id'])
        complementacao.processo_sei = request.form['processo_sei']
        complementacao.tipo_orcamento = request.form['tipo_orcamento']
        complementacao.valor = float(request.form['valor'])
        complementacao.descricao = request.form.get('descricao', '')
        
        db.session.commit()
        flash('Complementação atualizada com sucesso!', 'success')
        return redirect(url_for('complementacao'))
    
    orcamentos = Orcamento.query.order_by(Orcamento.data_criacao.desc()).all()
    return render_template('editar_complementacao.html', 
                         complementacao=complementacao,
                         orcamentos=orcamentos,
                         tipos=TIPOS_ORCAMENTO)

@app.route('/remover_complementacao/<int:comp_id>')
def remover_complementacao(comp_id):
    complementacao = db.session.get(ComplementacaoOrcamento, comp_id) or abort(404)
    db.session.delete(complementacao)
    db.session.commit()
    flash('Complementação removida com sucesso!', 'success')
    return redirect(url_for('complementacao'))

@app.route('/distribuir/<int:orcamento_id>')
def distribuir(orcamento_id):
    """Página de distribuição com saldos CORRETOS"""
    try:
        orcamento = db.session.get(Orcamento, orcamento_id)
        if not orcamento:
            flash('Orçamento não encontrado', 'error')
            return redirect(url_for('orcamento'))
        
        print(f"🔍 Carregando página de distribuição - Orçamento {orcamento_id}")
        
        # ✅ CALCULAR SALDOS DISPONÍVEIS (não total bruto)
        orcamento_totais = calcular_orcamento_total_com_complementacao(orcamento)
        
        # Buscar distribuições existentes
        distribuicoes = Distribuicao.query.filter_by(orcamento_id=orcamento_id).all()
        
        print(f"📋 Distribuições existentes: {len(distribuicoes)}")
        
        return render_template('distribuir.html', 
                             orcamento=orcamento, 
                             orcamento_totais=orcamento_totais,  # ✅ Saldos disponíveis
                             distribuicoes=distribuicoes,
                             unidades=UNIDADES[1:],  # Excluir CRPIV
                             tipos=TIPOS_ORCAMENTO)
                             
    except Exception as e:
        print(f"❌ Erro na rota distribuir: {e}")
        flash('Erro ao carregar página de distribuição', 'error')
        return redirect(url_for('orcamento'))



@app.route('/missoes', methods=['GET', 'POST'])
def missoes():
    # Filtros
    opm_filtro = request.args.get('opm_filtro', '')
    fonte_filtro = request.args.get('fonte_filtro', '')
    
    if request.method == 'POST':
        nova_missao = Missao(
            fonte_dinheiro=request.form['fonte_dinheiro'],
            opm_destino=request.form['opm_destino'],
            processo_sei=request.form['processo_sei'],
            descricao=request.form['descricao'],
            periodo=request.form['periodo'],
            mes=request.form['mes'],
            tipo=request.form['tipo'],
            valor=float(request.form['valor']),
            numero_autorizacao=request.form.get('numero_autorizacao', ''),
            status=request.form['status']
        )
        
        if nova_missao.status == 'autorizada':
            nova_missao.data_autorizacao = datetime.utcnow()
        
        db.session.add(nova_missao)
        db.session.commit()
        flash('Missão cadastrada com sucesso!', 'success')
        return redirect(url_for('missoes'))
    
    # Query com filtros
    query = Missao.query
    if opm_filtro:
        query = query.filter(Missao.opm_destino == opm_filtro)
    if fonte_filtro:
        query = query.filter(Missao.fonte_dinheiro == fonte_filtro)
    
    missoes = query.order_by(Missao.data_criacao.desc()).all()
    
    return render_template('missoes.html', 
                         missoes=missoes,
                         unidades=UNIDADES,
                         tipos=TIPOS_ORCAMENTO,
                         meses=MESES,
                         opm_filtro=opm_filtro,
                         fonte_filtro=fonte_filtro)

@app.route('/editar_missao/<int:missao_id>', methods=['GET', 'POST'])
def editar_missao(missao_id):
    missao = db.session.get(Missao, missao_id) or abort(404)
    
    if request.method == 'POST':
        valor_anterior = missao.valor
        novo_valor = float(request.form['valor'])
        
        missao.fonte_dinheiro = request.form['fonte_dinheiro']
        missao.opm_destino = request.form['opm_destino']
        missao.processo_sei = request.form['processo_sei']
        missao.descricao = request.form['descricao']
        missao.periodo = request.form['periodo']
        missao.mes = request.form['mes']
        missao.tipo = request.form['tipo']
        missao.valor = novo_valor
        missao.numero_autorizacao = request.form.get('numero_autorizacao', '')
        
        if valor_anterior != novo_valor:
            if missao.observacoes:
                missao.observacoes += f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Valor alterado de R$ {valor_anterior:,.2f} para R$ {novo_valor:,.2f}"
            else:
                missao.observacoes = f"[{datetime.now().strftime('%d/%m/%Y %H:%M')}] Valor alterado de R$ {valor_anterior:,.2f} para R$ {novo_valor:,.2f}"
        
        db.session.commit()
        flash('Missão atualizada com sucesso!', 'success')
        return redirect(url_for('missoes'))
    
    return render_template('editar_missao.html', 
                         missao=missao,
                         unidades=UNIDADES,
                         tipos=TIPOS_ORCAMENTO,
                         meses=MESES)

@app.route('/remover_missao/<int:missao_id>', methods=['POST'])
def remover_missao(missao_id):
    missao = db.session.get(Missao, missao_id)
    if not missao:
        flash('Missão não encontrada', 'error')
        return redirect(url_for('missoes'))

    try:
        db.session.delete(missao)
        db.session.commit()
        flash('Missão removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao remover missão.', 'error')
        print(f"Erro ao remover missão: {e}")

    return redirect(url_for('missoes'))

@app.route('/relatorios')
def relatorios():
    # Filtros
    unidade_filtro = request.args.get('unidade_filtro', '')
    
    # Usar orçamento total de todos os bimestres
    totais_geral = calcular_orcamento_total_todos_bimestres()
    tipos_valores = [
        totais_geral['diarias'],
        totais_geral['derso'],
        totais_geral['diarias_pav'],
        totais_geral['derso_pav']
    ]
    
    # Gráfico por unidade (gastos autorizados) - com filtro
    gastos_unidade = {}
    for unidade in UNIDADES:
        if unidade_filtro and unidade != unidade_filtro:
            continue
            
        total_gasto = db.session.query(Missao).filter_by(
            fonte_dinheiro=unidade, 
            status='autorizada'
        ).with_entities(db.func.sum(Missao.valor)).scalar() or 0
        gastos_unidade[unidade] = total_gasto
    
    # Gráfico por status - considerando filtro de unidade
    query_previsoes = db.session.query(Missao).filter_by(status='previsao')
    query_autorizadas = db.session.query(Missao).filter_by(status='autorizada')
    
    if unidade_filtro:
        query_previsoes = query_previsoes.filter(Missao.fonte_dinheiro == unidade_filtro)
        query_autorizadas = query_autorizadas.filter(Missao.fonte_dinheiro == unidade_filtro)
    
    total_previsoes = query_previsoes.with_entities(db.func.sum(Missao.valor)).scalar() or 0
    total_autorizadas = query_autorizadas.with_entities(db.func.sum(Missao.valor)).scalar() or 0
    
    dados = {
        'tipos_orcamento': TIPOS_ORCAMENTO,
        'tipos_valores': tipos_valores,
        'unidades': list(gastos_unidade.keys()),
        'gastos_unidade': list(gastos_unidade.values()),
        'status_labels': ['Previsões', 'Autorizadas'],
        'status_valores': [total_previsoes, total_autorizadas],
        'unidade_filtro': unidade_filtro
    }
    
    return render_template('relatorios.html', dados=dados, unidades_filtro=UNIDADES)


# Rotas para Orçamentos
@app.route('/editar_orcamento/<int:orcamento_id>', methods=['GET', 'POST'])
def editar_orcamento(orcamento_id):
    orcamento = db.session.get(Orcamento, orcamento_id) or abort(404)

    
    if request.method == 'POST':
        # Atualizar campos básicos
        orcamento.bimestre = request.form['bimestre']
        orcamento.ano = int(request.form['ano'])
        orcamento.diarias = float(request.form['diarias'])
        orcamento.derso = float(request.form['derso'])
        orcamento.diarias_pav = float(request.form['diarias_pav'])
        orcamento.derso_pav = float(request.form['derso_pav'])
        
        # Atualizar datas se existirem os campos
        if 'data_inicio' in request.form and request.form['data_inicio']:
            orcamento.data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date()
        if 'data_fim' in request.form and request.form['data_fim']:
            orcamento.data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date()
        
        db.session.commit()
        flash('Orçamento atualizado com sucesso!', 'success')
        return redirect(url_for('orcamento'))
    
    return render_template('editar_orcamento.html', 
                         orcamento=orcamento,
                         bimestres=BIMESTRES)

@app.route('/remover_orcamento/<int:orcamento_id>')
def remover_orcamento(orcamento_id):
    orcamento = db.session.get(Orcamento, orcamento_id) or abort(404)

    
    # Verificar se há distribuições ou complementações associadas
    distribuicoes = Distribuicao.query.filter_by(orcamento_id=orcamento_id).count()
    complementacoes = ComplementacaoOrcamento.query.filter_by(orcamento_id=orcamento_id).count()
    
    if distribuicoes > 0 or complementacoes > 0:
        flash(f'Não é possível remover este orçamento. Existem {distribuicoes} distribuições e {complementacoes} complementações associadas.', 'error')
        return redirect(url_for('orcamento'))
    
    db.session.delete(orcamento)
    db.session.commit()
    flash('Orçamento removido com sucesso!', 'success')
    return redirect(url_for('orcamento'))

@app.route('/debug_recolhimento/<int:orcamento_id>')
def debug_recolhimento(orcamento_id):
    """Rota de debug para testar cálculos de recolhimento"""
    try:
        print(f"🔍 DEBUG RECOLHIMENTO - Orçamento {orcamento_id}")
        
        # Verificar orçamento
        orcamento = db.session.get(Orcamento, orcamento_id)
        if not orcamento:
            return {"erro": "Orçamento não encontrado"}
        
        print(f"✅ Orçamento: {orcamento.bimestre}/{orcamento.ano}")
        
        # Verificar distribuições
        distribuicoes = Distribuicao.query.filter_by(orcamento_id=orcamento_id).all()
        print(f"📊 Distribuições encontradas: {len(distribuicoes)}")
        
        for dist in distribuicoes:
            print(f"  {dist.unidade} - {dist.tipo_orcamento}: R$ {dist.valor:,.2f}")
        
        # Verificar missões autorizadas
        missoes = Missao.query.filter_by(status='autorizada').all()
        print(f"🎯 Missões autorizadas: {len(missoes)}")
        
        # Calcular saldos
        saldos = calcular_saldos_para_recolher_bimestre_corrigido(orcamento_id)
        
        return {
            "status": "OK",
            "orcamento": f"{orcamento.bimestre}/{orcamento.ano}",
            "distribuicoes": len(distribuicoes),
            "missoes_autorizadas": len(missoes),
            "saldos_detalhados": saldos
        }
        
    except Exception as e:
        print(f"❌ Erro no debug: {e}")
        import traceback
        traceback.print_exc()
        return {"erro": str(e)}

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)

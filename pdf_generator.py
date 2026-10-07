import html
import io
import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Numbered canvas to calculate total pages dynamically
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header line & subtle watermark
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        
        # Footer text
        footer_text = f"PJzen | Handoff Comercial → Onboarding & Operação  •  Página {self._pageNumber} de {page_count}"
        self.drawRightString(A4[0] - 36, 25, footer_text)
        
        gen_text = f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}"
        self.drawString(36, 25, gen_text)
        
        self.line(36, 35, A4[0] - 36, 35)
        self.restoreState()


def _format_val(val):
    if not val:
        return "—"
    return html.escape(str(val))


def _parse_list(val):
    if not val:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        val = val.strip()
        if (val.startswith("[") and val.endswith("]")) or (val.startswith("{") and val.endswith("}")):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
                return [parsed]
            except Exception:
                pass
        return [val] if val else []
    return []


def _render_checkbox_group(all_options, selected_list, style):
    items = []
    selected_list = _parse_list(selected_list)
    selected_set = set(selected_list)
    for opt in all_options:
        is_checked = opt in selected_set
        box = "<b>[X]</b>" if is_checked else "[ &nbsp; ]"
        color = "#b45309" if is_checked else "#475569"
        weight = "<b>" if is_checked else ""
        end_weight = "</b>" if is_checked else ""
        items.append(f'<font color="{color}">{box} {weight}{html.escape(opt)}{end_weight}</font>')
    return Paragraph(" &nbsp;&nbsp;&nbsp;&nbsp; ".join(items), style)


def generate_handoff_pdf(submission_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    header_title_style = ParagraphStyle(
        'DocHeaderTitle',
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#003383")
    )
    header_sub_style = ParagraphStyle(
        'DocHeaderSub',
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569")
    )
    section_title_style = ParagraphStyle(
        'SectionTitle',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.white
    )
    field_label_style = ParagraphStyle(
        'FieldLabel',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1C1B1F")
    )
    field_value_style = ParagraphStyle(
        'FieldValue',
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#2C222D")
    )
    field_value_empty = ParagraphStyle(
        'FieldValueEmpty',
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#94a3b8")
    )
    rule_style = ParagraphStyle(
        'RuleStyle',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1C1B1F")
    )
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748b")
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b")
    )

    story = []

    # 1. Title & Subtitle Banner com Logotipo Oficial
    logo_path = Path(__file__).parent / "static" / "img" / "logo.png"
    if logo_path.exists():
        logo_img = RLImage(str(logo_path), width=38, height=38)
        title_flow = [
            Paragraph("PJzen | HANDOFF COMERCIAL → ONBOARDING & OPERAÇÃO", header_title_style),
            Spacer(1, 2),
            Paragraph("Diagnóstico de entrada • preencher antes de transferir o cliente", header_sub_style)
        ]
        header_tbl = Table([[logo_img, title_flow]], colWidths=[46, 474])
        header_tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(header_tbl)
    else:
        story.append(Paragraph("PJzen | HANDOFF COMERCIAL → ONBOARDING & OPERAÇÃO", header_title_style))
        story.append(Spacer(1, 3))
        story.append(Paragraph("Diagnóstico de entrada • preencher antes de transferir o cliente", header_sub_style))
    story.append(Spacer(1, 8))

    # 2. Meta box: Preenchedor, Status, Data, Versão
    nome_preench = submission_data.get("nome_preenchedor") or "Não informado (Rascunho)"
    email_preench = submission_data.get("email_preenchedor") or "—"
    status_tec = "Enviado" if submission_data.get("status_tecnico") == "enviado" else "Rascunho"
    data_envio = submission_data.get("submitted_at")
    data_atualizacao = submission_data.get("updated_at")
    versao = submission_data.get("version", 1)

    data_formatada = ""
    if data_envio:
        try:
            dt = datetime.fromisoformat(data_envio)
            data_formatada = dt.strftime("%d/%m/%Y às %H:%M")
        except Exception:
            data_formatada = str(data_envio)
    elif data_atualizacao:
        try:
            dt = datetime.fromisoformat(data_atualizacao)
            data_formatada = f"{dt.strftime('%d/%m/%Y às %H:%M')} (última alteração)"
        except Exception:
            data_formatada = str(data_atualizacao)
    else:
        data_formatada = "—"

    data_venda_raw = submission_data.get("data_venda")
    data_venda_formatada = "—"
    if data_venda_raw:
        try:
            dt_v = datetime.strptime(data_venda_raw, "%Y-%m-%d")
            data_venda_formatada = dt_v.strftime("%d/%m/%Y")
        except Exception:
            data_venda_formatada = str(data_venda_raw)

    meta_table_data = [
        [
            Paragraph("<b>Nome de quem preencheu:</b>", meta_label_style),
            Paragraph(html.escape(nome_preench), meta_val_style),
            Paragraph("<b>Status Técnico:</b>", meta_label_style),
            Paragraph(f"<b>{status_tec}</b>", meta_val_style)
        ],
        [
            Paragraph("<b>E-mail do Registrador:</b>", meta_label_style),
            Paragraph(html.escape(email_preench), meta_val_style),
            Paragraph("<b>Versão do Registro:</b>", meta_label_style),
            Paragraph(f"v{versao}", meta_val_style)
        ],
        [
            Paragraph("<b>Data do Registro:</b>", meta_label_style),
            Paragraph(data_formatada, meta_val_style),
            Paragraph("<b>Data da Venda:</b>", meta_label_style),
            Paragraph(html.escape(data_venda_formatada), meta_val_style)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[120, 160, 110, 130])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F2EFE9")),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#E5E0D8")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E0D8")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    def make_section_header(title):
        t = Table([[Paragraph(f"<b>{title}</b>", section_title_style)]], colWidths=[520])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#003383")),
            ('LINEBEFORE', (0, 0), (0, -1), 4, colors.HexColor("#FFD100")),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    def make_fields_table(rows_definition):
        """
        rows_definition is a list of:
        (label, value_flowable_or_text, is_full_width) or
        ((label1, val1), (label2, val2)) for two-column rows.
        """
        table_data = []
        table_style = [
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]

        for item in rows_definition:
            if item["type"] == "2col":
                l1 = Paragraph(item["label1"], field_label_style)
                v1 = item["val1"] if isinstance(item["val1"], Paragraph) else Paragraph(_format_val(item["val1"]), field_value_style if item["val1"] else field_value_empty)
                l2 = Paragraph(item["label2"], field_label_style)
                v2 = item["val2"] if isinstance(item["val2"], Paragraph) else Paragraph(_format_val(item["val2"]), field_value_style if item["val2"] else field_value_empty)
                table_data.append([l1, v1, l2, v2])
            elif item["type"] == "full":
                label = Paragraph(item["label"], field_label_style)
                val = item["val"] if isinstance(item["val"], Paragraph) else Paragraph(_format_val(item["val"]), field_value_style if item["val"] else field_value_empty)
                # Spans across cols 1 to 3
                row_idx = len(table_data)
                table_data.append([label, val, "", ""])
                table_style.append(('SPAN', (1, row_idx), (3, row_idx)))

        t = Table(table_data, colWidths=[120, 140, 120, 140])
        t.setStyle(TableStyle(table_style))
        return t

    # SECTION 01
    story.append(make_section_header("01 IDENTIFICAÇÃO E CONTRATAÇÃO | Comercial"))
    sec1_rows = [
        {
            "type": "2col",
            "label1": "Nome do cliente",
            "val1": submission_data.get("cliente_razao_social"),
            "label2": "CNPJ (se houver)",
            "val2": submission_data.get("cnpj")
        },
        {
            "type": "2col",
            "label1": "E-mail do novo cliente",
            "val1": submission_data.get("email_cliente"),
            "label2": "Telefone do novo cliente",
            "val2": submission_data.get("telefone_cliente")
        },
        {
            "type": "full",
            "label": "Data do repasse",
            "val": submission_data.get("data_repasse")
        },
        {
            "type": "full",
            "label": "Tipo de demanda",
            "val": _render_checkbox_group(
                ["Abertura", "Troca de contador", "Regularização / outro"],
                submission_data.get("tipo_demanda"),
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Plano contratado",
            "val": _render_checkbox_group(
                ["PJzen Plus", "PJzen Pro", "PJzen One"],
                submission_data.get("plano_contratado"),
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Faturamento mensal esperado",
            "val": _render_checkbox_group(
                ["R$ 0 a R$ 25 mil", "R$ 25.000,01 a R$ 50 mil", "R$ 50.000,01 a R$ 200 mil"],
                submission_data.get("faturamento_mensal_esperado"),
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Atividade principal / CNAE e município",
            "val": submission_data.get("atividade_cnae_municipio")
        },
        {
            "type": "full",
            "label": "Atividades secundárias",
            "val": submission_data.get("atividades_secundarias")
        }
    ]
    story.append(make_fields_table(sec1_rows))
    story.append(Spacer(1, 10))

    # SECTION 02
    story.append(make_section_header("02 DIAGNÓSTICO TRIBUTÁRIO | Time técnico"))
    sec2_rows = [
        {
            "type": "full",
            "label": "Terá pró-labore?",
            "val": _render_checkbox_group(
                ["Sim", "Não", "A definir"],
                submission_data.get("tera_pro_labore"),
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Regime tributário",
            "val": _render_checkbox_group(
                ["Lucro presumido", "Simples nacional puro", "Simples nacional híbrido"],
                [
                    "Simples nacional puro" if v == "Puro" else ("Simples nacional híbrido" if v == "Híbrido" else v)
                    for v in _parse_list(submission_data.get("regime_tributario") or submission_data.get("simples_nacional"))
                ],
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Tabelas e anexo",
            "val": _render_checkbox_group(
                ["III", "IV", "V", "V com Fator R", "Lucro Presumido"],
                submission_data.get("tabela_apuracao_anexo"),
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Pontos de atenção técnicos / premissas da análise",
            "val": submission_data.get("pontos_atencao_tecnicos")
        }
    ]
    story.append(make_fields_table(sec2_rows))
    story.append(Spacer(1, 10))

    # SECTION 03
    story.append(make_section_header("03 O QUE PRECISA SER FEITO | Comercial + Técnico"))
    sec3_rows = [
        {
            "type": "full",
            "label": "Frentes acionadas",
            "val": _render_checkbox_group(
                ["Legalização", "Fiscal", "Contábil", "DP/RH", "Financeiro", "Outras"],
                submission_data.get("frentes_acionadas"),
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Demandas acordadas, pendências e entregáveis para o onboarding",
            "val": submission_data.get("demandas_acordadas")
        },
        {
            "type": "full",
            "label": "Descrição de documentos anexados",
            "val": submission_data.get("documentos_pendentes")
        },
        {
            "type": "full",
            "label": "Prazo combinado com o cliente",
            "val": submission_data.get("prazo_combinado")
        }
    ]

    anexos = _parse_list(submission_data.get("anexos_documentos"))
    if anexos:
        anexo_paragraphs = []
        for a in anexos:
            if isinstance(a, str):
                try:
                    a = json.loads(a)
                except Exception:
                    a = {"nome_original": a}
            if not isinstance(a, dict):
                continue
            nome = html.escape(str(a.get("nome_original", "Documento")))
            tipo = html.escape(str(a.get("tipo", "")))
            data_pc = html.escape(str(a.get("data_pc", "")))
            storage = html.escape(str(a.get("storage", "Supabase")))
            url = html.escape(str(a.get("url", "")))
            anexo_paragraphs.append(
                f"• <b>{nome}</b> ({tipo}) - Registrado em: <b>{data_pc}</b> | Storage: {storage}<br/>&nbsp;&nbsp;<font color='#0047B9'><u>{url}</u></font>"
            )
        if anexo_paragraphs:
            sec3_rows.append({
                "type": "full",
                "label": "Documentos e mídias anexados (com data do PC)",
                "val": Paragraph("<br/><br/>".join(anexo_paragraphs), field_value_style)
            })

    story.append(make_fields_table(sec3_rows))
    story.append(Spacer(1, 10))

    # SECTION 04
    story.append(make_section_header("04 VALIDAÇÃO DO REPASSE"))
    sec4_rows = [
        {
            "type": "2col",
            "label1": "Responsável pelo onboarding",
            "val1": submission_data.get("responsavel_onboarding"),
            "label2": "Responsável técnico",
            "val2": submission_data.get("responsavel_tecnico")
        },
        {
            "type": "full",
            "label": "Status",
            "val": _render_checkbox_group(
                ["Completo para entrada", "Pendente de informações", "Exige alinhamento"],
                submission_data.get("status_repasse"),
                field_value_style
            )
        },
        {
            "type": "full",
            "label": "Próxima ação / responsável / data",
            "val": submission_data.get("proxima_acao_resp_data")
        }
    ]
    story.append(make_fields_table(sec4_rows))
    story.append(Spacer(1, 10))

    # REGRA DE PASSAGEM BANNER
    rule_table_data = [[
        Paragraph(
            "<b>Regra de passagem:</b> o onboarding confirma o recebimento e devolve dúvidas ao comercial antes de iniciar a execução.",
            rule_style
        )
    ]]
    rule_table = Table(rule_table_data, colWidths=[520])
    rule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F2EFE9")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E5E0D8")),
        ('LINEBEFORE', (0, 0), (0, -1), 4, colors.HexColor("#003383")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(rule_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()

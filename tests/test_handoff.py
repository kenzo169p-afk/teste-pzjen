import os
import tempfile
import unittest
import json
import io
import re

import database
import pdf_generator
from app import app

class TestPJzenHandoff(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        database.init_db(self.db_path)
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Monkey patch DB_FILE for app requests during test
        self.orig_db_file = database.DB_FILE
        database.DB_FILE = self.db_path

    def tearDown(self):
        database.DB_FILE = self.orig_db_file
        os.close(self.db_fd)
        try:
            os.remove(self.db_path)
        except Exception:
            pass

    # 1. Somente nome preenchido: o envio é concluído com sucesso
    def test_01_somente_nome_preenchido(self):
        res = self.client.post("/api/submit", json={"nome_preenchedor": "Maria Clara"})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status_tecnico"], "enviado")
        self.assertIsNotNone(data["view_token"])
        self.assertIsNotNone(data["edit_token"])

    # 2. Nome ausente ou apenas espaços: o envio é impedido com "Informe seu nome para enviar"
    def test_02_nome_ausente_ou_espacos(self):
        # Ausente
        res1 = self.client.post("/api/submit", json={})
        self.assertEqual(res1.status_code, 400)
        self.assertEqual(res1.get_json()["error"], "Informe seu nome para enviar")

        # Apenas espaços
        res2 = self.client.post("/api/submit", json={"nome_preenchedor": "    "})
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.get_json()["error"], "Informe seu nome para enviar")

    # 3. Demais campos vazios: nenhum deles impede o envio
    def test_03_demais_campos_vazios(self):
        payload = {
            "nome_preenchedor": "Carlos Silva",
            "cliente_razao_social": "",
            "cnpj": "",
            "responsavel_comercial": "",
            "data_repasse": "",
            "tipo_demanda": [],
            "plano_contratado": [],
            "faturamento_mensal_esperado": [],
            "atividade_cnae_municipio": "",
            "atividades_secundarias": "",
            "tera_pro_labore": [],
            "simples_nacional": [],
            "tabela_apuracao_anexo": [],
            "regime_validado_por": "",
            "pontos_atencao_tecnicos": "",
            "frentes_acionadas": [],
            "demandas_acordadas": "",
            "documentos_pendentes": "",
            "prazo_combinado": "",
            "responsavel_onboarding": "",
            "responsavel_tecnico": "",
            "status_repasse": [],
            "proxima_acao_resp_data": ""
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status_tecnico"], "enviado")

    # 4. Rascunho sem nome: é possível salvar e recuperar os dados
    def test_04_rascunho_sem_nome(self):
        payload = {
            "cliente_razao_social": "Alpha Serviços em Nuvem Ltda",
            "pontos_atencao_tecnicos": "Empresa precisa de desenquadramento do MEI"
        }
        res = self.client.post("/api/draft", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["status_tecnico"], "rascunho")

        # Recuperar via edit_token
        get_res = self.client.get(f"/api/get/{data['edit_token']}")
        self.assertEqual(get_res.status_code, 200)
        rec = get_res.get_json()["data"]
        self.assertEqual(rec["cliente_razao_social"], "Alpha Serviços em Nuvem Ltda")
        self.assertEqual(rec["pontos_atencao_tecnicos"], "Empresa precisa de desenquadramento do MEI")
        self.assertEqual(rec["nome_preenchedor"], "")

    # 5. Fidelidade: todos os 21 campos, oito grupos de alternativas, quatro títulos, cabeçalho, subtítulo e regra de passagem
    def test_05_fidelidade_elementos_interface(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html_content = res.get_data(as_text=True)

        # Cabeçalho original e subtítulo
        self.assertIn("PJzen | HANDOFF COMERCIAL → ONBOARDING & OPERAÇÃO", html_content)
        self.assertIn("Diagnóstico de entrada • preencher antes de transferir o cliente", html_content)

        # 4 seções
        self.assertIn("01 IDENTIFICAÇÃO E CONTRATAÇÃO | Comercial", html_content)
        self.assertIn("02 DIAGNÓSTICO TRIBUTÁRIO | Time técnico", html_content)
        self.assertIn("03 O QUE PRECISA SER FEITO | Comercial + Técnico", html_content)
        self.assertIn("04 VALIDAÇÃO DO REPASSE", html_content)

        # Campo adicional de nome e aviso
        self.assertIn("Nome de quem está preenchendo", html_content)
        self.assertIn("Todos os itens do formulário são de preenchimento obrigatório para envio.", html_content)

        # Regra de passagem
        plain_text = re.sub(r'<[^>]+>', ' ', html_content)
        plain_text = " ".join(plain_text.split())
        self.assertIn("Regra de passagem: o onboarding confirma o recebimento e devolve dúvidas ao comercial antes de iniciar a execução.", plain_text)

        # 21 campos originais
        campos_esperados = [
            "data_venda", "cliente_razao_social", "cnpj", "data_repasse",
            "tipo_demanda", "plano_contratado", "faturamento_mensal_esperado", "atividade_cnae_municipio",
            "atividades_secundarias",
            "tera_pro_labore", "regime_tributario", "tabela_apuracao_anexo", "pontos_atencao_tecnicos",
            "frentes_acionadas", "demandas_acordadas", "documentos_pendentes", "prazo_combinado",
            "responsavel_onboarding", "responsavel_tecnico", "status_repasse", "proxima_acao_resp_data"
        ]
        for c in campos_esperados:
            self.assertIn(f'name="{c}"', html_content, f"Campo {c} ausente no formulário")

        # 8 grupos de alternativas com seus textos exatos
        alternativas_esperadas = [
            # 1. Tipo de demanda
            "Abertura", "Troca de contador", "Regularização / outro",
            # 2. Plano contratado
            "PJzen Plus", "PJzen Pro", "PJzen One",
            # 3. Faturamento mensal
            "R$ 0 a R$ 25 mil", "R$ 25.000,01 a R$ 50 mil", "R$ 50.000,01 a R$ 200 mil",
            # 4. Pró-labore
            "Sim", "Não", "A definir",
            # 5. Regime tributário
            "Lucro presumido", "Simples nacional puro", "Simples nacional híbrido",
            # 6. Tabelas e anexo
            "III", "IV", "V", "V com Fator R", "Lucro Presumido",
            # 7. Frentes acionadas
            "Legalização", "Fiscal", "Contábil", "DP/RH", "Financeiro", "Outras",
            # 8. Status repasse
            "Completo para entrada", "Pendente de informações", "Exige alinhamento"
        ]
        for alt in alternativas_esperadas:
            self.assertIn(alt, html_content, f"Alternativa '{alt}' ausente no formulário")

    # 6. Caixas de seleção: todas podem ser marcadas, desmarcadas ou deixadas vazias, sem valores automáticos
    def test_06_caixas_selecao_independentes(self):
        # Submissão com múltiplas caixas marcadas simultaneamente em alguns grupos e outras vazias
        payload = {
            "nome_preenchedor": "Juliana Santos",
            "tipo_demanda": ["Abertura", "Regularização / outro"],
            "plano_contratado": ["PJzen Pro"],
            "faturamento_mensal_esperado": [], # vazio
            "tera_pro_labore": ["Sim"],
            "simples_nacional": ["Puro", "Em análise"],
            "tabela_apuracao_anexo": ["III", "V"],
            "frentes_acionadas": ["Fiscal", "Contábil", "DP/RH"],
            "status_repasse": [] # vazio
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        tokens = res.get_json()

        # Checar recuperação
        get_res = self.client.get(f"/api/get/{tokens['view_token']}")
        data = get_res.get_json()["data"]
        self.assertEqual(data["tipo_demanda"], ["Abertura", "Regularização / outro"])
        self.assertEqual(data["plano_contratado"], ["PJzen Pro"])
        self.assertEqual(data["faturamento_mensal_esperado"], [])
        self.assertEqual(data["simples_nacional"], ["Puro", "Em análise"])
        self.assertEqual(data["tabela_apuracao_anexo"], ["III", "V"])
        self.assertEqual(data["status_repasse"], [])

    # 7. Persistência: abrir o link em outro dispositivo recupera o conteúdo salvo
    def test_07_persistencia_recuperacao_link(self):
        payload = {
            "nome_preenchedor": "Roberto Alencar",
            "cliente_razao_social": "Beta Consultoria Eireli",
            "cnpj": "98.765.432/0001-10",
            "plano_contratado": ["PJzen Plus"]
        }
        res = self.client.post("/api/submit", json=payload)
        tokens = res.get_json()
        view_token = tokens["view_token"]
        edit_token = tokens["edit_token"]

        # Consulta (view)
        res_view = self.client.get(f"/view/{view_token}")
        self.assertEqual(res_view.status_code, 200)
        view_html = res_view.get_data(as_text=True)
        self.assertIn("Beta Consultoria Eireli", view_html)
        self.assertIn("98.765.432/0001-10", view_html)
        self.assertIn("PJzen Plus", view_html)

        # Edição (edit)
        res_edit = self.client.get(f"/edit/{edit_token}")
        self.assertEqual(res_edit.status_code, 200)
        edit_html = res_edit.get_data(as_text=True)
        self.assertIn('value="Beta Consultoria Eireli"', edit_html)
        self.assertIn('value="98.765.432/0001-10"', edit_html)

    # 8. Complementação: editar o registro mantém respostas existentes e atualiza somente o que foi alterado
    def test_08_complementacao_edicao(self):
        # Criação inicial
        init_res = self.client.post("/api/submit", json={
            "nome_preenchedor": "Autor 1",
            "cliente_razao_social": "Gama Tecnologia Ltda",
            "pontos_atencao_tecnicos": "Texto técnico original"
        })
        tokens = init_res.get_json()
        edit_token = tokens["edit_token"]

        # Atualização parcial
        update_payload = {
            "nome_preenchedor": "Autor 2",
            "demandas_acordadas": "Configurar folha de pagamento",
            "expected_version": 1
        }
        upd_res = self.client.post(f"/api/edit/{edit_token}", json=update_payload)
        self.assertEqual(upd_res.status_code, 200)
        self.assertEqual(upd_res.get_json()["version"], 2)

        # Verifica que cliente_razao_social e pontos_atencao_tecnicos foram preservados
        rec_res = self.client.get(f"/api/get/{edit_token}")
        rec = rec_res.get_json()["data"]
        self.assertEqual(rec["cliente_razao_social"], "Gama Tecnologia Ltda")
        self.assertEqual(rec["pontos_atencao_tecnicos"], "Texto técnico original")
        self.assertEqual(rec["demandas_acordadas"], "Configurar folha de pagamento")
        self.assertEqual(rec["nome_preenchedor"], "Autor 2")

    # 9. Falha de rede e duplo clique: não há falso sucesso, perda de dados ou duplicação
    def test_09_duplo_clique_e_idempotencia_versao(self):
        init_res = self.client.post("/api/submit", json={"nome_preenchedor": "Teste Concorrencia"})
        edit_token = init_res.get_json()["edit_token"]

        # Primeira atualização na versão 1 -> vai para versão 2
        res1 = self.client.post(f"/api/edit/{edit_token}", json={
            "expected_version": 1,
            "cliente_razao_social": "Cliente Primeira Atualizacao"
        })
        self.assertEqual(res1.status_code, 200)

        # Tentativa de atualizar com a versão desatualizada (1) -> Conflito 409
        res2 = self.client.post(f"/api/edit/{edit_token}", json={
            "expected_version": 1,
            "cliente_razao_social": "Cliente Desatualizado Sobrescrevendo"
        })
        self.assertEqual(res2.status_code, 409)
        self.assertIn("Conflito de versão", res2.get_json()["error"])

    # 10. Isolamento: um link não permite listar outros clientes; link de consulta não autoriza alterações
    def test_10_isolamento_e_permissoes(self):
        # 1. Cria 2 clientes diferentes
        c1 = self.client.post("/api/submit", json={"nome_preenchedor": "User 1", "cliente_razao_social": "Cliente Confidencial A"}).get_json()
        c2 = self.client.post("/api/submit", json={"nome_preenchedor": "User 2", "cliente_razao_social": "Cliente Confidencial B"}).get_json()

        # Link geral não lista clientes
        home_res = self.client.get("/")
        home_html = home_res.get_data(as_text=True)
        self.assertNotIn("Cliente Confidencial A", home_html)
        self.assertNotIn("Cliente Confidencial B", home_html)

        # Link de consulta do cliente 1 não expõe cliente 2
        v1_res = self.client.get(f"/view/{c1['view_token']}")
        v1_html = v1_res.get_data(as_text=True)
        self.assertIn("Cliente Confidencial A", v1_html)
        self.assertNotIn("Cliente Confidencial B", v1_html)

        # Link de consulta NÃO autoriza rota de alteração (não é um edit_token válido)
        bad_edit = self.client.post(f"/api/edit/{c1['view_token']}", json={"cliente_razao_social": "Tentativa Invasiva"})
        self.assertEqual(bad_edit.status_code, 404)

        # API get de view_token oculta edit_token
        get_view = self.client.get(f"/api/get/{c1['view_token']}").get_json()
        self.assertNotIn("edit_token", get_view["data"])

    # 11. PDF: acentos, respostas longas, campos vazios e seleções são exportados sem cortes
    def test_11_pdf_exportacao_completa(self):
        dados = {
            "nome_preenchedor": "João da Conceição & Filhos",
            "cliente_razao_social": "Comércio & Distribuição Acentuação e Caracteres Especiais S/A",
            "cnpj": "12.345.678/0001-99",
            "tipo_demanda": ["Abertura", "Regularização / outro"],
            "plano_contratado": ["PJzen Plus"],
            "faturamento_mensal_esperado": ["R$ 50.000,01 a R$ 200 mil"],
            "tera_pro_labore": ["Sim"],
            "simples_nacional": ["Puro"],
            "tabela_apuracao_anexo": ["III", "V"],
            "pontos_atencao_tecnicos": (
                "Texto longo com múltiplos parágrafos para verificação de quebra automática de página no ReportLab. "
                * 30
            ),
            "demandas_acordadas": "Demandas detalhadas com acentos: atenção, transição, contábil, tributário.",
            "status_repasse": ["Completo para entrada"],
            "status_tecnico": "enviado",
            "version": 1
        }
        pdf_bytes = pdf_generator.generate_handoff_pdf(dados)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Testar download via endpoint
        sub = self.client.post("/api/submit", json=dados).get_json()
        pdf_res = self.client.get(f"/pdf/{sub['view_token']}")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, "application/pdf")
        self.assertGreater(len(pdf_res.data), 1000)

    # 12. Uso no celular: todos os campos e botões podem ser utilizados sem rolagem horizontal
    def test_12_uso_no_celular(self):
        # Verifica elementos essenciais de responsividade no CSS e HTML
        css_res = self.client.get("/static/css/style.css")
        self.assertEqual(css_res.status_code, 200)
        css_text = css_res.get_data(as_text=True)
        css_res.close()

        self.assertIn("overflow-x: hidden", css_text)
        self.assertIn("box-sizing: border-box", css_text)
        self.assertIn("max-width: 100%", css_text)

        html_res = self.client.get("/")
        self.assertEqual(html_res.status_code, 200)
        html_text = html_res.get_data(as_text=True)
        html_res.close()
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1.0', html_text)

    # 13. Upload de documentos, imagens e vídeos com timestamp da data do PC
    def test_13_upload_documentos_com_data_pc(self):
        # Envio de arquivo com data do PC
        data = {
            'file': (io.BytesIO(b'%PDF-1.4 test file content'), 'contrato_social.pdf'),
            'client_date_pc': '02/10/2026 às 22:30:00'
        }
        res = self.client.post('/api/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertTrue(res_json['success'])
        self.assertEqual(res_json['nome_original'], 'contrato_social.pdf')
        self.assertEqual(res_json['data_pc'], '02/10/2026 às 22:30:00')
        self.assertIn('url', res_json)
        self.assertEqual(res_json['tipo'], 'Documento PDF')

    # 14. Documento de Comprovante & Dossiê de Anexos acessível antes de fechar o site
    def test_14_documento_comprovante_dossie(self):
        payload = {
            "nome_preenchedor": "Marina Souza",
            "cliente_razao_social": "Zen Tech Soluções",
            "email_preenchedor": "marina@empresa.com.br",
            "telefone_preenchedor": "(11) 98765-4321",
            "anexos_documentos": [
                {
                    "nome_original": "comprovante_pj.png",
                    "url": "/uploads/test.png",
                    "tipo": "Imagem",
                    "tamanho_formatado": "120 KB",
                    "data_pc": "02/10/2026 às 21:00:15",
                    "storage": "Local"
                }
            ]
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        view_token = res.get_json()["view_token"]

        # Acessa página do dossiê de documentos
        doc_res = self.client.get(f"/documento/{view_token}")
        self.assertEqual(doc_res.status_code, 200)
        doc_html = doc_res.get_data(as_text=True)
        self.assertIn("Zen Tech Soluções", doc_html)
        self.assertIn("comprovante_pj.png", doc_html)
        self.assertIn("02/10/2026 às 21:00:15", doc_html)

    # 15. Identificação ampliada (Nome, E-mail, Telefone) do registrador e novo cliente
    def test_15_campos_contato_ampliados_e_email(self):
        payload = {
            "nome_preenchedor": "Lucas Mendes",
            "email_preenchedor": "lucas@pjzen.com.br",
            "telefone_preenchedor": "(21) 99999-8888",
            "cliente_razao_social": "Mendes Engenharia Ltda",
            "email_cliente": "financeiro@mendeseng.com.br",
            "telefone_cliente": "(21) 3333-4444"
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        view_token = res.get_json()["view_token"]

        # Verifica recuperação na visualização
        v_res = self.client.get(f"/view/{view_token}")
        self.assertEqual(v_res.status_code, 200)
        v_html = v_res.get_data(as_text=True)
        self.assertIn("lucas@pjzen.com.br", v_html)
        self.assertIn("financeiro@mendeseng.com.br", v_html)
        self.assertIn("(21) 3333-4444", v_html)

        # Verifica renderização no PDF sem erros
        pdf_res = self.client.get(f"/pdf/{view_token}")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, "application/pdf")
        self.assertGreater(len(pdf_res.data), 1000)

    # 16. Campo de atividades secundárias: persistência, consulta e PDF
    def test_16_atividades_secundarias(self):
        payload = {
            "nome_preenchedor": "Beatriz Lima",
            "cliente_razao_social": "Lima Tech Ltda",
            "atividade_cnae_municipio": "Desenvolvimento de sistemas (6201-5/01)",
            "atividades_secundarias": "Consultoria em TI (6202-3/00) e Treinamento (8599-6/04)"
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        view_token = data["view_token"]

        # Verifica API get
        get_res = self.client.get(f"/api/get/{view_token}")
        self.assertEqual(get_res.status_code, 200)
        rec = get_res.get_json()["data"]
        self.assertEqual(rec["atividades_secundarias"], "Consultoria em TI (6202-3/00) e Treinamento (8599-6/04)")

        # Verifica na página de visualização HTML
        v_res = self.client.get(f"/view/{view_token}")
        self.assertEqual(v_res.status_code, 200)
        v_html = v_res.get_data(as_text=True)
        self.assertIn("Atividades secundárias", v_html)
        self.assertIn("Consultoria em TI (6202-3/00) e Treinamento (8599-6/04)", v_html)

        # Verifica PDF
        pdf_res = self.client.get(f"/pdf/{view_token}")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertGreater(len(pdf_res.data), 1000)

    # 17. Regime tributário com opções Lucro presumido, Simples nacional puro, Simples nacional híbrido
    def test_17_regime_tributario(self):
        payload = {
            "nome_preenchedor": "Fernando Costa",
            "cliente_razao_social": "Costa Contabilidade",
            "regime_tributario": ["Lucro presumido", "Simples nacional híbrido"]
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        view_token = data["view_token"]

        # Verifica API get
        get_res = self.client.get(f"/api/get/{view_token}")
        self.assertEqual(get_res.status_code, 200)
        rec = get_res.get_json()["data"]
        self.assertEqual(rec["regime_tributario"], ["Lucro presumido", "Simples nacional híbrido"])

        # Verifica na página de visualização HTML
        v_res = self.client.get(f"/view/{view_token}")
        self.assertEqual(v_res.status_code, 200)
        v_html = v_res.get_data(as_text=True)
        self.assertIn("Regime tributário", v_html)
        self.assertIn("<b>[X]</b> Lucro presumido", v_html)
        self.assertIn("<b>[X]</b> Simples nacional híbrido", v_html)
        self.assertIn("[ ] Simples nacional puro", v_html)

        # Verifica PDF
        pdf_res = self.client.get(f"/pdf/{view_token}")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertGreater(len(pdf_res.data), 1000)

    # 18. Tabelas e anexo com novas opções: III, IV, V, V com Fator R, Lucro Presumido
    def test_18_tabelas_e_anexo(self):
        payload = {
            "nome_preenchedor": "Gabriel Rocha",
            "cliente_razao_social": "Rocha Tecnologia",
            "tabela_apuracao_anexo": ["V com Fator R", "Lucro Presumido"]
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        view_token = data["view_token"]

        # Verifica API get
        get_res = self.client.get(f"/api/get/{view_token}")
        self.assertEqual(get_res.status_code, 200)
        rec = get_res.get_json()["data"]
        self.assertEqual(rec["tabela_apuracao_anexo"], ["V com Fator R", "Lucro Presumido"])

        # Verifica na página de visualização HTML
        v_res = self.client.get(f"/view/{view_token}")
        self.assertEqual(v_res.status_code, 200)
        v_html = v_res.get_data(as_text=True)
        self.assertIn("Tabelas e anexo", v_html)
        self.assertIn("<b>[X]</b> V com Fator R", v_html)
        self.assertIn("<b>[X]</b> Lucro Presumido", v_html)
        self.assertIn("[ ] III", v_html)
        self.assertIn("[ ] IV", v_html)
        self.assertIn("[ ] V", v_html)

        # Verifica PDF
        pdf_res = self.client.get(f"/pdf/{view_token}")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertGreater(len(pdf_res.data), 1000)

    # 19. Campo data_venda no início do formulário
    def test_19_data_venda(self):
        payload = {
            "nome_preenchedor": "Larissa Meireles",
            "email_preenchedor": "larissa@pjzen.com.br",
            "data_venda": "2026-10-04",
            "cliente_razao_social": "Meireles Software Ltda"
        }
        res = self.client.post("/api/submit", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        view_token = data["view_token"]

        # Verifica API get
        get_res = self.client.get(f"/api/get/{view_token}")
        self.assertEqual(get_res.status_code, 200)
        rec = get_res.get_json()["data"]
        self.assertEqual(rec["data_venda"], "2026-10-04")

        # Verifica visualização HTML
        v_res = self.client.get(f"/view/{view_token}")
        self.assertEqual(v_res.status_code, 200)
        v_html = v_res.get_data(as_text=True)
        self.assertIn("Data da venda: 2026-10-04", v_html)

        # Verifica dossiê / documento HTML
        doc_res = self.client.get(f"/documento/{view_token}")
        self.assertEqual(doc_res.status_code, 200)
        doc_html = doc_res.get_data(as_text=True)
        self.assertIn("Data da venda: 2026-10-04", doc_html)

        # Verifica PDF
        pdf_res = self.client.get(f"/pdf/{view_token}")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertGreater(len(pdf_res.data), 1000)

    # 20. Registro de Acessos: em localhost NÃO deve registrar no Supabase
    def test_20_log_acesso_ignorado_em_localhost(self):
        # Chamada de entrada em localhost
        res_entrada = self.client.post("/api/log-acesso", json={
            "tipo_evento": "entrada",
            "session_id": "test_sess_123",
            "pagina": "/"
        })
        self.assertEqual(res_entrada.status_code, 200)
        data_entrada = res_entrada.get_json()
        self.assertTrue(data_entrada["success"])
        self.assertTrue(data_entrada["ignored"])
        self.assertIn("localhost", data_entrada["reason"].lower())

        # Chamada de saída em localhost
        res_saida = self.client.post("/api/log-acesso", json={
            "tipo_evento": "saida",
            "session_id": "test_sess_123",
            "pagina": "/",
            "tempo_permanencia_segundos": 45
        })
        self.assertEqual(res_saida.status_code, 200)
        data_saida = res_saida.get_json()
        self.assertTrue(data_saida["success"])
        self.assertTrue(data_saida["ignored"])

    # 21. Sistema de Defesa: Cabeçalhos HTTP de segurança e anti-indexação
    def test_21_cabecalhos_seguranca_anti_vazamento(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertEqual(res.headers.get("X-Robots-Tag"), "noindex, nofollow, noarchive")
        self.assertEqual(res.headers.get("X-XSS-Protection"), "1; mode=block")

    # 22. Sistema de Defesa: Rejeição de tokens inválidos e tentativas de injeção
    def test_22_rejeicao_tokens_invalidos(self):
        tokens_invalidos_400 = [
            "token'OR'1'='1",
            "short",
            "a" * 100,
            "token with spaces",
            "token$special!#*",
            "token<script>"
        ]
        for token in tokens_invalidos_400:
            res_get = self.client.get(f"/api/get/{token}")
            self.assertEqual(res_get.status_code, 400, f"Token malicioso {token} não foi rejeitado com 400")

            res_view = self.client.get(f"/view/{token}")
            self.assertEqual(res_view.status_code, 400, f"View com token malicioso {token} não foi rejeitada com 400")

        # Tentativas de directory traversal são barradas com 400 ou 404
        for token_traversal in ["../etc/passwd", "..\\windows\\system32"]:
            res_trav = self.client.get(f"/api/get/{token_traversal}")
            self.assertIn(res_trav.status_code, [400, 404])

    # 23. Sistema de Defesa: Consulta via view_token NUNCA vaza o edit_token
    def test_23_view_token_nao_vaza_edit_token(self):
        res = self.client.post("/api/submit", json={
            "nome_preenchedor": "Segurança Teste",
            "cliente_razao_social": "Cliente Confidencial Ltda"
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        view_token = data["view_token"]
        edit_token = data["edit_token"]

        # Consulta via view_token pela API
        get_view = self.client.get(f"/api/get/{view_token}")
        self.assertEqual(get_view.status_code, 200)
        view_payload = get_view.get_json()["data"]

        # edit_token DEVE ser omitido na resposta para evitar sequestro de permissão de edição
        self.assertNotIn("edit_token", view_payload, "Vazamento crítico: edit_token foi retornado via view_token!")
        self.assertEqual(view_payload["view_token"], view_token)

        # Consulta via edit_token legítimo mantém as permissões
        get_edit = self.client.get(f"/api/get/{edit_token}")
        self.assertEqual(get_edit.status_code, 200)
        edit_payload = get_edit.get_json()["data"]
        self.assertEqual(edit_payload.get("edit_token"), edit_token)

if __name__ == "__main__":
    unittest.main()

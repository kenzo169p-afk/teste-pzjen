# PJzen | Formulário Digital de Handoff Comercial → Onboarding & Operação

Aplicação web responsiva (mobile e desktop) desenvolvida para a **PJzen**, transformando integralmente o documento de handoff em um formulário digital contínuo com suporte a envio parcial, persistência em banco de dados SQLite, links seguros de compartilhamento e exportação de cópia em PDF com fidelidade total.

---

## 🎯 Regras Centrais e Novas Funcionalidades

- **Regra Central**: Apenas o campo **"Nome de quem está preenchendo"** é obrigatório para envio ou confirmação de alterações. Todos os demais campos são opcionais.
- **Identificação Ampliada**:
  - Bloco inicial: **Nome** (obrigatório para envio), **E-mail do Registrador / Destinatário** (para envio automático das confirmações) e **Telefone / WhatsApp** (com máscara formatada).
  - Seção 01: Inclusão de **E-mail do novo cliente** e **Telefone do novo cliente**.
- **Upload de Documentos e Mídias (Supabase Storage)**:
  - Suporte a imagens, arquivos PDF e vídeos de até 10 segundos (validação nativa no navegador).
  - Armazenamento em nuvem via Supabase Storage REST API com fallback automático para pasta local (`uploads/`) se as credenciais não estiverem informadas no `.env`.
  - **Timestamp do Computador do Usuário**: Cada anexo registra com exatidão a data e a hora do PC do cliente no instante do anexo (`client_date_pc`).
- **Documento de Comprovante & Dossiê de Anexos**:
  - Rota dedicada: `/documento/<token>` acessível através do modal final antes de fechar o site e pela barra de ações da tela de visualização.
  - Apresenta o extrato cronológico de todos os documentos anexados com a data do PC e links de visualização/download direto.
- **Disparo Automático de E-mails**:
  - Ao registrar ou atualizar informações, o sistema envia automaticamente um e-mail formatado na identidade visual PJzen para o e-mail do registrador informado, contendo os links de consulta, edição, dossiê e PDF.
- **Rascunho**: É possível salvar rascunho sem preencher o nome.
- **Fidelidade Integral**: Todos os 21 campos originais, os 8 grupos de caixas de seleção independentes, as 4 seções com seus respectivos responsáveis nos títulos, cabeçalho, subtítulo e regra de passagem obrigatória foram integralmente preservados.
- **Isolamento**: Cada preenchimento gera tokens aleatórios e imprevisíveis. O link geral não lista outros clientes. O link de consulta é estritamente somente leitura.

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.10+ instalado no computador.

### 1. Clonar ou Acessar a Pasta do Projeto
```bash
cd "c:\Users\gordo\Desktop\teste pzjen"
```

### 2. Instalar as Dependências
```bash
py -m pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente (Opcional)
Renomeie ou copie `.env.example` para `.env` e preencha as variáveis do Supabase e SMTP (caso deseje usar armazenamento em nuvem e envio real de e-mails em vez de simulação no console):
```env
SUPABASE_URL=https://sua-url.supabase.co
SUPABASE_KEY=sua-chave-service-ou-anon
SUPABASE_BUCKET=handoff-anexos

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASS=sua-senha-de-app
```
*Se não configurado, o sistema opera automaticamente com fallback local (`uploads/`) e simulação de e-mails no terminal.*

---

### Modo 1: Com 1 Clique (Windows)
Basta dar um duplo clique no arquivo:
👉 [`iniciar_servidor.bat`](file:///c:/Users/gordo/Desktop/teste%20pzjen/iniciar_servidor.bat) (ou `start.bat`)

Ele iniciará o servidor e abrirá o seu navegador automaticamente no endereço do formulário!

---

### Modo 2: Pelo Terminal
```bash
py app.py
```

Pronto! A aplicação estará acessível no seu navegador em:
👉 **`http://localhost:5000`** (ou pelo IP local da sua rede pelo celular).

---

## 🧪 Suíte de Testes Automatizados (15 Cenários de Aceite)

Para executar a validação automatizada de todos os critérios de aceite:

```bash
py -m unittest tests/test_handoff.py -v
```

### Matriz de Verificação dos Cenários de Aceite

| # | Cenário de Validação | Status | Como foi implementado / testado |
|---|---|:---:|---|
| **1** | Somente nome preenchido | ✅ Aprovado | O envio é concluído com sucesso e status "enviado". |
| **2** | Nome ausente ou apenas espaços | ✅ Aprovado | Rejeitado tanto no frontend quanto no backend com `"Informe seu nome para enviar"`. |
| **3** | Demais campos vazios | ✅ Aprovado | Nenhum dos campos do documento original bloqueia o envio. |
| **4** | Rascunho sem nome | ✅ Aprovado | Rota `/api/draft` permite salvar dados parciais mesmo sem nome e recuperá-los pelo link de edição. |
| **5** | Fidelidade integral | ✅ Aprovado | 21 campos originais + identificação, 8 grupos de alternativas com seus textos e ordem exatos, 4 títulos, cabeçalho, subtítulo e regra de passagem. |
| **6** | Caixas de seleção | ✅ Aprovado | Checkboxes independentes que podem ser marcadas, desmarcadas, combinadas ou deixadas todas vazias. |
| **7** | Persistência | ✅ Aprovado | Banco SQLite persistente. Ao abrir o link de consulta ou de edição em qualquer navegador/dispositivo, todo o conteúdo é recuperado. |
| **8** | Complementação | ✅ Aprovado | Link de edição (`/edit/<token>`) mantém respostas existentes e atualiza apenas os campos modificados, incrementando a versão. |
| **9** | Falha de rede e duplo clique | ✅ Aprovado | Desabilita botão durante envio, controle de concorrência com optimistic locking (`version`), sem falso sucesso nem perda de dados na tela. |
| **10** | Isolamento | ✅ Aprovado | Sem rotas públicas de listagem de clientes; link de consulta (`/view/<token>`) não autoriza edição nem expõe o token de alteração. |
| **11** | PDF | ✅ Aprovado | Gerador em ReportLab preserva ordem, rótulos, alternativas marcadas `[X]` e desmarcadas `[ ]`, acentos UTF-8, anexos com timestamp do PC e quebra de páginas sem cortes. |
| **12** | Uso no celular | ✅ Aprovado | Meta viewport configurado, CSS responsivo com `max-width: 100%`, flexbox/grid e sem rolagem horizontal indesejada. |
| **13** | Upload com data do PC | ✅ Aprovado | Upload de imagens, PDFs e vídeos (<=10s) registrando data e hora exata do computador do cliente (`client_date_pc`). |
| **14** | Dossiê de Anexos | ✅ Aprovado | Rota `/documento/<token>` e modal de saída com acesso ao documento consolidado de comprovante e anexos. |
| **15** | Contatos ampliados e e-mail | ✅ Aprovado | Nome, e-mail e telefone do registrador e do cliente salvos, recuperados, exibidos no formulário, no PDF e disparados por e-mail. |

---

## 🌐 Instruções de Publicação em Produção (Gratuito / Cloud)

### Opção 1: Render (Recomendado)
1. Crie uma conta gratuita em [render.com](https://render.com).
2. Suba este código para um repositório GitHub (público ou privado).
3. No painel do Render, clique em **New +** e escolha **Web Service**.
4. Conecte seu repositório.
5. Configure:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (ou adicione `gunicorn` ao `requirements.txt`)
6. Configure as variáveis de ambiente do Supabase e SMTP nas configurações do serviço.

---

## 📁 Estrutura de Arquivos

```
teste pzjen/
├── app.py                   # Servidor Flask, rotas web, APIs de upload, documento e envio
├── database.py              # Camada SQLite com migrações para contatos ampliados e anexos JSON
├── supabase_storage.py      # Integração com Supabase Storage REST API com fallback local
├── email_service.py         # Envio de e-mails com links de acesso e design PJzen (SMTP ou simulação)
├── pdf_generator.py         # Geração de PDF vetorial ReportLab (com contatos e lista de anexos)
├── requirements.txt         # Dependências do projeto (Flask, ReportLab, Requests)
├── .env.example             # Modelo de variáveis de ambiente para Supabase e SMTP
├── static/
│   ├── css/
│   │   └── style.css        # Identidade visual oficial PJzen (amarelo #FFD100, azul #003383, etc.)
│   ├── js/
│   │   └── form.js          # Validação de vídeo (<=10s), captura data PC, máscaras de tel/CNPJ, upload
│   └── img/
│       └── logo.png         # Logotipo oficial da PJzen
├── templates/
│   ├── base.html            # Layout HTML5 base com fontes Inter e favicons
│   ├── form.html            # Formulário com upload, campos ampliados e modal com dossiê
│   ├── view.html            # Tela de consulta somente leitura com galeria de anexos
│   ├── documento.html       # Dossiê de anexos com timestamps do computador
│   └── error.html           # Tela amigável de erro / token não encontrado
├── tests/
│   └── test_handoff.py      # Suíte com os 15 testes de critérios de aceite
└── README.md                # Documentação do sistema
```

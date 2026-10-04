# PJzen | Guia de Hospedagem Universal e Acesso Multi-Dispositivo

O sistema PJzen Handoff foi transformado em uma **aplicação universal (PWA - Progressive Web App)** que roda perfeitamente em:
- **Smartphones** (iPhone, Samsung, Motorola, Xiaomi, etc.)
- **Tablets** (iPad, Galaxy Tab, etc.)
- **Computadores e Notebooks** (Windows, Mac, Linux, Chromebook)
- **Qualquer navegador** (Safari, Chrome, Firefox, Edge, Opera, Brave)

---

## 📱 1. Como Usar nos Celulares e Tablets (Sem Baixar Python ou Aplicativos)

Qualquer pessoa da sua equipe ou seus clientes podem acessar diretamente pelo navegador do celular.

### No iPhone / iPad (iOS):
1. Abra o link do sistema no **Safari**.
2. Toque no botão de **Compartilhar** (quadrado com uma seta para cima na barra inferior).
3. Selecione **"Adicionar à Tela de Início"**.
4. O ícone da PJzen aparecerá na sua tela como um aplicativo nativo, com carregamento rápido e sem barras do navegador!

### No Android (Samsung, Motorola, Xiaomi, etc.):
1. Abra o link do sistema no **Google Chrome**.
2. Toque nos **3 pontinhos** no canto superior direito.
3. Toque em **"Instalar aplicativo"** (ou "Adicionar à tela inicial").
4. O ícone da PJzen será instalado diretamente no celular.

### 📄 Como Baixar o PDF no Celular / Tablet:
- Ao clicar em **"Baixar PDF"**, o documento é gerado diretamente pelo navegador do celular com layout profissional A4.
- Também é possível tocar em **"Compartilhar no Celular / WhatsApp"** para enviar o link do handoff diretamente para a equipe ou para o cliente via WhatsApp com 1 toque!

---

## 🌐 2. Como Hospedar em Qualquer Lugar do Mundo

Você pode escolher **qualquer** uma das opções abaixo. Nenhuma delas exige que seus usuários tenham Python.

---

### Opção A: Hospedagem Gratuita em 1 Minuto (Recomendada)
Plataformas como **Vercel**, **Netlify** ou **Cloudflare Pages** oferecem hospedagem gratuita, com certificado SSL (HTTPS) e alta velocidade mundial.

#### Pela Vercel (Gratuito):
1. Crie uma conta gratuita em [vercel.com](https://vercel.com).
2. Clique em **"Add New..."** → **"Project"**.
3. Conecte seu repositório do GitHub (ou faça upload da pasta).
4. O arquivo `vercel.json` já está configurado. Basta clicar em **Deploy**.
5. Em 20 segundos você terá um link seguro (ex: `https://pjzen-handoff.vercel.app`) para usar em qualquer celular ou computador.

#### Pela Netlify (Gratuito):
1. Acesse [netlify.com](https://netlify.com).
2. Arraste e solte a pasta do projeto na tela ("Drag and drop your site").
3. Pronto! O site estará online imediatamente com link público.

---

### Opção B: Hospedagem Compartilhada Comum (Hostinger, cPanel, Locaweb, GoDaddy, KingHost)
Toda hospedagem compartilhada suporta **PHP e Apache/LiteSpeed** nativamente.

1. Acesse o **Gerenciador de Arquivos** ou use um cliente FTP (como FileZilla).
2. Envie todos os arquivos do projeto para dentro da pasta `public_html` (ou pasta raiz do seu domínio).
3. O sistema já conta com:
   - `index.php` (roteador automático)
   - `api.php` (API completa em PHP nativo com banco SQLite automático `handoff.db`)
   - `.htaccess` (regras para URLs limpas)
4. **Zero configurações adicionais**: o banco de dados é criado sozinho e os uploads vão para a pasta `uploads/`.

---

### Opção C: Nuvem ou VPS com Node.js (Render, Railway, Fly.io, VPS)
Se você utiliza servidores Node.js na nuvem:

1. O arquivo `server.js` foi construído com a biblioteca padrão do Node.js (**zero dependências externas / sem necessidade de npm install**).
2. Para rodar:
   ```bash
   node server.js
   ```
3. Compatível com as portas automáticas do Render (`process.env.PORT`).

---

### Opção D: Docker (Servidores Próprios, AWS, DigitalOcean, GCP)
Se você usa Docker ou Portainer:

1. No terminal do servidor, execute:
   ```bash
   docker compose up -d
   ```
2. O sistema estará rodando na porta `8080` com Apache e PHP 8.2 pré-configurados.

---

### Opção E: Modo Estático / Offline (Sem Servidor Algum)
Se você quiser apenas abrir o formulário no seu computador sem servidor:
1. Dê um duplo clique no arquivo `index.html`.
2. O formulário funcionará 100%: você pode preencher todos os campos obrigatórios, salvar rascunhos (armazenados com segurança no navegador do aparelho) e gerar PDFs diretamente.

---

## 🔒 Resumo de Compatibilidade

| Dispositivo / Ambiente | Compatibilidade | Como Funciona |
|---|---|---|
| **iPhone e iPad (iOS)** | 100% | Safari, PWA na tela inicial, geração de PDF e compartilhamento WhatsApp |
| **Android** | 100% | Chrome, PWA instalado como app nativo, geração de PDF |
| **Windows / Mac / Linux** | 100% | Qualquer navegador moderno (Chrome, Edge, Firefox, Safari) |
| **Hospedagem PHP (Hostinger, cPanel)** | 100% | Roda via `api.php` e SQLite automático com zero instalação |
| **Vercel / Netlify / Cloudflare** | 100% | 1-Click deploy gratuito via `vercel.json` e `netlify.toml` |
| **Node.js / Docker** | 100% | `server.js` nativo ou `docker compose up -d` |
| **Python / Flask (Local)** | 100% | `app.py` original preservado e testado |

---

## 📊 3. Registro de Entrada e Saída no Supabase (Hostinger Ativa vs Localhost)

O sistema conta com um **rastreador inteligente** de tráfego que grava no Supabase as entradas e saídas de visitantes no site com data, horário e IP real.

### Regra de Proteção:
- **Quando ativo na Hostinger (produção):** Grava automaticamente o IP do visitante, horário exato, página, aparelho e tempo de permanência no Supabase.
- **Quando em Localhost (desenvolvimento/testes):** O rastreador detecta o IP local/localhost e **bloqueia o envio**, não poluindo o seu banco do Supabase.

### Como Ativar no Supabase:
1. Abra o painel do seu projeto no [Supabase](https://supabase.com).
2. Clique em **SQL Editor** no menu lateral esquerdo.
3. Abra ou copie o conteúdo do arquivo `supabase_acessos.sql` deste projeto e clique em **Run**.
4. No arquivo `.env` da sua Hostinger, certifique-se de preencher:
   ```env
   SUPABASE_URL=https://seu-projeto.supabase.co
   SUPABASE_KEY=sua-chave-anon-ou-service-role
   ```
5. Pronto! Toda vez que alguém entrar ou sair do site na Hostinger, uma linha com `tipo_evento: entrada` e `tipo_evento: saida`, o IP e o horário será registrada na tabela `acessos_logs`.


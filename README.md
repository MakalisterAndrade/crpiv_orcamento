# Sistema de Controle Orçamentário CRPIV

## Descrição

Esse sistema foi desenvolvido para gerenciamento orçamentário do Comando Regional de Polícia IV (CRPIV), incluindo:

- Registro e controle de orçamentos bimestrais
- Gestão de complementações orçamentárias
- Distribuição de recursos entre unidades (subunidades e CRPIV)
- Gestão de missões e autorizações
- Transferência de saldo entre unidades
- Relatórios consolidados, dashboards e exportação para PDF

O sistema visa garantir transparência, controle rigoroso de saldos e distribuição, e automatizar registros das movimentações.

## Funcionalidades Principais

- **Cadastro de Orçamento Bimestral:** incluindo valores de diárias, derso e pav.
- **Complementação Orçamentária:** adicionar valores suplementares ao orçamento original.
- **Distribuição de Recursos:** alocação do orçamento do CRPIV para subunidades.
- **Gestão de Missões:** cadastro, edição, autorização e controle financeiro das missões.
- **Transferência de Saldo:** movimentação de recursos entre unidades, com registro detalhado.
- **Relatórios e Dashboards:** visão geral financeira, saldos por unidade, por bimestre e por tipo.
- **Exportação em PDF:** relatórios financeiros e operacionais para auditoria.
- **Logs de Movimentações:** registro completo para auditoria e transparência.

## Tecnologias Utilizadas

- Python 3.x  
- Flask (Framework web)  
- SQLAlchemy (ORM para banco de dados)  
- Jinja2 (Templates HTML)  
- Bootstrap 5 (Interface responsiva)  
- Chart.js (Gráficos no dashboard)  
- ReportLab (Geração de PDFs)  
- Banco de dados relacional (SQLite)

## Estrutura do Projeto

```

/app.py                 \# Aplicação principal Flask
/models.py              \# Definições das entidades do banco de dados
/templates/             \# Arquivos HTML com layouts do sistema
/static/                \# Arquivos estáticos (CSS, JS, imagens)
/config.py              \# Arquivo de configuração
/requirements.txt       \# Dependências Python
/README.md              \# Este arquivo

```

## Instalação e Configuração

### Pré-requisitos

- Python 3.7 ou superior  
- Virtualenv (recomendado)  
- Banco de dados configurado (SQLite para testes, PostgreSQL ou MySQL para produção)

### Passos para instalação

```


# Clonar o repositório

git clone https://github.com/MakalisterAndrade/crpiv_orcamento
cd controle_orcamentario_crpiv

# Criar ambiente virtual

python -m venv venv
source venv/bin/activate      \# Linux/macOS
venv\Scripts\activate.bat     \# Windows

# Instalar dependências

pip install -r requirements.txt


# Executar a aplicação

python app.py

```

### Acesso

Abra o navegador e acesse:  
[http://localhost:5000](http://localhost:5000)

## Como Usar

### Cadastro de Orçamento

- Navegue até a página de orçamento para cadastrar o orçamento bimestral com valores iniciais.
- Utilize a funcionalidade de complementação para adicionar recursos extras.

### Distribuição

- Na tela de distribuição, visualize os saldos disponíveis para cada tipo e unidade.
- Realize distribuições de valores para as unidades, podendo hacerlo de forma parcial ou total.

### Gestão de Missões

- Cadastre novas missões especificando fonte, unidade destino, valor, período e outras informações.
- Autorize missões para que os valores sejam debitados da unidade ou do CRPIV.
- Edite ou exclua missões conforme necessário.

### Transferência de Saldo

- Use a tela de transferência de saldo para movimentar recursos entre unidades, inclusive com o CRPIV.
- As transferências são registradas em log para auditar o fluxo financeiro.

### Relatórios e Exportação

- Geração de relatórios financeiros e operacionais em PDF.
- Exportação de listas de missões organizadas por unidades e status.
- Visualize dashboards com gráficos e dados consolidados para controle gerencial.

## Entidades Principais

| Entidade               | Descrição                                         |
| ---------------------- | ------------------------------------------------ |
| `Orcamento`            | Contém dados dos orçamentos bimestrais           |
| `ComplementacaoOrcamento` | Registra aumentos complementares ao orçamento     |
| `Distribuicao`         | Controla valores distribuídos para unidades      |
| `Missao`               | Informações e status das missões                   |
| `MovimentacaoOrcamentaria` | Registro detalhado das movimentações realizadas  |

## Fluxo Orçamentário

1. O orçamento inicial (cota) é alocado ao CRPIV.  
2. Complementações podem ser adicionadas para ampliar os recursos.  
3. A partir do CRPIV, valores são distribuídos às unidades (ou mantidos residualmente no CRPIV).  
4. Missões podem ser realizadas pelas unidades ou pelo CRPIV, debitando seus respectivos saldos.  
5. Transferências de saldo entre unidades são possíveis, com registro em log.  
6. Saldo em CRPIV representa recursos disponíveis para uso ou redistribuição.

## Contribuições

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto.  
2. Crie um branch para a sua feature (`git checkout -b minha-feature`).  
3. Faça commits claros e documentados.  
4. Envie um Pull Request para este repositório.

## Contato

Desenvolvedor principal: **Makalister Andrade da Silva**  
Email: makalister.andrade@outlook.com.com  
GitHub: [github.com/seunome](https://github.com/MakalisterAndrade)

## Licença

Este projeto está licenciado sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
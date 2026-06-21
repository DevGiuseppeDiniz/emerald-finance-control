# Emerald Finance Control Desktop

Aplicacao desktop local para controle financeiro pessoal, sem web e sem Excel.

## Recursos

- Banco local SQLite.
- Dashboard com saldo, receitas, despesas, dividas, juros e alertas.
- Lancamentos manuais.
- Importacao OFX/QFX.
- Plano de contas com grupo, categoria, resultado, tipo e essencialidade.
- Monitoramento de dividas com juros, vencimento, pagamentos e status.
- Orcamento mensal por categoria.
- Projecoes de caixa.
- Exportacao CSV/JSON para backup.
- Importacao de extrato de dividas Serasa em CSV/TXT.
- Sincronizacao obrigatoria com Postgres compativel com Supabase/Neon no fluxo de escrita.
- Registro mensal consolidado em `monthly_snapshots`.
- CRUD para lancamentos, dividas, plano de contas e orcamentos.

## Como executar

```powershell
.\run.ps1
```

Ou diretamente, se seu Python tiver Tkinter:

```powershell
python .\main.py
```

Observacao: o Python empacotado neste ambiente Codex nao inclui Tcl/Tk completo, entao ele valida o codigo, mas nao abre a janela. Para usar o app desktop no Windows, instale Python 3.11+ pelo python.org com Tcl/Tk habilitado.

## Dados

O banco fica em:

```text
data/emerald_finance.db
```

Voce pode fazer backup copiando esse arquivo ou usando a opcao de exportacao dentro do app.

## Importar dividas do Serasa

Use o botao `Importar Serasa` e selecione um arquivo `.csv` ou `.txt` exportado pelo Serasa.

O importador tenta reconhecer automaticamente colunas comuns como:

- credor, empresa, instituicao
- valor, valor atual, saldo devedor
- vencimento, data de vencimento, data de negativacao
- contrato, protocolo, status, situacao

Importacoes repetidas sao deduplicadas por um identificador calculado a partir de credor, contrato, valor, vencimento e status.

## Supabase / Postgres / Neon

O arquivo `.env` ja existe localmente e nao deve ser commitado. Preencha a URL:

```text
DATABASE_URL=postgresql://usuario:senha@host:5432/banco?sslmode=require
```

Nao commite `.env`. Ele esta no `.gitignore`.

Depois instale a dependencia opcional:

```powershell
pip install -r requirements.txt
```

Toda operacao de escrita tenta registrar o snapshot mensal e sincronizar com o Postgres. Tambem e possivel forcar a sincronizacao pelo botao `Sincronizar Postgres` ou pelo terminal:

```powershell
python .\scripts\sync_to_postgres.py
```

O schema Postgres tambem esta em:

```text
database/postgres_schema.sql
```

Observacao: Supabase e Neon usam Postgres, mas sao plataformas diferentes. A URL Postgres funciona para sincronizacao desde que a rede e as credenciais estejam corretas.

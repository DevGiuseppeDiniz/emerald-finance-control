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

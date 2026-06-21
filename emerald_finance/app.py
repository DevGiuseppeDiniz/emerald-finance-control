from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import database
from .database import add_debt_payment, add_transaction, export_backup, export_transactions_csv
from .ofx import parse_ofx
from .services import debt_status, money, percent


class FinanceApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Emerald Finance Control")
        self.geometry("1280x820")
        self.minsize(1120, 720)
        self.conn = database.connect()
        self.account_options: list[tuple[str, int]] = []

        self.configure(bg="#F4F7F5")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._configure_style()

        self._build_shell()
        self.refresh_all()

    def _configure_style(self) -> None:
        self.style.configure("TFrame", background="#F4F7F5")
        self.style.configure("Panel.TFrame", background="#FFFFFF", relief="flat")
        self.style.configure("TLabel", background="#F4F7F5", foreground="#16211C", font=("Segoe UI", 10))
        self.style.configure("Panel.TLabel", background="#FFFFFF", foreground="#16211C", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background="#F4F7F5", foreground="#10231C", font=("Segoe UI", 22, "bold"))
        self.style.configure("Section.TLabel", background="#FFFFFF", foreground="#087B5F", font=("Segoe UI", 12, "bold"))
        self.style.configure("Metric.TLabel", background="#FFFFFF", foreground="#16211C", font=("Segoe UI", 18, "bold"))
        self.style.configure("Muted.TLabel", background="#FFFFFF", foreground="#65746C", font=("Segoe UI", 9))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
        self.style.configure("Primary.TButton", background="#087B5F", foreground="#FFFFFF")
        self.style.map("Primary.TButton", background=[("active", "#0F9D75")])
        self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=26, background="#FFFFFF", fieldbackground="#FFFFFF")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#E8F3EE", foreground="#16211C")

    def _build_shell(self) -> None:
        header = ttk.Frame(self, padding=(18, 14))
        header.pack(fill="x")
        ttk.Label(header, text="Emerald Finance Control", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Importar OFX", style="Primary.TButton", command=self.import_ofx).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Backup JSON", command=self.backup_json).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="Exportar CSV", command=self.export_csv).pack(side="right", padx=(8, 0))

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.dashboard_tab = ttk.Frame(self.tabs, padding=14)
        self.transactions_tab = ttk.Frame(self.tabs, padding=14)
        self.debts_tab = ttk.Frame(self.tabs, padding=14)
        self.accounts_tab = ttk.Frame(self.tabs, padding=14)
        self.budget_tab = ttk.Frame(self.tabs, padding=14)
        self.projection_tab = ttk.Frame(self.tabs, padding=14)

        self.tabs.add(self.dashboard_tab, text="Dashboard")
        self.tabs.add(self.transactions_tab, text="Lancamentos")
        self.tabs.add(self.debts_tab, text="Dividas")
        self.tabs.add(self.accounts_tab, text="Plano de contas")
        self.tabs.add(self.budget_tab, text="Orcamento")
        self.tabs.add(self.projection_tab, text="Projecoes")

        self._build_dashboard()
        self._build_transactions()
        self._build_debts()
        self._build_accounts()
        self._build_budget()
        self._build_projection()

    def panel(self, parent: ttk.Frame, title: str) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        ttk.Label(frame, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        return frame

    def _build_dashboard(self) -> None:
        metrics = ttk.Frame(self.dashboard_tab)
        metrics.pack(fill="x", pady=(0, 12))
        self.metric_labels: dict[str, ttk.Label] = {}
        for idx, key in enumerate(["Saldo atual", "Receitas do mes", "Gastos do mes", "Dividas abertas", "Juros mes"]):
            card = ttk.Frame(metrics, style="Panel.TFrame", padding=14)
            card.grid(row=0, column=idx, sticky="ew", padx=6)
            metrics.columnconfigure(idx, weight=1)
            ttk.Label(card, text=key, style="Muted.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="R$ 0,00", style="Metric.TLabel")
            value.pack(anchor="w", pady=(6, 0))
            self.metric_labels[key] = value

        body = ttk.Frame(self.dashboard_tab)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = self.panel(body, "Gastos por grupo no mes")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.group_tree = self.tree(left, ["Grupo", "Valor", "% gastos"], [220, 120, 90])
        self.group_tree.pack(fill="both", expand=True)

        right = self.panel(body, "Alertas e proximos vencimentos")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.alert_text = tk.Text(right, height=12, borderwidth=0, bg="#FFFFFF", fg="#16211C", font=("Segoe UI", 10), wrap="word")
        self.alert_text.pack(fill="both", expand=True)
        self.alert_text.configure(state="disabled")

    def _build_transactions(self) -> None:
        form_panel = self.panel(self.transactions_tab, "Novo lancamento")
        form_panel.pack(fill="x", pady=(0, 12))
        form = ttk.Frame(form_panel, style="Panel.TFrame")
        form.pack(fill="x")
        self.tx_date = self.entry(form, "Data", 0, 0, date.today().isoformat())
        self.tx_desc = self.entry(form, "Descricao", 0, 1)
        self.tx_amount = self.entry(form, "Valor", 0, 2)
        ttk.Label(form, text="Conta", style="Panel.TLabel").grid(row=0, column=3, sticky="w")
        self.tx_account = ttk.Combobox(form, state="readonly", width=28)
        self.tx_account.grid(row=1, column=3, sticky="ew", padx=6)
        self.tx_counterparty = self.entry(form, "Credor/Projeto", 0, 4)
        ttk.Button(form, text="Adicionar", style="Primary.TButton", command=self.add_manual_transaction).grid(row=1, column=5, padx=6, sticky="ew")
        for col in range(6):
            form.columnconfigure(col, weight=1)

        listing = self.panel(self.transactions_tab, "Historico")
        listing.pack(fill="both", expand=True)
        self.tx_tree = self.tree(
            listing,
            ["ID", "Data", "Descricao", "Valor", "Conta", "Grupo", "Categoria", "Resultado", "Origem"],
            [60, 95, 260, 110, 160, 140, 160, 170, 90],
        )
        self.tx_tree.pack(fill="both", expand=True)

    def _build_debts(self) -> None:
        form_panel = self.panel(self.debts_tab, "Nova divida")
        form_panel.pack(fill="x", pady=(0, 12))
        form = ttk.Frame(form_panel, style="Panel.TFrame")
        form.pack(fill="x")
        self.debt_creditor = self.entry(form, "Credor", 0, 0)
        self.debt_type = self.combo(form, "Tipo", 0, 1, ["Cartao", "Emprestimo", "Financiamento", "Parcelamento", "Outro"])
        self.debt_initial = self.entry(form, "Saldo inicial", 0, 2)
        self.debt_paid = self.entry(form, "Pago", 0, 3, "0")
        self.debt_rate = self.entry(form, "Juros mensal %", 0, 4, "0")
        self.debt_minimum = self.entry(form, "Parcela minima", 0, 5, "0")
        self.debt_due = self.entry(form, "Vencimento", 2, 0, date.today().isoformat())
        self.debt_strategy = self.entry(form, "Estrategia", 2, 1)
        ttk.Button(form, text="Adicionar divida", style="Primary.TButton", command=self.add_debt).grid(row=3, column=5, padx=6, sticky="ew")
        for col in range(6):
            form.columnconfigure(col, weight=1)

        actions = ttk.Frame(self.debts_tab)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Registrar pagamento da divida selecionada", command=self.pay_selected_debt).pack(side="left")

        listing = self.panel(self.debts_tab, "Dividas abertas")
        listing.pack(fill="both", expand=True)
        self.debt_tree = self.tree(
            listing,
            ["ID", "Credor", "Tipo", "Saldo", "Juros %", "Juros mes", "Parcela", "Vencimento", "Status", "Estrategia"],
            [60, 190, 110, 110, 80, 110, 110, 105, 130, 250],
        )
        self.debt_tree.pack(fill="both", expand=True)

    def _build_accounts(self) -> None:
        form_panel = self.panel(self.accounts_tab, "Nova conta gerencial")
        form_panel.pack(fill="x", pady=(0, 12))
        form = ttk.Frame(form_panel, style="Panel.TFrame")
        form.pack(fill="x")
        self.acc_code = self.entry(form, "Codigo", 0, 0)
        self.acc_name = self.entry(form, "Conta", 0, 1)
        self.acc_group = self.entry(form, "Grupo", 0, 2)
        self.acc_category = self.entry(form, "Categoria", 0, 3)
        self.acc_result = self.entry(form, "Resultado", 0, 4)
        self.acc_type = self.combo(form, "Tipo", 0, 5, ["Entrada", "Saida", "Transferencia"])
        ttk.Button(form, text="Adicionar conta", style="Primary.TButton", command=self.add_account).grid(row=3, column=5, sticky="ew", padx=6)
        for col in range(6):
            form.columnconfigure(col, weight=1)

        listing = self.panel(self.accounts_tab, "Plano de contas")
        listing.pack(fill="both", expand=True)
        self.account_tree = self.tree(
            listing,
            ["ID", "Codigo", "Conta", "Grupo", "Categoria", "Resultado", "Tipo", "Essencial"],
            [60, 90, 190, 150, 170, 180, 100, 80],
        )
        self.account_tree.pack(fill="both", expand=True)

    def _build_budget(self) -> None:
        form_panel = self.panel(self.budget_tab, "Limite mensal por categoria")
        form_panel.pack(fill="x", pady=(0, 12))
        form = ttk.Frame(form_panel, style="Panel.TFrame")
        form.pack(fill="x")
        self.budget_category = self.entry(form, "Categoria", 0, 0)
        self.budget_limit = self.entry(form, "Limite mensal", 0, 1)
        self.budget_hint = self.entry(form, "Acao sugerida", 0, 2)
        ttk.Button(form, text="Salvar limite", style="Primary.TButton", command=self.add_budget).grid(row=1, column=3, padx=6, sticky="ew")
        for col in range(4):
            form.columnconfigure(col, weight=1)

        listing = self.panel(self.budget_tab, "Orcamento x realizado")
        listing.pack(fill="both", expand=True)
        self.budget_tree = self.tree(
            listing,
            ["Categoria", "Limite", "Realizado", "Saldo", "% usado", "Status", "Acao"],
            [180, 110, 110, 110, 90, 110, 330],
        )
        self.budget_tree.pack(fill="both", expand=True)

    def _build_projection(self) -> None:
        form_panel = self.panel(self.projection_tab, "Premissas")
        form_panel.pack(fill="x", pady=(0, 12))
        form = ttk.Frame(form_panel, style="Panel.TFrame")
        form.pack(fill="x")
        self.proj_income = self.entry(form, "Receita mensal", 0, 0, "7200")
        self.proj_expense = self.entry(form, "Despesa mensal", 0, 1, "4400")
        self.proj_debt = self.entry(form, "Pagamento dividas", 0, 2, "1420")
        self.proj_invest = self.entry(form, "Aportes", 0, 3, "900")
        ttk.Button(form, text="Atualizar projecao", style="Primary.TButton", command=self.refresh_projection).grid(row=1, column=4, padx=6, sticky="ew")
        for col in range(5):
            form.columnconfigure(col, weight=1)

        listing = self.panel(self.projection_tab, "Fluxo de caixa projetado")
        listing.pack(fill="both", expand=True)
        self.proj_tree = self.tree(listing, ["Mes", "Saldo inicial", "Receitas", "Saidas", "Saldo final"], [120, 140, 140, 140, 140])
        self.proj_tree.pack(fill="both", expand=True)

    def entry(self, parent: ttk.Frame, label: str, row: int, col: int, value: str = "") -> ttk.Entry:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=col, padx=6, sticky="w")
        item = ttk.Entry(parent)
        item.insert(0, value)
        item.grid(row=row + 1, column=col, padx=6, pady=(3, 8), sticky="ew")
        return item

    def combo(self, parent: ttk.Frame, label: str, row: int, col: int, values: list[str]) -> ttk.Combobox:
        ttk.Label(parent, text=label, style="Panel.TLabel").grid(row=row, column=col, padx=6, sticky="w")
        item = ttk.Combobox(parent, state="readonly", values=values)
        item.current(0)
        item.grid(row=row + 1, column=col, padx=6, pady=(3, 8), sticky="ew")
        return item

    def tree(self, parent: ttk.Frame, columns: list[str], widths: list[int]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings")
        for column, width in zip(columns, widths):
            tree.heading(column, text=column)
            tree.column(column, width=width, anchor="w")
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")
        return tree

    def refresh_all(self) -> None:
        self.refresh_accounts()
        self.refresh_dashboard()
        self.refresh_transactions()
        self.refresh_debts()
        self.refresh_budget()
        self.refresh_projection()

    def refresh_accounts(self) -> None:
        self.account_options = [(row["name"], row["id"]) for row in self.conn.execute("SELECT id, name FROM accounts WHERE active = 1 ORDER BY name")]
        self.tx_account["values"] = [name for name, _ in self.account_options]
        if self.account_options and not self.tx_account.get():
            self.tx_account.current(0)
        self.fill_tree(
            self.account_tree,
            [
                (r["id"], r["code"], r["name"], r["group_name"], r["category"], r["result_center"], r["type"], "Sim" if r["essential"] else "Nao")
                for r in self.conn.execute("SELECT * FROM accounts ORDER BY group_name, category, name")
            ],
        )

    def refresh_dashboard(self) -> None:
        summary = database.get_summary(self.conn)
        self.metric_labels["Saldo atual"].configure(text=money(summary.balance))
        self.metric_labels["Receitas do mes"].configure(text=money(summary.month_income))
        self.metric_labels["Gastos do mes"].configure(text=money(summary.month_expense))
        self.metric_labels["Dividas abertas"].configure(text=money(summary.open_debt))
        self.metric_labels["Juros mes"].configure(text=money(summary.monthly_interest))

        start, end = database.current_month_bounds()
        rows = self.conn.execute(
            """
            SELECT a.group_name, ABS(SUM(t.amount)) AS total
            FROM transactions t
            LEFT JOIN accounts a ON a.id = t.account_id
            WHERE t.amount < 0 AND t.tx_date >= ? AND t.tx_date < ?
            GROUP BY a.group_name
            ORDER BY total DESC
            """,
            (start, end),
        ).fetchall()
        total = sum(float(row["total"]) for row in rows) or 1
        self.fill_tree(self.group_tree, [(r["group_name"] or "Sem grupo", money(r["total"]), percent(float(r["total"]) / total * 100)) for r in rows])

        alerts = []
        if summary.overdue_debts:
            alerts.append(f"- {summary.overdue_debts} divida(s) vencida(s).")
        if summary.unclassified:
            alerts.append(f"- {summary.unclassified} lancamento(s) sem classificacao.")
        if summary.month_expense > summary.month_income * 0.75 and summary.month_income > 0:
            alerts.append("- Gastos do mes acima de 75% das receitas.")
        alerts.append(f"- Juros mensal estimado: {money(summary.monthly_interest)}.")
        alerts.append("- Proximos vencimentos:")
        for debt in self.conn.execute("SELECT * FROM debts WHERE active = 1 ORDER BY due_date LIMIT 5"):
            remaining = max(float(debt["initial_balance"]) - float(debt["paid_amount"]), 0)
            alerts.append(f"  {debt['creditor']}: {money(remaining)} - {debt_status(debt)}")
        self.alert_text.configure(state="normal")
        self.alert_text.delete("1.0", "end")
        self.alert_text.insert("1.0", "\n".join(alerts))
        self.alert_text.configure(state="disabled")

    def refresh_transactions(self) -> None:
        rows = self.conn.execute(
            """
            SELECT t.id, t.tx_date, t.description, t.amount, a.name AS account, a.group_name,
                   a.category, a.result_center, t.source
            FROM transactions t
            LEFT JOIN accounts a ON a.id = t.account_id
            ORDER BY t.tx_date DESC, t.id DESC
            LIMIT 500
            """
        )
        self.fill_tree(
            self.tx_tree,
            [(r["id"], r["tx_date"], r["description"], money(r["amount"]), r["account"] or "Classificar", r["group_name"] or "", r["category"] or "", r["result_center"] or "", r["source"]) for r in rows],
        )

    def refresh_debts(self) -> None:
        rows = []
        for r in self.conn.execute("SELECT * FROM debts WHERE active = 1 ORDER BY due_date"):
            remaining = max(float(r["initial_balance"]) - float(r["paid_amount"]), 0)
            monthly_interest = remaining * float(r["monthly_interest_rate"]) / 100
            rows.append(
                (
                    r["id"],
                    r["creditor"],
                    r["debt_type"],
                    money(remaining),
                    percent(r["monthly_interest_rate"]),
                    money(monthly_interest),
                    money(r["minimum_payment"]),
                    r["due_date"] or "",
                    debt_status(r),
                    r["strategy"] or "",
                )
            )
        self.fill_tree(self.debt_tree, rows)

    def refresh_budget(self) -> None:
        start, end = database.current_month_bounds()
        rows = []
        for r in self.conn.execute("SELECT * FROM budgets WHERE active = 1 ORDER BY category"):
            realized = abs(
                self.conn.execute(
                    """
                    SELECT COALESCE(SUM(t.amount), 0)
                    FROM transactions t
                    JOIN accounts a ON a.id = t.account_id
                    WHERE t.amount < 0 AND a.category = ? AND t.tx_date >= ? AND t.tx_date < ?
                    """,
                    (r["category"], start, end),
                ).fetchone()[0]
            )
            limit = float(r["monthly_limit"])
            balance = limit - realized
            used = realized / limit * 100 if limit else 0
            status = "Estourado" if realized > limit else "Atencao" if used >= 85 else "OK"
            rows.append((r["category"], money(limit), money(realized), money(balance), percent(used), status, r["action_hint"] or ""))
        self.fill_tree(self.budget_tree, rows)

    def refresh_projection(self) -> None:
        try:
            income = float(self.proj_income.get().replace(",", "."))
            expense = float(self.proj_expense.get().replace(",", "."))
            debt_payment = float(self.proj_debt.get().replace(",", "."))
            invest = float(self.proj_invest.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Projecao", "Premissas precisam ser numericas.")
            return
        balance = database.get_summary(self.conn).balance
        today = date.today().replace(day=1)
        rows = []
        for idx in range(12):
            month = today.month + idx
            year = today.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            label = f"{month:02d}/{year}"
            start_balance = balance
            outflow = expense + debt_payment + invest
            balance = balance + income - outflow
            rows.append((label, money(start_balance), money(income), money(outflow), money(balance)))
        self.fill_tree(self.proj_tree, rows)

    def fill_tree(self, tree: ttk.Treeview, rows: list[tuple] | list[sqlite3.Row]) -> None:
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", "end", values=tuple(row))

    def selected_account_id(self) -> int | None:
        name = self.tx_account.get()
        return dict(self.account_options).get(name)

    def add_manual_transaction(self) -> None:
        try:
            amount = float(self.tx_amount.get().replace(",", "."))
            date.fromisoformat(self.tx_date.get())
        except ValueError:
            messagebox.showerror("Lancamento", "Data ou valor invalido.")
            return
        if not self.tx_desc.get().strip():
            messagebox.showerror("Lancamento", "Informe a descricao.")
            return
        add_transaction(
            self.conn,
            self.tx_date.get(),
            self.tx_desc.get().strip(),
            amount,
            self.selected_account_id(),
            "Manual",
            None,
            self.tx_counterparty.get().strip() or None,
            None,
        )
        self.tx_desc.delete(0, "end")
        self.tx_amount.delete(0, "end")
        self.tx_counterparty.delete(0, "end")
        self.refresh_all()

    def add_debt(self) -> None:
        try:
            initial = float(self.debt_initial.get().replace(",", "."))
            paid = float(self.debt_paid.get().replace(",", "."))
            rate = float(self.debt_rate.get().replace(",", "."))
            minimum = float(self.debt_minimum.get().replace(",", "."))
            date.fromisoformat(self.debt_due.get())
        except ValueError:
            messagebox.showerror("Divida", "Valores ou vencimento invalidos.")
            return
        if not self.debt_creditor.get().strip():
            messagebox.showerror("Divida", "Informe o credor.")
            return
        self.conn.execute(
            """
            INSERT INTO debts
            (creditor, debt_type, opened_at, initial_balance, paid_amount, monthly_interest_rate, minimum_payment, due_date, strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.debt_creditor.get().strip(),
                self.debt_type.get(),
                date.today().isoformat(),
                initial,
                paid,
                rate,
                minimum,
                self.debt_due.get(),
                self.debt_strategy.get().strip(),
            ),
        )
        self.conn.commit()
        self.refresh_all()

    def pay_selected_debt(self) -> None:
        selected = self.debt_tree.selection()
        if not selected:
            messagebox.showinfo("Dividas", "Selecione uma divida.")
            return
        debt_id = int(self.debt_tree.item(selected[0], "values")[0])
        amount = simple_amount_dialog(self, "Pagamento", "Valor pago:")
        if amount and amount > 0:
            add_debt_payment(self.conn, debt_id, amount)
            self.refresh_all()

    def add_account(self) -> None:
        values = [self.acc_code.get().strip(), self.acc_name.get().strip(), self.acc_group.get().strip(), self.acc_category.get().strip(), self.acc_result.get().strip(), self.acc_type.get()]
        if any(not item for item in values):
            messagebox.showerror("Plano de contas", "Preencha todos os campos.")
            return
        try:
            self.conn.execute(
                """
                INSERT INTO accounts (code, name, group_name, category, result_center, type, essential)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                values,
            )
            self.conn.commit()
        except sqlite3.IntegrityError as exc:
            messagebox.showerror("Plano de contas", f"Conta ou codigo ja existe.\n{exc}")
            return
        self.refresh_all()

    def add_budget(self) -> None:
        try:
            limit = float(self.budget_limit.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Orcamento", "Limite invalido.")
            return
        category = self.budget_category.get().strip()
        if not category:
            messagebox.showerror("Orcamento", "Informe a categoria.")
            return
        self.conn.execute(
            """
            INSERT INTO budgets (category, monthly_limit, action_hint)
            VALUES (?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit, action_hint = excluded.action_hint, active = 1
            """,
            (category, limit, self.budget_hint.get().strip()),
        )
        self.conn.commit()
        self.refresh_all()

    def import_ofx(self) -> None:
        path = filedialog.askopenfilename(title="Importar OFX", filetypes=[("OFX/QFX", "*.ofx *.qfx"), ("Todos", "*.*")])
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        imported = 0
        skipped = 0
        for item in parse_ofx(text):
            account_id = database.find_account_for_description(self.conn, item.description)
            ok = add_transaction(self.conn, item.posted_at, item.description, item.amount, account_id, "OFX", item.external_id)
            imported += 1 if ok else 0
            skipped += 0 if ok else 1
        self.refresh_all()
        messagebox.showinfo("Importacao OFX", f"{imported} lancamento(s) importado(s).\n{skipped} duplicado(s) ignorado(s).")

    def backup_json(self) -> None:
        path = filedialog.asksaveasfilename(title="Salvar backup", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        export_backup(self.conn, Path(path))
        messagebox.showinfo("Backup", "Backup JSON salvo.")

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(title="Exportar lancamentos", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        export_transactions_csv(self.conn, Path(path))
        messagebox.showinfo("Exportacao", "Lancamentos exportados em CSV.")


def simple_amount_dialog(parent: tk.Tk, title: str, prompt: str) -> float | None:
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry("320x140")
    dialog.transient(parent)
    dialog.grab_set()
    ttk.Label(dialog, text=prompt).pack(padx=16, pady=(16, 4), anchor="w")
    entry = ttk.Entry(dialog)
    entry.pack(fill="x", padx=16)
    entry.focus()
    result: dict[str, float | None] = {"value": None}

    def confirm() -> None:
        try:
            result["value"] = float(entry.get().replace(",", "."))
            dialog.destroy()
        except ValueError:
            messagebox.showerror(title, "Valor invalido.", parent=dialog)

    ttk.Button(dialog, text="Confirmar", command=confirm).pack(pady=14)
    parent.wait_window(dialog)
    return result["value"]


def main() -> None:
    app = FinanceApp()
    app.mainloop()

from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner


def test_migrations_are_idempotent(tmp_path):
    con = Database(tmp_path / "f.db").connect()
    try:
        runner = MigrationRunner()
        expected = len(list(runner.migrations_dir.glob("*.sql")))
        runner.apply_all(con)
        runner.apply_all(con)
        assert con.execute("select count(*) from schema_migrations").fetchone()[0] == expected
    finally:
        con.close()


def test_all_migrations_create_required_financial_columns(tmp_path):
    con = Database(tmp_path / "f.db").connect()
    try:
        MigrationRunner().apply_all(con)
        columns = {row[1] for row in con.execute("pragma table_info(financial_entry)")}
        required = {
            "competence_date",
            "due_date",
            "settled_date",
            "description",
            "amount_cents",
            "entry_type",
            "status",
            "payment_method",
            "notes",
            "is_recurring",
            "installment_number",
            "installment_total",
            "recurrence_rule_id",
            "installment_group_id",
            "beneficiary_id",
            "category_id",
            "subcategory_id",
            "cost_center_id",
            "bank_account_id",
            "card_id",
            "asset_id",
            "expense_nature",
            "income_source_id",
            "created_at",
            "updated_at",
            "deleted_at",
        }
        assert required <= columns
    finally:
        con.close()

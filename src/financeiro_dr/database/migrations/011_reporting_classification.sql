CREATE TABLE IF NOT EXISTS income_source (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
INSERT OR IGNORE INTO income_source(name) VALUES
 ('Pró-labore/Salário'),('Distribuição de Lucros'),('Recebimentos de Empresas'),('Aluguéis'),
 ('Rendimentos de Investimentos'),('Reembolsos'),('Transferências Recebidas'),('Outras Receitas');
ALTER TABLE financial_entry ADD COLUMN expense_nature TEXT CHECK(expense_nature IN ('FIXA','VARIAVEL') OR expense_nature IS NULL);
ALTER TABLE financial_entry ADD COLUMN income_source_id INTEGER REFERENCES income_source(id);
UPDATE financial_entry SET expense_nature='VARIAVEL' WHERE entry_type='DESPESA' AND expense_nature IS NULL;

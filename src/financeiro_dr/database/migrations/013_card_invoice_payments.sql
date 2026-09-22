ALTER TABLE card_invoice_payment ADD COLUMN bank_account_id INTEGER REFERENCES bank_account(id);
CREATE INDEX IF NOT EXISTS idx_card_invoice_payment_bank ON card_invoice_payment(bank_account_id, paid_at);

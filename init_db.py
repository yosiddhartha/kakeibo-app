import sqlite3

def create_sample_db():
    # sample.dbというファイルが新しく作成されます
    conn = sqlite3.connect('sample.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            debit_account TEXT,
            credit_account TEXT,
            amount INTEGER,
            description TEXT
        )
    ''')
    
    # --- ダミーデータの挿入 ---
    cursor.execute("INSERT OR IGNORE INTO journal (date, debit_account, credit_account, amount, description) VALUES ('2026-10-25', '銀行預金', '給料', '100000', '給料入金')")
    cursor.execute("INSERT OR IGNORE INTO journal (date, debit_account, credit_account, amount, description) VALUES ('2026-10-26', '食費', 'クレジット未払金', '3500', 'スーパーで買い物')")
    cursor.execute("INSERT OR IGNORE INTO journal (date, debit_account, credit_account, amount, description) VALUES ('2026-10-27', 'クレジット未払金', '銀行預金', '3500', '引き落とし')")

    
    conn.commit()
    conn.close()
    print("個人情報を含まない sample.db を作成しました！")

if __name__ == '__main__':
    create_sample_db()
import sys
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QComboBox, QMessageBox, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget)
from PyQt5.QtCore import Qt
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

class MyAccountBook(QWidget):
    def __init__(self):
        super().__init__()
        # 科目の定義と分類
        self.accounts = {
            '資産': ['現金', '銀行預金', '備品', '備品減価償却費累計額', '前払金', '仮払金'],
            '負債': ['クレジット未払金'],
            '純資産': ['元入金', '資本金', '繰越利益剰余金'],
            '費用': ['食費', '娯楽費', '日用品', '交通費', '電気代', 'ガス代', '水道代', 'ネット代', 'テレビ代',
                    '医療費', '教育費', '交際費', '減価償却費', '出産育児費用', 'その他費用', 
                    '支払家賃', '支払保険料', '所得税および住民税', '社会保険料'],
            '収益': ['給料', '手当', '受取利息', '給付金等', '雑所得']
        }
        self.init_db()  # データベースを使えるようにする
        self.initUI()  # 画面の部品（テーブルなど）を作る
        self.load_data()  # データをテーブルに読み込む
        self.update_ledger_accounts() # 元帳の科目リストを更新

    def init_db(self):
        """データベースとテーブルを作成する"""
        db_path = 'kakeibo.db'
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                debit_account TEXT,
                credit_account TEXT,
                amount INTEGER,
                description TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                purchase_date TEXT,
                purchase_amount INTEGER,
                useful_life INTEGER,
                category TEXT
            )
        ''')
        self.conn.commit()

    def initUI(self):
        self.setWindowTitle('複式簿記家計簿 v1.9 - 収支推移グラフ追加')
        self.setGeometry(100, 100, 1000, 850) # 画面サイズを指定

        main_layout = QVBoxLayout() # メインレイアウト　Verticalは縦方向に配置するレイアウト
        self.tabs = QTabWidget() # タブを作るための部品

        # タブのセットアップ
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget() # B/S用
        self.tab4 = QWidget() # P/L用
        self.tab5 = QWidget() # クレジットカード用
        self.tab6 = QWidget() # 固定資産台帳用
        self.tab7 = QWidget() # 収支推移グラフ用

        self.setup_input_tab()
        self.setup_ledger_tab()
        self.setup_bs_tab() # B/Sタブ作成
        self.setup_pl_tab() # P/Lタブ作成
        self.setup_credit_tab() # クレジットカードタブ作成
        self.setup_asset_tab() # 固定資産台帳タブ作成
        self.setup_graph_tab() # 収支推移グラフタブ作成

        self.tabs.addTab(self.tab1, "仕訳帳 (入力)")
        self.tabs.addTab(self.tab2, "総勘定元帳")
        self.tabs.addTab(self.tab3, "貸借対照表 (B/S)")
        self.tabs.addTab(self.tab4, "損益計算書 (P/L)")
        self.tabs.addTab(self.tab5, "クレジットカード")
        self.tabs.addTab(self.tab6, "固定資産台帳")
        self.tabs.addTab(self.tab7, "収支推移グラフ")

        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        
        # タブが切り替わったときにB/Sを更新する設定
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.show()

    def setup_input_tab(self):
        """仕訳入力タブのレイアウト"""
        layout = QVBoxLayout()
        # 入力項目（全科目をリストに結合）
        all_ac = sum(self.accounts.values(), []) 
       
        layout.addWidget(QLabel('日付 (YYYY-MM-DD):'))
        self.date_input = QLineEdit() # 日付を入力するフィールド
        layout.addWidget(self.date_input)
        
        layout.addWidget(QLabel('借方:'))
        self.debit_input = QComboBox() # 借方の科目を選択するコンボボックス
        self.debit_input.addItems(all_ac) # 借方の科目を追加
        layout.addWidget(self.debit_input)
        
        layout.addWidget(QLabel('貸方:'))
        self.credit_input = QComboBox() # 貸方の科目を選択するコンボボックス
        self.credit_input.addItems(all_ac) # 同じリストを使用
        layout.addWidget(self.credit_input)
        
        layout.addWidget(QLabel('金額:'))
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText('金額') # 金額を入力するフィールド 入力欄が空のときに表示されるテキスト
        layout.addWidget(self.amount_input)

        layout.addWidget(QLabel('摘要 (メモ):'))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText('例：スーパー〇〇、昼食代など')
        layout.addWidget(self.desc_input)

        # 登録ボタン
        btn_save = QPushButton('仕訳を登録')
        btn_save.clicked.connect(self.save_data) # ボタンクリックで関数を呼ぶ
        layout.addWidget(btn_save)

        # 取引履歴テーブル
        self.table = QTableWidget()
        self.table.setColumnCount(6) # ID, 日付, 借方, 貸方, 金額, 摘要
        self.table.setHorizontalHeaderLabels(['ID', '日付', '借方', '貸方', '金額', '摘要'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # 削除ボタン
        btn_delete = QPushButton('選択した行を削除')
        btn_delete.setStyleSheet("background-color: #ffcccc;")
        btn_delete.clicked.connect(self.delete_data)
        layout.addWidget(btn_delete)

        self.tab1.setLayout(layout)

    def setup_ledger_tab(self):
        """総勘定元帳タブのレイアウト"""
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel('表示する科目を選択:'))
        self.ledger_combo = QComboBox()
        self.ledger_combo.currentTextChanged.connect(self.load_ledger) # 選択が変わったら自動更新
        layout.addWidget(self.ledger_combo)

        self.ledger_table = QTableWidget()
        self.ledger_table.setColumnCount(6) # 日付、相手勘定、借方、貸方、残高、摘要
        self.ledger_table.setHorizontalHeaderLabels(['日付', '相手勘定', '借方', '貸方', '残高', '摘要'])
        self.ledger_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.ledger_table)
        
        self.tab2.setLayout(layout)

    def setup_bs_tab(self):
        """B/Sタブのレイアウト（左右2カラム）"""
        layout = QVBoxLayout()
        layout.addWidget(QLabel('--- 貸借対照表 (現在) ---'))

        h_layout = QHBoxLayout()
        
        # 左側：資産の部
        self.bs_asset_table = QTableWidget()
        self.bs_asset_table.setColumnCount(2)
        self.bs_asset_table.setHorizontalHeaderLabels(['資産の部', '金額'])
        self.bs_asset_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        h_layout.addWidget(self.bs_asset_table)

        # 右側：負債・純資産の部
        self.liab_table = QTableWidget()
        self.liab_table.setColumnCount(2)
        self.liab_table.setHorizontalHeaderLabels(['負債・純資産の部', '金額'])
        self.liab_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        h_layout.addWidget(self.liab_table)

        layout.addLayout(h_layout)
        self.tab3.setLayout(layout)

    def setup_pl_tab(self):
        """P/Lタブのレイアウト"""
        layout = QVBoxLayout()
        
        # 月を選択するエリア
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel('表示月を選択:'))
        self.month_combo = QComboBox()
        self.month_combo.currentTextChanged.connect(self.refresh_pl) # 月を変えたら自動更新
        h_layout.addWidget(self.month_combo)
        
        # 月リストを更新するボタン
        btn_update_months = QPushButton('月リストを更新')
        btn_update_months.clicked.connect(self.update_month_list)
        h_layout.addWidget(btn_update_months)
        
        layout.addLayout(h_layout)

        # P/L表示用テーブル
        self.pl_table = QTableWidget()
        self.pl_table.setColumnCount(2)
        self.pl_table.setHorizontalHeaderLabels(['科目', '金額'])
        self.pl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.pl_table)
        
        self.tab4.setLayout(layout)
    
    def setup_credit_tab(self):
        """クレジットカード管理タブのレイアウト"""
        layout = QVBoxLayout()
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel('締め月を選択 (15日締め):'))
        self.card_month_combo = QComboBox()
        self.card_month_combo.currentTextChanged.connect(self.refresh_credit_status)
        h_layout.addWidget(self.card_month_combo)
        
        layout.addLayout(h_layout)

        # 支払予定額の表示
        self.credit_summary_label = QLabel('支払予定額: 0 円')
        self.credit_summary_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #d32f2f;")
        layout.addWidget(self.credit_summary_label)
        
        layout.addWidget(QLabel('--- 対象期間の利用明細 ---'))
        
        self.credit_detail_table = QTableWidget()
        self.credit_detail_table.setColumnCount(4)
        self.credit_detail_table.setHorizontalHeaderLabels(['日付', '借方(内容)', '金額', '摘要'])
        self.credit_detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.credit_detail_table)
        
        self.tab5 = QWidget() # 5つ目のタブとして作成
        self.tab5.setLayout(layout)
        self.tabs.addTab(self.tab5, "カード決済確認")
    
    def setup_asset_tab(self):
        """固定資産台帳タブ"""
        layout = QVBoxLayout()
        
        # 入力フォーム
        form_layout = QHBoxLayout()
        self.asset_name = QLineEdit(); self.asset_name.setPlaceholderText("資産名 (例: Mac Book)")
        self.asset_price = QLineEdit(); self.asset_price.setPlaceholderText("取得価額")
        self.asset_life = QLineEdit(); self.asset_life.setPlaceholderText("耐用年数(年)")
        self.asset_date = QLineEdit(); self.asset_date.setPlaceholderText("購入日(YYYY-MM-DD)")
        btn_reg = QPushButton("資産登録")
        btn_reg.clicked.connect(self.register_asset)
        
        for w in [self.asset_name, self.asset_price, self.asset_life, self.asset_date, btn_reg]:
            form_layout.addWidget(w)
        layout.addLayout(form_layout)

        # 台帳テーブル
        self.asset_table = QTableWidget()
        self.asset_table.setColumnCount(6)
        self.asset_table.setHorizontalHeaderLabels(['ID', '資産名', '購入日', '取得価額', '残存価額', '月額償却費'])
        self.asset_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.asset_table)
        
        # 償却実行ボタン
        btn_depreciate = QPushButton("今月分の減価償却を仕訳帳に一括登録")
        btn_depreciate.setStyleSheet("background-color: #e3f2fd; font-weight: bold; height: 40px;")
        btn_depreciate.clicked.connect(self.run_depreciation)
        layout.addWidget(btn_depreciate)

        self.tab6 = QWidget()
        self.tab6.setLayout(layout)
        self.tabs.addTab(self.tab6, "固定資産台帳")

    def setup_graph_tab(self):
        """収支推移グラフタブ"""
        layout = QVBoxLayout()
        
        # グラフを描画するキャンバス
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        btn_refresh = QPushButton("グラフを更新")
        btn_refresh.clicked.connect(self.refresh_graph)
        layout.addWidget(btn_refresh)

        self.tab7 = QWidget()
        self.tab7.setLayout(layout)
        self.tabs.addTab(self.tab7, "収支推移分析")

    def update_ledger_accounts(self):
        """元帳タブのコンボボックスを更新"""
        self.ledger_combo.clear()
        self.ledger_combo.addItems(sum(self.accounts.values(), [])) # 全科目を追加

    def save_data(self):
        """入力されたデータをSQLiteに保存する"""
        if not self.date_input.text() or not self.amount_input.text():
            QMessageBox.warning(self, 'エラー', '日付と金額を入力してください')
            return

        try:
            # 日付形式のバリデーション
            date_str = self.date_input.text().strip()  # 前後の空白を削除
            try:
                datetime.strptime(date_str, '%Y-%m-%d')  # YYYY-MM-DD形式を検証
            except ValueError:
                QMessageBox.warning(self, 'エラー', '日付は YYYY-MM-DD 形式で入力してください')
                return
            
            # 金額を整数に変換して仮保存 SQLインジェクション対策のためにプレースホルダを使用
            self.cursor.execute('''
                INSERT INTO journal (date, debit_account, credit_account, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (date_str, self.debit_input.currentText(), self.credit_input.currentText(), int(self.amount_input.text()), self.desc_input.text()))
            self.conn.commit() # データベースに変更を保存
            QMessageBox.information(self, '完了', 'データを保存しました！')
            self.load_data() # テーブルを更新
            self.load_ledger() # 元帳も更新
            self.desc_input.clear() # 保存後に摘要欄をクリア
            self.amount_input.clear() # 入力欄をリセット
        except ValueError:
            QMessageBox.warning(self, 'エラー', '入力内容を確認してください（金額は数字で）')
    
    # 削除処理
    def delete_data(self):
        # 1. 選択されている行を取得
        current_row = self.table.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(self, 'エラー', '削除したい行を選択してください')
            return

        # 2. 選択行のID（0列目）を取得
        record_id = self.table.item(current_row, 0).text()

        # 3. 確認ダイアログを表示
        reply = QMessageBox.question(self, '確認', f'ID: {record_id} のデータを削除しますか？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 4. DBから削除実行
            self.cursor.execute('DELETE FROM journal WHERE id = ?', (record_id,))
            self.conn.commit()
            # 5. 表示を更新
            self.load_data()
            QMessageBox.information(self, '完了', 'データを削除しました')
            self.load_ledger() # 元帳も更新

    def load_data(self):
        """データベースからデータを取得して表に表示する"""
        # SQLでデータを取得（IDの逆順＝新しい順）
        self.cursor.execute('SELECT id, date, debit_account, credit_account, amount, description FROM journal ORDER BY id DESC')
        rows = self.cursor.fetchall()

        # テーブルの行数を設定
        self.table.setRowCount(len(rows))

        # 1マスずつデータを埋めていく
        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                # QTableWidgetItemという部品にしてからセットする
                item = QTableWidgetItem(str(value))
                self.table.setItem(row_idx, col_idx, item)
    
    def load_ledger(self):
        """【Pandasを使用】選択された科目の元帳データを計算して表示"""
        target_account = self.ledger_combo.currentText()
        if not target_account: return

        # 全データをPandas DataFrameとして読み込む
        df = pd.read_sql_query("SELECT * FROM journal ORDER BY date ASC, id ASC", self.conn)
        
        if df.empty: return

        # 選択した科目が「借方」か「貸方」に出ている行だけ抽出
        ledger_df = df[(df['debit_account'] == target_account) | (df['credit_account'] == target_account)].copy()
        
        display_rows = []
        balance = 0
        
        for _, row in ledger_df.iterrows():
            date = row['date']
            amount = row['amount']
            desc = row['description'] if row['description'] else "" # 摘要を取得
            
            if row['debit_account'] == target_account:
                # 借方にその科目がある場合（資産の増加、費用の発生など）
                debit_val = amount
                credit_val = 0
                partner = row['credit_account']
                balance += amount
            else:
                # 貸方にその科目がある場合（資産の減少、負債の増加など）
                debit_val = 0
                credit_val = amount
                partner = row['debit_account']
                balance -= amount
            
            display_rows.append([date, partner, debit_val, credit_val, balance, desc])

        # テーブルへの表示
        self.ledger_table.setRowCount(len(display_rows))
        for r_idx, row_data in enumerate(display_rows):
            for c_idx, val in enumerate(row_data):
                self.ledger_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def update_month_list(self):
        """DBのデータ＋現在の日付から、選択可能な締め月リストを作成"""
        # 1. DBから既存の月を取得
        df = pd.read_sql_query("SELECT date FROM journal", self.conn)
        months = set()
        if not df.empty:
            df['month'] = df['date'].str[:7]
            months = set(df['month'].unique())
        
        # 2. 「今月」と「来月」を強制的に追加
        # (3月29日なら、3月15日締め分と4月15日締め分の両方を見たいはず)
        now = datetime.now()
        this_month = now.strftime("%Y-%m")
        # 来月を計算
        next_month_obj = (now.replace(day=28) + timedelta(days=5)) # 28日に5日足せば必ず翌月
        next_month = next_month_obj.strftime("%Y-%m")
        
        months.add(this_month)
        months.add(next_month)
        
        # 降順（新しい順）に並び替えてセット
        sorted_months = sorted(list(months), reverse=True)
        
        self.card_month_combo.blockSignals(True) # 更新中にイベントが飛ばないようにする
        current_sel = self.card_month_combo.currentText()
        self.card_month_combo.clear()
        self.card_month_combo.addItems(sorted_months)
        # 前回の選択を復元（なければ最新月）
        if current_sel in sorted_months:
            self.card_month_combo.setCurrentText(current_sel)
        self.card_month_combo.blockSignals(False)

        # P/Lタブの月コンボボックスも同様に更新
        self.month_combo.blockSignals(True)
        current_sel_pl = self.month_combo.currentText()
        self.month_combo.clear()
        self.month_combo.addItems(sorted_months)
        if current_sel_pl in sorted_months:
            self.month_combo.setCurrentText(current_sel_pl)
        self.month_combo.blockSignals(False)

    def on_tab_changed(self, index):
        if index == 2: # B/Sタブが開かれたとき
            self.refresh_bs()
        elif index == 3: # P/Lタブが開かれたとき
            self.update_month_list() # 最新の月リストを読み込み
            self.refresh_pl() # P/Lも更新
        elif index == 4: # クレジットカードタブが開かれたとき
            self.update_month_list() # 月リストを更新してからクレジット状況も更新
            self.refresh_credit_status() # クレジットカードの状況も更新
        elif index == 5: # 固定資産台帳タブが開かれたとき
            self.load_assets() # 台帳の内容を最新にする
        elif index == 6: # 収支推移グラフタブが開かれたとき
            self.refresh_graph() # グラフを最新にする

    def refresh_bs(self):
        """Pandasを使ってB/Sを計算して表示"""
        # データの読み込み
        df = pd.read_sql_query("SELECT * FROM journal", self.conn)

        # 全科目の残高（借方合計 - 貸方合計）を計算し、辞書形式にする
        # これにより、取引がない科目は 0円 として扱えるようになる
        debit_sum = df.groupby('debit_account')['amount'].sum()
        credit_sum = df.groupby('credit_account')['amount'].sum()
        
        def get_bal(acc):
            """科目名を受取り、現在の残高を返す補助関数"""
            d = debit_sum.get(acc, 0) # 借方合計（取引がない場合は0）
            c = credit_sum.get(acc, 0) # 貸方合計（取引がない場合は0）
            return int(d - c) # 借方 - 貸方

        # --- 【左側：資産の部】の作成 ---
        assets_display = []
        total_assets = 0
        for acc in self.accounts['資産']:
            bal = get_bal(acc)
            assets_display.append([acc, bal])
            total_assets += bal 
        # テーブルに表示
        self.bs_asset_table.setRowCount(len(assets_display))
        for i, (acc, bal) in enumerate(assets_display):
            self.bs_asset_table.setItem(i, 0, QTableWidgetItem(str(acc)))
            self.bs_asset_table.setItem(i, 1, QTableWidgetItem(str(bal)))

        # --- 【右側：負債・純資産の部】の作成 ---
        liab_display = []
        sum_liab = 0
        for acc in self.accounts['負債']:
            bal = get_bal(acc)
            # 負債は貸方残高が正なので、マイナスをかけて表示
            val = -bal
            liab_display.append([acc, val])
            sum_liab += val
        
        equity_display = []
        sum_equity_input = 0
        for acc in self.accounts['純資産']:
            bal = get_bal(acc)
            # 純資産も貸方残高が正なのでマイナスをかける
            val = -bal
            equity_display.append([acc, val])
            sum_equity_input += val
        
        # 当期純利益 = 資産合計 - (負債合計 + 入力済み純資産合計)
        net_income = total_assets - (sum_liab + sum_equity_input)
        total_equity = sum_equity_input + net_income
        total_right_side = sum_liab + total_equity

        # --- テーブルへの表示（左：資産） ---
        self.asset_table.setRowCount(len(assets_display) + 1)
        for i, (name, val) in enumerate(assets_display):
            self.asset_table.setItem(i, 0, QTableWidgetItem(name))
            self.asset_table.setItem(i, 1, QTableWidgetItem(f"{val:,}"))

        # 資産合計
        idx = len(assets_display)
        item_total_name = QTableWidgetItem("資産 総合計")
        item_total_val = QTableWidgetItem(f"{total_assets:,}")
        font = item_total_name.font()
        font.setBold(True)
        item_total_name.setFont(font)
        item_total_val.setFont(font)
        self.asset_table.setItem(idx, 0, item_total_name)
        self.asset_table.setItem(idx, 1, item_total_val)

        # --- テーブルへの表示（右：負債・純資産） ---
        # 表示用の行リストを組み立てる
        rows = []
        rows.extend(liab_display)
        rows.append(["【負債 小計】", sum_liab])
        rows.append(["", ""]) # 空行
        rows.extend(equity_display)
        rows.append(["当期純利益", net_income])
        rows.append(["【純資産 小計】", total_equity])
        rows.append(["", ""]) # 空行
        rows.append(["【負債・純資産 総合計】", total_right_side])

        self.liab_table.setRowCount(len(rows))
        for i, (name, val) in enumerate(rows):
            item_name = QTableWidgetItem(name)
            self.liab_table.setItem(i, 0, item_name)

            # 数値の表示（値が数値型の場合のみカンマ区切りにする）
            if isinstance(val, (int, float)):
                item_val = QTableWidgetItem(f"{val:,}")
            else:
                item_val = QTableWidgetItem("")

            # 合計行を少し協調（太字にするなど）
            if "合計" in name:
                font = item_name.font()
                font.setBold(True)
                item_name.setFont(font)
                item_val.setFont(font)
        
            self.liab_table.setItem(i, 1, item_val)

    def refresh_pl(self):
        """選択された月のP/Lを計算して表示"""
        target_month = self.month_combo.currentText()
        if not target_month: return

        # 指定された月のデータのみ取得
        query = "SELECT * FROM journal WHERE date LIKE ?"
        df = pd.read_sql_query(query, self.conn, params=(f"{target_month}%",))
        
        if df.empty:
            self.pl_table.setRowCount(0)
            return

        # 集計（借方合計 - 貸方合計）
        debit_sum = df.groupby('debit_account')['amount'].sum()
        credit_sum = df.groupby('credit_account')['amount'].sum()

        def get_bal(acc):
            return int(debit_sum.get(acc, 0) - credit_sum.get(acc, 0))

        revenue_rows = []
        expense_rows = []
        sum_rev = 0
        sum_exp = 0

        # 収益の集計 (貸方がプラスなので -bal)
        for acc in self.accounts['収益']:
            bal = get_bal(acc)
            val = -bal
            if val != 0:
                revenue_rows.append([acc, val])
                sum_rev += val

        # 費用の集計 (借方がプラスなので bal)
        for acc in self.accounts['費用']:
            bal = get_bal(acc)
            val = bal
            if val != 0:
                expense_rows.append([acc, val])
                sum_exp += val

        net_profit = sum_rev - sum_exp # 当期純利益

        # 表示用リストの作成
        display_data = []
        display_data.append(["【収益の部】", ""])
        display_data.extend(revenue_rows)
        display_data.append(["収益 合計", sum_rev])
        display_data.append(["", ""])
        display_data.append(["【費用の部】", ""])
        display_data.extend(expense_rows)
        display_data.append(["費用 合計", sum_exp])
        display_data.append(["", ""])
        display_data.append(["当期純利益", net_profit])

        # テーブルへ反映
        self.pl_table.setRowCount(len(display_data))
        for i, (name, val) in enumerate(display_data):
            item_n = QTableWidgetItem(name)
            self.pl_table.setItem(i, 0, item_n)
            
            if isinstance(val, (int, float)):
                item_v = QTableWidgetItem(f"{int(val):,}")
                self.pl_table.setItem(i, 1, item_v)
            else:
                self.pl_table.setItem(i, 1, QTableWidgetItem(""))

            # スタイル：合計行やタイトルを太字に
            if "合計" in name or "【" in name or "利益" in name:
                f = item_n.font()
                f.setBold(True)
                item_n.setFont(f)
                if self.pl_table.item(i, 1):
                    self.pl_table.item(i, 1).setFont(f)

    def refresh_credit_status(self):
        """15日締めの期間で集計（未来のデータがなくても期間を表示）"""
        target_month_str = self.card_month_combo.currentText()
        if not target_month_str: return

        # 締め日の計算 (例: 2026-04 を選んだら 2026-03-16 ～ 2026-04-15)
        end_date_obj = datetime.strptime(target_month_str + "-15", "%Y-%m-%d")
        # 前月の16日を算出
        first_day_of_target_month = end_date_obj.replace(day=1)
        last_day_of_prev_month = first_day_of_target_month - timedelta(days=1)
        start_date_obj = last_day_of_prev_month.replace(day=16)
        
        start_date = start_date_obj.strftime("%Y-%m-%d")
        end_date = end_date_obj.strftime("%Y-%m-%d")

        # クエリ：貸方が「クレジット未払金」のものを抽出
        query = """
            SELECT date, debit_account, amount, description 
            FROM journal 
            WHERE credit_account = 'クレジット未払金' 
            AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, self.conn, params=(start_date, end_date))
        
        total_bill = df['amount'].sum() if not df.empty else 0
        
        # ラベルを更新（今日が期間内でも、全期間の範囲を表示）
        self.credit_summary_label.setText(f"【{target_month_str}月15日締め】 支払予定額: {total_bill:,} 円")
        self.credit_summary_label.setToolTip(f"対象期間: {start_date} ～ {end_date}")

        # テーブル表示
        self.credit_detail_table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.credit_detail_table.setItem(i, 0, QTableWidgetItem(str(row['date'])))
            self.credit_detail_table.setItem(i, 1, QTableWidgetItem(str(row['debit_account'])))
            self.credit_detail_table.setItem(i, 2, QTableWidgetItem(f"{row['amount']:,}"))
            self.credit_detail_table.setItem(i, 3, QTableWidgetItem(str(row['description'])))

    def register_asset(self):
        """資産を台帳に登録（この時点では仕訳は作らず、台帳への登録のみ）"""
        try:
            self.cursor.execute('''
                INSERT INTO assets (name, purchase_date, purchase_amount, useful_life)
                VALUES (?, ?, ?, ?)
            ''', (self.asset_name.text(), self.asset_date.text(), 
                  int(self.asset_price.text()), int(self.asset_life.text())))
            self.conn.commit()
            self.load_assets()
            QMessageBox.information(self, "完了", "資産を台帳に登録しました。購入時の仕訳は別途『仕訳帳』で入力してください。")
        except:
            QMessageBox.warning(self, "エラー", "入力内容を確認してください。")

    def load_assets(self):
        """台帳の表示と現在の価値（残存価額）の計算"""
        self.cursor.execute("SELECT * FROM assets")
        rows = self.cursor.fetchall()
        self.asset_table.setRowCount(len(rows))
        
        today = datetime.now()
        
        for i, row in enumerate(rows):
            asset_id, name, p_date, p_amount, life = row[0], row[1], row[2], row[3], row[4]
            
            # 月額償却費の計算 (定額法)
            monthly_dep = p_amount / (life * 12)
            
            # 経過月数の計算
            start_date = datetime.strptime(p_date, "%Y-%m-%d")
            elapsed_months = (today.year - start_date.year) * 12 + (today.month - start_date.month)
            elapsed_months = max(0, elapsed_months)
            
            # 残存価額 (1円まで下がるものとする)
            current_val = max(1, p_amount - (monthly_dep * elapsed_months))
            
            # テーブル反映
            data = [asset_id, name, p_date, f"{p_amount:,}", f"{int(current_val):,}", f"{int(monthly_dep):,}"]
            for j, val in enumerate(data):
                self.asset_table.setItem(i, j, QTableWidgetItem(str(val)))

    def run_depreciation(self):
        """今月の減価償却費を自動仕訳"""
        today_month = datetime.now().strftime("%Y-%m")
        self.cursor.execute("SELECT name, purchase_amount, useful_life FROM assets")
        assets = self.cursor.fetchall()
        
        count = 0
        for name, p_amount, life in assets:
            monthly_dep = int(p_amount / (life * 12))
            
            # 仕訳登録 (借方: 減価償却費 / 貸方: 備品減価償却費累計額)
            self.cursor.execute('''
                INSERT INTO journal (date, debit_account, credit_account, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now().strftime("%Y-%m-%d"), "減価償却費", "備品減価償却費累計額", monthly_dep, f"減価償却: {name}"))
            count += 1
            
        self.conn.commit()
        QMessageBox.information(self, "実行完了", f"{count}件の資産について減価償却費を計上しました。")
        self.load_data() # 仕訳帳を更新

    def refresh_graph(self):
        """月ごとの収支推移をグラフ化"""
        df = pd.read_sql_query("SELECT date, debit_account, credit_account, amount FROM journal", self.conn)
        if df.empty: return

        # データクリーニング：全角スペースなどを削除
        df['date'] = df['date'].str.strip()  # 前後の空白を削除
        
        try:
            df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d', errors='coerce')
            # パース失敗したデータ（NaT）を削除
            df = df.dropna(subset=['date'])
            if df.empty:
                QMessageBox.warning(self, 'エラー', '有効な日付データが見つかりません')
                return
        except Exception as e:
            QMessageBox.warning(self, 'エラー', f'日付パースエラー: {str(e)}')
            return
        df = df.sort_values('date')

        # 月ごとの収益・費用を算出する準備
        months = sorted(df['date'].dt.to_period('M').unique())
        plot_data = []

        for m in months:
            m_df = df[df['date'].dt.to_period('M') == m]
            
            # 収益合計 (貸方に収益科目がある合計 - 借方にある合計)
            rev = m_df[m_df['credit_account'].isin(self.accounts['収益'])]['amount'].sum() - \
                  m_df[m_df['debit_account'].isin(self.accounts['収益'])]['amount'].sum()
            
            # 費用合計 (借方に費用科目がある合計 - 貸方にある合計)
            exp = m_df[m_df['debit_account'].isin(self.accounts['費用'])]['amount'].sum() - \
                  m_df[m_df['credit_account'].isin(self.accounts['費用'])]['amount'].sum()
            
            # 減価償却費も費用に含める（もし「減価償却費」という科目が費用リストにあれば自動計算されます）
            # もしリストにない場合でも、以下で明示的に足すことも可能です
            
            plot_data.append({
                'month': m.to_timestamp(),
                'revenue': int(rev),
                'expense': int(exp),
                'profit': int(rev - exp)
            })

        pdf = pd.DataFrame(plot_data)

        # グラフの描画
        self.ax.clear()
        
        # 日本語フォントの設定（WindowsならMS Gothicなど）
        plt.rcParams['font.family'] = 'Meiryo' 

        x = pdf['month']
        width = 15 # 棒の太さ（日単位）

        # 収益と費用の棒グラフ
        self.ax.bar(x - timedelta(days=7), pdf['revenue'], width=width, label='収益', color='#4caf50', alpha=0.7)
        self.ax.bar(x + timedelta(days=7), pdf['expense'], width=width, label='費用', color='#f44336', alpha=0.7)
        
        # 利益の折れ線グラフ
        self.ax.plot(x, pdf['profit'], label='今月の利益(貯金)', color='#2196f3', marker='o', linewidth=2)

        def comma_format(x, pos):
            """Y軸の数値をカンマ区切りにするフォーマッタ"""
            return f'{int(x):,}'
        
        self.ax.yaxis.set_major_formatter(FuncFormatter(comma_format))

        self.ax.yaxis.get_offset_text().set_visible(False) # 例えば「1e6」などのオフセット表記を消す

        # 補助線と装飾
        self.ax.axhline(0, color='black', linewidth=0.8) # ゼロライン
        self.ax.set_title("月次収支推移 (収益 vs 費用)")
        self.ax.set_ylabel("金額 (円)")
        self.ax.legend()
        
        # X軸のフォーマット（月表示）
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        self.figure.autofmt_xdate() # ラベルを斜めにして被りを防ぐ

        self.figure.tight_layout() # レイアウトの調整

        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyAccountBook()
    sys.exit(app.exec_())
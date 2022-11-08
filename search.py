#!/usr/bin/python

import os
import pandas as pd

from qgis.gui import QgsFilterLineEdit
from qgis.PyQt.QtCore import Qt, QSize, QModelIndex
from qgis.PyQt.QtWidgets import QFrame, QGridLayout, QCompleter, QLabel, QSizePolicy
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon

from .main import df_from_db

ICON_PATH = os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'ui' + os.path.sep
CASSES = [
        ['midas_id', '(Numer złoża w bazie MIDAS)', 'rgb(255, 0, 0)'],
        ['midas_name', '(Nazwa złoża w bazie MIDAS)', 'rgb(180, 0, 0)'],
        ['cbdg_id', '(Numer dokumentacji w bazie CBDG)', 'rgb(150, 40, 140)'],
        ['inw_id', '(Archiwalny numer inwentarzowy dokumentacji)', 'rgb(0, 90, 180)'],
        ['kat_id', '(Archiwalny numer katalogowy dokumentacji)', 'rgb(0, 128, 255)'],
        ['tag', '(Słowo kluczowe przypisane do dokumentacji)', 'rgb(80, 150, 0)'],
        ['phrase', '(Fraza wyszukana w tytułach dokumentacji)', 'rgb(100, 100, 100)']
    ]
RAW_SQLS = [
            ['midas_id', "SELECT d.dok_id, d.cbdg_id, d.t_nr_inw, d.b_nr_kat, d.t_dok_tytul, d.i_dok_rok, d.t_dok_path FROM dokumentacje d INNER JOIN dokumentacje_midas dm ON d.dok_id = dm.dok_id WHERE dm.midas_id = {val}"],
            ['midas_name', "SELECT d.dok_id, d.cbdg_id, d.t_nr_inw, d.b_nr_kat, d.t_dok_tytul, d.i_dok_rok, d.t_dok_path FROM dokumentacje d INNER JOIN dokumentacje_midas dm ON d.dok_id = dm.dok_id INNER JOIN midas m ON m.midas_id = dm.midas_id WHERE m.t_zloze_nazwa = '{val}'"],
            ['cbdg_id', "SELECT dok_id, cbdg_id, t_nr_inw, b_nr_kat, t_dok_tytul, i_dok_rok, t_dok_path FROM dokumentacje d WHERE cbdg_id = {val}"],
            ['inw_id', "SELECT dok_id, cbdg_id, t_nr_inw, b_nr_kat, t_dok_tytul, i_dok_rok, t_dok_path FROM dokumentacje d WHERE t_nr_inw = '{val}' AND b_nr_kat = false"],
            ['kat_id', "SELECT dok_id, cbdg_id, t_nr_inw, b_nr_kat, t_dok_tytul, i_dok_rok, t_dok_path FROM dokumentacje d WHERE t_nr_inw = '{val}' AND b_nr_kat = true"],
            ['tag', "SELECT d.dok_id, d.cbdg_id, d.t_nr_inw, d.b_nr_kat, d.t_dok_tytul, d.i_dok_rok, d.t_dok_path FROM dokumentacje d INNER JOIN dokumentacje_tagi dt ON d.dok_id = dt.dok_id INNER JOIN tagi t ON dt.tag_id = t.tag_id WHERE t.t_tag = '{val}'"],
            ['phrase', "SELECT d.dok_id, d.cbdg_id, d.t_nr_inw, d.b_nr_kat, d.t_dok_tytul, d.i_dok_rok, d.t_dok_path FROM dokumentacje d WHERE d.t_dok_tytul ilike '%{val}%'"]
        ]

class DokFromTextSearcher(QFrame):
    """Widget tekstowej wyszukiwarki dokumentacji."""
    def __init__(self, *args):
        super().__init__(*args)
        self.df = self.dataindex_from_db()  # Dataframe z indeksami dokumentacji
        # Konfiguracja widget'ów:
        self.le_search = QgsFilterLineEdit(self)
        self.le_search.setShowSearchIcon(True)
        self.le_search.setShowClearButton(True)
        self.le_search.setPlaceholderText("Wyszukaj dokumentacje...")
        self.le_search.setFixedHeight(30)
        self.completer = QCompleter()
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setModelSorting(QCompleter.CaseSensitivelySortedModel)
        self.completer.setMaxVisibleItems(10)
        self.completer.setCaseSensitivity(False)
        self.completer.popup().setIconSize(QSize(69, 25))
        self.completer.setModel(self.create_index_model())
        self.le_search.setCompleter(self.completer)
        self.l_result_title = QLabel()
        self.l_result = QLabel()
        self.l_result.setTextFormat(Qt.RichText)
        self.l_result.setWordWrap(True)
        self.l_result.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        # Połączenia:
        self.completer.activated[QModelIndex].connect(self.completer_activated)
        self.le_search.returnPressed.connect(self.enter_pressed)
        # Kompozycja:
        lay = QGridLayout()
        lay.setContentsMargins(0, 0, 0, 5)
        lay.setSpacing(10)
        lay.addWidget(self.le_search, 0, 0, 1, 3)
        lay.addWidget(self.l_result_title, 1, 0, 1, 1)
        lay.setAlignment(self.l_result_title, Qt.AlignLeft | Qt.AlignTop)
        lay.addWidget(self.l_result, 1, 1, 1, 1)
        self.setLayout(lay)
        # Definicja zmiennych:
        self.dlg = self.parent()  # Referencja do dockwidget'u
        self.act_search = []  # Lista z nazwą i kategorią aktualnego wyszukiwania

    def __setattr__(self, attr, val):
        """Przechwycenie zmiany atrybutu."""
        super().__setattr__(attr, val)
        if attr == "act_search":
            self.search_update()
            if val:
                self.df_from_dok_search()

    def enter_pressed(self):
        """Aktualizacja parametrów wyszukiwania po wyczyszczeniu"""
        if len(self.le_search.text()) == 0:
            # Wyszukiwanie jest puste
            return
        if not self.completer.popup().isVisible() or self.completer.currentIndex().row() == -1:
            # Nie wykorzystano completer'a, wyszukiwanie frazy w tytułach dokumentacji
            self.act_search = [self.le_search.text(), "phrase"]
            self.le_search.setText("")
            self.le_search.clearFocus()

    def completer_activated(self, index):
        """Ustala parametry wyszukiwania po wyborze elementu z completer'a."""
        self.le_search.setText("")
        self.le_search.clearFocus()
        self.act_search = [index.data(), index.sibling(index.row(), 1).data()]

    def search_update(self):
        """Aktualizacja po zmianie parametrów wyszukiwania."""
        if not self.act_search:
            self.l_result_title.setText("   Aktualne wyszukiwanie jest puste.")
            self.l_result.setText("")
            return
        self.l_result_title.setText("   Aktualne wyszukiwanie:")
        for case in CASSES:
            if case[0] == self.act_search[1]:
                txt = f'<p style="color:{case[2]};"><b>{self.act_search[0]}</b> {case[1]}</p>'
                self.l_result.setText(txt)

    def dataindex_from_db(self):
        """Zwraca dataframe z pobranymi z db indeksami wszystkich dokumentacji."""
        cats = [
            [f"SELECT DISTINCT midas_id FROM dokumentacje_midas ORDER BY midas_id", 'midas_id'],
            [f"SELECT DISTINCT ON (m.t_zloze_nazwa) m.t_zloze_nazwa FROM dokumentacje_midas dm INNER JOIN midas m ON dm.midas_id = m.midas_id", 'midas_name'],
            [f"SELECT DISTINCT cbdg_id FROM dokumentacje ORDER BY cbdg_id", 'cbdg_id'],
            [f"SELECT DISTINCT t_nr_inw FROM dokumentacje WHERE b_nr_kat = false ORDER BY t_nr_inw", 'inw_id'],
            [f"SELECT DISTINCT t_nr_inw FROM dokumentacje WHERE b_nr_kat = true ORDER BY t_nr_inw", 'kat_id'],
            [f"SELECT DISTINCT t_tag FROM tagi ORDER BY t_tag", 'tag']
        ]
        df = pd.DataFrame(columns=['val', 'cat'])
        for cat in cats:
            tdf = df_from_db(cat[0], ['val'])
            tdf['val'] = tdf['val'].astype(str)
            tdf['cat'] = cat[1]
            df = pd.concat([df, tdf], axis=0)
        # Quasi-naturalne sortowanie, bez biblioteki 'natsort':
        df[['_str', '_int']] = df['val'].str.extract(r'([A-Za-zżźćńółęąśŻŹĆĄŚĘŁÓŃ]*)(\d*)')
        df['_str'] = df['_str'].astype('str').str.replace('ł', 'l').str.replace('Ł', 'L').str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        df['_int'] = pd.to_numeric(df['_int'], errors='coerce')
        df = df.sort_values(by=['_str', '_int'], ignore_index=True).drop(columns=['_str', '_int'])
        return df

    def create_index_model(self):
        """W oparciu o dataframe z indeksami dokumentacji (self.df) tworzy model danych do zasilenia QCompleter'a."""
        model = QStandardItemModel(len(self.df), 2)
        for index in self.df.to_records():
            item_1 = QStandardItem(index[1])
            item_1.setIcon(QIcon(f"{ICON_PATH}{index[2]}.png"))
            item_1.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_2 = QStandardItem(index[2])
            model.setItem(index[0], 0, item_1)
            model.setItem(index[0], 1, item_2)
        return model

    def df_from_dok_search(self):
        """Zwraca dataframe z danymi dokumentacji wyszukanymi wg parametrów 'self.act_search'."""
        sql = self.sql_parser()
        if not sql:
            return
        cols=['dok_id', 'cbdg_id', 'nr_inw', 'czy_nr_kat', 'tytul', 'rok', 'path']
        self.dlg.dok_df = df_from_db(sql, cols)

    def sql_parser(self):
        """Zwraca tekst sql z wartością pobraną z 'self.act_search'."""
        sql = None
        val = self.act_search[0]
        for raw_sql in RAW_SQLS:
            if raw_sql[0] == self.act_search[1]:
                sql = eval('f"{}"'.format(raw_sql[1]))
                break
        return sql

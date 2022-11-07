#!/usr/bin/python

import os
import pandas as pd

from qgis.gui import QgsFilterLineEdit
from qgis.PyQt.QtCore import Qt, QSize, QModelIndex
from qgis.PyQt.QtWidgets import QFrame, QVBoxLayout, QCompleter
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem, QIcon

from .main import df_from_db

ICON_PATH = os.path.dirname(os.path.realpath(__file__)) + os.path.sep + 'ui' + os.path.sep

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
        # Połączenia:
        self.completer.activated[QModelIndex].connect(self.completer_activated)
        # Kompozycja:
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.le_search)
        self.setLayout(lay)

    def completer_activated(self, index):
        """Odpalony po wyborze elementu z completer'a."""
        print(f"completer_activated: {index.data()}, {index.sibling(index.row(), 1).data()}")

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
        df['_int'] = pd.to_numeric(df['_int'], errors='coerce')
        df = df.sort_values(by=['_str', '_int'], key=self.locale_sorting, ignore_index=True).drop(columns=['_str', '_int'])
        return df

    def locale_sorting(self, x):
        """Uwzględnia polskie znaki przy sortowaniu."""
        if x.name == "_str":
            return x.astype('str').str.replace('ł', 'l').str.replace('Ł', 'L').str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        else:
            return x

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

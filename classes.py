#!/usr/bin/python

import os
import psycopg2
import psycopg2.extras
import pandas as pd

from configparser import ConfigParser
from qgis.PyQt.QtCore import Qt, QAbstractTableModel, pyqtProperty, pyqtSlot, QVariant, QModelIndex
from qgis.PyQt.QtWidgets import QMessageBox, QHeaderView

DB_SOURCE = "PGI"

class CfgPars(ConfigParser):
    """Parser parametrów konfiguracji połączenia z bazą danych."""
    def __init__(self, filename='database.ini', section=DB_SOURCE):
        super().__init__()
        self.filename = self.resolve(filename)
        self.section = section
        self.read(self.filename)  # Pobranie zawartości pliku
        if not self.has_section(section):
            raise AttributeError(f'Sekcja {section} nie istnieje w pliku {filename}!')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        return True

    def resolve(self, name):
        """Zwraca ścieżkę do folderu plugina wraz z nazwą pliku .ini."""
        basepath = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(basepath, name)

    def psycopg2(self):
        """Przekazanie parametrów połączenia z db za pośrednictwem Psycopg2."""
        db = {}  # Stworzenie słownika
        # Ładowanie parametrów do słownika
        params = self.items(self.section)
        for param in params:
            db[param[0]] = param[1]
        return db

    def uri(self):
        """Przekazanie parametrów połączenia z db za pośrednictwem Uri."""
        result = ""
        # Ładowanie parametrów do słownika
        params = self.items(self.section)
        for key, val in params:
            if key == "database":
                key = "dbname"
                val = str('"' + val + '"')
            elif key == "user":
                val = str('"' + val + '"')
            result += key + "=" + val + " "
        return result


class PgConn:
    """Połączenie z bazą PostgreSQL przez psycopg2."""
    _instance = None

    def __new__(cls):
        """Próba połączenia z db."""
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            try:
                with CfgPars() as cfg:
                    params = cfg.psycopg2()
                connection = cls._instance.connection = psycopg2.connect(**params)
                cursor = cls._instance.cursor = connection.cursor()
                cursor.execute("SELECT VERSION()")
                cursor.fetchone()
            except Exception as error:
                cls._instance.__error_msg("connection", error)
                cls._instance = None
                return
        return cls._instance

    def __init__(self):
        self.connection = self._instance.connection
        self.cursor = self._instance.cursor

    @classmethod
    def __error_msg(cls, case, error, *query):
        """Komunikator błędów."""
        if case == "connection":
            QMessageBox.critical(None, "Połączenie z bazą danych", "Połączenie nie zostało nawiązane. \n Błąd: {}".format(error))
        if case == "query":
            print('Błąd w trakcie wykonywania kwerendy "{}", {}'.format(query, error))

    def query_sel(self, query, all):
        """Wykonanie kwerendy SELECT."""
        try:
            self.cursor.execute(query)
            if all:
                result = self.cursor.fetchall()
            else:
                result = self.cursor.fetchone()
        except Exception as error:
            self.__error_msg("query", error, query)
            return
        else:
            return result
        finally:
            self.close()

    def query_pd(self, query, col_names):
        """Wykonanie kwerendy SELECT i zwrócenie dataframe'u."""
        try:
            self.cursor.execute(query)
            result = self.cursor.fetchall()
        except Exception as error:
            self.__error_msg("query", error, query)
            return None
        else:
            df = pd.DataFrame(result, columns=col_names)
            return df
        finally:
            self.close()

    def query_upd(self, query):
        """Wykonanie kwerendy UPDATE."""
        try:
            self.cursor.execute(query)
            result = self.cursor.rowcount
            if result > 0:
                self.connection.commit()
            else:
                self.connection.rollback()
        except Exception as error:
            self.__error_msg("query", error, query)
            self.connection.rollback()
            return
        else:
            return result
        finally:
            self.close()

    def query_upd_ret(self, query):
        """Wykonanie kwerendy UPDATE ze zwracaniem wartości."""
        try:
            self.cursor.execute(query)
            result = self.cursor.rowcount
            if result > 0:
                self.connection.commit()
            else:
                self.connection.rollback()
        except Exception as error:
            self.__error_msg("query", error, query)
            self.connection.rollback()
            return
        else:
            return self.cursor.fetchone()[0]
        finally:
            self.close()

    def query_exeval(self, query, values):
        """Wykonanie kwerendy EXECUTE_VALUES."""
        try:
            psycopg2.extras.execute_values(self.cursor, query, values)
            self.connection.commit()
        except Exception as error:
            self.__error_msg("query", error, query)
            return
        finally:
            self.close()

    def close(self):
        """Zamykanie połączenia i czyszczenie instancji."""
        if PgConn._instance is not None:
            self.cursor.close()
            self.connection.close()
            PgConn._instance = None


class DataFrameModel(QAbstractTableModel):
    """Podstawowy model tabeli zasilany przez pandas dataframe."""
    DtypeRole = Qt.UserRole + 1000
    ValueRole = Qt.UserRole + 1001

    def __init__(self, df=pd.DataFrame(), tv=None, col_names=[], parent=None):
        super(DataFrameModel, self).__init__(parent)
        self._dataframe = df
        self.col_names = col_names
        self.tv = tv  # Referencja do tableview
        self.tv.setModel(self)
        self.tv.selectionModel().selectionChanged.connect(lambda: self.layoutChanged.emit())
        self.tv.horizontalHeader().setSortIndicatorShown(False)
        self.tv.horizontalHeader().setSortIndicator(-1, 0)
        self.sort_col = -1
        self.sort_ord = 0

    def col_names(self, df, col_names):
        """Nadanie nazw kolumn tableview'u."""
        df.columns = col_names
        return df

    def sort_reset(self):
        """Wyłącza sortowanie po kolumnie."""
        self.tv.horizontalHeader().setSortIndicator(-1, 0)
        self.sort_col = -1
        self.sort_ord = 0

    def setDataFrame(self, dataframe):
        self.beginResetModel()
        self._dataframe = dataframe.copy()
        self.endResetModel()

    def dataFrame(self):
        return self._dataframe

    dataFrame = pyqtProperty(pd.DataFrame, fget=dataFrame, fset=setDataFrame)

    @pyqtSlot(int, Qt.Orientation, result=str)
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if self.col_names:
                    try:
                        return self.col_names[section]
                    except:
                        pass
                return self._dataframe.columns[section]
            else:
                return str(self._dataframe.index[section])
        return QVariant()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._dataframe.index)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return self._dataframe.columns.size

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount() \
            and 0 <= index.column() < self.columnCount()):
            return QVariant()
        row = self._dataframe.index[index.row()]
        col = self._dataframe.columns[index.column()]
        dt = self._dataframe[col].dtype
        try:
            val = self._dataframe.iloc[row][col]
        except:
            return QVariant()
        if role == DataFrameModel.ValueRole:
            return val
        if role == DataFrameModel.DtypeRole:
            return dt
        return QVariant()

    def roleNames(self):
        roles = {
            Qt.DisplayRole: b'display',
            DataFrameModel.DtypeRole: b'dtype',
            DataFrameModel.ValueRole: b'value'
        }
        return roles


class DokDFM(DataFrameModel):
    """Subklasa dataframemodel dla tableview wyświetlającą listę dokumentacji."""

    def __init__(self, df=pd.DataFrame(), tv=None, col_widths=[], col_names=[], parent=None):
        super().__init__(df, tv, col_names)
        self.tv = tv  # Referencja do tableview
        self.col_format(col_widths)

    def col_format(self, col_widths):
        """Formatowanie szerokości kolumn tableview'u."""
        cols = list(enumerate(col_widths, 0))
        for col in cols:
            self.tv.setColumnWidth(col[0], col[1])
        h_header = self.tv.horizontalHeader()
        h_header.setMinimumSectionSize(1)
        h_header.setFixedHeight(30)
        h_header.setDefaultSectionSize(30)
        h_header.setSectionResizeMode(QHeaderView.Interactive)
        h_header.setSectionResizeMode(1, QHeaderView.Stretch)
        h_header.resizeSection(0, 70)
        h_header.resizeSection(1, 400)
        h_header.resizeSection(2, 40)
        v_header = self.tv.verticalHeader()
        v_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tv.setColumnHidden(0, True)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount() \
            and 0 <= index.column() < self.columnCount()):
            return QVariant()
        row = self._dataframe.index[index.row()]
        col = self._dataframe.columns[index.column()]
        dt = self._dataframe[col].dtype
        val = self._dataframe.iloc[row][col]
        if role == Qt.DisplayRole:
            return str(val)
        elif role == Qt.TextAlignmentRole:

            if index.column() == 1:
                return Qt.AlignLeft + Qt.AlignVCenter
            else:
                return Qt.AlignHCenter + Qt.AlignVCenter
        elif role == DataFrameModel.ValueRole:
            return val
        if role == DataFrameModel.DtypeRole:
            return dt
        return QVariant()


class MapDFM(DataFrameModel):
    """Subklasa dataframemodel dla tableview wyświetlającą listę map wybranej dokumentacji."""

    def __init__(self, df=pd.DataFrame(), tv=None, col_names=[], parent=None):
        super().__init__(df, tv, col_names)
        self.tv = tv  # Referencja do tableview
        self.col_format()

    def col_format(self):
        """Formatowanie szerokości kolumn tableview'u."""
        h_header = self.tv.horizontalHeader()
        h_header.setMinimumSectionSize(1)
        h_header.setFixedHeight(30)
        h_header.setDefaultSectionSize(30)
        h_header.setSectionResizeMode(QHeaderView.Interactive)
        h_header.setSectionResizeMode(1, QHeaderView.Stretch)
        h_header.setSectionResizeMode(2, QHeaderView.Stretch)
        h_header.setSectionResizeMode(3, QHeaderView.Fixed)
        h_header.resizeSection(0, 70)
        h_header.resizeSection(1, 200)
        h_header.resizeSection(2, 200)
        h_header.resizeSection(3, 40)
        h_header.resizeSection(4, 40)
        v_header = self.tv.verticalHeader()
        v_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tv.setColumnHidden(0, True)
        self.tv.setColumnHidden(4, True)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount() \
            and 0 <= index.column() < self.columnCount()):
            return QVariant()
        row = self._dataframe.index[index.row()]
        col = self._dataframe.columns[index.column()]
        dt = self._dataframe[col].dtype
        val = self._dataframe.iloc[row][col]
        if role == Qt.DisplayRole:
            return str(val)
        elif role == Qt.TextAlignmentRole:
            if index.column() == 3:
                return Qt.AlignHCenter + Qt.AlignVCenter
            else:
                return Qt.AlignLeft + Qt.AlignVCenter
        elif role == DataFrameModel.ValueRole:
            return val
        if role == DataFrameModel.DtypeRole:
            return dt
        return QVariant()

# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NagArchMapDockWidget
                                 A QGIS plugin
 Import do projektu QGIS georeferencjonowanych załączników mapowych dokumentacji zgromadzonych w NAG PIG-PIB
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-10-13
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Dominik Szrek / PIG-PIB
        email                : dszr@pgi.gov.pl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import pandas as pd

from .main import df_from_db
from .search import DokFromTextSearcher
from .classes import DokDFM, MapDFM

from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsRasterLayer, QgsLayerTreeLayer
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QTimer
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.utils import iface


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'nag_archmap_dockwidget_base.ui'))

CRS_1992 = QgsCoordinateReferenceSystem("EPSG:2180")

class NagArchMapDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(NagArchMapDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://doc.qt.io/qt-5/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.proj = QgsProject.instance()  # Referencja do instancji projektu
        self.root = self.proj.layerTreeRoot()  # Referencja do drzewka legendy projektu
        self.canvas = iface.mapCanvas()  # Referencja do mapy
        self.txt_search = DokFromTextSearcher(self)
        self.frm_search.layout().addWidget(self.txt_search)
        self.init_void = True
        self.init_tv_dok()
        self.init_tv_map()
        self.dok_df = pd.DataFrame(columns=['dok_id', 'cbdg_id', 'nr_inw', 'czy_nr_kat', 'tytul', 'rok', 'path'])
        self.map_df = pd.DataFrame(columns=['checkbox', 'map_id', 'nazwa', 'warstwa', 'rok', 'plik'])
        self.dok_id = None
        self.cbdg_id = None
        self.main_grp = None
        self.dok_grp = None
        self.init_void = False
        self.timer = None
        self.waiting = False
        self.tick = None
        self.tack = None
        self.structure_check()
        self.root.removedChildren.connect(self.node_removed)

    def __setattr__(self, attr, val):
        """Przechwycenie zmiany atrybutu."""
        super().__setattr__(attr, val)
        if attr == "dok_df":
            # Aktualizacja zawartości tableview po zmianie w dok_df
            self.tv_dok_unsel()  # Reset zaznaczenia w tv_dok
            self.dok_mdl.setDataFrame(self.dok_col(val))  # Załadowanie danych do tv_dok
        elif attr == "dok_id" and not self.init_void:
            print(f"dok_id: {self.dok_id}")
            self.sel_dok_attr_update()
            self.map_df_update()

    def node_removed(self, node, idx_from, idx_to):
        """Przeciwdziałanie rozsynchronizowaniu zawartości legendy i dataframe'ów."""
        self.wait_set()

    def wait_set(self):
        """Ograniczenie odbierania wielu sygnałów 'removedChildren' przez zastosowanie stopera."""
        if self.waiting:
            # Blokada jest już włączona
            self.tick += 1
            return
        if not self.waiting:
            # Włączanie blokady
            self.waiting = True
            self.tick = 1
            self.tack = 0
            self.timer = QTimer()
            self.timer.setInterval(300)
            self.timer.timeout.connect(self.wait_check)
            self.timer.start()

    def wait_check(self):
        """Zatrzymanie stopera, gdy wielokrotne sygnały 'removeChildren' ustały, następnie odpalenie funkcji 'structure_check'."""
        if self.tick != self.tack:
            self.tack = self.tick
        else:
            self.waiting = False
            if self.timer:
                self.timer.stop()
                self.timer = None
            self.tick = None
            self.tack = None
            self.structure_check()

    def structure_check(self):
        """Sprawdzenie, czy w legendzie istnieje grupa 'NAG_ArchMap'"""
        print("[structure_check]")
        if len(self.proj.mapLayers()) == 0:
            # QGIS nie ma otwartego projektu, tworzy nowy
            iface.newProject(promptToSaveFlag=False)
            self.proj.setCrs(CRS_1992)
        self.main_grp = self.root.findGroup("NAG_ArchMap")
        if not self.main_grp:
            # Utworzenie grupy systemowej, jeśli jej nie ma
            self.main_grp = self.root.insertGroup(-1, "NAG_ArchMap")
        self.map_df_update()  # Aktualizacja dataframe'ów

    def sel_dok_attr_update(self):
        """Aktualizacja widget'ów wyświetlających atrybuty wybranej dokumentacji."""
        labels = [self.l_cbdgid, self.l_dok_rok, self.l_tytul, self.l_nr_arch, self.l_zloza, self.l_tag]
        if not self.dok_id:
            self.stacked_dok.setCurrentIndex(0)
            for label in labels:
                label.setText("")
        else:
            self.attrs_for_sel_dok()
            self.stacked_dok.setCurrentIndex(1)

    def attrs_for_sel_dok(self):
        """Zwraca listę wartości atrybutów wybranej dokumentacji."""
        if not self.dok_id:
            return None
        sel_dok_df = self.dok_df[self.dok_df['dok_id'] == int(self.dok_id)]
        if len(sel_dok_df) == 0:
            return None
        self.cbdg_id = str(sel_dok_df['cbdg_id'].astype(int).values[0])
        self.l_cbdgid.setText(self.cbdg_id)
        self.l_dok_rok.setText(str(sel_dok_df['rok'].astype(int).values[0]))
        self.l_tytul.setText(str(sel_dok_df['tytul'].astype(str).values[0]))
        czy_kat = bool(sel_dok_df['czy_nr_kat'].astype(bool).values[0])
        arch_type = "Nr kat.:" if czy_kat else "Nr inw.:"
        self.l_nr_arch.setText(f"{arch_type} {str(sel_dok_df['nr_inw'].astype(str).values[0])} [NAG PIG-PIB]")
        sql = f"SELECT m.midas_id, m.t_zloze_nazwa FROM dokumentacje d INNER JOIN dokumentacje_midas dm ON d.dok_id = dm.dok_id INNER JOIN midas m ON m.midas_id = dm.midas_id WHERE d.dok_id = {self.dok_id};"
        cols=['midas_id', 'nazwa_zloza']
        zl_df = df_from_db(sql, cols)
        if len(zl_df) == 0:
            self.l_zloza.setText("")
        else:
            zl_txt = ""
            for index in zl_df.to_records():
                zl_txt = f"{zl_txt}{index[1]}  {index[2]}     "
            self.l_zloza.setText(zl_txt)
        sql = f"SELECT t.t_tag FROM dokumentacje d INNER JOIN dokumentacje_tagi dt ON d.dok_id = dt.dok_id INNER JOIN tagi t ON t.tag_id = dt.tag_id WHERE d.dok_id = {self.dok_id};"
        cols=['tag']
        tag_df = df_from_db(sql, cols)
        if len(tag_df) == 0:
            self.l_tag.setText("")
        else:
            tag_txt = ""
            for index in tag_df.to_records():
                tag_txt = f"{tag_txt}{index[1]}"
            self.l_tag.setText(tag_txt)

    def map_df_update(self):
        """Aktualizuje zawartość map_df po zmianie wyboru dokumentacji."""
        if not self.dok_id:
            self.map_df = pd.DataFrame(columns=['checkbox', 'map_id', 'tytuł mapy', 'warstwa mapy', 'rok', 'plik'])
        else:
            sql = f"SELECT map_id, t_map_nazwa, t_map_warstwa, i_map_rok, t_map_plik FROM public.mapy WHERE dok_id = {self.dok_id}"
            cols=['map_id', 'tytuł mapy', 'warstwa mapy', 'rok', 'plik']
            map_df_1 = df_from_db(sql, cols)
            if len(map_df_1) == 0:
                self.map_df = pd.DataFrame(columns=['checkbox', 'map_id', 'tytuł mapy', 'warstwa mapy', 'rok', 'plik'])
            else:
                map_list = self.maps_from_toc()
                map_df_2 = map_df_1['map_id'].to_frame()
                map_df_2['checkbox'] = map_df_2['map_id'].isin(map_list)
                self.map_df = pd.concat(objs=[map_df_2.iloc[:,-1], map_df_1.iloc[:,:]], axis=1)
        self.empty_dok_grp_check()
        self.map_mdl.setDataFrame(self.map_df)  # Załadowanie danych do tv_map

    def empty_dok_grp_check(self):
        """Kasuje w legendzie pustą grupę dokumentacji."""
        temp_df = self.map_df[self.map_df['checkbox'] == True]
        if len(temp_df) > 0:
            # Grupa nie jest pusta, nie powinno się jej kasować
            return
        root = self.proj.layerTreeRoot()
        main_grp = root.findGroup("NAG_ArchMap")
        dok_grp = self.find_group_node_by_property()
        if dok_grp:
            main_grp.removeChildNode(dok_grp)

    def maps_from_toc(self):
        """Przeszukuje legendę i zwraca listę załadowanych map."""
        if not self.cbdg_id:
            return []
        dok_grp = self.find_group_node_by_property()
        if not dok_grp:
            return []
        layers = [child.customProperty('map_id') for child in dok_grp.children() if isinstance(child, QgsLayerTreeLayer)]
        return layers

    def init_tv_dok(self):
        """Konfiguracja tableview dla listy dokumentacji."""
        self.stacked_dok.setCurrentIndex(0)
        tv_dok_headers = ['dok_id', 'Nr CBDG', 'Tytuł dokumentacji', 'Rok']
        temp_df = pd.DataFrame(columns=['dok_id', 'Nr CBDG', 'Tytuł dokumentacji', 'Rok'])
        self.dok_mdl = DokDFM(df=temp_df, tv=self.tv_dok, col_names=tv_dok_headers)
        self.tv_dok.selectionModel().selectionChanged.connect(self.tv_dok_sel_change)

    def init_tv_map(self):
        """Konfiguracja tableview dla listy map wybranej dokumentacji."""
        tv_map_headers = ['', 'ID', 'Tytuł mapy', 'Warstwa mapy', 'Rok', 'plik']
        temp_df = pd.DataFrame(columns=['checkbox', 'ID', 'Tytuł mapy', 'Warstwa mapy', 'Rok', 'plik'])
        self.map_mdl = MapDFM(df=temp_df, tv=self.tv_map, col_names=tv_map_headers, dlg=self)

    def tv_dok_unsel(self, scroll_top=True):
        """Odznaczenie wiersza w tv_dok po zmianie dok_df."""
        sel_tv = self.tv_dok.selectionModel()
        sel_tv.clearCurrentIndex()
        sel_tv.clearSelection()
        if scroll_top:
            self.tv_dok.scrollToTop()
        self.tv_dok.viewport().update()

    def tv_dok_sel_change(self):
        """Aktualizacja widget'ów po zmianie aktualnego wiersza w tv_dok."""
        sel_tv = self.tv_dok.selectionModel()
        sel_idx = sel_tv.currentIndex()
        self.dok_id = None if sel_idx.row() == -1 else sel_idx.sibling(sel_idx.row(), 0).data()

    def maps_in_toc_update(self, add_list, del_list):
        """Wczytanie i/lub usunięcie rastrów map z projektu po zmianie zrobionej z poziomu tv_map."""
        dok_grp = self.dok_grp_check()
        if len(del_list) > 0:
            for map in del_list:
                lyr_node = self.find_layer_node_by_property(dok_grp, map)
                if lyr_node:
                    self.proj.removeMapLayers([lyr_node.layerId()])
        if len(add_list) > 0:
            sel_dok_df = self.dok_df[self.dok_df['dok_id'] == int(self.dok_id)]
            path = sel_dok_df['path'].values[0]
            for map in add_list:
                mask = self.map_df[self.map_df['map_id'].astype(int) == int(map)]
                lyr_name = mask['tytuł mapy'].values[0]
                file = mask['plik'].values[0]
                path_file = os.path.join(path, file)
                lyr = QgsRasterLayer(path_file, str(lyr_name), "gdal")
                lyr.setCrs(CRS_1992)
                if lyr.isValid():
                    self.proj.addMapLayer(lyr, False)  # Dodaje warstwę bez pokazywania jej
                    dok_grp.addLayer(lyr)
                    lyr_node = self.root.findLayer(lyr.id())
                    lyr_node.setCustomProperty('map_id', map)
                    lyr_node.setExpanded(False)
                else:
                    QMessageBox.critical(None, "NAG_ArchMap", f"Nie udało się dodać warstwy rastrowej (id: {map}).")
        self.canvas.refresh()
        self.map_df_update()

    def find_layer_node_by_property(self, group, val):
        """Przeszukuje wszystkie warstwy projektu i zwraca tę, która ma poszukiwaną wartość customProperty 'map_id'."""
        for lyr in group.findLayers():
            if lyr.customProperty('map_id') == val:
                return lyr

    def find_group_node_by_property(self):
        """Przeszukuje wszystkie grupy projektu i zwraca tę, która ma poszukiwaną wartość customProperty 'cbdg_id'."""
        if not self.dok_id:
            return
        root = self.proj.layerTreeRoot()  # Referencja do drzewka legendy projektu
        main_grp = root.findGroup("NAG_ArchMap")
        for grp in main_grp.findGroups():
            if grp.customProperty('dok_id') == self.dok_id:
                return grp

    def dok_grp_check(self):
        """Sprawdza, czy w legendzie grupa o nazwie równej cbdg_id i tworzy jeśli trzeba."""
        root = self.proj.layerTreeRoot()  # Referencja do drzewka legendy projektu
        main_grp = root.findGroup("NAG_ArchMap")
        dok_grp = self.find_group_node_by_property()
        if not dok_grp:
            dok_grp = main_grp.insertGroup(0, self.create_group_name())
            dok_grp.setCustomProperty('dok_id', self.dok_id)
        dok_grp.setExpanded(True)
        return dok_grp

    def create_group_name(self):
        """Zwraca nazwę grupy utworzoną ze słowa kluczowego i roku wykonania dokumentacji."""
        tag_txt = self.l_tag.text()
        rok_txt = self.l_dok_rok.text()
        return f"{tag_txt} ({rok_txt} r.)"

    def dok_col(self, df):
        """Zwraca dataframe z kolumnami pasującymi do tv_dok."""
        return pd.concat(objs=[df.iloc[:,0:2], df.iloc[:,4:6]], axis=1)

    def map_update_from_tv(self, tv_df):
        """Aktualizacja stanu map po zmianie w tv_map."""
        tv_df = tv_df.rename(columns={'checkbox': 'checkbox_new'})
        tv_df = pd.concat(objs=[tv_df.iloc[:,1], tv_df.iloc[:,0]], axis=1)
        df = pd.merge(self.map_df, tv_df, on="map_id")
        mask = df[df['checkbox'] != df['checkbox_new']]
        add_df = mask[mask['checkbox_new'] == True]
        add_list = add_df['map_id'].tolist()
        del_df = mask[mask['checkbox_new'] == False]
        del_list = del_df['map_id'].tolist()
        self.maps_in_toc_update(add_list, del_list)

    def closeEvent(self, event):
        try:
            self.root.removedChildren.disconnect(self.node_removed)
        except:
            pass
        self.closingPlugin.emit()
        event.accept()

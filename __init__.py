# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NagArchMap
                                 A QGIS plugin
 Import do projektu QGIS georeferencjonowanych załączników mapowych dokumentacji zgromadzonych w NAG PIG-PIB
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2022-10-13
        copyright            : (C) 2022 by Dominik Szrek / PIG-PIB
        email                : dszr@pgi.gov.pl
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load NagArchMap class from file NagArchMap.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .nag_archmap import NagArchMap
    return NagArchMap(iface)

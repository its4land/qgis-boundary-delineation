# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BoundaryDelineation
                                 A QGIS plugin
 Supports the semi-automatic delineation of boundaries
                             -------------------
        begin                : 2017-05-10
        copyright            : (C) 2017 by Sophie Crommelinck
        email                : s.crommelinck@utwente.nl
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
    """Load BoundaryDelineation class from file BoundaryDelineation.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .BoundaryDelineation import BoundaryDelineation
    return BoundaryDelineation(iface)

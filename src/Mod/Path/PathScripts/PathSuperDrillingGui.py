# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 sliptonic <shopinthewoods@gmail.com>               *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import FreeCAD
import FreeCADGui
import PathScripts.PathCircularHoleBaseGui as PathCircularHoleBaseGui
import PathScripts.PathGui as PathGui
import PathScripts.PathLog as PathLog
import PathScripts.PathOpGui as PathOpGui

from PySide import QtCore, QtGui

from PathScripts import PathSuperDrilling

# Imports for Sub-operations creation
from PathScripts import PathDrillingGui
from PathScripts import PathHelixGui

__title__ = "Path Drilling Super Operation"
__author__ = "MH Tech"
__url__ = "http://www.vaerks.com"
__doc__ = "Super operation."

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.NOTICE, PathLog.thisModule())


class TaskPanelOpPage(PathCircularHoleBaseGui.TaskPanelOpPage):
    '''Controller for the drilling operation's page'''

    def getForm(self):
        '''getForm() ... return UI'''
        return FreeCADGui.PySideUic.loadUi(":/panels/PageOpSuperDrillingEdit.ui")

    def getFields(self, obj):
        '''setFields(obj) ... update obj's properties with values from the UI'''
        PathLog.track()
        PathGui.updateInputField(obj, 'PeckDepth', self.form.peckDepth)
        PathGui.updateInputField(obj, 'RetractHeight', self.form.retractHeight)
        PathGui.updateInputField(obj, 'DwellTime', self.form.dwellTime)

        if obj.DwellEnabled != self.form.dwellEnabled.isChecked():
            obj.DwellEnabled = self.form.dwellEnabled.isChecked()
        if obj.PeckEnabled != self.form.peckEnabled.isChecked():
            obj.PeckEnabled = self.form.peckEnabled.isChecked()
        if obj.AddTipLength != self.form.useTipLength.isChecked():
            obj.AddTipLength = self.form.useTipLength.isChecked()

        self.updateToolController(obj, self.form.toolController)

    def setFields(self, obj):
        '''setFields(obj) ... update UI with obj properties' values'''
        PathLog.track()

        self.form.peckDepth.setText(FreeCAD.Units.Quantity(obj.PeckDepth.Value, FreeCAD.Units.Length).UserString)
        self.form.retractHeight.setText(FreeCAD.Units.Quantity(obj.RetractHeight.Value, FreeCAD.Units.Length).UserString)
        self.form.dwellTime.setText(str(obj.DwellTime))

        if obj.DwellEnabled:
            self.form.dwellEnabled.setCheckState(QtCore.Qt.Checked)
        else:
            self.form.dwellEnabled.setCheckState(QtCore.Qt.Unchecked)

        if obj.PeckEnabled:
            self.form.peckEnabled.setCheckState(QtCore.Qt.Checked)
        else:
            self.form.peckEnabled.setCheckState(QtCore.Qt.Unchecked)

        if obj.AddTipLength:
            self.form.useTipLength.setCheckState(QtCore.Qt.Checked)
        else:
            self.form.useTipLength.setCheckState(QtCore.Qt.Unchecked)

        self.setupToolController(obj, self.form.toolController)

    def getSignalsForUpdate(self, obj):
        '''getSignalsForUpdate(obj) ... return list of signals which cause the receiver to update the model'''
        signals = []

        signals.append(self.form.retractHeight.editingFinished)
        signals.append(self.form.peckDepth.editingFinished)
        signals.append(self.form.dwellTime.editingFinished)
        signals.append(self.form.dwellEnabled.stateChanged)
        signals.append(self.form.peckEnabled.stateChanged)
        signals.append(self.form.useTipLength.stateChanged)
        signals.append(self.form.toolController.currentIndexChanged)

        return signals


# The subCmdResources has to be manually updated by adding a new Resource type when a new sub-operation
# has to be done in the Super Operation procedure
subCmdResources = [PathDrillingGui.Resource, PathDrillingGui.Resource, PathHelixGui.Resource]
Resource = PathOpGui.CommandResources('SuperDrilling',
        PathSuperDrilling.Create,
        TaskPanelOpPage,
        'Path-SuperDrilling',
        QtCore.QT_TRANSLATE_NOOP("PathSuperDrilling", "SuperDrilling"),
        QtCore.QT_TRANSLATE_NOOP("PathSuperDrilling", "SuperDrilling Super Operation"),
        None)

Command = PathOpGui.SetupOperation(Resource, subCmdResources)

FreeCAD.Console.PrintLog("Loading PathSuperDrillingGui... done\n")

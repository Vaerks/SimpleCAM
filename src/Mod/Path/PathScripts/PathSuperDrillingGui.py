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

__title__ = "Path Drilling Test Operation"
__author__ = "Peter"
__url__ = "http://www.freecadweb.org"
__doc__ = "Test operation."

if True:
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
        if obj.IsActive != self.form.isActiveEnabled.isChecked():
            obj.IsActive = self.form.isActiveEnabled.isChecked()

        self.updateToolController(obj, self.form.toolController)

        # If the obj is active, it needs to setup all its sub-operations once
        if obj.IsActive and obj.IsTestCreated is False:
            PathSuperDrilling.createSubOperations(["Test1", "Test2"], obj)
            obj.IsTestCreated = True # used to know if the associated sub-operations are already created

        # If the sub-operations are already created but we don't want them anymore, they need to be deleted
        elif obj.IsActive is False and obj.IsTestCreated:
            PathSuperDrilling.destroySubOperations(["Test1", "Test2"])
            obj.IsTestCreated = False

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

        if obj.IsActive:
            self.form.isActiveEnabled.setCheckState(QtCore.Qt.Checked)
        else:
            self.form.isActiveEnabled.setCheckState(QtCore.Qt.Unchecked)

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

        signals.append(self.form.isActiveEnabled.stateChanged)

        return signals

Command = PathOpGui.SetupOperation('SuperDrilling',
        PathSuperDrilling.Create,
        TaskPanelOpPage,
        'Path-SuperDrilling',
        QtCore.QT_TRANSLATE_NOOP("PathSuperDrilling", "SuperDrilling"),
        QtCore.QT_TRANSLATE_NOOP("PathSuperDrilling", "SuperDrilling Super Operation"))

FreeCAD.Console.PrintLog("Loading PathTestDrillingGui... done\n")

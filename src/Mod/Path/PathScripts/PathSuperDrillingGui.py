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

import copy

from PySide import QtCore, QtGui

from PathScripts import PathSuperDrilling

# Imports for Sub-operations creation
from PathScripts import PathDrillingGui
from PathScripts import PathHelixGui

from PathScripts import PathUtils

__title__ = "Path Drilling Super Operation"
__author__ = "MH Tech"
__url__ = "http://www.vaerks.com"
__doc__ = "Super operation."

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.NOTICE, PathLog.thisModule())


def checkHolesBase(obj):
    """ Function used to make sure the holes selected to be the base of the operation have the same hole diameter and
        are under 8mm. """
    if obj.TypeId != "Path::FeatureCompoundPython":
        return
    n = 0
    holediameter = 0
    for i, (base, subs) in enumerate(obj.Base):
        for sub in subs:
            if n > 0 and holediameter != obj.Proxy.holeDiameter(obj, base, sub):
                w = QtGui.QWidget()
                QtGui.QMessageBox.critical(w, "Warning",
                                               "Super Drilling Operation can not support different hole diameters.")
                return False
            else:
                holediameter = obj.Proxy.holeDiameter(obj, base, sub)

            if holediameter >= 8.0:
                w = QtGui.QWidget()
                QtGui.QMessageBox.critical(w, "Warning",
                                               "A hole diameter can not exceed 8 mm. Tip: Use Super Helix instead.")
                return False

            n = n + 1

        return True


class TaskPanelOpPage(PathCircularHoleBaseGui.TaskPanelOpPage):
    '''Controller for the drilling operation's page'''

    def getBaseGeometryForm(self):
        return FreeCADGui.PySideUic.loadUi(":/panels/PageBaseHoleGeometryEdit.ui")

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

        # Sub-operations properties
        # Enable/disable the Helix (Hole Milling) operation if needed
        if obj.Group[2].Active != self.form.basehelix_active.isChecked():
            obj.Group[2].Active = self.form.basehelix_active.isChecked()
            obj.Group[2].ViewObject.Visibility = self.form.basehelix_active.isChecked()
            obj.Group[2].Visible = self.form.basehelix_active.isChecked()
            obj.Group[2].Valid = True

        # Update the Super Drilling Auto-Suggest properties for each sub-operation
        if obj.DrillingAutoSuggest != self.form.basedrill_autosuggest.isChecked():
            obj.DrillingAutoSuggest = self.form.basedrill_autosuggest.isChecked()
        if obj.HoleMillingAutoSuggest != self.form.basehelix_autosuggest.isChecked():
            obj.HoleMillingAutoSuggest = self.form.basehelix_autosuggest.isChecked()
        if obj.ThreadMillingAutoSuggest != self.form.thread_autosuggest.isChecked():
            obj.ThreadMillingAutoSuggest = self.form.thread_autosuggest.isChecked()

        # Apply the selected Tool Controller to the sub-operations.
        for subobj in obj.Group:
            name = subobj.Name.split("_")
            opname = name[2]
            oplocation = name[3]

            if opname == "drill" and oplocation == "base":
                self.updateSuggestionToolController(subobj, self.form.basedrill_tool)

            elif opname == "helix":
                self.updateSuggestionToolController(subobj, self.form.basehelix_tool)

        self.setSuggestedToolFields()

    def updateOpField(self, op, checkbox):
        ''' Check the checkbox with the operation is active and valid '''
        if op.Active and op.Valid:
            checkbox.setCheckState(QtCore.Qt.Checked)

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

        # For sub-operations:
        # Enable/disable Tool Auto-Suggest and operation visibility
        self.updateOpField(obj.Group[2], self.form.basehelix_active)

        if obj.DrillingAutoSuggest:
            self.form.basedrill_autosuggest.toggle()
        if obj.HoleMillingAutoSuggest:
            self.form.basehelix_autosuggest.toggle()
        if obj.ThreadMillingAutoSuggest:
            self.form.thread_autosuggest.toggle()

        self.suggestionsChangeState()

        # Change the SuggestionToolControllers GUI
        self.setSuggestedToolFields()

    def getHoleDiameter(self, obj):
        for i, (base, subs) in enumerate(obj.Base):
            for sub in subs:
                return obj.Proxy.holeDiameter(obj, base, sub)

    def setSuggestedToolFields(self):
        obj = self.obj
        holediameter = self.getHoleDiameter(obj)

        self.form.missing_tool_info.hide()

        for subobj in obj.Group:
            if not self.updateSuggestedTool(subobj, holediameter):
                self.form.missing_tool_info.show()

    def updateSuggestedTool(self, subobj, holediameter):
        """
        Description:
            Update the Tool Suggestions for the specified sub-operation.

        Details:
            1) Drill, Hole Milling and Thread Milling tools can be defined manually by disabling the auto-suggest
            from the GUI.

            - If disabled, the manually defined tool for the sub-operation must be at the first position
            of the combobox list.

            - If enabled, getAllSuggestedTools from PathUtils must be called alone.

            - self.setupSuggestedToolController is used at the end of the iterations to update the combobox with
            the new tools list.

            2) The other sub-operations such as Center Drill and Chamfering can only apply for one tool.
        """

        nomissingtool = True
        name = subobj.Name.split("_")
        opname = name[2]
        oplocation = name[3]

        tc = PathUtils.getToolControllers(subobj)

        if opname == "drill" and oplocation == "center":
            # It can be only one tool type CenterDrill for now.
            subobj.ToolController = PathUtils.filterToolControllers(tc, "CenterDrill")[0]

        elif opname == "chamfering":
            # It can be only one tool type ChamferMill for now.
            subobj.ToolController = PathUtils.filterToolControllers(tc, "ChamferMill")[0]

        elif opname == "drill" and oplocation == "base":
            toolslist = PathUtils.getAllSuggestedTools(
                                              PathUtils.filterToolControllers(tc, "Drill"), holediameter)

            nomissingtool = len(toolslist) > 0  # Simple check if the Tool Suggestion has found at least one tool

            # If Tool Suggestions for the Drill operation are disabled from the GUI,
            # select the actual operation tool and show it as the first element in the combobox
            if self.form.basedrill_autosuggest.isChecked() is False \
                    and toolslist.__contains__(subobj.ToolController):

                # Remove the sub-operation Tool Controller to insert it at the first position of the list
                toolslist.insert(0, toolslist.pop(toolslist.index(subobj.ToolController)))

            self.setupSuggestedToolController(subobj, self.form.basedrill_tool, toolslist)

        elif opname == "helix":
            toolslist = PathUtils.getAllSuggestedTools(
                PathUtils.filterToolControllers(tc, "EndMill"), holediameter)

            nomissingtool = len(toolslist) > 0  # Simple check if the Tool Suggestion has found at least one tool

            # If Tool Suggestions for the Helix (Hole Milling) operation are disabled from the GUI,
            # select the actual operation tool and show it as the first element in the combobox
            if self.form.basehelix_autosuggest.isChecked() is False \
                    and toolslist.__contains__(subobj.ToolController):

                # Remove the sub-operation Tool Controller to insert it at the first position of the list
                toolslist.insert(0, toolslist.pop(toolslist.index(subobj.ToolController)))

            self.setupSuggestedToolController(subobj, self.form.basehelix_tool, toolslist)

        return nomissingtool  # The check is returned to make sure each sub-operation has a valid tool


    def getSignalsForUpdate(self, obj):
        '''getSignalsForUpdate(obj) ... return list of signals which cause the receiver to update the model'''
        signals = []

        signals.append(self.form.retractHeight.editingFinished)
        signals.append(self.form.peckDepth.editingFinished)
        signals.append(self.form.dwellTime.editingFinished)
        signals.append(self.form.dwellEnabled.stateChanged)
        signals.append(self.form.peckEnabled.stateChanged)
        signals.append(self.form.useTipLength.stateChanged)

        signals.append(self.form.basedrill_tool.currentIndexChanged)
        signals.append(self.form.basehelix_tool.currentIndexChanged)

        signals.append(self.form.basehelix_active.stateChanged)

        self.form.basedrill_autosuggest.clicked.connect(self.suggestionsChangeState)
        self.form.basehelix_autosuggest.clicked.connect(self.suggestionsChangeState)
        self.form.thread_autosuggest.clicked.connect(self.suggestionsChangeState)

        self.updateOpField(obj.Group[2], self.form.basehelix_active)

        return signals

    def suggestionsChangeState(self):
        self.updateState(self.form.basedrill_tool, self.form.basedrill_autosuggest)
        self.updateState(self.form.basehelix_tool, self.form.basehelix_autosuggest)
        self.updateState(self.form.thread_tool, self.form.thread_autosuggest)

        self.setSuggestedToolFields()

    def updateState(self, combo, button):
        if hasattr(button, "isChecked"):
            combo.setEnabled(not button.isChecked())



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

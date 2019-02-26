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


class TaskPanelOpPage(PathCircularHoleBaseGui.TaskPanelOpPage):
    '''Controller for the drilling operation's page'''
    holediameter = 0.0

    def getForm(self):
        '''getForm() ... return UI'''
        return FreeCADGui.PySideUic.loadUi(":/panels/PageOpSuperDrillingEdit.ui")

    def setToolSuggestions(self, obj):
        # Tool suggestions:
        # It selects all the ToolControllers in the job and checks which has the closer diameter with the hole.
        # For that, it simply takes all the tools that have a diameter under the hole and sort them by reverse
        #  so the biggest one will be at the start of the list (which is the best suggested tool that will be given
        #  as the first element in the combobox).
        # TODO: Code optimization is required because for now, these "heavy" actions are made for each field update

        # -------------------------------------------------------------
        # Retrieve the hole diameter for tool suggestions searching
        holediameter = 0.0

        # The code will only looking for one hole
        # TODO: Making it for few holes
        for i, (base, subs) in enumerate(obj.Base):
            for sub in subs:
                holediameter = obj.Proxy.holeDiameter(obj, base, sub)
                break
            break

        basedrilltool = None
        basehelixtool = None

        # Get the current ToolController
        for subobj in obj.Group:
            name = subobj.Name.split("_")
            opname = name[2]
            oplocation = name[3]

            if opname == "drill" and oplocation == "base":
                basedrilltool = subobj.ToolController

            elif opname == "helix":
                basehelixtool = subobj.ToolController


        suggestedToolList = []
        centerdrillTools = []
        drillTools = []
        helixTools = []
        chamferingTools = []

        toolcontrollers = PathUtils.getToolControllers(obj)

        for tc in toolcontrollers:
            if holediameter > tc.Tool.Diameter > 0.0:
                suggestedToolList.append(tc)

            # Center Drill
            if tc.Tool.ToolType == "CenterDrill":
                centerdrillTools.append(tc)

            # Chamfering
            if tc.Tool.ToolType == "ChamferMill":
                chamferingTools.append(tc)

        # Center Drill
        if len(centerdrillTools) > 0:
            self.setupSuggestedToolController(obj, self.form.centerdrill_tool, centerdrillTools)

        # Chamfering
        if len(chamferingTools) > 0:
            self.setupSuggestedToolController(obj, self.form.chamfering_tool, chamferingTools)

        if len(suggestedToolList) > 0:
            suggestedToolList.sort(key=lambda x: x.Tool.Diameter, reverse=True)

            for tool in suggestedToolList:
                # Base Helix & Hole Milling
                if tool.Tool.ToolType == "EndMill":
                    helixTools.append(tool)

                # Base Drill
                elif tool.Tool.ToolType == "Drill":
                    drillTools.append(tool)

            if len(helixTools) > 0:
                if helixTools.__contains__(basehelixtool):
                    helixTools.remove(basehelixtool)
                    helixTools.insert(0, basehelixtool)

                self.setupSuggestedToolController(obj, self.form.basehelix_tool, helixTools)

            if len(drillTools) > 0:

                if drillTools.__contains__(basedrilltool):
                    drillTools.remove(basedrilltool)
                    drillTools.insert(0, basedrilltool)
                self.setupSuggestedToolController(obj, self.form.basedrill_tool, drillTools)

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

        # For sub-operations parameter:
        if obj.Group[0].Active != self.form.centerdrill_active.isChecked():
            obj.Group[0].Active = self.form.centerdrill_active.isChecked()
        if obj.Group[1].Active != self.form.basedrill_active.isChecked():
            obj.Group[1].Active = self.form.basedrill_active.isChecked()
        if obj.Group[2].Active != self.form.basehelix_active.isChecked():
            obj.Group[2].Active = self.form.basehelix_active.isChecked()

        self.updateToolController(obj, self.form.toolController)

        # Max diameter and holes with different diameters detection:
        n = 0
        for i, (base, subs) in enumerate(obj.Base):
            for sub in subs:
                if n > 0 and self.holediameter != obj.Proxy.holeDiameter(obj, base, sub):
                    w = QtGui.QWidget()
                    QtGui.QMessageBox.critical(w, "Warning",
                                               "Super Drilling Operation can not support different hole diameters.")
                else:
                    self.holediameter = obj.Proxy.holeDiameter(obj, base, sub)

                if self.holediameter >= 8.0:
                    w = QtGui.QWidget()
                    QtGui.QMessageBox.critical(w, "Warning", "A hole diameter can not exceed 8 mm. Tip: Use Super Helix instead.")

                n = n+1
            break

        for subobj in obj.Group:
            name = subobj.Name.split("_")
            opname = name[2]
            oplocation = name[3]

            if opname == "drill" and oplocation == "center":
                self.updateSuggestionToolController(subobj, self.form.centerdrill_tool)

            elif opname == "drill" and oplocation == "base":
                self.updateSuggestionToolController(subobj, self.form.basedrill_tool)

            elif opname == "helix":
                self.updateSuggestionToolController(subobj, self.form.basehelix_tool)

            elif opname == "chamfering":
                self.updateSuggestionToolController(subobj, self.form.chamfering_tool)


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

        # For sub-operations parameter
        if obj.Group[0].Active:
            self.form.centerdrill_active.setCheckState(QtCore.Qt.Checked)
        else:
            self.form.centerdrill_active.setCheckState(QtCore.Qt.UnChecked)

        if obj.Group[1].Active:
            self.form.basedrill_active.setCheckState(QtCore.Qt.Checked)
        else:
            self.form.basedrill_active.setCheckState(QtCore.Qt.UnChecked)

        if obj.Group[2].Active:
            self.form.basehelix_active.setCheckState(QtCore.Qt.Checked)
        else:
            self.form.basehelix_active.setCheckState(QtCore.Qt.UnChecked)

        # Change the SuggestionToolControllers GUI
        holediameter = self.getHoleDiameter(obj)
        for subobj in obj.Group:
             self.updateSuggestedTool(subobj, holediameter)

    def getHoleDiameter(self, obj):
        for i, (base, subs) in enumerate(obj.Base):
            for sub in subs:
                return obj.Proxy.holeDiameter(obj, base, sub)

        return 0.0

    def updateSuggestedTool(self, subobj, holediameter):
        name = subobj.Name.split("_")
        opname = name[2]
        oplocation = name[3]

        if opname == "drill" and oplocation == "center":
            self.setupSuggestedToolController(subobj, self.form.centerdrill_tool,
                                              PathUtils.filterToolControllers(PathUtils.getToolControllers(subobj), "CenterDrill"))

        elif opname == "drill" and oplocation == "base":
            toolslist = PathUtils.getAllSuggestedTools(
                                              PathUtils.filterToolControllers(PathUtils.getToolControllers(subobj),
                                                                              "Drill"), holediameter)

            if subobj.ToolController is not None:
                toolslist.remove(subobj.ToolController)
                toolslist.insert(0, subobj.ToolController)

            self.setupSuggestedToolController(subobj, self.form.basedrill_tool, toolslist)

        elif opname == "helix":
            toolslist = PathUtils.getAllSuggestedTools(
                PathUtils.filterToolControllers(PathUtils.getToolControllers(subobj),
                                                "EndMill"), holediameter)

            if subobj.ToolController is not None:
                toolslist.remove(subobj.ToolController)
                toolslist.insert(0, subobj.ToolController)

            self.setupSuggestedToolController(subobj, self.form.basehelix_tool, toolslist)

        elif opname == "chamfering":
            self.setupSuggestedToolController(subobj, self.form.chamfering_tool,
                                              PathUtils.filterToolControllers(PathUtils.getToolControllers(subobj),
                                                                              "ChamferMill"))

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

        signals.append(self.form.centerdrill_tool.currentIndexChanged)
        signals.append(self.form.basedrill_tool.currentIndexChanged)
        signals.append(self.form.basehelix_tool.currentIndexChanged)
        signals.append(self.form.chamfering_tool.currentIndexChanged)

        signals.append(self.form.centerdrill_active.stateChanged)
        signals.append(self.form.basedrill_active.stateChanged)
        signals.append(self.form.basehelix_active.stateChanged)

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
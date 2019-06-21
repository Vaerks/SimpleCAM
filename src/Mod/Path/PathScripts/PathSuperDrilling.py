# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2014 Yorik van Havre <yorik@uncreated.net>              *
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

from __future__ import print_function

import ArchPanel
import FreeCAD
import FreeCADGui
import Path
import PathScripts.PathLog as PathLog
import PathScripts.PathOp as PathOp
import PathScripts.PathUtils as PathUtils

# Imports for Sub-operations creation
import PathScripts.PathSuperOperation as PathSuperOperation
import PathScripts.PathDrilling as PathDrilling
import PathScripts.PathHelix as PathHelix

from PathScripts.PathUtils import fmt, waiting_effects
from PySide import QtCore

__title__ = "Path Drilling Super Operation"
__author__ = "MH Tech"
__url__ = "http://www.vaerks.com"
__doc__ = "Super operation."

if False:
    PathLog.setLevel(PathLog.Level.DEBUG, PathLog.thisModule())
    PathLog.trackModule(PathLog.thisModule())
else:
    PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())


# Qt tanslation handling
def translate(context, text, disambig=None):
    return QtCore.QCoreApplication.translate(context, text, disambig)


class ObjectSuperDrilling(PathSuperOperation.ObjectSuperCircularHoleBase):
    '''Proxy object for Drilling operation.'''

    def circularHoleFeatures(self, obj):
        '''circularHoleFeatures(obj) ... drilling works on anything, turn on all Base geometries and Locations.'''
        return PathOp.FeatureBaseGeometry | PathOp.FeatureLocations

    def initCircularHoleOperation(self, obj):
        '''initCircularHoleOperation(obj) ... add drilling specific properties to obj.'''

        obj = self.initSuperOperation(obj, "SuperDrilling")  # SuperOperation init function

        # Default Drilling properties:
        obj.addProperty("App::PropertyLength", "PeckDepth", "Drill", QtCore.QT_TRANSLATE_NOOP("App::Property", "Incremental Drill depth before retracting to clear chips"))
        obj.addProperty("App::PropertyBool", "PeckEnabled", "Drill", QtCore.QT_TRANSLATE_NOOP("App::Property", "Enable pecking"))
        obj.addProperty("App::PropertyFloat", "DwellTime", "Drill", QtCore.QT_TRANSLATE_NOOP("App::Property", "The time to dwell between peck cycles"))
        obj.addProperty("App::PropertyBool", "DwellEnabled", "Drill", QtCore.QT_TRANSLATE_NOOP("App::Property", "Enable dwell"))
        obj.addProperty("App::PropertyBool", "AddTipLength", "Drill", QtCore.QT_TRANSLATE_NOOP("App::Property", "Calculate the tip length and subtract from final depth"))
        obj.addProperty("App::PropertyEnumeration", "ReturnLevel", "Drill", QtCore.QT_TRANSLATE_NOOP("App::Property", "Controls how tool retracts Default=G98"))

        obj.ReturnLevel = ['G98', 'G99']  # this is the direction that the Contour runs

        obj.addProperty("App::PropertyDistance", "RetractHeight", "Drill", QtCore.QT_TRANSLATE_NOOP("App::Property", "The height where feed starts and height during retract tool when path is finished"))

        ################################################################################################
        # Super Operations properties:
        #
        # AutoSuggest: These properties are used to know if the user wants the program to auto-selects a Tool Controller
        #   with the most suitable Tool Suggestion. They can be disabled in the edition GUI of the SuperDrilling.
        obj.addProperty("App::PropertyBool", "DrillingAutoSuggest", "SuperDrilling",
                        QtCore.QT_TRANSLATE_NOOP("App:Property", "Drilling tool auto suggestion"))
        obj.addProperty("App::PropertyBool", "HoleMillingAutoSuggest", "SuperDrilling",
                        QtCore.QT_TRANSLATE_NOOP("App:Property", "Hole Milling tool auto suggestion"))
        obj.addProperty("App::PropertyBool", "ThreadMillingAutoSuggest", "SuperDrilling",
                        QtCore.QT_TRANSLATE_NOOP("App:Property", "Thread Milling tool auto suggestion"))

        # Init
        obj.DrillingAutoSuggest = True
        obj.HoleMillingAutoSuggest = True
        obj.ThreadMillingAutoSuggest = True
        ################################################################################################

    def circularHoleExecute(self, obj, holes):
        '''circularHoleExecute(obj, holes) ... generate drill operation for each hole in holes.'''
        PathLog.track()

        self.commandlist.append(Path.Command("(Begin SuperDrilling)"))

        # rapid to clearance height
        self.commandlist.append(Path.Command('G0', {'Z': obj.ClearanceHeight.Value, 'F': self.vertRapid}))

        tiplength = 0.0
        if obj.AddTipLength:
            tiplength = PathUtils.drillTipLength(self.tool)

        holes = PathUtils.sort_jobs(holes, ['x', 'y'])
        self.commandlist.append(Path.Command('G90'))
        self.commandlist.append(Path.Command(obj.ReturnLevel))

        cmd = "G81"
        cmdParams = {}
        cmdParams['Z'] = obj.FinalDepth.Value - tiplength
        cmdParams['F'] = self.vertFeed
        cmdParams['R'] = obj.RetractHeight.Value
        if obj.PeckEnabled and obj.PeckDepth.Value > 0:
            cmd = "G83"
            cmdParams['Q'] = obj.PeckDepth.Value
        elif obj.DwellEnabled and obj.DwellTime > 0:
            cmd = "G82"
            cmdParams['P'] = obj.DwellTime

        for p in holes:
            params = {}
            params['X'] = p['x']
            params['Y'] = p['y']
            params.update(cmdParams)
            self.commandlist.append(Path.Command(cmd, params))

        self.commandlist.append(Path.Command('G80'))

    def opSetDefaultValues(self, obj, job):
        '''opSetDefaultValues(obj) ... set default value for RetractHeight'''
        obj.RetractHeight = 10

    def updateSubOperations(self, obj):
        """ SuperOperation overwritten method
            Update the sub-operations properties with the Super Operation data. """
        if obj.TypeId == "Path::FeatureCompoundPython":
            for subobj in obj.Group:
                try:
                    suboperationname = subobj.Name.split("_")
                    suboperationtype = suboperationname[2]
                    suboperationlocation = suboperationname[3]
                except:
                    suboperationtype = "unknown"
                    suboperationlocation = "unknown"

                subobj.SafeHeight = obj.SafeHeight
                subobj.ClearanceHeight = obj.ClearanceHeight

                if hasattr(subobj, "StepOver"):
                    subobj.StepOver = 50

                if hasattr(subobj, 'Locations'):
                    subobj.Locations = obj.Locations

                if hasattr(subobj, 'Base'):
                    subobj.Base = obj.Base

                if hasattr(subobj, "StepDown") and subobj.ToolController is not None:
                    subobj.StepDown = str((subobj.ToolController.Tool.Diameter * 0.2)) + " mm"

                if suboperationtype == 'drill' \
                        or suboperationtype == 'holemill' \
                        or suboperationtype == 'gevind' \
                        or suboperationtype == "helix":

                    subobj.StartDepth = obj.OpStartDepth

                    # The Quantity properties seem to have a specific way to edit them with strings,
                    # that is why we need to parse it to integer first and then to string again
                    if suboperationlocation == 'center':
                        intDepth = int(str(obj.OpStartDepth).split(" ")[0])
                        newFinalDepth = str(intDepth-1)+' mm'
                        subobj.FinalDepth = newFinalDepth
                    else:
                        subobj.FinalDepth = obj.OpFinalDepth

    def initSubOperations(self, obj):
        pass


def Create(name):
    superop = FreeCAD.ActiveDocument.addObject("Path::FeatureCompoundPython", name)
    proxy = ObjectSuperDrilling(superop, name)
    if superop.Proxy:
        proxy.findAllHoles(superop)

    # Creating sub-operations
    drill1_name = "sub_"+superop.Name + "_drill_center"
    drill2_name = "sub_"+superop.Name + "_drill_base"
    helix1_name = "sub_"+superop.Name + "_helix_holemilling"
    op_drill1 = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", drill1_name)
    op_drill2 = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", drill2_name)
    op_helix1 = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", helix1_name)

    # Adding sub-objects to super operation. Objects must be added before initialization to avoid
    #  being claimed by Job.Operations.
    superop.Group = [op_drill1, op_drill2, op_helix1]

    drill1 = PathDrilling.ObjectDrilling(op_drill1, drill1_name)
    drill2 = PathDrilling.ObjectDrilling(op_drill2, drill2_name)
    helix1 = PathHelix.ObjectHelix(op_helix1, helix1_name)

    proxy.initSubOperations(superop)

    # To select all edges of a hole:
    if len(FreeCADGui.Selection.getSelectionEx()) > 0:
        selection = FreeCADGui.Selection.getSelectionEx()[0]
        PathUtils.selectAllLoops(selection)

    return superop

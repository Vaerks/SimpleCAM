# /**************************************************************************
# *   Copyright (c) Kresimir Tusek         (kresimir.tusek@gmail.com) 2018  *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This library is free software; you can redistribute it and/or         *
# *   modify it under the terms of the GNU Library General Public           *
# *   License as published by the Free Software Foundation; either          *
# *   version 2 of the License, or (at your option) any later version.      *
# *                                                                         *
# *   This library  is distributed in the hope that it will be useful,      *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this library; see the file COPYING.LIB. If not,    *
# *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
# *   Suite 330, Boston, MA  02111-1307, USA                                *
# *                                                                         *
# ***************************************************************************/



import PathScripts.PathOp as PathOp
import PathScripts.PathUtils as PathUtils
import Path
import FreeCAD
import FreeCADGui
from FreeCAD import Console
import time
import json
import math
import area
from pivy import coin

from PathScripts import PathAdaptive
from PathScripts import PathProfileBase

__doc__ = "Class and implementation of the Super Clearing path operation."


class ObjectSuperClearing(PathOp.ObjectOp):
    def opFeatures(self, obj):
        '''opFeatures(obj) ... returns the OR'ed list of features used and supported by the operation.
        The default implementation returns "FeatureTool | FeatureDeptsh | FeatureHeights | FeatureStartPoint"
        Should be overwritten by subclasses.'''
        return PathOp.FeatureTool | PathOp.FeatureBaseEdges | PathOp.FeatureDepths | PathOp.FeatureFinishDepth | PathOp.FeatureStepDown | PathOp.FeatureHeights | PathOp.FeatureBaseGeometry

    def initOperation(self, obj):
        '''initOperation(obj) ... implement to create additional properties.
        Should be overwritten by subclasses.'''
        obj.addProperty("App::PropertyEnumeration", "Side", "Adaptive", "Side of selected faces that tool should cut")
        obj.Side = ['Outside', 'Inside']  # side of profile that cutter is on in relation to direction of profile

        obj.addProperty("App::PropertyEnumeration", "OperationType", "Adaptive", "Type of adaptive operation")
        obj.OperationType = ['Clearing', 'Profiling']  # side of profile that cutter is on in relation to direction of profile

        obj.addProperty("App::PropertyFloat", "Tolerance", "Adaptive",  "Influences accuracy and performance")
        obj.addProperty("App::PropertyPercent", "StepOver", "Adaptive", "Percent of cutter diameter to step over on each pass")
        obj.addProperty("App::PropertyDistance", "LiftDistance", "Adaptive", "Lift distance for rapid moves")
        obj.addProperty("App::PropertyDistance", "KeepToolDownRatio", "Adaptive", "Max length of keep tool down path compared to direct distance between points")
        obj.addProperty("App::PropertyDistance", "StockToLeave", "Adaptive", "How much stock to leave (i.e. for finishing operation)")
        # obj.addProperty("App::PropertyBool", "ProcessHoles", "Adaptive","Process holes as well as the face outline")

        obj.addProperty("App::PropertyBool", "ForceInsideOut", "Adaptive","Force plunging into material inside and clearing towards the edges")
        obj.addProperty("App::PropertyBool", "Stopped",
                        "Adaptive", "Stop processing")
        obj.setEditorMode('Stopped', 2) #hide this property

        obj.addProperty("App::PropertyBool", "StopProcessing",
                                  "Adaptive", "Stop processing")
        obj.setEditorMode('StopProcessing', 2)  # hide this property

        obj.addProperty("App::PropertyPythonObject", "AdaptiveInputState",
                        "Adaptive", "Internal input state")
        obj.addProperty("App::PropertyPythonObject", "AdaptiveOutputState",
                        "Adaptive", "Internal output state")
        obj.setEditorMode('AdaptiveInputState', 2) #hide this property
        obj.setEditorMode('AdaptiveOutputState', 2) #hide this property
        obj.addProperty("App::PropertyAngle", "HelixAngle", "Adaptive",  "Helix ramp entry angle (degrees)")
        obj.addProperty("App::PropertyLength", "HelixDiameterLimit", "Adaptive", "Limit helix entry diameter, if limit larger than tool diameter or 0, tool diameter is used")


    def opSetDefaultValues(self, obj, job):
        obj.Side="Inside"
        obj.OperationType = "Clearing"
        obj.Tolerance = 0.1
        obj.StepOver = 20
        obj.LiftDistance=0
        # obj.ProcessHoles = True
        obj.ForceInsideOut = False
        obj.Stopped = False
        obj.StopProcessing = False
        obj.HelixAngle = 5
        obj.HelixDiameterLimit = 0.0
        obj.AdaptiveInputState = ""
        obj.AdaptiveOutputState = ""
        obj.StockToLeave= 0
        obj.KeepToolDownRatio=3.0

    def opExecute(self, obj):
        pass



def Create(name, obj = None):
    '''Create(name) ... Creates and returns a Adaptive operation.'''
    if obj is None:
        superop = FreeCAD.ActiveDocument.addObject("Path::FeatureCompoundPython", name)
    proxy = ObjectSuperClearing(superop, name)

    adaptive_name = "sub_" + superop.Name + "_adaptive_base"
    profile_name = "sub_" + superop.Name + "_profile_base"

    op_adaptive = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", adaptive_name)
    op_profile = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", profile_name)

    superop.Group = [op_adaptive, op_profile]

    adaptive = PathAdaptive.PathAdaptive(op_adaptive, adaptive_name)
    pocket = PathProfileBase.ObjectProfile(op_profile, profile_name)

    # To select all edges of a hole:
    if len(FreeCADGui.Selection.getSelectionEx()) > 0:
        selection = FreeCADGui.Selection.getSelectionEx()[0]
        PathUtils.selectAllAreaLoops(selection)

    return superop

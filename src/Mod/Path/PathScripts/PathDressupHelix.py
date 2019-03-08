# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 Pekka Roivainen <pekkaroi@gmail.com>               *
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
import Path
import Part
import PathScripts.PathDressup as PathDressup
import PathScripts.PathLog as PathLog
import math

from PathScripts import PathUtils
from PathScripts.PathGeom import PathGeom
from PySide import QtCore

from PathScripts import PathHelix

# Qt tanslation handling
def translate(text, context="Path_DressupHelix", disambig=None):
    return QtCore.QCoreApplication.translate(context, text, disambig)


PathLog.setLevel(PathLog.Level.INFO, PathLog.thisModule())


class ObjectDressup:

    def __init__(self, obj):
        self.obj = obj
        obj.addProperty("App::PropertyLink", "Base", "Path", QtCore.QT_TRANSLATE_NOOP("Path_DressupRampEntry", "The base path to modify"))
        obj.addProperty("App::PropertyAngle", "Angle", "Path", QtCore.QT_TRANSLATE_NOOP("Path_DressupRampEntry", "Angle of ramp."))
        obj.addProperty("App::PropertyEnumeration", "Method", "Path", QtCore.QT_TRANSLATE_NOOP("App::Property", "Ramping Method"))
        obj.addProperty("App::PropertyEnumeration", "RampFeedRate", "FeedRate", QtCore.QT_TRANSLATE_NOOP("App::Property", "Which feed rate to use for ramping"))
        obj.addProperty("App::PropertySpeed", "CustomFeedRate", "FeedRate", QtCore.QT_TRANSLATE_NOOP("App::Property", "Custom feedrate"))
        obj.Method = ['Helix']
        obj.RampFeedRate = ['Horizontal Feed Rate', 'Vertical Feed Rate', 'Custom']
        obj.Proxy = self
        self.setEditorProperties(obj)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def onChanged(self, obj, prop):
        if prop == "RampFeedRate":
            self.setEditorProperties(obj)

    def setEditorProperties(self, obj):
        if obj.RampFeedRate == 'Custom':
            obj.setEditorMode('CustomFeedRate', 0)
        else:
            obj.setEditorMode('CustomFeedRate', 2)

    def setup(self, obj):
        obj.Angle = 60
        #obj.Method = 1

    def execute(self, obj):

        if not obj.Base:
            return
        if not obj.Base.isDerivedFrom("Path::Feature"):
            return
        if not obj.Base.Path:
            return
        if obj.Angle >= 90:
            obj.Angle = 89.9
        elif obj.Angle <= 0:
            obj.Angle = 0.1
        self.angle = obj.Angle
        self.method = obj.Method
        self.wire, self.rapids = PathGeom.wireForPath(obj.Base.Path)
        if self.method == 'Helix':
            self.outedges = self.generateHelix()

        obj.Path = self.createCommands(obj, self.outedges)

    def generateHelix(self):
        edges = self.wire.Edges
        minZ = self.findMinZ(edges)
        outedges = []
        i = 0
        while i < len(edges):
            edge = edges[i]
            israpid = False
            for redge in self.rapids:
                if PathGeom.edgesMatch(edge, redge):
                    israpid = True
            if not israpid:
                bb = edge.BoundBox
                p0 = edge.Vertexes[0].Point
                p1 = edge.Vertexes[1].Point
                if bb.XLength < 1e-6 and bb.YLength < 1e-6 and bb.ZLength > 0 and p0.z > p1.z:
                    # plungelen = abs(p0.z-p1.z)
                    PathLog.debug("Found plunge move at X:{} Y:{} From Z:{} to Z{}, Searching for closed loop".format(p0.x, p0.y, p0.z, p1.z))
                    # next need to determine how many edges in the path after plunge are needed to cover the length:
                    loopFound = False
                    rampedges = []
                    j = i + 1
                    while not loopFound:
                        candidate = edges[j]
                        cp0 = candidate.Vertexes[0].Point
                        cp1 = candidate.Vertexes[1].Point
                        if PathGeom.pointsCoincide(p1, cp1):
                            # found closed loop
                            loopFound = True
                            rampedges.append(candidate)
                            break
                        if abs(cp0.z - cp1.z) > 1e-6:
                            # this edge is not parallel to XY plane, not qualified for ramping.
                            break
                        # PathLog.debug("Next edge length {}".format(candidate.Length))
                        rampedges.append(candidate)
                        j = j + 1
                        if j >= len(edges):
                            break
                    if len(rampedges) == 0 or not loopFound:
                        PathLog.debug("No suitable helix found")
                        outedges.append(edge)
                    else:
                        outedges.extend(self.createHelix(rampedges, p0, p1))
                        if not PathGeom.isRoughly(p1.z, minZ):
                            # the edges covered by the helix not handled again,
                            # unless reached the bottom height
                            i = j

                else:
                    outedges.append(edge)
            else:
                outedges.append(edge)
            i = i + 1
        return outedges

    def createHelix(self, rampedges, startPoint, endPoint):
        outedges = []
        ramplen = 0
        for redge in rampedges:
            ramplen = ramplen + redge.Length
        rampheight = abs(endPoint.z - startPoint.z)
        rampangle_rad = math.atan(ramplen / rampheight)
        curPoint = startPoint
        for i, redge in enumerate(rampedges):
            if i < len(rampedges) - 1:
                deltaZ = redge.Length / math.tan(rampangle_rad)
                newPoint = FreeCAD.Base.Vector(redge.valueAt(redge.LastParameter).x, redge.valueAt(redge.LastParameter).y, curPoint.z - deltaZ)
                outedges.append(self.createRampEdge(redge, curPoint, newPoint))
                curPoint = newPoint
            else:
                # on the last edge, force it to end to the endPoint
                # this should happen automatically, but this avoids any rounding error
                outedges.append(self.createRampEdge(redge, curPoint, endPoint))
        return outedges

    def createRampEdge(self, originalEdge, startPoint, endPoint):
        # PathLog.debug("Create edge from [{},{},{}] to [{},{},{}]".format(startPoint.x,startPoint.y, startPoint.z, endPoint.x, endPoint.y, endPoint.z))
        if type(originalEdge.Curve) == Part.Line or type(originalEdge.Curve) == Part.LineSegment:
            return Part.makeLine(startPoint, endPoint)
        elif type(originalEdge.Curve) == Part.Circle:
            arcMid = originalEdge.valueAt((originalEdge.FirstParameter + originalEdge.LastParameter) / 2)
            arcMid.z = (startPoint.z + endPoint.z) / 2
            return Part.Arc(startPoint, arcMid, endPoint).toShape()
        else:
            PathLog.error("Edge should not be helix")

    def getreversed(self, edges):
        """
        Reverses the edge array and the direction of each edge
        """
        outedges = []
        for edge in reversed(edges):
            # reverse the start and end points
            startPoint = edge.valueAt(edge.LastParameter)
            endPoint = edge.valueAt(edge.FirstParameter)
            if type(edge.Curve) == Part.Line or type(edge.Curve) == Part.LineSegment:
                outedges.append(Part.makeLine(startPoint, endPoint))
            elif type(edge.Curve) == Part.Circle:
                arcMid = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
                outedges.append(Part.Arc(startPoint, arcMid, endPoint).toShape())
            else:
                PathLog.error("Edge should not be helix")
        return outedges

    def findMinZ(self, edges):
        minZ = 99999999999
        for edge in edges:
            for v in edge.Vertexes:
                if v.Point.z < minZ:
                    minZ = v.Point.z
        return minZ

    def getSplitPoint(self, edge, remaining):
        if type(edge.Curve) == Part.Line or type(edge.Curve) == Part.LineSegment:
            return edge.valueAt(remaining)
        elif type(edge.Curve) == Part.Circle:
            param = remaining / edge.Curve.Radius
            return edge.valueAt(param)

    def createCommands(self, obj, edges):
        commands = []
        for edge in edges:
            israpid = False
            for redge in self.rapids:
                if PathGeom.edgesMatch(edge, redge):
                    israpid = True
            if israpid:
                v = edge.valueAt(edge.LastParameter)
                commands.append(Path.Command('G0', {'X': v.x, 'Y': v.y, 'Z': v.z}))
            else:
                commands.extend(PathGeom.cmdsForEdge(edge))

        lastCmd = Path.Command('G0', {'X': 0.0, 'Y': 0.0, 'Z': 0.0})

        outCommands = []

        tc = PathDressup.toolController(obj.Base)

        horizFeed = tc.HorizFeed.Value
        vertFeed = tc.VertFeed.Value
        if obj.RampFeedRate == "Horizontal Feed Rate":
            rampFeed = tc.HorizFeed.Value
        elif obj.RampFeedRate == "Vertical Feed Rate":
            rampFeed = tc.VertFeed.Value
        else:
            rampFeed = obj.CustomFeedRate.Value
        horizRapid = tc.HorizRapid.Value
        vertRapid = tc.VertRapid.Value

        for cmd in commands:
            params = cmd.Parameters
            zVal = params.get('Z', None)
            zVal2 = lastCmd.Parameters.get('Z', None)

            xVal = params.get('X', None)
            xVal2 = lastCmd.Parameters.get('X', None)

            yVal2 = lastCmd.Parameters.get('Y', None)
            yVal = params.get('Y', None)

            zVal = zVal and round(zVal, 8)
            zVal2 = zVal2 and round(zVal2, 8)

            if cmd.Name in ['G1', 'G2', 'G3', 'G01', 'G02', 'G03']:
                if zVal is not None and zVal2 != zVal:
                    if PathGeom.isRoughly(xVal, xVal2) and PathGeom.isRoughly(yVal, yVal2):
                        # this is a straight plunge
                        params['F'] = vertFeed
                    else:
                        # this is a ramp
                        params['F'] = rampFeed
                else:
                    params['F'] = horizFeed
                lastCmd = cmd

            elif cmd.Name in ['G0', 'G00']:
                if zVal is not None and zVal2 != zVal:
                    params['F'] = vertRapid
                else:
                    params['F'] = horizRapid
                lastCmd = cmd

            outCommands.append(Path.Command(cmd.Name, params))

        return Path.Path(outCommands)


class ViewProviderDressup:

    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.obj = vobj.Object

    def claimChildren(self):
        if hasattr(self.obj.Base, "InList"):
            for i in self.obj.Base.InList:
                if hasattr(i, "Group"):
                    group = i.Group
                    for g in group:
                        if g.Name == self.obj.Base.Name:
                            group.remove(g)
                    i.Group = group
                    print(i.Group)
        # FreeCADGui.ActiveDocument.getObject(obj.Base.Name).Visibility = False
        return [self.obj.Base]

    def onDelete(self, arg1=None, arg2=None):
        PathLog.debug("Deleting Dressup")
        '''this makes sure that the base operation is added back to the project and visible'''
        FreeCADGui.ActiveDocument.getObject(arg1.Object.Base.Name).Visibility = True
        job = PathUtils.findParentJob(self.obj)
        job.Proxy.addOperation(arg1.Object.Base)
        arg1.Object.Base = None
        return True

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class CommandPathDressupHelix:

    def GetResources(self):
        return {'Pixmap': 'Path-Dressup',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Path_DressupHelix", "Helix Dress-up"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Path_DressupHelix", "Creates a Helix Dress-up object from a selected path")}

    def IsActive(self):
        op = PathDressup.selection()
        if op:
            return not PathDressup.hasEntryMethod(op)
        return False

    def Activated(self):

        # check that the selection contains exactly what we want
        selection = FreeCADGui.Selection.getSelection()
        if len(selection) != 1:
            PathLog.error(translate("Please select one path object\n"))
            return
        baseObject = selection[0]
        if not baseObject.isDerivedFrom("Path::Feature"):
            PathLog.error(translate("The selected object is not a path\n"))
            return
        if baseObject.isDerivedFrom("Path::FeatureCompoundPython"):
            PathLog.error(translate("Please select a Profile object"))
            return

        subobjs = []

        helixname = "center_helix"
        op_helix = FreeCAD.ActiveDocument.addObject("Path::FeaturePython", helixname)

        subobjs.append(op_helix)

        obj = FreeCAD.ActiveDocument.addObject("Path::FeatureCompoundPython", "HelixDressup")
        dbo = ObjectDressup(obj)

        obj.Group = subobjs
        obj.Base = baseObject
        #FreeCADGui.doCommand('obj.Group.append(FreeCAD.ActiveDocument.' + selection[0].Name+')')
        #FreeCADGui.doCommand('obj.Base.append(FreeCAD.ActiveDocument.' + helixname + ')')

        PathUtils.addToJob(obj)

        dbo.setup(obj)

        helix = PathHelix.ObjectHelix(op_helix)


if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_DressupHelix', CommandPathDressupHelix())

PathLog.notice("Loading Path_DressupHelix... done\n")

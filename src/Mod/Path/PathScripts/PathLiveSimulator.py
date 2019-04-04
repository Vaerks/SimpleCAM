import FreeCAD
import Mesh
import Part
import Path
import PathScripts.PathDressup as PathDressup
import PathScripts.PathGeom as PathGeom
import PathScripts.PathLog as PathLog
import PathSimulator
import math
import os

from PathScripts import PathAdaptive
from PathScripts import PathUtils

from FreeCAD import Vector, Base

_filePath = os.path.dirname(os.path.abspath(__file__))

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtGui, QtCore

def createShapeResult():
    cutMaterialMeshes = [FreeCAD.ActiveDocument.findObjects("Mesh::FeaturePython", "CutMaterial")[0].Mesh,
                         FreeCAD.ActiveDocument.findObjects("Mesh::FeaturePython", "CutMaterialIn")[0].Mesh]

    shape = PathUtils.convertMeshesToPart(cutMaterialMeshes)
    PathUtils.hideObject("Shape")

def resetSimulation():
    PathUtils.deleteObject("CutTool")
    PathUtils.deleteObject("CutMaterial")
    PathUtils.deleteObject("CutMaterialIn")
    PathUtils.deleteObject("Shape")

def activateSimulation():
    resetSimulation()
    simulation = PathLiveSimulation()
    simulation.Activate()
    simulation.SimFF()  # Show the result without the animation

    job = PathUtils.GetJobs("Job")[0]
    if job.Simulation is False:
        PathUtils.hideObject("CutMaterial")
        PathUtils.hideObject("CutMaterialIn")

class CAMSimTaskUi:
    def __init__(self, parent):
        # this will create a Qt widget from our ui file
        self.form = FreeCADGui.PySideUic.loadUi(":/panels/TaskPathSimulator.ui")
        self.parent = parent

    def accept(self):
        self.parent.accept()
        FreeCADGui.Control.closeDialog()

    def reject(self):
        self.parent.cancel()
        FreeCADGui.Control.closeDialog()


def TSError(msg):
    QtGui.QMessageBox.information(None, "Path Simulation", msg)


class PathLiveSimulation:
    def __init__(self):
        self.debug = False
        self.timer = QtCore.QTimer()
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.PerformCut)
        self.stdrot = FreeCAD.Rotation(Vector(0, 0, 1), 0)
        self.iprogress = 0
        self.numCommands = 0
        self.simperiod = 20
        self.accuracy = 0.1
        self.resetSimulation = False

        self.simulationList = FreeCAD.ActiveDocument.getObject("Simulation")
        if self.simulationList is None:
            self.simulationList = FreeCAD.ActiveDocument.addObject("Path::FeatureCompoundPython", "Simulation")
            self.simulationList.Group = []


    def Connect(self, but, sig):
        QtCore.QObject.connect(but, QtCore.SIGNAL("clicked()"), sig)

    def UpdateProgress(self):
        if self.numCommands > 0:
            self.taskForm.form.progressBar.setValue(self.iprogress * 100 / self.numCommands)

    def Activate(self):
        self.initdone = False
        self.taskForm = CAMSimTaskUi(self)
        form = self.taskForm.form
        self.Connect(form.toolButtonStop, self.SimStop)
        self.Connect(form.toolButtonPlay, self.SimPlay)
        self.Connect(form.toolButtonPause, self.SimPause)
        self.Connect(form.toolButtonStep, self.SimStep)
        self.Connect(form.toolButtonFF, self.SimFF)
        form.sliderSpeed.valueChanged.connect(self.onSpeedBarChange)
        self.onSpeedBarChange()
        form.sliderAccuracy.valueChanged.connect(self.onAccuracyBarChange)
        self.onAccuracyBarChange()
        form.comboJobs.currentIndexChanged.connect(self.onJobChange)
        jobList = FreeCAD.ActiveDocument.findObjects("Path::FeaturePython", "Job.*")
        form.comboJobs.clear()
        self.jobs = []
        for j in jobList:
            self.jobs.append(j)
            form.comboJobs.addItem(j.ViewObject.Icon, j.Label)
        #FreeCADGui.Control.showDialog(self.taskForm)
        self.disableAnim = False
        self.isVoxel = True
        self.firstDrill = True
        self.voxSim = PathSimulator.PathSim()
        self.SimulateMill()
        self.initdone = True

    def SetupSimulation(self):
        form = self.taskForm.form
        self.activeOps = []
        self.numCommands = 0
        self.ioperation = 0
        for i in range(form.listOperations.count()):
            if form.listOperations.item(i).checkState() == QtCore.Qt.CheckState.Checked:
                self.firstDrill = True
                self.activeOps.append(self.operations[i])
                self.numCommands += len(self.operations[i].Path.Commands)

                # If the operations list contains a Adaptive (which is a expensive op to process)
                # it will adapt the accuracy to provide a faster preview
                if isinstance(self.operations[i].Proxy, PathAdaptive.PathAdaptive):
                    self.accuracy = 1.0

        self.stock = self.job.Stock.Shape
        if (self.isVoxel):
            maxlen = self.stock.BoundBox.XLength
            if (maxlen < self.stock.BoundBox.YLength):
                maxlen = self.stock.BoundBox.YLength
            self.voxSim.BeginSimulation(self.stock, 0.01 * self.accuracy * maxlen)
            (self.cutMaterial.Mesh, self.cutMaterialIn.Mesh) = self.voxSim.GetResultMesh()
        else:
            self.cutMaterial.Shape = self.stock
        self.busy = False
        self.tool = None
        for i in range(len(self.activeOps)):
            self.SetupOperation(0)
            if (self.tool is not None):
                break
        self.iprogress = 0
        self.UpdateProgress()

    def SetupOperation(self, itool):
        self.operation = self.activeOps[itool]
        try:
            self.tool = PathDressup.toolController(self.operation).Tool
        except:
            self.tool = None

        # if hasattr(self.operation, "ToolController"):
        #     self.tool = self.operation.ToolController.Tool
        if (self.tool is not None):
            toolProf = self.CreateToolProfile(self.tool, Vector(0, 1, 0), Vector(0, 0, 0), self.tool.Diameter / 2.0)
            self.cutTool.Shape = Part.makeSolid(toolProf.revolve(Vector(0, 0, 0), Vector(0, 0, 1)))
            # self.cutTool.ViewObject.show()
            self.voxSim.SetCurrentTool(self.tool)
        self.icmd = 0
        self.curpos = FreeCAD.Placement(self.initialPos, self.stdrot)
        # self.cutTool.Placement = FreeCAD.Placement(self.curpos, self.stdrot)
        self.cutTool.Placement = self.curpos
        self.opCommands =  self.operation.Path.Commands

    def SimulateMill(self):
        self.job = self.jobs[self.taskForm.form.comboJobs.currentIndex()]
        self.busy = False
        # self.timer.start(100)
        self.height = 10
        self.skipStep = False
        self.initialPos = Vector(0, 0, self.job.Stock.Shape.BoundBox.ZMax)
        # Add cut tool
        self.cutTool = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "CutTool")
        # self.cutTool.Visibility = False
        self.cutTool.ViewObject.Proxy = 0
        self.cutTool.ViewObject.hide()

        # Add cut material
        if self.isVoxel:
            self.cutMaterial = FreeCAD.ActiveDocument.addObject("Mesh::FeaturePython", "CutMaterial")
            self.cutMaterialIn = FreeCAD.ActiveDocument.addObject("Mesh::FeaturePython", "CutMaterialIn")

            self.simulationList.Group = [self.cutMaterial, self.cutMaterialIn]

            self.cutMaterialIn.ViewObject.Proxy = 0
            self.cutMaterialIn.ViewObject.show()
            self.cutMaterialIn.ViewObject.ShapeColor = (1.0, 0.85, 0.45, 0.0)
        else:
            self.cutMaterial = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "CutMaterial")
            self.cutMaterial.Shape = self.job.Stock.Shape
        self.cutMaterial.ViewObject.Proxy = 0
        self.cutMaterial.ViewObject.show()
        self.cutMaterial.ViewObject.ShapeColor = (0.5, 0.25, 0.25, 0.0)

        # Add cut path solid for debug
        if self.debug:
            self.cutSolid = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "CutDebug")
            self.cutSolid.ViewObject.Proxy = 0
            self.cutSolid.ViewObject.hide()

        self.SetupSimulation()
        self.resetSimulation = True
        FreeCAD.ActiveDocument.recompute()

    # def SkipStep(self):
    #     self.skipStep = True
    #     self.PerformCut()

    def PerformCutBoolean(self):
        if self.resetSimulation:
            self.resetSimulation = False
            self.SetupSimulation()

        if self.busy:
            return
        self.busy = True

        cmd = self.operation.Path.Commands[self.icmd]
        # for cmd in job.Path.Commands:
        pathSolid = None

        if cmd.Name in ['G0']:
            self.curpos = self.RapidMove(cmd, self.curpos)
        if cmd.Name in ['G1', 'G2', 'G3']:
            if self.skipStep:
                self.curpos = self.RapidMove(cmd, self.curpos)
            else:
                (pathSolid, self.curpos) = self.GetPathSolid(self.tool, cmd, self.curpos)
        if cmd.Name in ['G81', 'G82', 'G83']:
            if self.firstDrill:
                extendcommand = Path.Command('G0', {"X": 0.0, "Y": 0.0, "Z": cmd.r})
                self.curpos = self.RapidMove(extendcommand, self.curpos)
                self.firstDrill = False
            extendcommand = Path.Command('G0', {"X": cmd.x, "Y": cmd.y, "Z": cmd.r})
            self.curpos = self.RapidMove(extendcommand, self.curpos)
            extendcommand = Path.Command('G1', {"X": cmd.x, "Y": cmd.y, "Z": cmd.z})
            self.curpos = self.RapidMove(extendcommand, self.curpos)
            extendcommand = Path.Command('G1', {"X": cmd.x, "Y": cmd.y, "Z": cmd.r})
            self.curpos = self.RapidMove(extendcommand, self.curpos)
        self.skipStep = False
        if pathSolid is not None:
            if self.debug:
                self.cutSolid.Shape = pathSolid
            newStock = self.stock.cut([pathSolid], 1e-3)
            try:
                if newStock.isValid():
                    self.stock = newStock.removeSplitter()
            except:
                if self.debug:
                    print("invalid cut at cmd #{}".format(self.icmd))
        if not self.disableAnim:
            self.cutTool.Placement = FreeCAD.Placement(self.curpos, self.stdrot)
        self.icmd += 1
        self.iprogress += 1
        self.UpdateProgress()
        if self.icmd >= len(self.operation.Path.Commands):
            # self.cutMaterial.Shape = self.stock.removeSplitter()
            self.ioperation += 1
            if self.ioperation >= len(self.activeOps):
                self.EndSimulation()
                return
            else:
                self.SetupOperation(self.ioperation)
        if not self.disableAnim:
            self.cutMaterial.Shape = self.stock
        self.busy = False

    def PerformCutVoxel(self):
        if self.resetSimulation:
            self.resetSimulation = False
            self.SetupSimulation()

        if self.busy:
            return
        self.busy = True

        cmd = self.opCommands[self.icmd]
        # for cmd in job.Path.Commands:
        if cmd.Name in ['G0', 'G1', 'G2', 'G3']:
            self.curpos = self.voxSim.ApplyCommand(self.curpos, cmd)
            if not self.disableAnim:
                self.cutTool.Placement = self.curpos  # FreeCAD.Placement(self.curpos, self.stdrot)
                (self.cutMaterial.Mesh, self.cutMaterialIn.Mesh) = self.voxSim.GetResultMesh()
        if cmd.Name in ['G81', 'G82', 'G83']:
            extendcommands = []
            if self.firstDrill:
                extendcommands.append(Path.Command('G0', {"X": 0.0, "Y": 0.0, "Z": cmd.r}))
                self.firstDrill = False
            extendcommands.append(Path.Command('G0', {"X": cmd.x, "Y": cmd.y, "Z": cmd.r}))
            extendcommands.append(Path.Command('G1', {"X": cmd.x, "Y": cmd.y, "Z": cmd.z}))
            extendcommands.append(Path.Command('G1', {"X": cmd.x, "Y": cmd.y, "Z": cmd.r}))
            for ecmd in extendcommands:
                self.curpos = self.voxSim.ApplyCommand(self.curpos, ecmd)
                if not self.disableAnim:
                    self.cutTool.Placement = self.curpos  # FreeCAD.Placement(self.curpos, self.stdrot)
                    (self.cutMaterial.Mesh, self.cutMaterialIn.Mesh) = self.voxSim.GetResultMesh()
        self.icmd += 1
        self.iprogress += 1
        self.UpdateProgress()
        if self.icmd >= len(self.opCommands):
            # self.cutMaterial.Shape = self.stock.removeSplitter()
            self.ioperation += 1
            if self.ioperation >= len(self.activeOps):
                self.EndSimulation()
                return
            else:
                self.SetupOperation(self.ioperation)
        self.busy = False

    def PerformCut(self):
        if (self.isVoxel):
            self.PerformCutVoxel()
        else:
            self.PerformCutBoolean()

    def RapidMove(self, cmd, curpos):
        path = PathGeom.edgeForCmd(cmd, curpos)  # hack to overcome occ bug
        if path is None:
            return curpos
        return path.valueAt(path.LastParameter)

    def GetPathSolid(self, tool, cmd, pos):
        toolPath = PathGeom.edgeForCmd(cmd, pos)
        # curpos = e1.valueAt(e1.LastParameter)
        startDir = toolPath.tangentAt(0)
        startDir[2] = 0.0
        endPos = toolPath.valueAt(toolPath.LastParameter)
        endDir = toolPath.tangentAt(toolPath.LastParameter)
        try:
            startDir.normalize()
            endDir.normalize()
        except:
            return (None, endPos)
        # height = self.height

        # hack to overcome occ bugs
        rad = tool.Diameter / 2.0 - 0.001 * pos[2]
        # rad = rad + 0.001 * self.icmd
        if type(toolPath.Curve) is Part.Circle and toolPath.Curve.Radius <= rad:
            rad = toolPath.Curve.Radius - 0.01 * (pos[2] + 1)
            return (None, endPos)

        # create the path shell
        toolProf = self.CreateToolProfile(tool, startDir, pos, rad)
        rotmat = Base.Matrix()
        rotmat.move(pos.negative())
        rotmat.rotateZ(math.pi)
        rotmat.move(pos)
        mirroredProf = toolProf.transformGeometry(rotmat)
        fullProf = Part.Wire([toolProf, mirroredProf])
        pathWire = Part.Wire(toolPath)
        try:
            pathShell = pathWire.makePipeShell([fullProf], False, True)
        except:
            if self.debug:
                Part.show(pathWire)
                Part.show(fullProf)
            return (None, endPos)

        # create the start cup
        startCup = toolProf.revolve(pos, Vector(0, 0, 1), -180)

        # create the end cup
        endProf = self.CreateToolProfile(tool, endDir, endPos, rad)
        endCup = endProf.revolve(endPos, Vector(0, 0, 1), 180)

        fullShell = Part.makeShell(startCup.Faces + pathShell.Faces + endCup.Faces)
        return (Part.makeSolid(fullShell).removeSplitter(), endPos)

    # create radial profile of the tool (90 degrees to the direction of the path)
    def CreateToolProfile(self, tool, dir, pos, rad):
        type = tool.ToolType
        # rad = tool.Diameter / 2.0 - 0.001 * pos[2] # hack to overcome occ bug
        xf = dir[0] * rad
        yf = dir[1] * rad
        xp = pos[0]
        yp = pos[1]
        zp = pos[2]
        h = tool.CuttingEdgeHeight
        if h <= 0.0:  # set default if user fails to avoid freeze
            h = 1.0
            PathLog.error("SET Tool Length")
        # common to all tools
        vTR = Vector(xp + yf, yp - xf, zp + h)
        vTC = Vector(xp, yp, zp + h)
        vBC = Vector(xp, yp, zp)
        lT = Part.makeLine(vTR, vTC)
        res = None
        if type == "ChamferMill":
            ang = 90 - tool.CuttingEdgeAngle / 2.0
            if ang > 80:
                ang = 80
            if ang < 0:
                ang = 0
            h1 = math.tan(ang * math.pi / 180) * rad
            if h1 > (h - 0.1):
                h1 = h - 0.1
            vBR = Vector(xp + yf, yp - xf, zp + h1)
            lR = Part.makeLine(vBR, vTR)
            lB = Part.makeLine(vBC, vBR)
            res = Part.Wire([lB, lR, lT])

        elif type == "BallEndMill":
            h1 = rad
            if h1 >= h:
                h1 = h - 0.1
            vBR = Vector(xp + yf, yp - xf, zp + h1)
            r2 = h1 / 2.0
            h2 = rad - math.sqrt(rad * rad - r2 * r2)
            vBCR = Vector(xp + yf / 2.0, yp - xf / 2.0, zp + h2)
            cB = Part.Edge(Part.Arc(vBC, vBCR, vBR))
            lR = Part.makeLine(vBR, vTR)
            res = Part.Wire([cB, lR, lT])

        else:  # default: assume type == "EndMill"
            vBR = Vector(xp + yf, yp - xf, zp)
            lR = Part.makeLine(vBR, vTR)
            lB = Part.makeLine(vBC, vBR)
            res = Part.Wire([lB, lR, lT])

        return res

    def addOperation(self, form, op):
        listItem = QtGui.QListWidgetItem(op.ViewObject.Icon, op.Label)
        listItem.setFlags(listItem.flags() | QtCore.Qt.ItemIsUserCheckable)
        listItem.setCheckState(QtCore.Qt.CheckState.Checked)
        self.operations.append(op)
        form.listOperations.addItem(listItem)

    def onJobChange(self):
        form = self.taskForm.form
        j = self.jobs[form.comboJobs.currentIndex()]
        self.job = j
        form.listOperations.clear()
        self.operations = []
        for op in j.Operations.OutList:
            if hasattr(op, "Group"):
                for subop in op.Group:
                    self.addOperation(form, subop)
            else:
                self.addOperation(form, op)
        if  self.initdone:
          self.SetupSimulation()

    def onSpeedBarChange(self):
        form = self.taskForm.form
        self.simperiod = 1000 / form.sliderSpeed.value()
        form.labelGPerSec.setText(str(form.sliderSpeed.value()) + " G/s")
        # if (self.timer.isActive()):
        self.timer.setInterval(self.simperiod)

    def onAccuracyBarChange(self):
        form = self.taskForm.form
        self.accuracy = 1.1 - 0.1 * form.sliderAccuracy.value()
        form.labelAccuracy.setText(str(self.accuracy) + "%")

    def GuiBusy(self, isBusy):
        form = self.taskForm.form
        # form.toolButtonStop.setEnabled()
        form.toolButtonPlay.setEnabled(not isBusy)
        form.toolButtonPause.setEnabled(isBusy)
        form.toolButtonStep.setEnabled(not isBusy)
        form.toolButtonFF.setEnabled(not isBusy)

    def EndSimulation(self):
        self.UpdateProgress()
        self.timer.stop()
        self.GuiBusy(False)
        self.ViewShape()
        self.resetSimulation = True

        # Create the final Shape for stock
        createShapeResult()

    def SimStop(self):
        self.cutTool.ViewObject.hide()
        self.iprogress = 0
        self.EndSimulation()

    def InvalidOperation(self):
        if len(self.activeOps) == 0:
          return True
        if (self.tool == None):
          TSError("No tool assigned for the operation")
          return True
        return False

    def SimFF(self):
        if self.InvalidOperation():
            return
        self.GuiBusy(True)
        self.timer.start(1)
        self.disableAnim = True

    def SimStep(self):
        if self.InvalidOperation():
            return
        self.disableAnim = False
        self.PerformCut()

    def SimPlay(self):
        if self.InvalidOperation():
            return
        self.disableAnim = False
        self.GuiBusy(True)
        self.timer.start(self.simperiod)

    def ViewShape(self):
        if self.isVoxel:
            (self.cutMaterial.Mesh, self.cutMaterialIn.Mesh) = self.voxSim.GetResultMesh()
        else:
            self.cutMaterial.Shape = self.stock

    def SimPause(self):
        if self.disableAnim:
            self.ViewShape()
        self.GuiBusy(False)
        self.timer.stop()

    def RemoveTool(self):
        if self.cutTool is None:
            return
        FreeCAD.ActiveDocument.removeObject(self.cutTool.Name)
        self.cutTool = None

    def RemoveInnerMaterial(self):
        if self.cutMaterialIn is not None:
            if self.isVoxel and self.cutMaterial is not None:
                mesh = Mesh.Mesh()
                mesh.addMesh(self.cutMaterial.Mesh)
                mesh.addMesh(self.cutMaterialIn.Mesh)
                self.cutMaterial.Mesh = mesh
            FreeCAD.ActiveDocument.removeObject(self.cutMaterialIn.Name)
            self.cutMaterialIn = None

    def RemoveMaterial(self):
        if self.cutMaterial is not None:
            FreeCAD.ActiveDocument.removeObject(self.cutMaterial.Name)
            self.cutMaterial = None
        self.RemoveInnerMaterial()

    def accept(self):
        self.EndSimulation()
        self.RemoveInnerMaterial()
        self.RemoveTool()

    def cancel(self):
        self.EndSimulation()
        self.RemoveTool()
        self.RemoveMaterial()
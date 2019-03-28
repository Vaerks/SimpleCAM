import FreeCAD
from PathScripts import PathLiveSimulator
from PathScripts import PathUtils
import os

from FreeCAD import Vector, Base

_filePath = os.path.dirname(os.path.abspath(__file__))

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtGui, QtCore

def recomputeSimulation():
    PathLiveSimulator.activateSimulation()

class CommandPathLiveSimulate:

    def GetResources(self):
        return {'Pixmap': 'Path-LiveSimulator',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Path_LiveSimulator", "Live CAM Simulator"),
                'Accel': "P, M",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Path_LiveSimulator", "Live Simulate Path G-Code on stock")}

    def IsActive(self):
        if FreeCAD.ActiveDocument is not None:
            for o in FreeCAD.ActiveDocument.Objects:
                if o.Name[:3] == "Job":
                        return True
        return False

    def resetSimulation(self):
        PathUtils.deleteObject("CutTool")
        PathUtils.deleteObject("CutMaterial")
        PathUtils.deleteObject("CutMaterialIn")

    def activateSimulation(self):
        simulation = PathLiveSimulator.PathLiveSimulation()
        simulation.Activate()
        simulation.SimFF()  # Show the result without the animation

    def Activated(self):
        job = PathUtils.GetJobs("Job")[0]
        # self.resetSimulation()
        if job.Simulation:
            PathUtils.hideObject("CutMaterial")
            PathUtils.hideObject("CutMaterialIn")
            job.Simulation = False
        else:
            PathUtils.showObject("CutMaterial")
            PathUtils.showObject("CutMaterialIn")
            job.Simulation = True



if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_LiveSimulator', CommandPathLiveSimulate())
    FreeCAD.Console.PrintLog("Loading PathLiveSimulator Gui... done\n")

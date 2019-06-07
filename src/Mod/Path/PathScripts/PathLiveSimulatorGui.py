import FreeCAD
from PathScripts import PathLiveSimulator
from PathScripts import PathUtils
import os
from threading import Thread
import time

from FreeCAD import Vector, Base

_filePath = os.path.dirname(os.path.abspath(__file__))

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtGui, QtCore

LIVE_SIMULATION = False

def recomputeSimulation(obj=None, job=None):
    if LIVE_SIMULATION:
        PathLiveSimulator.activateSimulation(obj, job)

def recomputeResult(job):
    if LIVE_SIMULATION:
        PathLiveSimulator.createResultStock(job)


class CommandPathLiveSimulate:

    def GetResources(self):
        return {'Pixmap': 'Path-LiveSimulator',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Path_LiveSimulator", "Live CAM Simulator"),
                'Accel': "P, M",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Path_LiveSimulator", "Live Simulate Path G-Code on stock")}

    def IsActive(self):
        if FreeCAD.ActiveDocument is not None:
            selection = FreeCADGui.Selection.getSelectionEx()

            if selection is not None:
                job = PathUtils.findParentJob(selection[0].Object)
                if job is not None:
                    if FreeCAD.ActiveDocument.getObject("ResultStock_"+job.Name):
                        return True

        return False

    def activateSimulation(self):
        simulation = PathLiveSimulator.PathLiveSimulation()
        simulation.Activate()
        simulation.SimFF()  # Show the result without the animation

    def Activated(self):
        selections = FreeCADGui.Selection.getSelectionEx()
        if len(selections) == 1:
            obj = selections[0].Object
            job = PathUtils.findParentJob(obj)

            if job.Simulation:
                PathUtils.hideObject("ResultStock_"+job.Name)
                job.Simulation = False
            else:
                PathUtils.showObject("ResultStock_"+job.Name)
                job.Simulation = True


if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_LiveSimulator', CommandPathLiveSimulate())
    FreeCAD.Console.PrintLog("Loading PathLiveSimulator Gui... done\n")

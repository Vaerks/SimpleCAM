import FreeCAD
from PathScripts import PathLiveSimulator
import os

from FreeCAD import Vector, Base

_filePath = os.path.dirname(os.path.abspath(__file__))

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtGui, QtCore

IS_SIMULATION_ACTIVE = False

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

    def resetObject(self, obj):
        try:
            FreeCAD.ActiveDocument.removeObject(obj)
        except:
            print("PathLiveSimulatorGUi: The "+obj+" object cannot be deleted.")

    def resetSimulation(self):
        self.resetObject("CutTool")
        self.resetObject("CutMaterial")
        self.resetObject("CutMaterialIn")

    def activateSimulation(self):
        simulation = PathLiveSimulator.PathLiveSimulation()
        simulation.Activate()
        simulation.SimFF()  # Show the result without the animation

    def Activated(self):
        global IS_SIMULATION_ACTIVE
        self.resetSimulation()
        if IS_SIMULATION_ACTIVE:
            IS_SIMULATION_ACTIVE = False
        else:
            self.activateSimulation()
            IS_SIMULATION_ACTIVE = True



if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_LiveSimulator', CommandPathLiveSimulate())
    FreeCAD.Console.PrintLog("Loading PathLiveSimulator Gui... done\n")

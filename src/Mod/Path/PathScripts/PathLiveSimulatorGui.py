import FreeCAD
from PathScripts import PathLiveSimulator
import os

from FreeCAD import Vector, Base

_filePath = os.path.dirname(os.path.abspath(__file__))

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtGui, QtCore


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
        try:
            FreeCAD.ActiveDocument.removeObject("CutTool")
        except:
            print("PathLiveSimulatorGUi: The CutTool object cannot be found.")

        try:
            FreeCAD.ActiveDocument.removeObject("CutMaterial")
            FreeCAD.ActiveDocument.removeObject("CutMaterialIn")
        except:
            print("PathLiveSimulatorGUi: The CutMaterial object cannot be found.")

    def Activated(self):
        self.resetSimulation()
        simulation = PathLiveSimulator.PathLiveSimulation()
        simulation.Activate()
        simulation.SimFF()  # Show the result without the animation
        # FreeCAD.ActiveDocument.removeObject("CutTool")



if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_LiveSimulator', CommandPathLiveSimulate())
    FreeCAD.Console.PrintLog("Loading PathLiveSimulator Gui... done\n")

import FreeCAD
import FreeCADGui
import PathScripts.PathJob as PathJob
import PathScripts.PathJobDlg as PathJobDlg
import PathScripts.PathLog as PathLog
import PathScripts.PathPreferences as PathPreferences
import PathScripts.PathStock as PathStock
import PathScripts.PathUtil as PathUtil
import json

if FreeCAD.GuiUp:
    from PySide import QtGui, QtCore

class ModelClone:
    class ViewProvideer:

        def __init__(self, vobj):
            vobj.Proxy = self
            # self.job = job

        def setEdit(self, vobj=None, mode=0):
            print("ModelClone is edited.")
            return True

        def accept(self):
            print("Clone accepted")


class CommandPathJobSide:

    def GetResources(self):
        return {'Pixmap': 'Path-JobSide',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Path_JobSide", "Job Side"),
                'Accel': "P, M",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Path_JobSide", "New Job Side (Multi-side)")}

    def IsActive(self):
        if FreeCAD.ActiveDocument is not None:
            for o in FreeCAD.ActiveDocument.Objects:
                if o.Name[:3] == "Job":
                        return True
        return False

    def getModels(self, job):
        if job is not None and hasattr(job, "Model"):
            models = job.Model.Group
            return models

    def Activated(self):
        # Retrieve the project model to create the new Job Side
        models = [FreeCAD.ActiveDocument.getObject("Part__Feature")]

        if models:
            self.Execute(models)
            FreeCAD.ActiveDocument.recompute()

    @classmethod
    def Execute(cls, base):
        from PathScripts import PathJobGui
        models = [o.Name for o in base]
        PathJobGui.Create(models)


if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_JobSide', CommandPathJobSide())
    FreeCAD.Console.PrintLog("Loading JobSide Gui... done\n")

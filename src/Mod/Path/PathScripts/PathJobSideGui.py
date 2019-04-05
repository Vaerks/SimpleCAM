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

    def Activated(self):
        print("Create new working job side")
        dialog = PathJobDlg.JobCreate()
        dialog.setupTemplate()
        dialog.setupModel()
        if dialog.exec_() == 1:
            models = dialog.getModels()
            if models:
                self.Execute(models, dialog.getTemplate())
                FreeCAD.ActiveDocument.recompute()

    @classmethod
    def Execute(cls, base, template):
        FreeCADGui.addModule('PathScripts.PathJobGui')
        if template:
            template = "'%s'" % template
        else:
            template = 'None'
        FreeCADGui.doCommand('PathScripts.PathJobGui.Create(%s, %s)' % ([o.Name for o in base], template))


if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_JobSide', CommandPathJobSide())
    FreeCAD.Console.PrintLog("Loading JobSide Gui... done\n")

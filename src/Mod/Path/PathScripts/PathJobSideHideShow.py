import FreeCAD
import FreeCADGui
import PathScripts.PathJob as PathJob
import PathScripts.PathJobDlg as PathJobDlg
import PathScripts.PathLog as PathLog
import PathScripts.PathPreferences as PathPreferences
import PathScripts.PathStock as PathStock
import PathScripts.PathUtil as PathUtil
import json

import PathUtils

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


class CommandPathJobSideHideShow:

    def GetResources(self):
        return {'Pixmap': 'Path-JobSide',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Path_JobSideHideShow", "Job Side HideShow"),
                'Accel': "P, M",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Path_JobSideHideShow", "Hide or Show a Job Side")}

    def IsActive(self):
        if FreeCAD.ActiveDocument is not None:
            if FreeCADGui.Selection.getCompleteSelection():
                for o in FreeCADGui.Selection.getCompleteSelection():
                    if o.Name[:3] == "Job" or PathUtils.findParentJob(o) is not None:
                        return True

        return False

    def getModels(self, job):
        if job is not None and hasattr(job, "Model"):
            models = job.Model.Group
            return models

    def Activated(self):
        print("Hide Show activated")
        if FreeCAD.ActiveDocument is not None:
            if FreeCADGui.Selection.getCompleteSelection():
                for o in FreeCADGui.Selection.getCompleteSelection():
                    if hasattr(o, "Active"):
                        o.Active = not o.Active
                        o.ViewObject.Visibility = o.Active

                        # For Super Operations
                        if o.TypeId == "Path::FeatureCompoundPython":
                            for subop in o.Group:
                                subop.Active = o.Active
                                subop.ViewObject.Visibility = o.Active

                        FreeCAD.ActiveDocument.recompute()
                        return

                    elif hasattr(o, "IsActive"):
                        job = o
                        break

                    else:
                        job = PathUtils.findParentJob(o)
                        break

                self.toggleJob(job, True)

                for j in PathUtils.getJobs():
                    if j is not job:
                        self.toggleJob(j, False)

                FreeCAD.ActiveDocument.recompute()

    def toggleJob(self, job, visible):
        operations = job.Operations.OutList
        job.IsActive = visible

        for op in operations:
            op.Active = job.IsActive
            op.ViewObject.Visibility = job.IsActive

            if op.TypeId == "Path::FeatureCompoundPython":
                for subop in op.Group:
                    subop.Active = job.IsActive
                    subop.ViewObject.Visibility = job.IsActive

        job.ViewObject.Visibility = job.IsActive
        job.Stock.ViewObject.Visibility = job.IsActive

        for model in job.Model.Group:
            model.ViewObject.Visibility = job.IsActive

    @classmethod
    def Execute(cls, base, template=None):
        from PathScripts import PathJobGui
        FreeCADGui.addModule('PathScripts.PathJobGui')
        if template:
            template = "'%s'" % template
        else:
            template = 'None'

        models = [o.Name for o in base]
        PathJobGui.Create(models, jobside=False)
        # FreeCADGui.doCommand('PathScripts.PathJobGui.Create(%s)' % ([o.Name for o in base]))

if FreeCAD.GuiUp:
    # register the FreeCAD command
    # PathJobSideHideShow
    FreeCADGui.addCommand('Path_JobSideHideShow', CommandPathJobSideHideShow())
    FreeCAD.Console.PrintLog("Loading PathJobSideHideShow... done\n")

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


class CommandPathJobSideHideShow:

    def GetResources(self):
        return {'Pixmap': 'Path-JobSide',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Path_JobSideHideShow", "Job Side HideShow"),
                'Accel': "P, M",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Path_JobSideHideShow", "Hide or Show a Job Side")}

    def IsActive(self):
        # The Job hide/show button shall only be active if the user selects a job or an object from a job
        if FreeCAD.ActiveDocument is not None:
            if FreeCADGui.Selection.getCompleteSelection():
                for o in FreeCADGui.Selection.getCompleteSelection():
                    if o.Name[:3] == "Job" or PathUtils.findParentJob(o) is not None:
                        return True

        return False

    def Activated(self):
        if FreeCAD.ActiveDocument is not None:
            if FreeCADGui.Selection.getCompleteSelection():
                for o in FreeCADGui.Selection.getCompleteSelection():
                    if hasattr(o, "Active"):
                        # If the object has the attribute "Active", it is an operation
                        # and the visibility shall be toggled
                        o.Active = not o.Active
                        o.ViewObject.Visibility = o.Active

                        # For Super Operations, toggle visibility of all the sub-operations as well
                        if o.TypeId == "Path::FeatureCompoundPython":
                            for subop in o.Group:
                                if subop.Visible:  # A sub-operation is not "Visible" if it has been disabled
                                    # from the Super Operation GUI, in this case, the visibility must always be disabled
                                    subop.Active = o.Active
                                    subop.ViewObject.Visibility = o.Active

                        FreeCAD.ActiveDocument.recompute()
                        return

                    elif hasattr(o, "IsActive"):  # This means that the object is a job
                        job = o
                        break

                    else:  # Another type of object in the job (Stock/Model for instance)
                        job = PathUtils.findParentJob(o)
                        break

                self.showJob(job)

    def showJob(self, job):
        # The function shall show one job and hide the others by turning their visibility to off
        self.toggleJob(job, True)

        for j in PathUtils.getJobs():
            if j is not job:
                self.toggleJob(j, False)

    def toggleJob(self, job, visible):
        operations = job.Operations.OutList
        job.IsActive = visible

        # Disable/enable all the operations of the job
        for op in operations:
            op.Active = job.IsActive
            op.ViewObject.Visibility = job.IsActive

            # For Super Operations, don't forget the sub-operations
            if op.TypeId == "Path::FeatureCompoundPython":
                for subop in op.Group:
                    if subop.Visible:  # A sub-operation is not "Visible" if it has been disabled
                        # from the Super Operation GUI, in this case, the visibility must always be disabled
                        subop.Active = job.IsActive
                        subop.ViewObject.Visibility = job.IsActive

        job.ViewObject.Visibility = job.IsActive
        job.Stock.ViewObject.Visibility = job.IsActive

        for model in job.Model.Group:
            model.ViewObject.Visibility = job.IsActive

        FreeCAD.ActiveDocument.recompute()


if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_JobSideHideShow', CommandPathJobSideHideShow())
    FreeCAD.Console.PrintLog("Loading PathJobSideHideShow... done\n")

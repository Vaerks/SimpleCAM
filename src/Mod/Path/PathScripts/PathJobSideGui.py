import FreeCAD

if FreeCAD.GuiUp:
    import FreeCADGui
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



if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_JobSide', CommandPathJobSide())
    FreeCAD.Console.PrintLog("Loading JobSide Gui... done\n")

# -*- coding: utf-8 -*-

# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2015 Dan Falck <ddfalck@gmail.com>                      *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************
''' Post Process command that will make use of the Output File and Post Processor entries in PathJob '''

from __future__ import print_function

import FreeCAD
import FreeCADGui
import PathScripts.PathJob as PathJob
import PathScripts.PathLog as PathLog
import PathScripts.PathPreferences as PathPreferences
import PathScripts.PathToolController as PathToolController
import PathScripts.PathUtil as PathUtil
import PathScripts.PathUtils as PathUtils
import os

from PathScripts.PathPostProcessor import PostProcessor
from PySide import QtCore, QtGui


LOG_MODULE = PathLog.thisModule()

PathLog.setLevel(PathLog.Level.DEBUG, LOG_MODULE)
#PathLog.trackModule(LOG_MODULE)

# Qt tanslation handling
def translate(context, text, disambig=None):
    return QtCore.QCoreApplication.translate(context, text, disambig)

class DlgSelectPostProcessor:

    def __init__(self, parent=None):
        self.dialog = FreeCADGui.PySideUic.loadUi(":/panels/DlgSelectPostProcessor.ui")
        firstItem = None
        for post in PathPreferences.allEnabledPostProcessors():
            item = QtGui.QListWidgetItem(post)
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsSelectable | QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.dialog.lwPostProcessor.addItem(item)
            if not firstItem:
                firstItem = item
        if firstItem:
            self.dialog.lwPostProcessor.setCurrentItem(firstItem)
        else:
            self.dialog.buttonBox.button(QtGui.QDialogButtonBox.Ok).setEnabled(False)
        self.tooltips = {}
        self.dialog.lwPostProcessor.itemDoubleClicked.connect(self.dialog.accept)
        self.dialog.lwPostProcessor.setMouseTracking(True)
        self.dialog.lwPostProcessor.itemEntered.connect(self.updateTooltip)

    def updateTooltip(self, item):
        if item.text() in self.tooltips.keys():
            tooltip = self.tooltips[item.text()]
        else:
            processor = PostProcessor.load(item.text())
            self.tooltips[item.text()] = processor.tooltip
            tooltip = processor.tooltip
        self.dialog.lwPostProcessor.setToolTip(tooltip)

    def exec_(self):
        if self.dialog.exec_() == 1:
            posts = self.dialog.lwPostProcessor.selectedItems()
            return posts[0].text()
        return None

class CommandPathPost:

    def resolveFileName(self, job, name):
        path = PathPreferences.defaultOutputFile()
        if job.PostProcessorOutputFile:
            path = job.PostProcessorOutputFile
        filename = path
        if '%D' in filename:
            D = FreeCAD.ActiveDocument.FileName
            if D:
                D = os.path.dirname(D)
                # in case the document is in the current working directory
                if not D:
                    D = '.'
            else:
                FreeCAD.Console.PrintError("Please save document in order to resolve output path!\n")
                return None
            filename = filename.replace('%D', D)

        if '%d' in filename:
            d = FreeCAD.ActiveDocument.Label
            filename = filename.replace('%d', d)

        if '%j' in filename:
            j = job.Label
            filename = filename.replace('%j', j)

        if '%M' in filename:
            pref = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Macro")
            M = pref.GetString("MacroPath", FreeCAD.getUserAppDataDir())
            filename = filename.replace('%M', M)

        policy = PathPreferences.defaultOutputPolicy()

        openDialog = policy == 'Open File Dialog'
        if os.path.isdir(filename) or not os.path.isdir(os.path.dirname(filename)):
            # Either the entire filename resolves into a directory or the parent directory doesn't exist.
            # Either way I don't know what to do - ask for help
            openDialog = True

        if os.path.isfile(filename) and not openDialog:
            if policy == 'Open File Dialog on conflict':
                openDialog = True

        # In case of multiple jobs (multi-sides), if a project name is already given by the saving dialog (first job),
        #  it has to re-use the name without asking the user again.
        if openDialog and name is None:
            foo = QtGui.QFileDialog.getSaveFileName(QtGui.QApplication.activeWindow(), "Output File", filename)
            if foo:
                filename = foo[0]
            else:
                filename = None

        elif name is not None:
            filename = name

        path = filename
        filename = filename + "_" + job.Label

        # Apply version number in the filename
        if policy == 'Append Unique ID on conflict':
            fn, ext = os.path.splitext(filename)
            n = job.Version
            filename = "%s_%03d%s" % (fn, n, ext)

        job.Version = job.Version + 1

        return filename, path

    def resolvePostProcessor(self, job):
        if hasattr(job, "PostProcessor"):
            post = PathPreferences.defaultPostProcessor()
            if job.PostProcessor:
                post = job.PostProcessor
            if post and PostProcessor.exists(post):
                return post
        dlg = DlgSelectPostProcessor()
        return dlg.exec_()


    def GetResources(self):
        return {'Pixmap': 'Path-Post',
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Path_Post", "Post Process"),
                'Accel': "P, P",
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Path_Post", "Post Process the selected Job")}

    def IsActive(self):
        """
        if FreeCAD.ActiveDocument is not None:
            if FreeCADGui.Selection.getCompleteSelection():
                for o in FreeCAD.ActiveDocument.Objects:
                    if o.Name[:3] == "Job":
                        return True

        return False
        """
        if len(PathUtils.getJobs()) > 0:
            return True
        else:
            return False

    def exportObjectsWith(self, objs, job, needFilename = True, name=None):
        PathLog.track()
        # check if the user has a project and has set the default post and
        # output filename
        postArgs = PathPreferences.defaultPostProcessorArgs()
        if hasattr(job, "PostProcessorArgs") and job.PostProcessorArgs:
            postArgs = job.PostProcessorArgs
        elif hasattr(job, "PostProcessor") and job.PostProcessor:
            postArgs = ''

        path = None

        postname = self.resolvePostProcessor(job)
        filename = '-'
        if postname and needFilename:
            filename, path = self.resolveFileName(job, name)

        subobjs = []

        for obj in objs:
            if obj.TypeId == "Path::FeatureCompoundPython":
                objs.remove(obj)
                for subobj in obj.Group:
                    subobjs.append(subobj)

        if postname and filename:
            print("post: %s(%s, %s)" % (postname, filename, postArgs))
            processor = PostProcessor.load(postname)
            objs = objs + subobjs
            gcode = processor.export(objs, filename, postArgs)
            return (False, gcode, path)
        else:
            return (True, '', path)

    def Activated(self):
        PathLog.track()
        FreeCAD.ActiveDocument.openTransaction(
            translate("Path_Post", "Post Process the Selected path(s)"))
        FreeCADGui.addModule("PathScripts.PathPost")

        actualjob = None
        from PathScripts import PathJobSideHideShow
        cmd = PathJobSideHideShow.CommandPathJobSideHideShow()

        jobs = PathUtils.getJobs()
        path = None
        for job in jobs:
            PathLog.debug("about to postprocess job: {}".format(job.Name))

            # If the job is active, it means that this job has to be shown again after the post process.
            if job.IsActive:
                actualjob = job
            # If not, it means it is a hidden job that has to be set active for the process and then
            #   inactive again to hide it.
            else:
                cmd.toggleJob(job, True)

            # Build up an ordered list of operations and tool changes.
            # Then post-the ordered list
            postlist = []
            currTool = None
            for obj in job.Operations.Group:
                PathLog.debug("obj: {}".format(obj.Name))
                tc = PathUtil.toolControllerForOp(obj)
                if tc is not None:
                    if tc.ToolNumber != currTool:
                        postlist.append(tc)
                        currTool = tc.ToolNumber
                postlist.append(obj)

            fail = True
            rc = ''

            print(postlist)

            # Path is re-use to give all the files the same location.
            (fail, rc, path) = self.exportObjectsWith(postlist, job, name=path)

            if fail:
                FreeCAD.ActiveDocument.abortTransaction()
            else:
                FreeCAD.ActiveDocument.commitTransaction()
            FreeCAD.ActiveDocument.recompute()

        if actualjob is not None:
            cmd.showJob(actualjob)

if FreeCAD.GuiUp:
    # register the FreeCAD command
    FreeCADGui.addCommand('Path_Post', CommandPathPost())

FreeCAD.Console.PrintLog("Loading PathPost... done\n")

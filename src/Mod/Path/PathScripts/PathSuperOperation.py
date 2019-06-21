import PathScripts.PathLog as PathLog

import PathScripts.PathCircularHoleBase as PathCircularHoleBase
from PathScripts import PathOp

from PySide import QtCore


class ObjectSuperOp(PathOp.ObjectOp):
    def initSuperOperation(self, obj, superOpType):
        PathLog.track()

        # SuperOperationType: This property is used  to know what type of Super Operation is done.
        obj.addProperty("App::PropertyString", "SuperOperationType", "SuperOperation",
                        QtCore.QT_TRANSLATE_NOOP("App:Property", "Super Operation Type"))

        obj.SuperOperationType = superOpType

        return obj

    def updateSubOperations(self, obj):
        """ Sub-classes overwritten method used to update the sub-operations during a change. """
        pass

    def initSubOperations(self, obj):
        """ Sub-classes overwritten method used to init the sub-operations properties. """
        pass


class ObjectSuperCircularHoleBase(PathCircularHoleBase.ObjectOp):
    def initSuperOperation(self, obj, superOpType):
        PathLog.track()

        # SuperOperationType: This property is used  to know what type of Super Operation is done.
        obj.addProperty("App::PropertyString", "SuperOperationType", "SuperOperation",
                            QtCore.QT_TRANSLATE_NOOP("App:Property", "Super Operation Type"))

        obj.SuperOperationType = superOpType
        return obj

    def updateSubOperations(self, obj):
        """ Sub-classes overwritten method used to update the sub-operations during a change. """
        pass

    def initSubOperations(self, obj):
        """ Sub-classes overwritten method used to init the sub-operations properties. """
        pass

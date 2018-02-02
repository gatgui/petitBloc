from numbers import Number
import copy


class Proxy():
    pass


class PBEnum():
    pass


class ParameterBase(object):
    def __init__(self, name, typeClass=None, value=None, parent=None):
        super(ParameterBase, self).__init__()
        self.__name = name
        self.__parent = parent

    def __str__(self):
        return "ParameterBase<'{}'>".format(self.__name)

    def __repr__(self):
        return self.__str__()

    def activate(self):
        pass

    def terminate(self):
        pass

    def hasExpression(self):
        return False

    def validExpression(self):
        return False

    def setExpression(self, expression):
        return False

    def getExpression(self):
        return ""

    def ancestor(self):
        if self.__parent is None:
            return None

        return self.__parent.ancestor()

    def parent(self):
        return self.__parent

    def name(self):
        return self.__name

    def path(self):
        if self.__parent is None:
            return self.__name

        return "{}@{}".format(self.__parent.path(), self.__name)

    def typeClass(self):
        return None

    def get(self):
        return None

    def set(self, value):
        return False


class PacketBase(object):
    def __init__(self, value=None):
        super(PacketBase, self).__init__()
        self.__value = value
        self.__type_class = value.__class__

    def __repr__(self):
        self.__str__()

    def __str__(self):
        return "Packet<'{}'>".format(self.__type_class.__name__)

    def typeClass(self):
        return self.__type_class

    def value(self):
        return copy.deepcopy(self.__value)

    def _del(self):
        del self.__value
        del self

    def pickUp(self):
        pass

    def drop(self):
        pass

    def refCount(self):
        return -1

    def isEOP(self):
        return False


class PortBase(object):
    def __init__(self, typeClass, name=None, parent=None):
        super(PortBase, self).__init__()
        self.__type_class = typeClass
        self.__parent = parent
        self.__name = name

    def name(self):
        return self.__name

    def ancestor(self):
        if self.__parent is None:
            return None

        return self.__parent.ancestor()

    def parent(self):
        return self.__parent

    def path(self):
        if self.__parent is None:
            return self.__name

        return "{}.{}".format(self.__parent.path(), self.__name)

    def match(self, port):
        if self.__type_class == port.typeClass():
            return True

        if issubclass(self.__type_class, Number) and issubclass(port.typeClass(), Number):
            return True

        return False

    def isConnected(self):
        return False

    def chains(self):
        for i in range(0):
            yield i

    def send(self):
        return False

    def receive(self):
        return None

    def typeClass(self):
        return self.__type_class

    def isInPort(self):
        return False

    def isOutPort(self):
        return False

    def activate(self):
        pass

    def terminate(self):
        pass

    def activate(self):
        pass

    def packetHistory(self):
        return []


class ChainBase(object):
    def __new__(self, srcPort, dstPort):
        if not srcPort.isOutPort() or not dstPort.isInPort():
            return None

        if not dstPort.match(srcPort):
            return None

        return super(ChainBase, self).__new__(self, srcPort, dstPort)

    def __init__(self, srcPort, dstPort):
        super(ChainBase, self).__init__()
        self.__src = srcPort
        self.__dst = dstPort
        self.__need_to_cast = False

        srcPort.connect(self)
        dstPort.connect(self)

        if srcPort.typeClass() != dstPort.typeClass():
            self.__need_to_cast = True

    def src(self):
        return self.__src

    def dst(self):
        return self.__dst

    def isConnected(self):
        return (self.__src is not None) and (self.__dst is not None)

    def empty(self):
        return True

    def disconnect(self):
        self.__src.disconnect(self)
        self.__dst.disconnect(self)
        self.__src = None
        self.__dst = None

    def activate(self):
        pass

    def terminate(self):
        pass

    def send(self, pack):
        return False

    def sendEOP(self):
        return False

    def receive(self, timeout=None):
        return None

    def needToCast(self):
        return self.__need_to_cast


class ComponentBase(object):
    Initialized = 0
    Active = 1
    Terminated = 2
    Failed = 3

    def __init__(self, name="", parent=None):
        self.__name = name
        self.__class_name = self.__class__.__name__
        self.__state = ComponentBase.Initialized
        self.__parent = parent

    def __str__(self):
        return "{}<'{}'>".format(self.__class_name, self.__name)

    def __repr__(self):
        return self.__str__()

    def debug(self, message):
        pass

    def warn(self, message):
        pass

    def error(self, message):
        pass

    def type(self):
        return self.__class_name

    def hasNetwork(self):
        return False

    def expandable(self):
        return False

    def rename(self, name):
        self.__name = name

    def name(self):
        return self.__name

    def ancestor(self):
        if self.__parent is None:
            return None

        return self.__parent.ancestor()

    def parent(self):
        return self.__parent

    def path(self):
        if self.__parent is None:
            return "/{}".format(self.__name)

        return "{}/{}".format(self.__parent.path(), self.__name)

    def setParent(self, parent):
        self.__parent = parent

    def getSchedule(self):
        return []

    def run(self):
        while (True):
            if not self.process():
                break

    def process(self):
        return False

    def initialize(self):
        pass

    def state(self):
        return self.__state

    def isWaiting(self):
        return self.__state is ComponentBase.Initialized

    def isWorking(self):
        return self.__state is ComponentBase.Active

    def isTerminated(self):
        return self.__state is ComponentBase.Terminated

    def isFailed(self):
        return self.__state is ComponentBase.Failed

    def resetState(self):
        self.__state = ComponentBase.Initialized

    def activate(self):
        self.__state = ComponentBase.Active

    def terminate(self, success=True):
        if success:
            self.__state = ComponentBase.Terminated
        else:
            self.__state = ComponentBase.Failed

    def addInput(self, typeClass, name=None):
        return None

    def removeInput(self, inPort):
        return False

    def removeOutput(self, outPort):
        return False

    def addOutput(self, typeClass, name=None):
        return None

    def outputs(self):
        for i in range(0):
            yield i

    def inputs(self):
        for i in range(0):
            yield i

    def hasConnection(self, port):
        return False

    def removeParam(self, name_or_param):
        return False

    def addParam(self, typeClass=None, name=None, value=None):
        return None

    def addEnumParam(self, name, valueList, value=None):
        return None

    def params(self, includeExtraParam=True):
        for i in range(0):
            yield i

    def addExtraParam(self, typeClass=None, name=None, value=None):
        return None

    def extraParams(self):
        for i in range(0):
            yield i

    def param(self, index_or_name):
        return None

    def output(self, index_or_name):
        return None

    def input(self, index_or_name):
        return None

    def upstream(self):
        return []
        
    def downstream(self):
        return []

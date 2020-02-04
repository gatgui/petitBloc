import re
import json
import operator
from . import box
from . import chain
from . import proxy
from . import blockManager
from . import workerManager
from . import const
import os


ReBootNode = re.compile("^{}\/".format(const.RootBoxName))


def __sortDataBtPath(data):
    return sorted(data, cmp=__blockCompare, key=operator.itemgetter("path"))


def __blockCompare(x, y):
    xc = x.count("/")
    yc = y.count("/")

    return cmp(x, y) if xc == yc else cmp(xc, yc)


def __addRootPath(path):
    if ReBootNode.search(path):
        return path

    return "/{}/{}".format(const.RootBoxName, path)


def __shortName(path):
    return os.path.basename(path)


def __parentPath(path):
    return os.path.dirname(path)


def __setVerboseLevel(l):
    if l < 0 or l > 3:
        print("Invalid verbose level {}. Use default level (1)".format(l))
        l = 1

    if l == 0:
        workerManager.WorkerManager.SetLogLevel(const.LogLevel.NoLog)
    elif l == 1:
        workerManager.WorkerManager.SetLogLevel(const.LogLevel.Error)
    elif l == 2:
        workerManager.WorkerManager.SetLogLevel(const.LogLevel.Warn)
    elif l == 3:
        workerManager.WorkerManager.SetLogLevel(const.LogLevel.Debug)


def __query(filePath):
    data = Read(filePath)

    if (data["blocks"]):
        print("# List Blocks")
    for b in data["blocks"]:
        print("    '{}'({})".format(__addRootPath(b["path"]), b["type"]))

        for k, v in b.get("params", {}).iteritems():
            if v["expression"]:
                print("        {}@{}: {}".format(__addRootPath(b["path"]), k, str(v["expression"])))
            else:
                print("        {}@{}: {}".format(__addRootPath(b["path"]), k, str(v["value"])))
        for k, v in b.get("extraParams", {}).iteritems():
            if v["expression"]:
                print("        {}@{}: {} ({})".format(__addRootPath(b["path"]), k, str(v["expression"]), str(v["type"])))
            else:
                print("        {}@{}: {} ({})".format(__addRootPath(b["path"]), k, str(v["value"]), str(v["type"])))

    if data["connections"]:
        print("# List Connections")
    for con in data["connections"]:
        print("    {} >> {}".format(__addRootPath(con["src"]), __addRootPath(con["path"])))


def __read(filePath):
    manager = blockManager.BlockManager()
    root = box.Box(const.RootBoxName)

    data = Read(filePath)

    ## create blocks
    for b in data["blocks"]:
        full_path = __addRootPath(b["path"])
        short_name = __shortName(full_path)
        parent = root.findBlock(__parentPath(full_path))
        if not parent:
            print("Warning : Could not find the parent block - {}".format(full_path))
            continue

        if b["type"] == "ProxyBlock":
            if not isinstance(parent, box.Box):
                print("Warning : Invalid proxyblock {}".format(full_path))

            continue

        else:
            bc = manager.block(b["type"])
            bloc = None

            if bc:
                if bc == box.SceneContext:
                    bloc = root.createContext()
                    if not bloc:
                        print("Warning : Failed to create a scene context block")

                else:
                    try:
                        bloc = bc()
                        if short_name is not None:
                            bloc.rename(short_name)

                        parent.addBlock(bloc)

                    except Exception as e:
                        print("Warning : Could not create an instance of {}".format(b["type"]))
                        print(e)
                        bloc = None

            else:
                print("Warning : Unknown block type : {}".format(b["type"]))
                bloc = None

            if bloc is not None:
                for k, vv in b.get("params", {}).iteritems():
                    parm = bloc.param(k)
                    if parm is None:
                        print("Warning : {} has not the parameter : {}".format(str(bloc), k))
                        continue

                    if not parm.set(vv["value"]):
                        print("Warning : Failed to set value {}@{} - {}".format(bloc.path(), k, str(vv["value"])))

                    if not parm.setExpression(vv["expression"]):
                        print("Warning : Failed to set expression {}@{} - {}".format(bloc.path(), k, str(vv["expression"])))

                for k, vv in b.get("extraParams", {}).iteritems():
                    type_name = vv["type"]
                    type_class = manager.findObjectClass(type_name)
                    if not type_class:
                        print("Warning : unknown parameter type - {}".format(type_name))
                        continue

                    parm = bloc.addExtraParam(type_class, k)
                    if parm is None:
                        print("Warning : Failed to add an extra parameter : {}".format(str(bloc), k))
                        continue

                    if not parm.set(vv["value"]):
                        print("Warning : Failed to set value {}@{} - {}".format(bloc.path(), k, str(vv["value"])))

                    if not parm.setExpression(vv["expression"]):
                        print("Warning : Failed to set expression {}@{} - {}".format(bloc.path(), k, str(vv["expression"])))

    ## proxy ports
    for prx in data["proxyPorts"]:
        full_path = __addRootPath(prx["path"])
        parent = root.findBlock(full_path)

        if parent is None or not isinstance(parent, box.Box):
            print("Warning : Could not find the parent box - {}".format(full_path))

            continue

        for inp in prx.get("in", []):
            type_name = inp["type"]
            type_class = manager.findObjectClass(type_name)
            if not type_class:
                print("Failed to load : Unknown port type - {}".format(type_name))

            parent.addInputProxy(type_class, inp["name"])

        for outp in prx.get("out", []):
            type_name = outp["type"]
            type_class = manager.findObjectClass(type_name)
            if not type_class:
                print("Failed to load : Unknown port type - {}".format(type_name))

            parent.addOutputProxy(type_class, outp["name"])

    ## connect ports
    for con in data["connections"]:
        src_full_path, src_port_name = __addRootPath(con["src"]).split(".")
        dst_full_path, dst_port_name = __addRootPath(con["path"]).split(".")
        chain_class = chain.Chain

        src_bloc = root.findBlock(src_full_path)
        if src_bloc is None:
            print("Warning: Could not find the source block - {}".format(src_full_path))
            continue

        if src_bloc.isProxy():
            src_proxy = src_bloc.proxy(src_port_name)
            if src_proxy is None:
                print("Warning : Could not find the source port - {}.{}".format(src_full_path, src_port_name))
                continue

            src_port = src_proxy.outPort()
            chain_class = proxy.ProxyChain

        else:
            src_port = src_bloc.output(src_port_name)
            if src_port is None:
                print("Warning : Could not find the source port - {}.{}".format(src_full_path, src_port_name))
                continue

        dst_bloc = root.findBlock(dst_full_path)
        if dst_bloc is None:
            print("Warning: Could not find the destination block - {}".format(dst_full_path))
            continue

        if dst_bloc.isProxy():
            dst_proxy = dst_bloc.proxy(dst_port_name)
            if dst_proxy is None:
                print("Warning : Could not find the source port - {}.{}".format(src_full_path, src_port_name))
                continue

            dst_port = dst_proxy.inPort()
            chain_class = proxy.ProxyChain

        else:
            dst_port = dst_bloc.input(dst_port_name)
            if dst_port is None:
                print("Warning : Could not find the destination port - {}.{}".format(dst_full_path, dst_port_name))
                continue

        res = chain_class(src_port, dst_port)
        if res is None:
            print("Warning : Faild to connect {}.{} >> {}.{}".format(src_port.path(), dst_port.path()))

    return root


def __overrideContext(root, parameters):
    for p in parameters:
        if p.count("=") != 1:
            print("Warning : Invalid context setting - {}".format(p))
            continue

        context_name, value = p.split("=")

        param = root.context(context_name)
        if param is None:
            print("Warning : Failed to override context. Could not find the parameter - {}".format(context_name))
            continue

        type_class = param.typeClass()
        try:
            if type_class == bool:
                v = bool(int(value))
            else:
                v = type_class(value)

            param.set(v)
        except Exception as e:
            print("Warning : Failed to override context. Invalid value - {} : {}".format(type_class.__name__, value))


def __override(root, parameters):
    for p in parameters:
        if p.count("@") != 1 or p.count("=") != 1:
            print("Warning : Invalid parameter setting - {}".format(p))
            continue

        paramfull, value = p.split("=")
        bloc_path, param_name = paramfull.split("@")
        bloc = root.findBlock(bloc_path)
        if bloc is None:
            print("Warning : Failed to override parameter. Could not find the block - {}".format(bloc_path))
            continue

        param = bloc.param(param_name)
        if param is None:
            print("Warning : Failed to override parameter. Could not find the parameter - {}".format(paramfull))
            continue

        type_class = param.typeClass()
        try:
            if type_class == bool:
                v = bool(int(value))
            else:
                v = type_class(value)

            param.set(v)
        except Exception as e:
            print("Warning : Failed to override parameter. Invalid value - {} : {}".format(type_class.__name__, value))


def Write(path, data):
    data["blocks"] = __sortDataBtPath(data["blocks"])
    data["connections"] = __sortDataBtPath(data["connections"])
    data["proxyPorts"] = __sortDataBtPath(data["proxyPorts"])

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

    print("// Save : {}".format(path))


def Read(path):
    data = {}
    with open(path, "r") as f:
        data = json.load(f)

    print("// Load : {}".format(path))

    data["blocks"] = __sortDataBtPath(data["blocks"])
    data["connections"] = __sortDataBtPath(data["connections"])
    data["proxyPorts"] = __sortDataBtPath(data["proxyPorts"])

    return data


def BlockInfo(blockType):
    manager = blockManager.BlockManager()
    bc = manager.block(blockType)

    if bc:
        try:
            bloc = bc()
            print("# <{}>".format(bloc.__class__.__name__))

            print("    InPort")
            for inp in bloc.inputs():
                print("        '{}' ({})".format(inp.name(), inp.typeClass().__name__))
            print("    OutPort")
            for inp in bloc.outputs():
                print("        '{}' ({})".format(inp.name(), inp.typeClass().__name__))
            print("    Parameter")
            for param in bloc.params():
                print("        '{}' ({})".format(param.name(), param.typeClass().__name__))

        except Exception as e:
            print("Warning : Could not create an instance of {}".format(blockType))
            print(e)
            return False

    else:
        print("Warning : Unknown block type : {}".format(blockType))
        return False

    return True


def BlockList():
    manager = blockManager.BlockManager()

    print("# Block List")
    for b in manager.blockNames():
        print("    {}".format(b))


def Query(filePath):
    try:
        __query(filePath)

    except Exception as e:
        print("ERROR : {}".format(str(e)))

        return False

    return True


def Run(filePath, contexts=None, parameters=None, maxProcess=1, multiProcessing=False, attrbutes=None, verbose=1):
    try:
        if contexts is None:
            contexts = []
        if parameters is None:
            parameters = []

        __setVerboseLevel(verbose)

        workerManager.WorkerManager.SetUseProcess(multiProcessing)

        root = __read(filePath)

        __override(root, parameters)
        __overrideContext(root, contexts)

        schedule = root.getSchedule()
        return workerManager.WorkerManager.RunSchedule(schedule, maxProcess=maxProcess)
    except Exception as e:
        print("ERROR : {}".format(str(e)))

        return False

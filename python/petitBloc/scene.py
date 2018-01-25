import re
import json
import operator
from . import box
from . import chain
from . import blockManager
from . import workerManager
from . import const


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

    return "{}/{}".format(const.RootBoxName, path)


def __shortName(path):
    return path[path.rfind("/") + 1:]


def __parentPath(path):
    return path[:path.rfind("/")]


def __query(filePath):
    data = Read(filePath)

    if (data["blocks"]):
        print("# List Blocks")
    for b in data["blocks"]:
        print("    '{}'({})".format(__addRootPath(b["path"]), b["type"]))

        for k, v in b.get("params", {}).iteritems():
            print("        {}: {}".format(k, str(v)))

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
                try:
                    bloc = bc(name=short_name)
                    parent.addBlock(bloc)

                except Exception as e:
                    print("Warning : Could not create an instance of {}".format(b["type"]))
                    print(e)
                    bloc = None

            else:
                print("Warning : Unknown block type : {}".format(b["type"]))
                bloc = None

            if bloc is not None:
                for k, v in b.get("params", {}).iteritems():
                    parm = bloc.param(k)
                    if parm is None:
                        print("Warning : {} has not the parameter : {}".format(str(bloc), k))
                        continue

                    if not parm.set(v):
                        print("Warning : Failed to set value {}@{} - {}".format(bloc.path(), k, str(v)))

    ## proxy ports
    for proxy in data["proxyPorts"]:
        full_path = __addRootPath(proxy["path"])
        parent = root.findBlock(full_path)

        if parent is None or not isinstance(parent, box.Box):
            print("Warning : Could not find the parent box - {}".format(full_path))

            continue

        for inp in proxy.get("in", []):
            type_name = inp["type"]
            type_class = manager.findObjectClass(type_name)
            if not type_class:
                print("Failed to load : Unknown port type - {}".format(type_name))

            parent.addInputProxy(type_class, inp["name"])

        for outp in proxy.get("out", []):
            type_name = outp["type"]
            type_class = manager.findObjectClass(type_name)
            if not type_class:
                print("Failed to load : Unknown port type - {}".format(type_name))

            parent.addOutputProxy(type_class, outp["name"])

    ## proxy params
    for pam in data["proxyParameters"]:
        full_path = __addRootPath(pam["path"])
        parent = root.findBlock(__parentPath(full_path))

        if parent is None or not isinstance(parent, box.Box):
            print("Warning : Could not find the parent box - {}".format(full_path))

        continue

        for pdata in pam["params"]:
            bloc_path, param_name = __addRootPath(pdata["param"]).split("@")
            target_bloc = root.findBlock(bloc_path)

            if target_bloc is None:
                print("Warning : Could not find target parent block - {}".format(bloc_path))
                continue

            param = target_bloc.param(param_name)
            if param is None:
                print("Warning : Could not find target param - {}".format(full_path))

            parent.addProxyParam(param, name=pdata["name"])

    ## connect ports
    for con in data["connections"]:
        src_full_path, src_port_name = __addRootPath(con["src"]).split(".")
        dst_full_path, dst_port_name = __addRootPath(con["path"]).split(".")

        src_bloc = root.findBlock(src_full_path)
        if src_bloc is None:
            print("Warning: Could not find the source block - {}".format(src_full_path))
            continue

        src_port = src_bloc.output(src_port_name)
        if src_port is None:
            print("Warning : Could not find the source port - {}.{}".format(src_full_path, src_port_name))
            continue

        dst_bloc = root.findBlock(dst_full_path)
        if dst_bloc is None:
            print("Warning: Could not find the destination block - {}".format(dst_full_path))
            continue

        dst_port = dst_bloc.input(dst_port_name)
        if dst_port is None:
            print("Warning : Could not find the destination port - {}.{}".format(dst_full_path, dst_port_name))
            continue

        res = chain.Chain(src_port, dst_port)
        if res is None:
            print("Warning : Faild to connect {}.{} >> {}.{}".format(src_port.path(), dst_port.path()))

    return root


def Write(path, data):
    data["blocks"] = __sortDataBtPath(data["blocks"])
    data["connections"] = __sortDataBtPath(data["connections"])
    data["proxyPorts"] = __sortDataBtPath(data["proxyPorts"])
    data["proxyParameters"] = __sortDataBtPath(data["proxyParameters"])

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
    data["proxyParameters"] = __sortDataBtPath(data["proxyParameters"])

    return data


def BlockInfo(blockType):
    manager = blockManager.BlockManager()
    bc = manager.block(blockType)

    if bc:
        try:
            bloc = bc()
            print("# Block Info")
            for inp in bloc.inputs():
                print("    InPort : '{}' ({})".format(inp.name(), inp.typeClass().__name__))
            for inp in bloc.outputs():
                print("    OutPort : '{}' ({})".format(inp.name(), inp.typeClass().__name__))
            for param in bloc.params():
                print("    Parameter : '{}' ({})".format(param.name(), param.typeClass().__name__))

        except Exception as e:
            print("Warning : Could not create an instance of {}".format(blockType))
            print(e)
            return False

    else:
        print("Warning : Unknown block type : {}".format(blockType))
        return False

    return True


def Query(filePath):
    try:
        __query(filePath)

    except Exception as e:
        print("ERROR : {}".format(str(e)))

        return False

    return True


def Run(filePath, multiProcessing=False, attrbutes=[]):
    try:
        workerManager.WorkerManager.SetUseProcess(multiProcessing)

        root = __read(filePath)
        schedule = root.getSchedule()
        workerManager.WorkerManager.RunSchedule(schedule)

        return True
    except Exception as e:
        print("ERROR : {}".format(str(e)))

        return False
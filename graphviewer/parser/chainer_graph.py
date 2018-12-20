import chainer
from chainer.computational_graph import build_computational_graph
import numpy

from graphviewer.parser.dtypes import convert_dtype
from graphviewer.proto.attr_value_pb2 import AttrValue
from graphviewer.proto.graph_pb2 import GraphDef
from graphviewer.proto.node_def_pb2 import NodeDef
from graphviewer.proto.tensor_shape_pb2 import TensorShapeProto
from graphviewer.proto.versions_pb2 import VersionDef


def get_graphdef_from_model(model, args):
    outputs = forward(model, args)
    return parse(outputs)


def parse(outputs):
    cgraph = build_computational_graph([outputs])

    nodes = []
    input_dict = {}
    for head, tail in cgraph.edges:
        input_dict.setdefault(id(tail), []).append(head)
    for node in cgraph.nodes:
        assert isinstance(node, (
            chainer.variable.VariableNode, chainer.function_node.FunctionNode))

        if id(node) not in input_dict:
            shpeproto = TensorShapeProto(
                dim=[TensorShapeProto.Dim(size=s) for s in node.shape])
            nodes.append(NodeDef(
                name=get_unique_name(node).encode(encoding='utf_8'),
                op='Variable',
                input=[],
                attr={
                    'dtype': AttrValue(type=convert_dtype(node.dtype)),
                    'shpae': AttrValue(shape=shpeproto),
                }
            ))
        else:
            inputs = [get_unique_name(n).encode(encoding='utf_8') for n in input_dict[id(node)]]
            attr = node.label.encode(encoding='utf_8')  # TODO
            nodes.append(NodeDef(
                name=get_unique_name(node).encode(encoding='utf_8'),
                op=node.__class__.__name__,
                input=inputs,
                attr={'parameters': AttrValue(s=attr)},
            ))
    return GraphDef(node=nodes, versions=VersionDef(producer=22))


def get_unique_name(node):
    return id(node)


def forward(model, args):
    if isinstance(args, tuple):
        args = list(args)
    if isinstance(args, list):
        for i, arg in enumerate(args):
            if isinstance(arg, numpy.ndarray):
                args[i] = chainer.Variable(arg)
        outputs = model(*args)
    elif isinstance(args, dict):
        for key, arg in args.items():
            if isinstance(arg, numpy.ndarray):
                args[key] = chainer.Variable(args)
        outputs = model(**args)
    elif isinstance(args, numpy.ndarray):
        outputs = model(chainer.Variable(args))
    elif isinstance(args, chainer.Variable):
        outputs = model(args)
    else:
        raise ValueError('type of passed arguments is not supported')
    return outputs

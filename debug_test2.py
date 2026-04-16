import torch
from eml_mcp.trees import EMLNode, NodeType
from eml_mcp.transformer import EMLCompiledFFN

z = EMLNode(NodeType.VAR, var_name="z")
tree = EMLNode(NodeType.EML, left=EMLNode(NodeType.CONST, value=0.0), right=z)
model = EMLCompiledFFN(trees=tree, variable_names=["z"], learnable=True)

print("unique_nodes:", {k: v['index'] for k,v in model.unique_nodes.items()})
print("root_indices_list:", model.root_indices_list)

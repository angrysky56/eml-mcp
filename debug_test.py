import torch
from eml_mcp.trees import EMLNode, NodeType
from eml_mcp.transformer import EMLCompiledFFN

z = EMLNode(NodeType.VAR, var_name="z")
tree = EMLNode(NodeType.EML, left=EMLNode(NodeType.CONST, value=0.0), right=z)
model = EMLCompiledFFN(trees=tree, variable_names=["z"], learnable=True)

print("root_indices:", model.root_indices)
print("const_indices:", model.const_indices)
print("var_indices:", model.var_indices)

etrees = model.network_to_etree()
print("etrees[0]:", etrees[0].node_type)

"""
==================
Connectivity Graph
==================

A connectivity graph is a mathmatical view of the connections between components in a netlist. This kind of 
representation enables the use of graph theory algorithms to better understand relations between components. There are
many different schemes (or configurations) that could be used to generate a connectivity graph. In general, nodes in a
connectivity graph represent components in the netlist and edges represent connections between components.

The connectivity graph generated in this example represents leaf instances (and optionally top level ports) as nodes
and connections between nodes as directed edges (from sources to sinks). It is assumed that input and output pins within
a leaf instance node are fully connected meaning that all input pins are connected to all output pins. This approach 
likely suggests greater connectivity than actually exists, but it maintains plausible paths found in the original 
netlist.

A connectivity graph is generated by traversing all of paths between components in the netlist. This includes 
connectionsthat cross hierarchical boundaries (e.g., connectivity of two leaf instances through ports on several
non-leaf instances). This can be an expensive operation; but once the graph is generated, it can be used to quickly 
identify connectivity between components.

A mechanism of uniquely identifying a component in the netlist is provided in this example. It is possible in a netlist
for a non-leaf definition, (i.e. a definition that instances other definitions), to be instanced more than once. In this
senarario, instances within the non-leaf definition are not unique. Uniqueness can be guarenteed by including the 
hierarchical path when referencing the desired instance. Accordingly, a lightweight object is created to preserve the
full hierarchical path when referencing the instances.
"""

import spydrnet as sdn
import networkx as nx

netlist = None
connectivity_graph = None

def run():
    """
    This example loads a netlist and then generates two connectivity graphs: one with top level ports and one without.
    The connectivity graph without top level ports could be generated more quickly by copying the graph containing the
    ports and then removing the nodes that represent top level ports. These connectivity graphs can also be used to
    generate sequential connectivity graphs by removing nodes that represent combinational logic and propagating their
    created connections (add an edge from all predecessors to all successors).    
    """
    global netlist
    global connectivity_graph
    netlist = sdn.load_example_netlist_by_name('b13')
    
    connectivity_graph_with_top_level_ports = get_connectivity_graph(include_top_ports=True)
    print("Total nodes in connectivity_graph with top_level_ports", 
        connectivity_graph_with_top_level_ports.number_of_nodes())
    print("Total edges in connectivity_graph with top_level_ports", 
        connectivity_graph_with_top_level_ports.number_of_edges())
    
    connectivity_graph_without_top_level_ports = get_connectivity_graph(include_top_ports=False)
    print("Total nodes in connectivity_graph without top_level_ports", 
        connectivity_graph_without_top_level_ports.number_of_nodes())
    print("Total edges in connectivity_graph without top_level_ports", 
        connectivity_graph_without_top_level_ports.number_of_edges())
    
def get_connectivity_graph(include_top_ports = True):
    """
    This function generates the connectivity graph of the netlist. 
    """
    connectivity_graph = nx.DiGraph()
    top_instance_node = generate_nodes()
    
    leaf_instance_nodes = get_leaf_instance_nodes(top_instance_node)
    connectivity_graph.add_nodes_from(leaf_instance_nodes)
    
    if include_top_ports:
        top_port_nodes = get_top_port_nodes(top_instance_node)
        connectivity_graph.add_nodes_from(top_port_nodes)
    
    for node in list(connectivity_graph.nodes):
        downstream_nodes = get_downstream_nodes(node, include_top_ports)
        for downstream_node in downstream_nodes:
            connectivity_graph.add_edge(node, downstream_node)
    
    return connectivity_graph
    
def generate_nodes():
    """
    This function generates a unique node for all instances of elements in a netlist.
    """
    top_node = Node(None, netlist.top_instance)
    search_stack = [top_node]
    while search_stack:
        node = search_stack.pop()
        item = node.item
        if isinstance(item, sdn.Instance):
            ref = item.reference
            for port in ref.ports:
                new_node = Node(node, port)
                node.children[port] = new_node
                search_stack.append(new_node)
            for cable in ref.cables:
                new_node = Node(node, cable)
                node.children[cable] = new_node
                search_stack.append(new_node)
            for instance in ref.children:
                new_node = Node(node, instance)
                node.children[instance] = new_node
                search_stack.append(new_node)
        elif isinstance(item, sdn.Port):
            for pin in item.pins:
                new_node = Node(node, pin)
                node.children[pin] = new_node
                search_stack.append(new_node)
        elif isinstance(item, sdn.Cable):
            for wire in item.wires:
                new_node = Node(node, wire)
                node.children[wire] = new_node
                search_stack.append(new_node) 
    return top_node

def get_leaf_instance_nodes(top_instance_node):
    """
    This function returns all leaf instance nodes in a netlist.
    """
    leaf_instance_nodes = list()
    search_stack = [top_instance_node]
    while search_stack:
        current_node = search_stack.pop()
        if isinstance(current_node.item, sdn.Instance):
            if current_node.item.reference.is_leaf():
                leaf_instance_nodes.append(current_node)
            else:
                search_stack += current_node.children.values()
    return leaf_instance_nodes

def get_top_port_nodes(top_instance_node):
    """
    This function returns top_level_ports in a netlist, (i.e., ports that belong to the top_instance if the netlist).
    """
    top_port_nodes = list(top_instance_node.children[x] for x in top_instance_node.children if isinstance(x, sdn.Port))
    return top_port_nodes
    
def get_downstream_nodes(node, include_top_ports):
    """
    This function finds downstream nodes (leaf instance and optionally top_level ports) from a given node. There are 
    some involved traversals included in this function (going from an InnerPin to and OuterPin and visa-versa).
    """
    downstream_nodes = list()    
    found_pin_nodes = set()
    search_stack = list()
    # Find starting wires if provided node is a leaf instance.
    if isinstance(node.item, sdn.Instance):
        instance = node.item
        parent_instance = node.parent
        
        for pin in instance.pins:
            inner_pin = pin.inner_pin
            wire = pin.wire
            if inner_pin.port.direction in {sdn.OUT, sdn.INOUT} and wire:
                port_node = node.children[inner_pin.port]
                pin_node = port_node.children[inner_pin]
                found_pin_nodes.add(pin_node)
                
                cable = wire.cable
                cable_node = parent_instance.children[cable]
                wire_node = cable_node.children[wire]
                search_stack.append(wire_node)
    # Find starting wires if provided node is a top_level_port and include_top_ports is asserted. 
    elif include_top_ports and isinstance(node.item, sdn.Port):
        port = node.item
        parent_instance = node.parent
        
        if port.direction in {sdn.IN, sdn.INOUT}:
            for pin in port.pins:
                wire = pin.wire
                if wire:
                    pin_node = node.children[pin]
                    found_pin_nodes.add(pin_node)
                    
                    cable = wire.cable
                    cable_node = parent_instance.children[cable]
                    wire_node = cable_node.children[wire]
                    search_stack.append(wire_node)
    
    # Perform a non-recursive traversal of identified wires until all leaf instances (and optionally top_level_ports)
    # are found.
    while search_stack:
        current_wire_node = search_stack.pop()
        current_cable_node = current_wire_node.parent
        current_instance_node = current_cable_node.parent
        
        current_wire = current_wire_node.item
        for pin in current_wire.pins:
            if isinstance(pin, sdn.InnerPin):
                port = pin.port
                port_node = current_instance_node.children[port]
                pin_node = port_node.children[pin]
                if pin_node not in found_pin_nodes:
                    found_pin_nodes.add(pin_node)
                    current_instance_parent_node = current_instance_node.parent
                    if current_instance_parent_node:
                        outer_pin = current_instance_node.item.pins[pin]
                        wire = outer_pin.wire
                        if wire:
                            cable = wire.cable
                            cable_node = current_instance_parent_node.children[cable]
                            wire_node = cable_node.children[wire]
                            search_stack.append(wire_node)
                    elif include_top_ports:
                        downstream_nodes.append(port_node)
            elif isinstance(pin, sdn.OuterPin):
                instance = pin.instance
                instance_node = current_instance_node.children[instance]
                if instance.reference.is_leaf():
                    downstream_nodes.append(instance_node)
                else:
                    inner_pin = pin.inner_pin
                    port = inner_pin.port
                    port_node = instance_node.children[port]
                    pin_node = port_node.children[inner_pin]
                    found_pin_nodes.add(pin_node)
                    
                    wire = inner_pin.wire
                    if wire:
                        cable = wire.cable
                        cable_node = instance_node.children[cable]
                        wire_node = cable_node.children[wire]
                        search_stack.append(wire_node)
                        
    return downstream_nodes

class Node:
    def __init__(self, parent, item):
        self.parent = parent
        self.item = item
        self.children = dict()
        
    def get_hiearchical_name(self):
        parents = list()
        parent = self.parent
        while parent:
            parents.append(parent)
            parent = parent.parent
        prefix = '/'.join(x.get_name() for x in reversed(parents))
        if isinstance(self.item, sdn.Wire):
            return "{}[{}]".format(prefix, self.item.cable.wires.index(self.item))
        elif isinstance(self.item, sdn.Pin):
            return "{}[{}]".format(prefix, self.item.port.pins.index(self.item))
        else:
            if prefix:
                return "{}/{}".format(prefix, self.get_name())
            else:
                return self.get_name()
            
    def get_name(self):
        if 'EDIF.original_identifier' in self.item:
            return self.item['EDIF.original_identifier']
        elif 'EDIF.identifier' in self.item:
            return self.item['EDIF.identifier']
    
run()

vm1@l2forwarding-vm:~$ cat dumb_ryu_controller.py
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.topology.event import EventSwitchEnter, EventSwitchLeave
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from topology import load_topology
import networkx as nx

# This function takes as input a networkx graph. It then computes
# the minimum Spanning Tree, and returns it, as a networkx graph.
def compute_spanning_tree(G):

    # The Spanning Tree of G
    ST = nx.minimum_spanning_tree(G)

    return ST

class L2Forwarding(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(L2Forwarding, self).__init__(*args, **kwargs)

        # Load the topology
        topo_file = 'topology.txt'
        self.G = load_topology(topo_file)

        # For each node in the graph, add an attribute mac-to-port
        for n in self.G.nodes():
            self.G.add_node(n, mactoport={})

        # Compute a Spanning Tree for the graph G
        self.ST = compute_spanning_tree(self.G)

        self.SPTTupList = self.ST.edges(data=False)


        print self.get_str_topo(self.G)
        print "printing spanning tree"
        print sorted(self.ST.edges(data=True))

    # This method returns a string that describes a graph (nodes and edges, with
    # their attributes). You do not need to modify this method.
    def get_str_topo(self, graph):
        res = 'Nodes\tneighbors:port_id\n'

        att = nx.get_node_attributes(graph, 'ports')
        for n in graph.nodes_iter():
            res += str(n)+'\t'+str(att[n])+'\n'

        res += 'Edges:\tfrom->to\n'
        for f in graph:
            totmp = []
            for t in graph[f]:
                totmp.append(t)
            res += str(f)+' -> '+str(totmp)+'\n'

        return res

    # This method returns a string that describes the Mac-to-Port table of a
    # switch in the graph. You do not need to modify this method.
    def get_str_mactoport(self, graph, dpid):
        res = 'MAC-To-Port table of the switch '+str(dpid)+'\n'

        for mac_addr, outport in graph.node[dpid]['mactoport'].items():
            res += str(mac_addr)+' -> '+str(outport)+'\n'

        return res.rstrip('\n')

    @set_ev_cls(EventSwitchEnter)
    def _ev_switch_enter_handler(self, ev):
        print('enter: %s' % ev)

    @set_ev_cls(EventSwitchLeave)
    def _ev_switch_leave_handler(self, ev):
        print('leave: %s' % ev)

    # This method is called every time an OF_PacketIn message is received by
    # the switch. Here we must calculate the best action to take and install
    # a new entry on the switch's forwarding table if necessary
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser
        in_port = msg.in_port

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        print pkt.protocols
        for p in pkt.protocols:
            try:
                src_node = p.src_ip.split('.')[-1]
                dst_node = p.dst_ip.split('.')[-1]
            except : pass
            if 'ipv4' in str(type(p)):
                src_node = p.src.split('.')[-1]
                dst_node = p.dst.split('.')[-1]
        dst = eth.dst
        src = eth.src

        dpid = dp.id

        print "dpid: ", dpid
        #self.mac_to_port.setdefault(dpid, {})
        """
        print "ofp", ofp
        print "ofp_parser", ofp_parser
        print "in_port", in_port
        print "pkt", pkt
        print "dest", dst
        print "src", src
        print "dpid", dpid
        print "printing the debug info"
        print self.G.node.keys()
        print self.G.node[dpid].keys()
        # learn a mac address to avoid FLOOD next time.
        #self.mac_to_port[dpid][src] = in_port"""

        #print "dpid, src mac"
        #print dpid, src

        self.G.node[dpid]['mactoport'][src] = in_port

        if dst in self.G.node[dpid]['mactoport']:
            out_port = self.G.node[dpid]['mactoport'][dst]
        else:
            #att = nx.get_node_attributes(graph, 'ports')
            #out_port_list =
            out_port = ofp.OFPP_FLOOD

#       if out_port == ofp.OFPP_FLOOD:
#               print "flooding now", ofp.OFPP_FLOOD

        actions = [ofp_parser.OFPActionOutput(out_port)]
        print "h{} -> h{}".format(src_node,dst_node)
        # install a flow to avoid packet_in next time
        #self.SPTTupList = self.ST.edges(data=False)
        """
        if out_port != ofp.OFPP_FLOOD:
            print SPTTupList
            for inp, outp in SPTTupList:
                print " {} {} {} {}".format(inp,dst,outp,src)
                if (inp == dst and outp == src) or (inp == src and outp == dst):
                    self.add_flow(dp, msg.in_port, dst, actions)
                    print "addflow {} {} {} {}".format(dp,msg.in_port,dst,actions)
                    #break
                else:
                    print "Blocking {} {} {}".format(dp,dst,outp)
                    print "Blocking {} {} {}".format(dp,src,inp)
                    self.send_port_mod(dp, dst, outp)
                    self.send_port_mod(dp, src, inp)
        """
        """
        mod = opf_parser.OFPFlowMod(datapath=dp, priority=priority,
                            match=match, instructions=inst)
        datapath.send_msg(mod)

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
            data = msg.data

        out = ofp_parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                  in_port=msg.in_port, actions=actions, data=data)
        dp.send_msg(out)
        # We create an OF_PacketOut message with action of type FLOOD
        # This simple forwarding action works only for loopless topologies
        """
        #actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions)
        dp.send_msg(out)


    def add_flow(self, datapath, in_port, dst, actions):
        ofproto = datapath.ofproto

        match = datapath.ofproto_parser.OFPMatch(
            in_port=in_port, dl_dst=haddr_to_bin(dst))

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=ofproto.OFP_DEFAULT_PRIORITY,
            flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
        datapath.send_msg(mod)

    def send_port_mod(self, datapath, hw_addr, port_no):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        #port_no = 3
        #hw_addr = 'fa:c8:e8:76:1d:7e'
        config = 0
        mask = (ofp.OFPPC_PORT_DOWN | ofp.OFPPC_NO_RECV |
            ofp.OFPPC_NO_FWD | ofp.OFPPC_NO_PACKET_IN)
        advertise = (ofp.OFPPF_10MB_HD | ofp.OFPPF_100MB_FD |
                 ofp.OFPPF_1GB_FD | ofp.OFPPF_COPPER |
                 ofp.OFPPF_AUTONEG | ofp.OFPPF_PAUSE |
                 ofp.OFPPF_PAUSE_ASYM)
        req = ofp_parser.OFPPortMod(datapath, port_no, hw_addr, config,
                                mask, advertise)
        datapath.send_msg(req)

    def get_out_ports(self):
        pass

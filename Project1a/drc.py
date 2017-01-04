from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.topology.event import EventSwitchEnter, EventSwitchLeave
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

from topology import load_topology
import networkx as nx


from heapq import heappop, heappush
from itertools import count
from networkx.utils import UnionFind

def compute_spanning_tree(G, weight='weight', data = True):
    ST = nx.minimum_spanning_tree(G)
    return ST	
	


##########################
	



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

        print self.get_str_topo(self.G)
		print self.get_str_topo(self.ST)
		print "printing spanning tree"
	#print get_str_mactoport(graph,dpid)
       #print sorted(self.ST.edges(data=False))
	#print sorted(self.ST)

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
    #def _ev_switch_leave_handler(self, ev):
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

		dst = eth.dst
        src = eth.src
       
		dpid = dp.id
	#print "dpid",dpid
        #self.mac_to_port.setdefault(dpid, {})	
		t = self.get_str_mactoport(self.G,dpid)	
		print t
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
            out_port = ofp.OFPP_FLOOD

#	if out_port == ofp.OFPP_FLOOD:
#		print "flooding now", ofp.OFPP_FLOOD

		actions = [ofp_parser.OFPActionOutput(out_port)]

	# install a flow to avoid packet_in next time
	#SPTTupList = self.ST.edges(data=False)
	'''
        SPTTupList = self.ST
		if out_port != ofp.OFPP_FLOOD:
			for inp, outp in SPTTupList:
				if (inp == dst and outp == src) or (inp == src and outp == dst):
					self.add_flow(dp, msg.in_port, dst, actions)
		else:
		    in_port.down(PORT_STATE_BLOCK, msg_init=init)
		    out_port.down(PORT_STATE_BLOCK, msg_init=init)

	'''
	if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
	#actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
        #out = ofp_parser.OFPPacketOut(
         #   datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
          #  actions=actions)
        #dp.send_msg(out)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
 
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


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



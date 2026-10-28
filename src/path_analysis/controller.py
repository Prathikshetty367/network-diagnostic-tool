import json
from pathlib import Path

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.lib.packet import ethernet, ether_types, packet
from os_ken.ofproto import ofproto_v1_3
from os_ken.topology import api as topology_api
from os_ken.topology import event as topology_event


def switch_id(dpid):
    return f"switch-{int(dpid)}"


def host_id(mac):
    return f"host-{int(mac.split(':')[-1], 16)}"


class PathAnalysisController(app_manager.OSKenApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.hosts = {}
        self.output_file = (
            Path.home()
            / "network-diagnostic-tool"
            / "tests/sample_data/topology_live.json"
        )

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        # Send unknown packets to this controller so it can learn and forward them.
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        instructions = [
            parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)
        ]
        dp.send_msg(
            parser.OFPFlowMod(
                datapath=dp,
                priority=0,
                match=parser.OFPMatch(),
                instructions=instructions,
            )
        )

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return
        if eth.src.lower().startswith("01:"):
            return

        self.mac_to_port.setdefault(dpid, {})[eth.src] = in_port
        self.hosts.setdefault(eth.src, (dpid, in_port))
        out_port = self.mac_to_port[dpid].get(eth.dst, ofp.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst)
            instructions = [
                parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)
            ]
            dp.send_msg(
                parser.OFPFlowMod(
                    datapath=dp,
                    priority=10,
                    match=match,
                    instructions=instructions,
                )
            )

        dp.send_msg(
            parser.OFPPacketOut(
                datapath=dp,
                buffer_id=ofp.OFP_NO_BUFFER,
                in_port=in_port,
                actions=actions,
                data=msg.data,
            )
        )
        self.export_topology()

    @set_ev_cls(topology_event.EventSwitchEnter)
    def switch_enter_handler(self, ev):
        self.export_topology()

    @set_ev_cls(topology_event.EventLinkAdd)
    def link_add_handler(self, ev):
        self.export_topology()

    @set_ev_cls(topology_event.EventLinkDelete)
    def link_delete_handler(self, ev):
        self.export_topology()

    def export_topology(self):
        switches = topology_api.get_switch(self, None)
        discovered_links = topology_api.get_link(self, None)

        nodes = []
        known_switches = set()
        for switch in switches:
            node = switch_id(switch.dp.id)
            known_switches.add(switch.dp.id)
            nodes.append({"id": node, "type": "switch"})

        links = []
        seen_links = set()
        for link in discovered_links:
            source = switch_id(link.src.dpid)
            target = switch_id(link.dst.dpid)
            key = tuple(sorted((source, target)))
            if key not in seen_links:
                seen_links.add(key)
                links.append({
                    "source": source,
                    "target": target,
                    "latency_ms": 1.0,
                    "status": "up",
                })

        for mac, (dpid, port) in self.hosts.items():
            if dpid not in known_switches:
                continue
            node = host_id(mac)
            nodes.append({"id": node, "type": "host", "mac": mac})
            links.append({
                "source": node,
                "target": switch_id(dpid),
                "latency_ms": 1.0,
                "status": "up",
            })

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(
            json.dumps({"nodes": nodes, "links": links}, indent=2) + "\n",
            encoding="utf-8",
        )
        self.logger.info("Topology saved to %s", self.output_file)

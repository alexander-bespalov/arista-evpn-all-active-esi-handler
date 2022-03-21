#!/usr/bin/env python

from jsonrpclib import Server

def main():
	api = Server("unix:/var/run/command-api.sock")

	### Get BGP peers with EVPN AF ###
	bgp_evpn_peers = api.runCmds(1, ["show bgp evpn summary"])
	bgp_evpn_established_peers = []
	for peer, state in bgp_evpn_peers[0]["vrfs"]["default"]["peers"].items():
		if state["peerState"] == "Established":
			bgp_evpn_established_peers.append(peer)

	### Get BGP peers with IPv4 unicast AF ###
	bgp_ipv4_peers = api.runCmds(1, ["show bgp ipv4 unicast summary"])
	bgp_ipv4_established_peers = []
	for peer, state in bgp_ipv4_peers[0]["vrfs"]["default"]["peers"].items():
		if state["peerState"] == "Established":
			bgp_ipv4_established_peers.append(peer)

	### Get dualhomed interfaces ###
	dualhomed_interfaces = []
	try:
		esi = api.runCmds(1, ["show bgp evpn instance"])
		for vlan, segments in esi[0]["bgpEvpnInstances"].items():
			for segment, interface in segments["ethernetSegments"].items():
				if segment != "0000:0000:0000:0000:0000":
					if interface["intf"] not in dualhomed_interfaces:
						dualhomed_interfaces.append(interface["intf"])
	except:
		show_run = api.runCmds(1, ["show running-config"])
		for section, commands in show_run[0]["cmds"].items():
			if section.startswith("interface"):
				if "evpn ethernet-segment" in commands["cmds"] and "identifier 0000:0000:0000:0000:0000" not in commands["cmds"]["evpn ethernet-segment"]["cmds"]:
					interface = section.split()[1]
					if interface not in dualhomed_interfaces:
						dualhomed_interfaces.append(interface)

	### Get errdisabled interfaces ###
	interfaces_status = api.runCmds(1, ["show interfaces status"])
	errdisabled_interfaces = []
	for interface, status in interfaces_status[0]["interfaceStatuses"].items():
		if interface in dualhomed_interfaces and status["linkStatus"] == "errdisabled":
			errdisabled_interfaces.append(interface)

	### Put all dualhomed interfaces to "errdisable" if no establisd BGP EVPN or IPv4 peers ###
	if len(bgp_evpn_established_peers) == 0 or len(bgp_ipv4_established_peers) == 0:
		commands = []
		for interface in dualhomed_interfaces:
			commands.append("errdisable test interface " + interface)
		if len(commands) > 0:
			api.runCmds(1, commands)

	### Enable errdisabled interfaces on BGP EVPN session established ###
	if len(bgp_evpn_established_peers) > 0 and len(bgp_ipv4_established_peers) > 0 and len(errdisabled_interfaces) > 0:
		commands = ["configure"]
		for interface in errdisabled_interfaces:
			commands.append("interface " + interface)
			commands.append("shutdown")
			commands.append("no shutdown")
		if len(commands) > 1:
			api.runCmds(1, commands)

if __name__ == "__main__":
	main()

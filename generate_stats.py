#!/usr/bin/env python

###
# Joseph Kennedy
# @netsiphon
#
# Generate Interface Statistics
###
import profile
import random
import sys
import os
import re
import argparse
from collections import namedtuple

DEBUG = 1
DEBUG_UTIL = 0
DEBUG_LOOP = 1
script_version = '0.00007'
max_interfaces = 684
default_int_max = 48
default_mac_oui = 'D099.D500.0000'
default_uplink1 = 1
default_uplink2 = 2
default_vlan_file = 'vlan.txt'
default_uplink_speed = 1000
max_interface_speed = 40000
default_int_speed = 100
max_traffic = 10000
max_broadcast = 100024
max_multicast = 100024
default_broadcast = 12
default_broadcast_limit = 1024
default_multicast_limit = 1024
default_unicast = 10
default_multicast = 1
default_vlan = 1
default_tag_vlan = "N/A"
default_runtime = 3600
default_rstp_transitions = 0
default_loop_after = 0
# ~1 year
max_runtime = 31536000
min_packet_size = 84
default_packet_size = 1024
max_packet_size = 1500
max_rstp_transitions = 1024
# Base all values on 1M
multiplier = 1000000
byte_multiplier = 1000


class VLAN(object):
    def __init__(self):
        self.id = None
        self.tag_members = []
        self.untag_members = []
        self.members = []
        self.member_lookup = {}
        self.name = ""
        self.router_interface = None
        self.rstp_priority = -1


class VLANTable:
    def __init__(self):
        self.vlans = []
        self.vlan_lookup = {}
        self.platform = "icx"


class InterfaceTable:
    def __init__(self):
        self.interfaces = []
        self.interface_lookup = {}
        self.platform = "icx"
        self.chassis_mac = default_mac_oui
        self.stats = None


class InterfaceObject(object):
    def __init__(self):
        self.interface_id = None
        self.module_id = None
        self.port_id = None
        self.status = None
        self.pim = None
        self.ospf_mode = ""
        self.ospf_area = ""
        self.vrf = ""
        self.name = ""
        self.ip_address = ""
        self.netmask = ""
        self.vrrp_id = None
        self.vrrp_ip = ""
        self.helpers = []
        self.rstp_mode = None
        self.sflow = None
        self.interface_type = ""
        self.interface_stats = None
        self.mac = "0000.0000.0000"


class DefaultInterfaceStats(object):

    def __init__(self):
        self._link = "Down"
        self._state = "None"
        self._duplex = "None"
        self._speed = 0
        self._trunk = "None"
        self._tag = "None"
        self._prio = "level0"
        self._vlan = 1
        self._uplink = 0
        self._in_octets = 0
        self._out_octets = 0
        self._in_pkts = 0
        self._out_pkts = 0
        self._in_broadcast_pkts = 0
        self._out_broadcast_pkts = 0
        self._in_multicast_pkts = 0
        self._out_multicast_pkts = 0
        self._in_unicast_pkts = 0
        self._out_unicast_pkts = 0
        self._in_good_fragments = 0
        self._in_bad_fragments = 0
        self._in_discards = 0
        self._in_errors = 0
        self._collisions = 0
        self._late_collisions = 0
        self._crc_errors = 0
        self._mac_rx_errors = 0
        self._giant_pkts = 0
        self._short_pkts = 0
        self._jabber = 0
        self._in_bits_per_sec = 0
        self._out_bits_per_sec = 0
        self._in_pkts_per_sec = 0
        self._out_pkts_per_sec = 0
        self._in_utilization = 0.00
        self._out_utilization = 0.00
        self._packet_size = default_packet_size
        self._broadcast_limit = [0, default_broadcast_limit]
        self._multicast_limit = [0, default_multicast_limit]
        self._runtime = 0

        # Limits
        self.link_val_list = ["Up", "Down", "Disable"]
        self.state_val_list = ["None", "Up", "Down"]
        self.duplex_val_list = ["None", "Half", "Full"]
        self.speed_val_list = [10, 100, 1000, 10000, 40000]
        self.trunk_val_list = ["None", "Yes"]
        self.tag_val_list = ["None", "Yes"]
        self.prio_val_list = ["level0", "level1", "level2", "level3"]
        self.vlan_limits = [1, 4095]
        self.uplink_limits = [0, 2]
        self.packet_size_limits = [min_packet_size, max_packet_size]
        # This actually needs to be updated whenever setting bits_per_sec
        self.bits_per_sec_limits = [
            0,
            multiplier * default_int_speed
        ]
        self.default_int_limits = [
            0,
            (multiplier * multiplier * multiplier * multiplier)
        ]
        self.default_float_limits = [
            0.00,
            float(multiplier * multiplier * multiplier * multiplier)
        ]

    @property
    def link(self):
        return self._link

    @link.setter
    def link(self, link):
        self._link = self.limit_list(link, self.link_val_list)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = self.limit_list(state, self.state_val_list)

    @property
    def duplex(self):
        return self._duplex

    @duplex.setter
    def duplex(self, duplex):
        self._duplex = self.limit_list(duplex, self.duplex_val_list)

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        self._speed = self.limit_list(speed, self.speed_val_list)

    @property
    def trunk(self):
        return self._trunk

    @trunk.setter
    def trunk(self, trunk):
        self._trunk = self.limit_list(trunk, self.trunk_val_list)

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, tag):
        self._tag = self.limit_list(tag, self.tag_val_list)

    @property
    def prio(self):
        return self._prio

    @prio.setter
    def prio(self, prio):
        self._prio = self.limit_list(prio, self.prio_val_list)

    @property
    def vlan(self):
        return self._vlan

    @vlan.setter
    def vlan(self, vlan):
        self._vlan = self.limit_int_value(vlan, self.vlan_limits)

    @property
    def uplink(self):
        return self._uplink

    @vlan.setter
    def uplink(self, uplink):
        self._uplink = self.limit_int_value(uplink, self.uplink_limits)

    @property
    def in_octets(self):
        return self._in_octets

    @in_octets.setter
    def in_octets(self, in_octets):
        self._in_octets = self.limit_int_value(in_octets, None)

    @property
    def out_octets(self):
        return self._out_octets

    @out_octets.setter
    def out_octets(self, out_octets):
        self._out_octets = self.limit_int_value(out_octets, None)

    @property
    def in_pkts(self):
        return self._in_pkts

    @in_pkts.setter
    def in_pkts(self, in_pkts):
        change = in_pkts - self._in_pkts
        self._in_pkts += self.limit_pkt_per_sec(change)

    @property
    def out_pkts(self):
        return self._out_pkts

    @out_pkts.setter
    def out_pkts(self, out_pkts):
        change = out_pkts - self._out_pkts
        self._out_pkts += self.limit_pkt_per_sec(change)

    @property
    def in_broadcast_pkts(self):
        return self._in_broadcast_pkts

    @in_broadcast_pkts.setter
    def in_broadcast_pkts(self, in_broadcast_pkts):
        change = in_broadcast_pkts - self._in_broadcast_pkts
        limit = self._broadcast_limit[1]
        if change >= self._in_broadcast_pkts + limit:
            self._in_broadcast_pkts += limit
            self._in_pkts += limit
            self._in_octets += (limit * 8)
        else:
            self._in_broadcast_pkts += change
            self._in_pkts += change
            self._in_octets += (change * 8)

    @property
    def out_broadcast_pkts(self):
        return self._out_broadcast_pkts

    @out_broadcast_pkts.setter
    def out_broadcast_pkts(self, out_broadcast_pkts):
        change = out_broadcast_pkts - self._out_broadcast_pkts
        limit = self._broadcast_limit[1]
        if change >= self._out_broadcast_pkts + limit:
            self._out_broadcast_pkts += limit
            self._out_pkts += limit
            self._out_octets += (limit * 8)
        else:
            self._out_broadcast_pkts += change
            self._out_pkts += change
            self._out_octets += (change * 8)

    @property
    def in_multicast_pkts(self):
        return self._in_multicast_pkts

    @in_multicast_pkts.setter
    def in_multicast_pkts(self, in_multicast_pkts):
        change = in_multicast_pkts - self._in_multicast_pkts
        self._in_multicast_pkts += self.limit_pkt_per_sec(change)
        self._in_pkts += self.limit_pkt_per_sec(change)
        self._in_octets += (self.limit_pkt_per_sec(change) * 8)

    @property
    def out_multicast_pkts(self):
        return self._out_multicast_pkts

    @out_multicast_pkts.setter
    def out_multicast_pkts(self, out_multicast_pkts):
        change = out_multicast_pkts - self._out_multicast_pkts
        self._out_multicast_pkts += self.limit_pkt_per_sec(change)
        self._out_pkts += self.limit_pkt_per_sec(change)
        self._out_octets += (self.limit_pkt_per_sec(change) * 8)

    @property
    def in_unicast_pkts(self):
        return self._in_unicast_pkts

    @in_unicast_pkts.setter
    def in_unicast_pkts(self, in_unicast_pkts):
        change = in_unicast_pkts - self._in_unicast_pkts
        self._in_unicast_pkts += self.limit_pkt_per_sec(change)
        self._in_pkts += self.limit_pkt_per_sec(change)
        self._in_octets += (self.limit_pkt_per_sec(change) * 8)

    @property
    def out_unicast_pkts(self):
        return self._out_unicast_pkts

    @out_unicast_pkts.setter
    def out_unicast_pkts(self, out_unicast_pkts):
        change = out_unicast_pkts - self._out_unicast_pkts
        self._out_unicast_pkts += self.limit_pkt_per_sec(change)
        self._out_pkts += self.limit_pkt_per_sec(change)
        self._out_octets += (self.limit_pkt_per_sec(change) * 8)

    @property
    def in_good_fragments(self):
        return self._in_good_fragments

    @in_good_fragments.setter
    def in_good_fragments(self, in_good_fragments):
        self._in_good_fragments = self.limit_int_value(in_good_fragments, None)

    @property
    def in_bad_fragments(self):
        return self._in_bad_fragments

    @in_bad_fragments.setter
    def in_bad_fragments(self, in_bad_fragments):
        self._in_bad_fragments = self.limit_int_value(in_bad_fragments, None)

    @property
    def in_discards(self):
        return self._in_discards

    @in_discards.setter
    def in_discards(self, in_discards):
        self._in_discards = self.limit_int_value(in_discards, None)

    @property
    def in_errors(self):
        return self._in_errors

    @in_errors.setter
    def in_errors(self, in_errors):
        self._in_errors = self.limit_int_value(in_errors, None)

    @property
    def collisions(self):
        return self._collisions

    @collisions.setter
    def collisions(self, collisions):
        self._collisions = self.limit_int_value(collisions, None)

    @property
    def late_collisions(self):
        return self._late_collisions

    @late_collisions.setter
    def late_collisions(self, late_collisions):
        self._late_collisions = self.limit_int_value(late_collisions, None)

    @property
    def crc_errors(self):
        return self._crc_errors

    @crc_errors.setter
    def crc_errors(self, crc_errors):
        self._crc_errors = self.limit_int_value(crc_errors, None)

    @property
    def mac_rx_errors(self):
        return self._mac_rx_errors

    @mac_rx_errors.setter
    def mac_rx_errors(self, mac_rx_errors):
        self._mac_rx_errors = self.limit_int_value(mac_rx_errors, None)

    @property
    def giant_pkts(self):
        return self._giant_pkts

    @giant_pkts.setter
    def giant_pkts(self, giant_pkts):
        self._giant_pkts = self.limit_int_value(giant_pkts, None)

    @property
    def short_pkts(self):
        return self._short_pkts

    @short_pkts.setter
    def short_pkts(self, short_pkts):
        self._short_pkts = self.limit_int_value(short_pkts, None)

    @property
    def jabber(self):
        return self._jabber

    @jabber.setter
    def jabber(self, jabber):
        self._jabber = self.limit_int_value(jabber, None)

    @property
    def in_bits_per_sec(self):
        return self._in_bits_per_sec

    @in_bits_per_sec.setter
    def in_bits_per_sec(self, in_bits_per_sec):
        self._in_bits_per_sec = self.limit_bit_per_sec(in_bits_per_sec)

    @property
    def out_bits_per_sec(self):
        return self._out_bits_per_sec

    @out_bits_per_sec.setter
    def out_bits_per_sec(self, out_bits_per_sec):
        self._out_bits_per_sec = self.limit_bit_per_sec(out_bits_per_sec)

    @property
    def in_pkts_per_sec(self):
        return self._in_pkts_per_sec

    @in_pkts_per_sec.setter
    def in_pkts_per_sec(self, in_pkts_per_sec):
        self._in_pkts_per_sec = self.limit_pkt_per_sec(in_pkts_per_sec)

    @property
    def out_pkts_per_sec(self):
        return self._out_pkts_per_sec

    @out_pkts_per_sec.setter
    def out_pkts_per_sec(self, out_pkts_per_sec):
        self._out_pkts_per_sec = self.limit_pkt_per_sec(out_pkts_per_sec)

    @property
    def in_utilization(self):
        self._in_utilization = self.calc_utilization(
            self._in_utilization,
            self.in_pkts_per_sec
            )
        return self._in_utilization

    @property
    def out_utilization(self):
        self._out_utilization = self.calc_utilization(
            self._out_utilization,
            self.out_pkts_per_sec
            )
        return self._out_utilization

    @property
    def packet_size(self):
        return self._packet_size

    @packet_size.setter
    def packet_size(self, packet_size):
        self._packet_size = self.limit_int_value(
            packet_size,
            self.packet_size_limits
            )

    @property
    def broadcast_limit(self):
        return self._broadcast_limit[1]

    @broadcast_limit.setter
    def broadcast_limit(self, broadcast_limit):
        self._broadcast_limit[1] = self.limit_int_value(
            broadcast_limit,
            None
            )

    @property
    def multicast_limit(self):
        return self._multicast_limit[1]

    @multicast_limit.setter
    def multicast_limit(self, multicast_limit):
        self._multicast_limit[1] = self.limit_int_value(
            multicast_limit,
            None
            )

    @property
    def runtime(self):
        return self._runtime

    @collisions.setter
    def runtime(self, runtime):
        self._runtime = self.limit_int_value(runtime, None)

    def calc_utilization(self, value, pkts_per_sec):
        utilization = (
            float(pkts_per_sec * 100) /
            (float(self.speed * multiplier)/float(self.packet_size * 8))
        )
        if utilization > '100.00':
            return '100.00'
        return utilization

    def limit_bit_per_sec(self, value):
        low_limit = 0
        upper_limit = (self.speed * multiplier)
        if value < low_limit:
            value = low_limit
        elif value > upper_limit:
            value = upper_limit
        return value

    def limit_pkt_per_sec(self, value):
        low_limit = 0
        upper_limit = (self.speed * multiplier)/(self.packet_size * 8)
        if value < low_limit:
            value = low_limit
        elif value > upper_limit:
            value = upper_limit
        return value

    def limit_int_value(self, value, limits):
        if not limits:
            low_limit = self.default_int_limits[0]
            upper_limit = self.default_int_limits[1]
        else:
            low_limit = limits[0]
            upper_limit = limits[1]
        if value < low_limit:
            value = low_limit
        elif value > upper_limit:
            value = upper_limit
        return value

    def limit_float_value(self, value, limits):
        if not limits:
            low_limit = self.default_float_limits[0]
            upper_limit = self.default_float_limits[1]
        else:
            low_limit = limits[0]
            upper_limit = limits[1]
        if value < low_limit:
            value = low_limit
        elif value > upper_limit:
            value = upper_limit
        return value

    def limit_list(self, value, allow_list):
        if value in allow_list:
            return value
        return None


class InterfaceStats(DefaultInterfaceStats):
    def __init__(self, link, state, duplex, speed, trunk, tag, vlan):
        DefaultInterfaceStats.__init__(self)
        self.link = link
        self.state = state
        self.duplex = duplex
        self.speed = speed
        self.trunk = trunk
        self.tag = tag
        self.vlan = vlan


###
# Class that contains all patterns used to parse config
###
class CompiledPattern:
    default_pattern = re.compile(".+ ")


######
# Main
###
def main(args):
    welcome_banner()
    eth_table = InterfaceTable()
    vlan_table = VLANTable()

    # Change to allow modules and stuff later...maybe
    int_start = 1
    eth_table.chassis_mac = args.mac[:13]

    # Total Ports
    int_end = default_int_max
    if args.total_ports >= 1:
        int_end = args.total_ports
    elif args.total_ports < 1:
        int_end = random.randint(int_start, max_interfaces)

    # Uplinks
    uplink1 = args.uplink1
    uplink2 = args.uplink2
    if args.uplink1 > int_end:
        uplink1 = default_uplink1
    elif args.uplink1 < 1:
        uplink1 = random.randint(int_start, int_end)
    elif args.uplink2 > int_end:
        uplink2 = default_uplink2
    elif args.uplink2 < 1:
        uplink2 = uplink1
        while uplink2 == uplink1:
            uplink2 = random.randint(int_start, int_end)

    # Uplink Speed
    uplink_speed = default_uplink_speed
    if args.uplink_speed < 100:
        uplink_speed = default_uplink_speed
    elif args.uplink_speed > max_interface_speed:
        uplink_speed = max_interface_speed

    # Loop Type
    loop1 = 0
    loop2 = 0
    if args.loop == 0:
        loop1 = 0
        loop2 = 0
    elif args.loop >= 1:
        if (args.loop_interface1 < 1) or (args.loop_interface1 > int_end):
            while ((loop1 == 0) or (loop1 == uplink1) or (loop1 == uplink2)):
                loop1 = random.randint(1, int_end)
        elif args.loop_interface1 <= int_end:
            loop1 = args.loop_interface1
        loop2 = 0
    if args.loop == 2:
        if args.loop_interface2 < 1 or (args.loop_interface2 > int_end):
            loop2 = loop1
            while (
                (loop2 == loop1) or (loop2 == uplink1) or (loop2 == uplink2)
                    ):
                loop2 = random.randint(1, int_end)
        elif args.loop_interface2 <= int_end:
            loop2 = args.loop_interface2

    if DEBUG_LOOP:
        print('LoopInterface1 -> ' + str(loop1))
        print('LoopInterface2 -> ' + str(loop2))

    # RSTP Root
    if args.root > int_end:
        args.root = args.uplink1
    elif args.root < 1:
        args.root = random.randint(int_start, int_end)

    # % Mix of interface speeds
    if args.interface_mix < 1:
        int_mix = random.randint(int_start, int_end)
    elif args.interface_mix > 100:
        int_mix = 100

    # Unicast traffic
    if args.unicast < 1:
        int_unicast = -1
    elif args.unicast >= 1:
        int_unicast = args.unicast
    elif args.unicast > max_traffic:
        int_unicast = max_traffic

    # Multicast traffic
    if args.multicast < 1:
        int_multicast = -1
    elif args.multicast >= 1:
        int_multicast = args.multicast
    elif args.multicast > max_traffic:
        int_multicast = max_traffic

    # Multicast limit
    multicast_limit = 0
    if args.multicast_limit >= 0 and args.multicast_limit <= max_multicast:
        multicast_limit = args.multicast_limit
    elif args.multicast_limit > max_multicast:
        multicast_limit = max_multicast
    elif args.multicast_limit == -1:
        multicast_limit = random.randint(0, max_multicast)
    else:
        multicast_limit = default_multicast_limit

    # Broadcast traffic
    if args.broadcast < 1:
        int_broadcast = -1
    elif args.broadcast >= 1:
        int_broadcast = args.broadcast
    elif args.broadcast > max_broadcast:
        int_broadcast = max_broadcast

    # Broadcast limit
    broadcast_limit = 0
    if args.broadcast_limit >= 0 and args.broadcast_limit <= max_broadcast:
        broadcast_limit = args.broadcast_limit
    elif args.broadcast_limit > max_broadcast:
        broadcast_limit = max_broadcast
    elif args.broadcast_limit == -1:
        broadcast_limit = random.randint(0, max_broadcast)
    else:
        broadcast_limit = default_broadcast_limit

    # VLAN Setup
    if not args.vlan_list:
        vlan = VLAN()
        if args.vlan > 0:
            vlan.id = args.vlan
        elif args.vlan < 0:
            vlan.id = random.randint(1, 4095)
        if args.uplink1:
            vlan.members.append(uplink1)
            vlan.tag_members.append(uplink1)
        if args.uplink2:
            vlan.members.append(uplink2)
            vlan.tag_members.append(uplink2)

        vlan_table.vlans.append(vlan)
        vlan_table.vlan_lookup[vlan.id] = len(vlan_table.vlans)

    # Runtime
    if args.runtime >= 1:
        runtime = args.runtime
    elif args.runtime < 1:
        runtime = random.randint(1, max_runtime)
    elif args.runtime > max_runtime:
        runtime = max_runtime

    # Loop After
    if args.loop_after > runtime:
        loop_after = runtime
    elif((args.loop_after <= runtime) and (args.loop_after > 0)):
        loop_after = args.loop_after
    else:
        loop_after = default_loop_after

    # Packet size
    packet_size = default_packet_size
    if args.packet_size == -1:
        packet_size = random.randint(min_packet_size, max_packet_size)
    elif args.packet_size >= 1:
        packet_size = args.packet_size
    elif args.packet_size < min_packet_size:
        packet_size = min_packet_size
    elif args.packet_size > max_packet_size:
        packet_size = max_packet_size
    # Setup all interfaces
    for int in range(int_start, int_end + 1):
        if int not in eth_table.interface_lookup:
            # Setup the interface if not done already
            eth_int = InterfaceObject()
            eth_int.interfaceID = int
            eth_int.name = str(int)
            eth_int.mac = "{seed:0<12}{mac_gen:>02X}".format(
                seed=eth_table.chassis_mac[:12], mac_gen=int
                )
            # Initialize the Stats
            eth_int.interface_stats = DefaultInterfaceStats()
            eth_int.interface_stats.vlan = vlan.id
            eth_int.interface_stats.link = "Up"
            eth_int.interface_stats.duplex = "Full"
            eth_int.interface_stats.speed = 100
            eth_int.interface_stats.state = "Up"
            eth_int.interface_stats.broadcast_limit = broadcast_limit
            eth_int.interface_stats.multicast_limit = multicast_limit

            eth_table.interfaces.append(eth_int)
            eth_table.interface_lookup[int] = len(eth_table.interfaces) - 1

    # Set special interfaces
    # Uplink 1
    uplink1_int = eth_table.interfaces[eth_table.interface_lookup[uplink1]]
    uplink1_int.interface_stats = InterfaceStats(
        "Up", "Up", "Full", uplink_speed, "Yes", "Yes", default_tag_vlan
        )
    uplink1_int.interface_stats.uplink = 1
    # uplink1_int.interface_stats.broadcast_limit = broadcast_limit
    # uplink1_int.interface_stats.multicast_limit = multicast_limit
    # Uplink 2
    uplink2_int = eth_table.interfaces[eth_table.interface_lookup[uplink2]]
    uplink2_int.interface_stats = InterfaceStats(
        "Up", "Up", "Full", uplink_speed, "Yes", "Yes", default_tag_vlan
        )
    uplink2_int.interface_stats.uplink = 2
    # uplink2_int.interface_stats.broadcast_limit = broadcast_limit
    # uplink2_int.interface_stats.multicast_limit = multicast_limit

    total_in_broadcast_per_sec = 0
    total_in_multicast_per_sec = 0
    total_out_broadcast_per_sec = 0
    total_out_multicast_per_sec = 0

    # Packet Generator Loop
    for i in range(0, runtime):

        in_pkts_per_sec = 0
        out_pkts_per_sec = 0

        if loop1 == 0 and loop2 == 0:
            total_in_broadcast_per_sec = 0
            total_in_multicast_per_sec = 0
            total_out_broadcast_per_sec = 0
            total_out_multicast_per_sec = 0
        # Reset Uplink per second stats
        reset_per_sec(uplink1_int.interface_stats)
        reset_per_sec(uplink2_int.interface_stats)
        # Statistics outside of Main generation loop
        rstp_hellos = runtime / 2
        if uplink1_int:
            uplink1_int.interface_stats.in_multicast_pkts += rstp_hellos
            uplink1_int.interface_stats.out_multicast_pkts += rstp_hellos
            # Standard broadcast should happen here
            # uplink1_int.interface_stats.out_pkts += int_broadcast
            # uplink1_int.interface_stats.out_broadcast_pkts += int_broadcast *
            # runtime
        if uplink2_int:
            uplink2_int.interface_stats.out_multicast_pkts += rstp_hellos
            uplink2_int.interface_stats.in_multicast_pkts += rstp_hellos
            # Standard broadcast should happen here
            # uplink2_int.interface_stats.out_pkts += int_broadcast * runtime
            # uplink2_int.interface_stats.out_broadcast_pkts += int_broadcast *
            # runtime

        # Main Work Area
        for int in range(int_start, int_end + 1):
            if (int in eth_table.interface_lookup and
                    (int != uplink1) and
                    (int != uplink2)):
                eth_int = eth_table.interfaces[eth_table.interface_lookup[int]]
                stats = eth_int.interface_stats

                stats.packet_size = packet_size
                # Reset the per second stats every run
                reset_per_sec(stats)
                # Statistics Generation
                # Switch originated traffic
                stats.out_multicast_pkts += rstp_hellos

                # Calculate broadcast first to prevent exclusion
                # if (int != loop1) and (int != loop2):
                if int_broadcast <= -1:
                    if args.broadcast_max > 0:
                        broadcast = (
                            args.broadcast_max
                            )
                    else:
                        broadcast = int_broadcast
                    random_broadcast = random.randint(
                        0,
                        stats.broadcast_limit
                        )
                    stats.in_broadcast_pkts += random_broadcast
                    total_in_broadcast_per_sec += random_broadcast
                else:
                    # stats.in_pkts += int_broadcast
                    stats.in_broadcast_pkts += int_broadcast
                    total_in_broadcast_per_sec += int_broadcast
                # Calculate multicast second to prevent exclusion
                if int_multicast == -1:
                    if (args.multicast_max > 0 and
                            stats.multicast_limit < args.multicast_max):
                        multicast = (
                            args.multicast_max
                            )
                    else:
                        multicast = int_multicast

                    random_multicast = random.randint(
                        0, stats.multicast_limit
                        )
                    stats.in_multicast_pkts += random_multicast
                    total_in_multicast_per_sec += random_multicast
                    stats.in_pkts_per_sec += random_multicast
                else:
                    # stats.in_pkts += int_multicast
                    stats.in_multicast_pkts += int_multicast
                    total_in_multicast_per_sec += int_multicast
                    stats.in_pkts_per_sec += int_multicast
                if int_unicast == -1:
                    if args.unicast_max > 0 and args.unicast_max < stats.speed:
                        max_unicast = (
                            args.unicast_max * multiplier/packet_size
                            )
                    else:
                        max_unicast = (
                            stats.speed * multiplier/packet_size
                            )
                else:
                    max_unicast = (int_unicast * multiplier/packet_size)
                in_pkts = random.randint(0, max_unicast)
                out_pkts = random.randint(0, max_unicast)
                # stats.in_pkts += in_pkts
                stats.in_unicast_pkts += in_pkts
                # stats.in_octets += (in_pkts * packet_size)
                stats.in_pkts_per_sec += in_pkts
                # stats.out_pkts += out_pkts
                stats.out_unicast_pkts += out_pkts
                # stats.out_octets += (out_pkts * packet_size)
                stats.out_pkts_per_sec += out_pkts
                stats.in_bits_per_sec += (
                    stats.in_pkts_per_sec * packet_size * 8
                    )
                stats.out_bits_per_sec += (
                    stats.out_pkts_per_sec * packet_size * 8
                    )
                # Utilization In
                # Automatic Calculation Now

                # Utilization Out
                # Automatic Calculation Now

        # Inbound Broadcast and Multicast to All standard ports now...
        for int in range(int_start, int_end + 1):
            if (int in eth_table.interface_lookup and
                    (int != uplink1) and
                    (int != uplink2)):
                eth_int = eth_table.interfaces[eth_table.interface_lookup[int]]
                stats = eth_int.interface_stats

                # Broadcast Outbound...
                # stats.out_pkts += total_in_broadcast_per_sec
                stats.out_broadcast_pkts += total_in_broadcast_per_sec
                # Multicast Outbound...
                # stats.out_pkts += total_in_multicast_per_sec
                stats.out_multicast_pkts += total_in_multicast_per_sec
                # Increment Outbound packets per sec
                stats.out_pkts_per_sec += total_in_broadcast_per_sec
                stats.out_pkts_per_sec += total_in_multicast_per_sec

        # Looped Ports Broadcast/Multicast
        if i >= loop_after:
            if loop1 > 0:
                loop1_int = eth_table.interfaces[
                    eth_table.interface_lookup[loop1]
                    ]
                loop_interface_stats_manual(
                    loop1_int,
                    total_in_broadcast_per_sec,
                    total_in_multicast_per_sec,
                    stats.packet_size
                    )
            if loop2 > 0:
                loop2_int = eth_table.interfaces[
                    eth_table.interface_lookup[loop2]
                    ]
                loop_interface_stats_manual(
                    loop2_int,
                    total_in_broadcast_per_sec,
                    total_in_multicast_per_sec,
                    stats.packet_size
                    )

        # Aggregate for looped ports and uplinks
        for int in range(int_start, int_end + 1):
            if ((int != uplink1) and
                    (int != uplink2)):
                # and
                # (int != loop1) and
                # (int != loop2)
                eth_int = eth_table.interfaces[eth_table.interface_lookup[int]]
                stats.speed = eth_int.interface_stats.speed

                # Statistics Generation
                # Switch originated traffic
                aggregate_interface_stats(eth_int, uplink1_int)
                # aggregate_interface_stats(eth_int, uplink2_int)

        # Uplink 1 - Primary
        stats = uplink1_int.interface_stats

        # Uplink 2 - Secondary
        stats = uplink2_int.interface_stats

    # OUTPUT
    # try:
    out_file = open(args.out_file, 'wb')
    out_line = ""
    for int in range(0, len(eth_table.interfaces)):
        out_line += (interface_print(eth_table.interfaces[int]))

    out_file.write(out_line)


def reset_per_sec(stats):
    stats.out_bits_per_sec = 0
    stats.in_bits_per_sec = 0
    stats.out_pkts_per_sec = 0
    stats.in_pkts_per_sec = 0
    return


def loop_interface_stats_manual(int, broadcast, multicast, packet_size):
    stats = int.interface_stats

    # stats.in_pkts += broadcast
    # stats.out_pkts += broadcast
    #stats.out_broadcast_pkts += broadcast
    stats.in_broadcast_pkts += broadcast
    #stats.out_multicast_pkts += multicast
    stats.in_multicast_pkts += multicast
    stats.in_pkts_per_sec += broadcast + multicast
    # stats.out_pkts_per_sec += broadcast + multicast
    stats.packet_size = packet_size
    return


def loop_interface_stats(int_from, int_to):
    stats_in = int_from.interface_stats
    stats_out = int_to.interface_stats

    stats_out.out_broadcast_pkts += stats_in.in_broadcast_pkts
    stats_out.in_broadcast_pkts += stats_in.out_broadcast_pkts
    stats_out.out_multicast_pkts += stats_in.in_multicast_pkts
    stats_out.in_multicast_pkts += stats_in.out_multicast_pkts

    stats_out.packet_size = stats_in.packet_size
    return


def aggregate_interface_stats(int_from, int_to):
    stats_in = int_from.interface_stats
    stats_out = int_to.interface_stats
    #
    #stats_out.out_octets += stats_in.in_octets
    #stats_out.in_octets += stats_in.out_octets
    #stats_out.out_pkts += stats_in.in_pkts
    #stats_out.in_pkts += stats_in.out_pkts
    stats_out.out_broadcast_pkts += stats_in.out_broadcast_pkts
    stats_out.in_broadcast_pkts += stats_in.in_broadcast_pkts
    stats_out.out_multicast_pkts += stats_in.out_multicast_pkts
    stats_out.in_multicast_pkts += stats_in.in_multicast_pkts
    stats_out.out_unicast_pkts += stats_in.in_unicast_pkts
    stats_out.in_unicast_pkts += stats_in.out_unicast_pkts
    #
    stats_out.in_good_fragments += stats_in.in_good_fragments
    stats_out.in_bad_fragments += stats_in.in_bad_fragments
    stats_out.in_discards += stats_in.in_discards
    stats_out.in_errors += stats_in.in_errors
    stats_out.collisions += stats_in.collisions
    stats_out.late_collisions += stats_in.late_collisions
    stats_out.crc_errors += stats_in.crc_errors
    stats_out.mac_rx_errors += stats_in.mac_rx_errors
    stats_out.giant_pkts += stats_in.giant_pkts
    stats_out.short_pkts += stats_in.short_pkts
    stats_out.jabber += stats_in.jabber
    stats_out.out_bits_per_sec += stats_in.in_bits_per_sec
    stats_out.in_bits_per_sec += stats_in.out_bits_per_sec
    stats_out.out_pkts_per_sec += stats_in.in_pkts_per_sec
    stats_out.in_pkts_per_sec += stats_in.out_pkts_per_sec
    # stats_out.out_utilization += stats_in.in_utilization
    # stats_out.in_utilization += stats_in.out_utilization
    stats_out.packet_size = stats_in.packet_size
    return


def interface_print(interface):
    stats = interface.interface_stats
    output = (
        "Port    Link    State   Dupl Speed Trunk Tag Pvid Pri    MAC"
        "             Name    \n"
        "{int:<6} {link:>5} {state:>7} {duplex:>7} {speed:>4} {trunk:>5}"
        " {tag:>5}"
        " {vlan:>4} {prio} {mac} \n\n"
        " Port {int} Counters:                                                "
        "        \n"
        "         InOctets {in_octets:>20}           "
        "OutOctets {out_octets:>20}\n"
        "           InPkts {in_pkts:>20}             "
        "OutPkts {out_pkts:>20}\n"
        "  InBroadcastPkts {in_broadcast_pkts:>20}"
        "    OutBroadcastPkts {out_broadcast_pkts:>20}\n"
        "  InMulticastPkts {in_multicast_pkts:>20}"
        "    OutMulticastPkts {out_multicast_pkts:>20}\n"
        "    InUnicastPkts {in_unicast_pkts:>20}"
        "      OutUnicastPkts {out_unicast_pkts:>20}\n"
        "        InBadPkts {in_bad_fragments:>20}                             "
        "        \n"
        "      InFragments {in_good_fragments:>20}                            "
        "        \n"
        "       InDiscards {in_discards:>20}                                  "
        "        \n"
        "              CRC {crc_errors:>20}          "
        "Collisions {collisions:>20}\n"
        "         InErrors {in_errors:>20}      "
        "LateCollisions {late_collisions:>20}  \n"
        "      InGiantPkts {giant_pkts:>20}                                   "
        "        \n"
        "      InShortPkts {short_pkts:>20}                                   "
        "        \n"
        "         InJabber {jabber:>20}                                       "
        "        \n"
        "   InFlowCtrlPkts                    0"
        "     OutFlowCtrlPkts                    0\n"
        "     InBitsPerSec {in_bits_per_sec:>20}"
        "       OutBitsPerSec {out_bits_per_sec:>20}\n"
        "     InPktsPerSec {in_pkts_per_sec:>20}"
        "       OutPktsPerSec {out_pkts_per_sec:>20}\n"
        "    InUtilization {in_utilization:>20.2f}%"
        "     OutUtilization {out_utilization:>20.2f}%\n"
    ).format(
        int=interface.name,
        link=stats.link,
        state=stats.state,
        duplex=stats.duplex,
        speed=stats.speed,
        trunk=stats.trunk,
        tag=stats.tag,
        prio=stats.prio,
        mac=interface.mac,
        in_octets=stats.in_octets,
        out_octets=stats.out_octets,
        in_pkts=stats.in_pkts,
        out_pkts=stats.out_pkts,
        in_broadcast_pkts=stats.in_broadcast_pkts,
        out_broadcast_pkts=stats.out_broadcast_pkts,
        in_multicast_pkts=stats.in_multicast_pkts,
        out_multicast_pkts=stats.out_multicast_pkts,
        in_unicast_pkts=stats.in_unicast_pkts,
        out_unicast_pkts=stats.out_unicast_pkts,
        in_good_fragments=stats.in_good_fragments,
        in_bad_fragments=stats.in_bad_fragments,
        in_discards=stats.in_discards,
        in_errors=stats.in_errors,
        collisions=stats.collisions,
        late_collisions=stats.late_collisions,
        crc_errors=stats.crc_errors,
        mac_rx_errors=stats.mac_rx_errors,
        giant_pkts=stats.giant_pkts,
        short_pkts=stats.short_pkts,
        jabber=stats.jabber,
        in_bits_per_sec=stats.in_bits_per_sec,
        out_bits_per_sec=stats.out_bits_per_sec,
        in_pkts_per_sec=stats.in_pkts_per_sec,
        out_pkts_per_sec=stats.out_pkts_per_sec,
        in_utilization=stats.in_utilization,
        out_utilization=stats.out_utilization,
        vlan=stats.vlan, space20=" "
    )
    return output


def search(text, pattern):
    if DEBUG_SEARCH:
        print 'search()::text->: ' + text.strip("\n")
    matches = pattern.search(text)
    # Confirm a match
    if matches:
        if DEBUG_SEARCH:
            print 'Match!'
        # Check for count matches if requested
        return matches, len(matches.groups())
    # No Match!
    else:
        if DEBUG_SEARCH:
            print 'No Match!'
        matches = None
        return None, -1


def welcome_banner():
    temp_version = ''
    for chr in range(0, len(script_version)):
        temp_version += ' ' + script_version[chr:(chr + 1)] + '  '

    print(
        "=========================================================\n"
        "                                                         \n"
        "                                                         \n"
        "  .--.--.       ___                   ___                \n"
        " /  /    '.   ,--.'|_               ,--.'|_              \n"
        "|  :  /`. /   |  | :,'              |  | :,'             \n"
        ";  |  |--`    :  : ' :              :  : ' :  .--.--.    \n"
        "|  :  ;_    .;__,'  /    ,--.--.  .;__,'  /  /  /    '   \n"
        " \  \    `. |  |   |    /       \ |  |   |  |  :  /`./   \n"
        "  `----.   \:__,'| :   .--.  .-. |:__,'| :  |  :  ;_     \n"
        "  __ \  \  |  '  : |__  \__\/: . .  '  : |__ \  \    `.  \n"
        " /  /`--'  /  |  | '.'| ,' .--.; |  |  | '.'| `----.   \ \n"
        "'--'.     /   ;  :    ;/  /  ,.  |  ;  :    ;/  /`--'  / \n"
        "  `--'---'    |  ,   /;  :   .'   \ |  ,   /'--'.     /  \n"
        "               ---`-' |  ,     .-./  ---`-'   `--'---'   \n"
        "                       `--`---'                          \n"
        "                                                         \n"
        " +++ +++ +++ +++ +++ +++ +++   +++ +++ +++ +++ +++ +++ +++\n"
        "v   e   r   s   i   o   n    " + temp_version + "        \n"
        " +++ +++ +++ +++ +++ +++ +++   +++ +++ +++ +++ +++ +++ +++\n"
        "=========================================================\n"
        )

if __name__ == "__main__":
    # try:
    parser = argparse.ArgumentParser(
        usage='%(prog)s [out-file] [options]',
        description='Generate Arbitrary Interface statistics for the purposes'
        ' of training/testing'
        )
    parser.add_argument('out_file', type=str, help='File output')
    parser.add_argument(
        '--total-ports', metavar='n', type=int, default=default_int_max,
        help='Total number of ports on the switch [-1=random,0...2048]'
        )
    parser.add_argument(
        '--loop', metavar='n', type=int, default=2,
        help='Simulate bridge loop [0=off,1=single,2=two-port loop]'
        )
    parser.add_argument(
        '--loop-interface1', metavar='n', type=int, default=-1,
        help='Looping port 1 [-1=random,1...total]'
        )
    parser.add_argument(
        '--loop-interface2', metavar='n', type=int, default=-1,
        help='Looping port 2 [-1=random,0...total]'
        )
    parser.add_argument(
        '--loop-after', metavar='n', type=int, default=default_loop_after,
        help='Start the loop after this many seconds from runtime end ' +
        '[0=off,1=single,2=two-port loop]'
        )
    parser.add_argument(
        '--vlan', metavar='n', type=int, default=-1,
        help='VLAN ID to use if using a single vlan [-1=random,1...4095]'
        )
    parser.add_argument(
        '--vlan-list', metavar='vlan.txt', type=str, default="",
        help="List of VLAN's to use if not using a single VLAN [" +
        default_vlan_file + "]"
        )
    parser.add_argument(
        '--mac', metavar='xxxx.xxxx.xxxx', type=str, default=default_mac_oui,
        help='Seed to use for MAC addresses'
        )
    parser.add_argument(
        '--active', metavar='n', type=int, default=1,
        help='Active ports [-1=random,1...total]'
        )
    parser.add_argument(
        '--root', metavar='n', type=int, default=default_uplink1,
        help='RSTP Root port -- default is to match uplink1 [-1=random,1...' +
        'total]'
        )
    parser.add_argument(
        '--uplink1', metavar='n', type=int, default=default_uplink1,
        help='Uplink 1 [-1=random,1...total]'
        )
    parser.add_argument(
        '--uplink2', metavar='n', type=int, default=default_uplink2,
        help='Uplink 2 [-1=random,1...total]'
        )
    parser.add_argument(
        '--uplink-speed', metavar='n', type=int, default=1000,
        help="Uplink speed [-1=random,100..." + str(max_interface_speed) + "]"
        )
    parser.add_argument(
        '--broadcast', metavar='n', type=int, default=default_broadcast,
        help="Normal Broadcast Traffic in bytes [-1=random,0..." +
        str(max_traffic) + "]"
        )
    parser.add_argument(
        '--broadcast-max', metavar='n', type=int, default=default_broadcast,
        help="Allows you to set a ceiling for random broadcast [-1=random," +
        "0..." + str(max_traffic) + "]"
        )
    parser.add_argument(
        '--interface-speed', metavar='n', type=int, default=default_int_speed,
        help='Standard Interface speed in Mbit/sec [-1=random,10...10000]'
        )
    parser.add_argument(
        '--interface-mix', metavar='n', type=int, default=100,
        help='Standard Interface speed in Mbit/sec [-1=random,0...100]'
        )
    parser.add_argument(
        '--unicast', metavar='n', type=int, default=10,
        help='Standard Unicast Traffic in Mbit/sec [-1=random,0...10000]'
        )
    parser.add_argument(
        '--unicast-max', metavar='n', type=int, default=default_unicast,
        help='Allows you to set a ceiling for random unicast [0...10000]'
        )
    parser.add_argument(
        '--multicast', metavar='n', type=int, default=1,
        help='Standard Multicast Traffic in Mbit/sec [-1=random,0...10000]'
        )
    parser.add_argument(
        '--multicast-max', metavar='n',
        type=int, default=default_multicast,
        help='Allows you to set a ceiling for random multicast [0...10000]'
        )
    parser.add_argument(
        '--runtime', metavar='n', type=int, default=default_runtime,
        help='Runtime for the switch to base stats on [-1=random,1...31536000]'
        )
    parser.add_argument(
        '--packet-size', metavar='n', type=int, default=default_packet_size,
        help="Average packet size for generation [-1=random," +
        str(min_packet_size) +
        "..." + str(max_packet_size) + "]"
        )
    parser.add_argument(
        '--rstp-transitions', metavar='n', type=int,
        default=default_rstp_transitions,
        help="Assume this many transitions have occurred [-1=random,0..." +
        str(max_rstp_transitions) + "]"
        )
    parser.add_argument(
        '--broadcast-limit', metavar='n', type=int,
        default=default_broadcast_limit,
        help="Broadcast limit if required [-1,0...100000]"
        )
    parser.add_argument(
        '--multicast-limit', metavar='n', type=int,
        default=default_multicast_limit,
        help="Multicast limit if required [-1,0...100000]"
        )
    args = parser.parse_args()
    reCP = CompiledPattern()
    main(args)
    # except Exception as e:
    #    sys.exit(0)

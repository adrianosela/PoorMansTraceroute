import socket
import sys
import io
import struct
import time

# class that wraps stdout into a console by modifying the write() function
# of the io.FileIO type to make it flush after every call to write()
class console(io.FileIO):
    def __init__(self, infile):
        self.infile = infile
    def write(self, x):
        self.infile.write(x)
        self.infile.flush()

# set up a raw internet socket to receive ICMP messages on
# a specified port and with a specified read timeout
def RXsetup(icmp_port, icmp_timeout):
    timeout = struct.pack("ll", icmp_timeout, 0) # 16-bit timeout value
    rx_s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    rx_s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeout)
    rx_s.bind(("", icmp_port))
    return rx_s

# set up an internet datagram socket to send UDP packets
# with a given time-to-live (ttl)
def TXsetup(ttl):
    tx_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    tx_s.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
    return tx_s

# returns the current time in milliseconds
def time_ms():
    return int(round(time.time()*1000))

# performs a reverse DNS lookup for a given ip address
def reverse_lookup(ip):
    try:
        name = socket.gethostbyaddr(ip)[0]
    except socket.error as translation_error:
        return ip, False
    return name, True

# attempts to measure the round trip time to a server
def try_measure_round_trip(dst_host, dst_port, rx_port, ttl, tries, read_timeout):
    tx_socket = TXsetup(ttl)
    rx_socket = RXsetup(rx_port, read_timeout)
    addr = None
    while addr is None and tries > 0:
        try:
            start = time_ms()
            tx_socket.sendto(bytes("", "utf-8"), (dst_host, dst_port))
            _, icmp_sender_addr = rx_socket.recvfrom(256)
            rtt = time_ms() - start
        except socket.error:
            tries = tries - 1
            sys.stdout.write("* ")
            continue
        return icmp_sender_addr[0], rtt, True
    tx_socket.close()
    rx_socket.close()
    return None, 0, False

# runs the classic ping operation with rtt_calculations for round trip time
def ping(dst_addr, ttl, timeout, icmp_port, tries_per_hop, rtt_calculations):
    results = ""
    for calc in range(rtt_calculations):
        addr, rtt, ok = try_measure_round_trip(dst_addr, icmp_port, icmp_port, ttl, tries_per_hop, timeout)
        if not ok:
            sys.stdout.write("\n")
            return None
        if calc == 0:
            name, _ = reverse_lookup(addr)
            results += ("%s (%s) [%dms" % (name, addr, rtt))
        else:
            results += ("|%dms" % rtt)
    sys.stdout.write("%s]\n" % results)
    return addr

# traceroute will perform a traceroute from the source host to the destination host
# hosts running ICMP. Each ICMP request will have the timeout value provided.
# If by max_hops hops we have not reached the destination host, we exit.
def traceroute(hostname, max_hops, timeout, icmp_port, tries_per_hop, rtt_calculations):
    print("----> Traceroute for %s <----" % hostname)
    dst_addr = socket.gethostbyname(hostname)
    for hop in range(1, max_hops+1):
        # print the hop number and perform ping
        sys.stdout.write(" %d " % hop)
        cur_addr = ping(dst_addr, hop, timeout, icmp_port, tries_per_hop, rtt_calculations)
        if (cur_addr == dst_addr):
            print("-----> SUCCESS: Done in %d hops <-----" % hop)
            return
    print("----> ERROR: Could not trace route in %d hops <----" % max_hops)
    return

if __name__=="__main__":
    if len(sys.argv) < 2:
        print("USAGE: (sudo) python3 traceroute.py [ hostname ]")
        exit(1)
    sys.stdout = console(sys.stdout) # wrap stdout in a flushing console
    traceroute(hostname=sys.argv[1], max_hops=30, timeout=2, icmp_port=33434, tries_per_hop=3, rtt_calculations=3)

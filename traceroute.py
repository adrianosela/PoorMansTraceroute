import socket
import sys
import io
import struct
import time

"""
The console class wraps stdout into a console by modifying the write() function of the 
io.FileIO type to make it flush after every call to write()
"""
class console(io.FileIO):
    def __init__(self, infile):
        self.infile = infile
    def write(self, x):
        self.infile.write(x)
        self.infile.flush()

# Build an ICMP socket (for ICMP raw data) which includes a GNU timeout struct
def RXsetup(icmp_port, icmp_timeout):
    rx_s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    GNUtimeout = struct.pack("ll", icmp_timeout, 0)
    rx_s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, GNUtimeout)
    rx_s.bind(("", icmp_port))
    return rx_s

# Build a normal UDP socket (for UDP datagrams) with a given time-to-live (ttl)
def TXsetup(ttl):
    tx_s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    tx_s.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
    return tx_s

# Close a pair of sockets
def closeSockets(s1, s2):
    s1.close()
    s2.close()

# returns the current time in milliseconds
def timeMillis():
    return int(round(time.time()*1000))

"""
ping() is our core function, it sends an empty ICMP packet to the destination
address with the respective rtt (or hop number) and calculates the RTT
"""
def ping(dst_addr, ttl, timeout, icmp_port, icmp_attempts_per_hop, rtt_calculations):
    results = ""
    current_addr = None
    for pingNo in range(1, rtt_calculations+1):
        # set-up sockets
        tx_socket = TXsetup(ttl)
        rx_socket = RXsetup(icmp_port, timeout)
        """
        send an empty ICMP request to the target host
        We try to read a response "tries_left" times
        """
        start = timeMillis()
        tx_socket.sendto(bytes("", "utf-8"), (dst_addr, icmp_port))
        current_addr = None
        done = False
        tries_left = icmp_attempts_per_hop
        while not done and tries_left > 0:
            try:
                _, current_addr = rx_socket.recvfrom(512) # receive the IP of the next host to hit
                done = True
                rtt = timeMillis()-start
                current_addr = current_addr[0]
            except socket.error:
                tries_left = tries_left - 1
                sys.stdout.write("* ")
        
        if current_addr is None:
            sys.stdout.write("\n")
            return None
        else:
            """
            try to identify the host we made a hop to,
            if we can't get a hostname we use the IP address
            """
            try:
                current_name = socket.gethostbyaddr(current_addr)[0]
            except socket.error as translationErr:
                current_name = current_addr       
            if pingNo == 1: 
                results += ("%s (%s) [%dms" % (current_name, current_addr, rtt))
            else:
                results += ("|%dms" % rtt)
        closeSockets(tx_socket, rx_socket)
    sys.stdout.write("%s]\n" % results)
    return current_addr

# traceroute will perform a traceroute from the source host to the destination host
# hosts running ICMP. Each ICMP request will have the timeout value provided.
# If by max_hops hops we have not reached the destination host, we exit.
def traceroute(hostname, max_hops, timeout, icmp_port, icmp_attempts_per_hop, rtt_calculations):
    print("----> Traceroute for %s <----" % hostname)
    dst_addr = socket.gethostbyname(hostname)
    for hop in range(1, max_hops+1):
        # print the hop number and perform ping
        sys.stdout.write(" %d " % hop)
        cur_addr = ping(dst_addr, hop, timeout, icmp_port, icmp_attempts_per_hop, rtt_calculations)
        if (cur_addr == dst_addr):
            print("-----> SUCCESS: Done in %d hops <-----" % hop)
            return
    print("----> ERROR: Could not trace route in %d hops <----" % max_hops)
    return

if __name__=="__main__":
    sys.stdout = console(sys.stdout) # wrap stdout in a flushing console
    hostname = sys.argv[1]
    traceroute(hostname, max_hops=30, timeout=4, icmp_port=33434, icmp_attempts_per_hop=3, rtt_calculations=3)

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

# returns the current time in milliseconds
def timeMillis():
    return int(round(time.time()*1000))

# reverse lookup performs a reverse DNS lookup for a given ip address
def reverse_lookup(ip):
    try:
        name = socket.gethostbyaddr(ip)[0]
    except socket.error as translation_error:
        return ip, False
    return name, True

"""
ping() is our core function, it sends an empty ICMP packet to the destination
address with the respective rtt (or hop number) and calculates the RTT
"""
def ping(dst_addr, ttl, timeout, icmp_port, icmp_attempts_per_hop, rtt_calculations):
    results = ""
    for calc in range(rtt_calculations):

        tx_socket, rx_socket = TXsetup(ttl), RXsetup(icmp_port, timeout)
        current_addr, done, tries_left = None, False, icmp_attempts_per_hop

        while not done and tries_left > 0:
            try:
                """
                Send an empty UDP request to the target host
                """
                start = timeMillis()
                tx_socket.sendto(bytes("", "utf-8"), (dst_addr, icmp_port))
                _, addr = rx_socket.recvfrom(512) # receive the IP of the next host to hit
                rtt = timeMillis()-start

                done = True
                current_addr = addr[0]
            except socket.error:
                tries_left = tries_left - 1
                sys.stdout.write("* ")

        if current_addr is None:
            sys.stdout.write("\n")
            return None

        if calc == 0:
            name, _ = reverse_lookup(current_addr) 
            results += ("%s (%s) [%dms" % (name, current_addr, rtt))
        else:
            results += ("|%dms" % rtt)

        tx_socket.close()
        rx_socket.close()

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

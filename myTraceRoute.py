import socket
import sys
import io
import struct
import time

# Build an ICMP socket (for ICMP raw data) which includes a GNU timeout struct
def RXsetup(icmp_port, icmp_timeout):
    GNUtimeout = struct.pack("ll", icmp_timeout, 0)
    rx_s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
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

# traceroute will perform a traceroute from the source host to the destination host
# hosts running ICMP do it at port 33434 by convention, so we are basically pinging
# that port. Each ICMP request will have the timeout value provided.
# If by max_hops hops we have not reached the destination host, we exit.
def traceroute(dst_addr, max_hops, timeout, icmp_port):
    for ttl in range(1, max_hops+1):
        sys.stdout.write(" %d  " % ttl) # print number of current hop

        tx_socket = TXsetup(ttl)
        rx_socket = RXsetup(icmp_port, timeout)

        """
        Here we send the intial -empty- ICMP request to the target host
        We try to read a response tries_left times
        """
        tx_socket.sendto(bytes("", "utf-8"), (dst_addr, icmp_port))
        current_addr = None
        tries_left = 3
        while tries_left > 0:
            try:
                _, current_addr = rx_socket.recvfrom(512) # receive the IP of the next host to hit
            except socket.error:
                tries_left = tries_left - 1
                sys.stdout.write("* ")
        
        closeSockets(tx_socket, rx_socket)

        """
        Here we try to identify the host we made a hop to,
        if we can't get a hostname (via DNS) we use the IP address
        """
        current_addr = current_addr[0]
        try:
            current_name = socket.gethostbyaddr(current_addr)[0]
        except socket.error as dnsErr:
            current_name = current_addr

        if current_addr is not None:
            sys.stdout.write("%s (%s)\n" % (current_name, current_addr))

        if (current_addr == dst_addr):
            return ttl

        if ttl == max_hops:
            print("----> ERROR: Could not trace route in %d hops <----" % max_hops)
            exit(1)

def main(dst_host):
    print("----> Traceroute for %s <----" % dst_host)
    dst_addr = socket.gethostbyname(dst_host)
    hops_taken = traceroute(dst_addr, 30, 4, 33434)
    print("-----> Done in %d hops <-----" % hops_taken)

if __name__=="__main__":
    hostname = sys.argv[1]
    main(hostname)

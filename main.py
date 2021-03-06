
import os
import logging
import argparse
import simpy
import numpy as np
from store_fifo import FIFOStore
from store_rr import RRStore
from store_drr import DRRStore
from source import *
from analysis import *
#from scapy import *
#This specifices how many packets we can receive at a time
START_IP = 100
BASE_IP = "192.168.1."
FTP_PORT = 21
FTP_LENGTH = 8192 #bits
FTP_SOURCES = 6
TELENET_PORT = 23
TELENET_LENGTH = 512 #bits
TELENET_SOURCES = 4
ROUGE_SOURCES = 1 
ROUTER_IP = "192.168.1.1"
ROGUE_LENGTH = 5000 #constant bits
ROGUE_PORT = 2222 # rogue any port
ROGUE_RATE = 0.5
class Router:
    def __init__(self, env, store):
        self.env = env
        self.store = store
        self.logger = logging.getLogger('q')
    def tx(self):
        while True:
#            print str(self.env.now)
#            print  str(self.store)
            #print 'Any packets at t=', env.now, '?'
            pkt = yield self.store.get() #Store is FIFO, when this is called the packet is consumed because the store is a generator
#            print str(self.env.now)
#            print str(self.store)
            #pkt = IP(data)
            self.logger.debug('<<' + str(pkt.src) + "(" + str(pkt.len) + ")")
            yield self.env.timeout(pkt.len) #this is the tx time l/bps
            
            #TODO Is this going to work for all algs?
            #self.store._log[pkt.src][pkt.seq].tx_time = time.time()
            pkt.tx_time = self.env.now 





def get_total_number_sources():
    return [FTP_SOURCES,TELENET_SOURCES,ROUGE_SOURCES]

def convert_to_real_name(index, port):
    return BASE_IP + str(START_IP + index) + "(" + str(port) + ")"

def get_real_source_list():
    sources = []
    last_ip =0
    k=0
    for i in get_total_number_sources():
        dport = '?'
        if k == 0:
            dport = str(FTP_PORT)
        elif k == 1:
            dport = str(TELENET_PORT)

        for j in range(i):
            sources.append(BASE_IP + str(START_IP + last_ip) + "(" + dport + ")") 
            last_ip = last_ip + 1
        k = k + 1

    return sources

def create_sources(env, store, count, start_ip, dport, rate, mu_len, variate, pool):
    for i in range(count):
#        ip = BASE_IP + "." + str(start_ip + i)
        ip = start_ip + i
        s = TrafficSource(env, store, dport, ip, ROUTER_IP, pool)
        #print "Creating ", str(s)
        env.process(s.tx(rate, mu_len, variate))

def run(alg, n, rate):
    """
    Return tuple of latencies and throughputs
    """
    logger = logging.getLogger('q')
    env = simpy.Environment()
    pkt_pool = simpy.Container(env, init=n, capacity=n)
    store = None
    if alg == 'fifo':
        logger.debug("Using FIFO Algorithm")
        store = FIFOStore(env) #simpy.Store(env, capacity=RECQ_SIZE)
    elif alg == 'rr':
        logger.debug("Using RR Algorithm")
        store = RRStore(env)
    elif alg == 'drr': #drr
        logger.debug("Using DRR Algorithm")
        store = DRRStore(env)
    else:
        assert False, "not given a queue algorithm  type argument"
#TODO mofidy these values

    #create ftp sources
    create_sources(env, store, FTP_SOURCES, 0, FTP_PORT, rate, FTP_LENGTH, True, pkt_pool)
    #create telnet sources
    create_sources(env, store, TELENET_SOURCES, FTP_SOURCES, TELENET_PORT, rate, TELENET_LENGTH, True, pkt_pool)
    #Create rogue source but with constant payload
    create_sources(env, store, ROUGE_SOURCES, TELENET_SOURCES+FTP_SOURCES, ROGUE_PORT, ROGUE_RATE, ROGUE_LENGTH, False, pkt_pool)

    router = Router(env,store)
    env.process(router.tx())

    env.run()
    
    an = QMetrics(store.get_log())
    #print "Summary of results: "
    #an.print_data()
    #The order of the data matches the source list so it needs to be returned
    #as well
    return (an.get_source_list(), an.get_source_latencies(), an.get_source_throughputs())



def main(M, x, n, alg, shouldPlot):

    """
    M: total load
    x: number of experiments
    n: number of packets
    alg: one of fifo, rr, drr
    shouldPlot: boolean whether to plot or no
    """

    filenamebody = "%s_%s" % (alg, str(M))
    filenamebody = filenamebody.replace(".", "")
    logging.basicConfig(
        format='%(message)s',
        filemode='w',
        filename= "log_%s.out" % filenamebody,
        level=logging.DEBUG)
    
    rate = M/((FTP_SOURCES + TELENET_SOURCES)*1.0)
    #rogue is last...
    rates = [rate]*(FTP_SOURCES + TELENET_SOURCES)
    rates.append(ROGUE_RATE)
    l = [[] for srcnum in xrange(sum(get_total_number_sources()))]
    t = [[] for srcnum in xrange(sum(get_total_number_sources()))]
    tnd = [[] for srcnum in xrange(sum(get_total_number_sources()))]
    for i in range(x):
        print "Running experiment..."
        (srcs, delay, tput) = run(alg, n, rate)
        sources = srcs
        i=0
        print "Rates", rates
        print "Measured throughput " , tput
        for s in srcs:
            l[s].append(delay[s])
            t[s].append(tput[s] - rates[i])
            tnd[s].append(tput[s])
            i = i+1
    #print "All latencies", l
    print "All throughputs", t
    sources = get_real_source_list()
    #print "Sources", sources
    if shouldPlot:
        an = QAnalysis()
        an.plot(
            "Average Measured/Actual Throughput Difference",
            "Measured rate - offered load (bps)",
            sources, t, "report%simg_%s_%s.png" % (os.sep, filenamebody, "tput"))
        an.plot(
            "Average Measured Throughput",
            "Throughput (bps)",
            sources, tnd, "report%simg_%s_%s.png" % (os.sep, filenamebody, "tput_nodelta"))
        an.plot(
            "Average Source Latencies",
            "Latency (seconds) ",
            sources, l, "report%simg_%s_%s.png" % (os.sep, filenamebody, "latency"))





if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Test various queuing algorithms')
    parser.add_argument('-M', metavar='M', required=True, type=float, help='load')
    parser.add_argument('-x', metavar='x', type=int, help='Number of experiements to run')
    parser.add_argument('-n', metavar='num_packets', type=int, help='Number of packets to use in experiements', required=True)
    parser.add_argument('-p', action='store_true', help='Whether to display the plots')


   # fh = logging.FileHandler('q.out')
   # fh.setLevel(logging.DEBUG)
   # logger.addHandler(fh)
   # logger.setLevel(logging.ERROR)
   
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--fifo', action='store_true')
    group.add_argument('--rr', action='store_true')
    group.add_argument('--drr', action='store_true')

    # set the output filenames:
    args = parser.parse_args()
    store_type = None
    if args.fifo:
        store_type = "fifo"
    elif args.rr:
        store_type = "rr"
    elif args.drr:
        store_type = "drr"
    else:
        assert False

    main(args.M, args.x, args.n, store_type, args.p)

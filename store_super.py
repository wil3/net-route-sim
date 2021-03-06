import logging
import simpy

class QStore(simpy.Store):
    """
    Subclasses the simpy Store class for our needs.
    Should be further subclassed by a store implementing a specific queuing
    protocol.
    """
    
    def __init__(self, env, buffersize=100000):
        super(QStore, self).__init__(env)
        self._log = {}
        self.logger = logging.getLogger('q')
        self._buffersize = buffersize
        self._bufferoccupancy = 0
        self.env = env

    def _do_put(self, event):
        self.logger.debug( "Do put" + str(event.item))
        event.item.set_arrive_time(self.env.now)
        self.logger.debug("Do put" + str(event.item))

    def _do_get(self, event):
        pass
    
    def _record(self, pkt):
        if not (pkt.src in self._log):
            self._log[pkt.src] = {}
        self._log[pkt.src][pkt.seq] = pkt

    def get_log(self):
        """Returns the log."""
        return self._log

    def _get_queue_str(self,q):
        pkts = ""
        for pkt in q:
            pkts += str(pkt.len) + "|"
        return pkts


    def _print_q_out(self):
        border = "<<----------"
        return self.print_q(border)

    def _print_q_in(self):
        border = "----------<<"
        return self.print_q(border)





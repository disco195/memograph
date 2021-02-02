import time
import typing
import itertools
import collections

import mg.webisu.ebisu as ebisu
import mg.topk as topk

from mg.node import Node, load_node


# # #
# Bayesian Memory Model
# 

class MemoryModel:
    def __init__(self, key, database, log):
        self.key = key
        self.data = database[key] # modifiable reference
        self.log = log
    
    def is_new(self):
        """
        bool: the memory model is yet to be initialised
        """
        return self.data == {}

    def is_recalled(self):
        """
        bool: the last trial with this link passed
        (false if failed *or* if never tried)
        """
        if 'lastResult' in self.data:
            return self.data['lastResult']
        else:
            return False

    def init(self, prior_params=[1, 1, 1*60*60]):
        """
        set up the memory model for the first time
        """
        self.data['priorParams'] = prior_params
        self.data['numDrills'] = 0
        self.data['lastTime'] = self._current_time()
        self._log("LEARN", prior=prior_params)
    
    def predict(self, exact=False):
        """
        compute the expected (log) probability of recalling the link
        (link must be initialised)
        """
        # new card, skip
        elapsed_time = self._current_time() - self.data['lastTime']
        prior_params = self.data['priorParams']
        return ebisu.predictRecall(prior_params, elapsed_time, exact=exact)

    def review(self):
        """update time without updating memory model"""
        self.data['lastTime'] = self._current_time()
        self._log("REVIEW")

    def update(self, got):
        """
        update the memory model based on the result of a drill
        note: must be initialised
        """
        self.data['numDrills'] += 1
        self.data['lastResult'] = got
        now = self._current_time()
        prior_params = self.data['priorParams']
        elapsed_time = now - self.data['lastTime']
        postr_params = ebisu.updateRecall(prior_params, got, 1, elapsed_time)
        self.data['priorParams'] = postr_params
        self.data['lastTime'] = now
        self._log("DRILL", got=got)

    def _current_time(_self):
        return int(time.time())

    def _log(self, event, **data):
        self.log.log(
            id=self.key,
            time=self._current_time(),
            event=event,
            data=data,
        )


# # #
# Knowledge Graph Link
# 

class Link(typing.NamedTuple):
    u: Node
    v: Node
    t: str
    m: MemoryModel
    i: int
    # w: int   # weight TODO

    def __str__(self):
        s = f"[{self.t}] {self.u.label()}"
        if self.m.is_new():
            return s
        else:
            elapsed_time = self.m._current_time() - self.m.data['lastTime']
            return f"{s} [{elapsed_time}s ago]"


# # #
# Knowledge Graph
#


class KnowledgeGraph:
    def __init__(self, items, database, log):
        # generate and load all nodes and links from this script
        unodes = collections.defaultdict(list)
        vnodes = collections.defaultdict(list)
        links  = collections.defaultdict(set)
        indexs = set()
        for i, (u, v, *t) in enumerate(items):
            # topic is optional
            t = t[0] if t else ""
            # cast from primitive types
            u = load_node(u)
            v = load_node(v)
            # detect duplicates
            if u in unodes:
                u.setnum(len(unodes[u])+1)
                unodes[u][0].setnum(1)
            unodes[u].append(u)
            if v in vnodes:
                v.setnum(len(vnodes[v])+1)
                vnodes[v][0].setnum(1)
            vnodes[v].append(v)
            # load memory model
            lindex = f"{u.index()}-[{t}]-{v.index()}"
            model = MemoryModel(lindex, database, log)
            # ensure no duplicates (this allows repeats in graph.py)
            if lindex in indexs:
                continue
            else:
                indexs.add(lindex)
            # load and index link
            link = Link(u, v, t, model, i)
            for topic in t.split("."):
                links[topic].add(link)
            if link.m.is_new():
                links[".new"].add(link)
            else:
                links[".old"].add(link)
                if link.m.is_recalled():
                    links[".got"].add(link)
                else:
                    links[".forgot"].add(link)
            links[".all"].add(link)
        self.topic_links = links
        
    def count(self, topics=None, new=False, review=False):

        if not topics:
            topics = [".all"]
        if new:
            topics = [".new", *topics]
        else:
            topics = [".old", *topics]
        if review:
            topics = [".forgot", *topics]
        links = set.intersection(*(self.topic_links[t] for t in topics))
        return len(links)

    def query(self, number=None, topics=None, new=False, review=False):
        if not topics:
            topics = [".all"]
        if new:
            topics = [".new", *topics]
        else:
            topics = [".old", *topics]
        if review:
            topics = [".forgot", *topics]
        links = set.intersection(*(self.topic_links[t] for t in topics))
        if new:
            key = lambda l: l.i
        else:
            key = lambda l: l.m.predict()
        if number is None:
            return sorted(links, key=key)
        else:
            return topk.topk(links, number, key=key, reverse=True)


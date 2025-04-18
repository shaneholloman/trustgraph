
from . clients.graph_embeddings_client import GraphEmbeddingsClient
from . clients.triples_query_client import TriplesQueryClient
from . clients.embeddings_client import EmbeddingsClient
from . clients.prompt_client import PromptClient

from . schema import GraphEmbeddingsRequest, GraphEmbeddingsResponse
from . schema import TriplesQueryRequest, TriplesQueryResponse
from . schema import prompt_request_queue
from . schema import prompt_response_queue
from . schema import embeddings_request_queue
from . schema import embeddings_response_queue
from . schema import graph_embeddings_request_queue
from . schema import graph_embeddings_response_queue
from . schema import triples_request_queue
from . schema import triples_response_queue

LABEL="http://www.w3.org/2000/01/rdf-schema#label"
DEFINITION="http://www.w3.org/2004/02/skos/core#definition"

class Query:

    def __init__(
            self, rag, user, collection, verbose,
            entity_limit=50, triple_limit=30, max_subgraph_size=1000,
            max_path_length=2,
    ):
        self.rag = rag
        self.user = user
        self.collection = collection
        self.verbose = verbose
        self.entity_limit = entity_limit
        self.triple_limit = triple_limit
        self.max_subgraph_size = max_subgraph_size
        self.max_path_length = max_path_length

    def get_vector(self, query):

        if self.verbose:
            print("Compute embeddings...", flush=True)

        qembeds = self.rag.embeddings.request(query)

        if self.verbose:
            print("Done.", flush=True)

        return qembeds

    def get_entities(self, query):

        vectors = self.get_vector(query)

        if self.verbose:
            print("Get entities...", flush=True)

        entities = self.rag.ge_client.request(
            user=self.user, collection=self.collection,
            vectors=vectors, limit=self.entity_limit,
        )

        entities = [
            e.value
            for e in entities
        ]

        if self.verbose:
            print("Entities:", flush=True)
            for ent in entities:
                print(" ", ent, flush=True)

        return entities
        
    def maybe_label(self, e):

        if e in self.rag.label_cache:
            return self.rag.label_cache[e]

        res = self.rag.triples_client.request(
            user=self.user, collection=self.collection,
            s=e, p=LABEL, o=None, limit=1,
        )

        if len(res) == 0:
            self.rag.label_cache[e] = e
            return e

        self.rag.label_cache[e] = res[0].o.value
        return self.rag.label_cache[e]

    def follow_edges(self, ent, subgraph, path_length):

        # Not needed?
        if path_length <= 0:
            return

        # Stop spanning around if the subgraph is already maxed out
        if len(subgraph) >= self.max_subgraph_size:
            return

        res = self.rag.triples_client.request(
            user=self.user, collection=self.collection,
            s=ent, p=None, o=None,
            limit=self.triple_limit
        )

        for triple in res:
            subgraph.add(
                (triple.s.value, triple.p.value, triple.o.value)
            )
            if path_length > 1:
                self.follow_edges(triple.o.value, subgraph, path_length-1)

        res = self.rag.triples_client.request(
            user=self.user, collection=self.collection,
            s=None, p=ent, o=None,
            limit=self.triple_limit
        )

        for triple in res:
            subgraph.add(
                (triple.s.value, triple.p.value, triple.o.value)
            )

        res = self.rag.triples_client.request(
            user=self.user, collection=self.collection,
            s=None, p=None, o=ent,
            limit=self.triple_limit,
        )

        for triple in res:
            subgraph.add(
                (triple.s.value, triple.p.value, triple.o.value)
            )
            if path_length > 1:
                self.follow_edges(triple.s.value, subgraph, path_length-1)

    def get_subgraph(self, query):

        entities = self.get_entities(query)

        if self.verbose:
            print("Get subgraph...", flush=True)

        subgraph = set()

        for ent in entities:
            self.follow_edges(ent, subgraph, self.max_path_length)

        subgraph = list(subgraph)

        return subgraph

    def get_labelgraph(self, query):

        subgraph = self.get_subgraph(query)

        sg2 = []

        for edge in subgraph:

            if edge[1] == LABEL:
                continue

            s = self.maybe_label(edge[0])
            p = self.maybe_label(edge[1])
            o = self.maybe_label(edge[2])

            sg2.append((s, p, o))

        sg2 = sg2[0:self.max_subgraph_size]

        if self.verbose:
            print("Subgraph:", flush=True)
            for edge in sg2:
                print(" ", str(edge), flush=True)

        if self.verbose:
            print("Done.", flush=True)

        return sg2
    
class GraphRag:

    def __init__(
            self,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
            pr_request_queue=None,
            pr_response_queue=None,
            emb_request_queue=None,
            emb_response_queue=None,
            ge_request_queue=None,
            ge_response_queue=None,
            tpl_request_queue=None,
            tpl_response_queue=None,
            verbose=False,
            module="test",
    ):

        self.verbose=verbose

        if pr_request_queue is None:
            pr_request_queue = prompt_request_queue

        if pr_response_queue is None:
            pr_response_queue = prompt_response_queue

        if emb_request_queue is None:
            emb_request_queue = embeddings_request_queue

        if emb_response_queue is None:
            emb_response_queue = embeddings_response_queue

        if ge_request_queue is None:
            ge_request_queue = graph_embeddings_request_queue

        if ge_response_queue is None:
            ge_response_queue = graph_embeddings_response_queue

        if tpl_request_queue is None:
            tpl_request_queue = triples_request_queue

        if tpl_response_queue is None:
            tpl_response_queue = triples_response_queue

        if self.verbose:
            print("Initialising...", flush=True)

        self.ge_client = GraphEmbeddingsClient(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            subscriber=module + "-ge",
            input_queue=ge_request_queue,
            output_queue=ge_response_queue,
        )            

        self.triples_client = TriplesQueryClient(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            subscriber=module + "-tpl",
            input_queue=tpl_request_queue,
            output_queue=tpl_response_queue
        )

        self.embeddings = EmbeddingsClient(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_queue=emb_request_queue,
            output_queue=emb_response_queue,
            subscriber=module + "-emb",
        )

        self.label_cache = {}

        self.prompt = PromptClient(
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_queue=pr_request_queue,
            output_queue=pr_response_queue,
            subscriber=module + "-prompt",
        )

        if self.verbose:
            print("Initialised", flush=True)

    def query(
            self, query, user="trustgraph", collection="default",
            entity_limit=50, triple_limit=30, max_subgraph_size=1000,
            max_path_length=2,
    ):

        if self.verbose:
            print("Construct prompt...", flush=True)

        q = Query(
            rag=self, user=user, collection=collection, verbose=self.verbose,
            entity_limit=entity_limit, triple_limit=triple_limit,
            max_subgraph_size=max_subgraph_size,
            max_path_length=max_path_length,
        )

        kg = q.get_labelgraph(query)

        if self.verbose:
            print("Invoke LLM...", flush=True)
            print(kg)
            print(query)

        resp = self.prompt.request_kg_prompt(query, kg)

        if self.verbose:
            print("Done", flush=True)

        return resp


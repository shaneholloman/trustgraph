
"""
Simple decoder, accepts text documents on input, outputs chunks from the
as text as separate output objects.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter


from ... schema import TextDocument, Chunk, Source
from ... log_level import LogLevel
from ... base import ConsumerProducer

default_input_queue = 'text-doc-load'
default_output_queue = 'chunk-load'
default_subscriber = 'chunker-recursive'

class Processor(ConsumerProducer):

    def __init__(
            self,
            pulsar_host=None,
            input_queue=default_input_queue,
            output_queue=default_output_queue,
            subscriber=default_subscriber,
            log_level=LogLevel.INFO,
            chunk_size=2000,
            chunk_overlap=100,
    ):

        super(Processor, self).__init__(
            pulsar_host=pulsar_host,
            log_level=log_level,
            input_queue=input_queue,
            output_queue=output_queue,
            subscriber=subscriber,
            input_schema=TextDocument,
            output_schema=Chunk,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def handle(self, msg):

        v = msg.value()
        print(f"Chunking {v.source.id}...", flush=True)

        texts = self.text_splitter.create_documents(
            [v.text.decode("utf-8")]
        )

        for ix, chunk in enumerate(texts):

            id = v.source.id + "-c" + str(ix)

            r = Chunk(
                source=Source(
                    source=v.source.source,
                    id=id,
                    title=v.source.title
                ),
                chunk=chunk.page_content.encode("utf-8"),
            )

            self.send(r)

            print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-z', '--chunk-size',
            type=int,
            default=2000,
            help=f'Chunk size (default: 2000)'
        )

        parser.add_argument(
            '-v', '--chunk-overlap',
            type=int,
            default=100,
            help=f'Chunk overlap (default: 100)'
        )

def run():

    Processor.start('chunker', __doc__)


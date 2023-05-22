from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from io import StringIO
from threading import Thread
import xmltodict
from textwrap import wrap as t_wrap
from queue import Queue

import requests
from Bio.SeqIO.FastaIO import SimpleFastaParser

from tqdm.auto import tqdm
from loguru import logger


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DATABASE = "nuccore"


def batched(iterable, n=1):
    as_l = len(iterable)
    for ndx in range(0, as_l, n):
        yield iterable[ndx:min(ndx + n, as_l)]


def parse_arguments():
    parser = argparse.ArgumentParser(description="Download listed NCBI")

    parser.add_argument('-in', '--input',
                        type=str, required=True,
                        help="Path-like input pattern for the output, results would follow the provided pattern")

    parser.add_argument('-out', '--out',
                        type=str, required=True,
                        help="Pattern ")

    parser.add_argument('-rt', '--ret_type',
                        default='fasta',
                        choices=['fasta', 'fasta_cds_na', 'fasta_cds_aa'],
                        help="Type of the returned info, default: %(default)s")

    parser.add_argument('--max_workers',
                        type=int, default=1,
                        help="Number of threads used for requests, default: %(default)s")

    parser.add_argument('--chunk_size',
                        type=int, default=100,
                        help="Maximum accessions to request per one request, default: %(default)s")

    parser.add_argument('--max_symbols',
                        type=int, default=60,
                        help="Maximum symbols per sequence row in fasta file, default: %(default)s")
    parser.add_argument('--api_key',
                        type=str, default="",
                        help="Path for the file with your special API key for NCBI requests, not set by the default")

    return parser.parse_args()


def request_sequences(operation_id: int, accessions_list: list) -> tuple[int, bool, str]:
    result = ""
    operation_success = False
    logger.debug(f"OpID {operation_id} Current target: [{','.join(accessions_list[:3])}, ...]")

    search_request = requests.get(
        BASE_URL + 'esearch.fcgi',
        params={
            "db": DATABASE,
            "term": ",".join(accessions_list),
            "retmax": str(args.chunk_size)
        } | _token_dict
    )

    if search_request.ok:
        as_data = xmltodict.parse(search_request.content)
        if as_data['eSearchResult'].get('Count'):
            found_records = as_data['eSearchResult']['Count']
            if int(found_records) > 0:
                logger.debug(f"OpID {operation_id} Found records: {found_records}")
                ask_data = requests.get(
                    BASE_URL + "epost.fcgi",
                    params={
                        "db": DATABASE,
                        "id": ",".join(as_data['eSearchResult']['IdList']["Id"])
                    } | _token_dict
                )
                if ask_data.ok:
                    p_data = xmltodict.parse(ask_data.content)
                    query, env = p_data['ePostResult']['QueryKey'], p_data['ePostResult']['WebEnv']

                    fasta_request = requests.get(
                        BASE_URL + "efetch.fcgi",
                        params={
                            "db": DATABASE,
                            "query_key": query,
                            "WebEnv": env,
                            "rettype": args.ret_type,
                            "retmode": "text"
                        } | _token_dict
                    )
                    if fasta_request.ok:  # if only we succeed with the requests chain
                        operation_success = True
                        logger.debug(f"OpID {operation_id} Fasta obtained for [{','.join(accessions_list[:3])}, ...]")
                        result = fasta_request.text
                    else:
                        logger.error(f"OpID {operation_id} Request fasta failed with " +
                                     f"{fasta_request.status_code}: {fasta_request.text}")
                else:
                    logger.error(f"OpID {operation_id} request query " +
                                 f"failed with {ask_data.status_code}: {ask_data.text}")
            else:
                logger.warning(f"OpID {operation_id} Search resulted in zero values for current target")
        else:
            if data['eSearchResult'].get('ERROR'):
                logger.error(f"OpID {operation_id} request search results" +
                             f" report error {data['eSearchResult']['ERROR']}")
            else:
                logger.error(f"OpID {operation_id} request search results failed without error description from NCBI")
    else:
        logger.error(f"OpID {operation_id} Request search failed with " +
                     f"{search_request.status_code}: {search_request.text}")

    return operation_id, operation_success, result


def consume():
    while True:
        if not queue.empty():
            sample_from_queue = queue.get()
            if sample_from_queue is None:
                break
            else:
                operation_id, operation_success, raw_text = sample_from_queue

                if operation_success:
                    logger.debug(f"Succeed operation {operation_id} passing to " + args.out + f"_{operation_id}.fasta")
                    with open(args.out + f"_{operation_id}.fasta", "w") as wr:
                        for name, seq in SimpleFastaParser(StringIO(raw_text)):
                            beautiful_seq = "\n".join(t_wrap(seq, args.max_symbols))
                            wr.write(f">{name}\n{beautiful_seq}\n")
                else:
                    logger.debug(f"Failed operation {operation_id} passing to " + args.out + f"_{operation_id}.fail")
                    with open(args.out + f"_{operation_id}.fail", "w") as wr:
                        for elem in cleaned_queries[operation_id]:
                            wr.write(elem + "\n")


if __name__ == "__main__":
    logger.remove()
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True, level="INFO", diagnose=False)
    logger.info("Requesting NCBI API for some accessions")

    args = parse_arguments()

    logger.add(args.out + "_records.log", level="DEBUG", diagnose=False)
    logger.info(f"Descriptive logs could be found at {args.out}_records.log")

    logger.debug(f"Max number of accessions per request set {args.chunk_size}")
    logger.debug(f"Return type of sequences set {args.ret_type}")
    logger.debug(f"Max workers for requests set {args.max_workers}")
    num_of_workers = args.max_workers
    logger.debug(f"Max symbols per row in FASTA set {args.max_symbols}")

    if args.api_key:
        try:
            with open(args.api_key, "r") as fr:
                _token_dict = {"api_key": fr.read()}
            logger.debug(f"API Key file was set from {args.api_key}")
        except FileNotFoundError:
            logger.warning(f"API Key file was set but was not found from {args.api_key}")
            logger.warning("Switching to 1 worker to provide requests success")
            num_of_workers = 1
            _token_dict = {}
    else:
        logger.warning("No API key found, switching to 1 worker to provide success")
        num_of_workers = 1
        _token_dict = {}

    cleaned_queries = list()

    with open(args.input, "r") as fr:
        for batch in batched(fr.read().splitlines(), args.chunk_size):
            cleaned_queries.append(batch)

    logger.info(f"Found {len(cleaned_queries)} chunk(s) of accessions")

    queue = Queue()

    consumer = Thread(target=consume, daemon=True)
    consumer.start()

    with ThreadPoolExecutor(max_workers=num_of_workers) as executor:
        p_bar = tqdm(total=len(cleaned_queries), position=1)
        future_to_files = {
            executor.submit(request_sequences,
                            op_id, target): op_id for op_id, target in enumerate(cleaned_queries)
            }

        for future in as_completed(future_to_files):
            current_operation = future_to_files[future]

            try:
                data = future.result()
            except Exception as exc:
                logger.critical(f"OpID {current_operation} failed with {type(exc)}: {exc}")
            else:
                queue.put(data)
                p_bar.update()

        p_bar.close()
    logger.success("Done requesting, waiting for files")

    queue.put(None)

    consumer.join()

    logger.info("Done")

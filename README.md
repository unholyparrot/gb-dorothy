# GB-Dorothy — NCBI Accessions Puller
The importance of downloading selected sequences from GenBank cannot be overstated. 
The NCBI team do their best to provide a convenient interface for researchers around the world, 
but a simple desire to download several hundred sequences becomes a tedious and even daunting task.
Despite the presence of [Entrez Programming Utilities (E-utilities)](https://www.ncbi.nlm.nih.gov/home/develop/api/), 
the NCBI API can seem rather cumbersome to use at first glance, so an easy-to-use script is provided to download selected accessions.

## Quick start 

__NB: Requires Python 3.9, installation is still under review.__

### Conda installation

1. Clone the repo
2. Go to the project directory `cd gb-dorothy`
3. Create virtual environment `python3 -m venv venv`
4. Activate the environment 
   * Linux `source venv/bin/activate`
   * Windows `./venv/Scripts/activate`
5. Satisfy the dependencies `pip install -r requirements.txt`
6. Check the usage `python call_seqs.py -in example/example_list.txt -out example/init_run`

_NB: You must activate the environment each time you want to use the script._

### Pip installation

1. Clone the repo
2. Go to the project directory `cd gb-dorothy`
3. Satisfy the dependencies `conda install --file requirements.txt`
4. Check the usage `python call_seqs.py -in example/example_list.txt -out example/init_run`

_NB: Here we assume that conda environment is enabled by default each time._

## Results overview 

You will have *((number of accessions listed) // (chunk size)) + 1* files according, whereas:
* `*.log` file reports the sequence download process;
* `*.fasta` files contain the desired sequences;
* `*.fail` files list the accessions from the chunk that could not be downloaded.

The contents of the FASTA files depend on `-rt / --ret_type` according to the [Entrez Programming Utilities Help](https://www.ncbi.nlm.nih.gov/books/NBK25499/table/chapter4.T._valid_values_of__retmode_and/).

| `--ret_type` argument  | Content              |
|------------------------|----------------------|
| `fasta`                | FASTA                |
| `fasta_cds_na`         | CDS nucleotide FASTA |
| `fasta_cds_aa`         | CDS protein FASTA    |

## Retrieval speed

NCBI limits the rate at which the API can be used, so we have to take this into account when retrieving the information.
The limit without the API key is 3 requests per second, with a personal API key 10 requests per second.

The script will run without the API key by default; 
you will need to obtain it according to the [instructions provided](https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/) 
and write it into the file (simply, in one line, no new line characters, etc.). 
Later, you can simply specify the location of the file for each run with the `--api_key` argument.

If you don't want to keep an API key, or you still get the _request rate exceeded_ error, 
increase the chunk limit manually, this will reduce the request rate.

## Example 

Let's say you want to download some bat coronavirus sequences found in a publication. Let's put them into a 
[TXT file](example/example_list.txt), accession by accession. 

Run the script without the API key:

`python call_seqs.py -in example/example_list.txt -out example/second_run` 

or with an API key and at a higher speed:

`python call_seqs.py -in example/example_list.txt -out example/second_run --api_key api.key --max_workers 4 --chunk_size 50`

and see the results with the name pattern `second_run_` in the `example` folder. 

The accessions list is deliberately provided with an error accession `T797609.1` 
to show how the script handles accessions it cannot find.

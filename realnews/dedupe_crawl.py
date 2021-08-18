import boto3
import ujson as json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from tempfile import NamedTemporaryFile
from collections import defaultdict
import random
from boto3.s3.transfer import TransferConfig
s3client = boto3.client('s3')
from util import _fix_notfound_authors, _fix_photos, _get_split, _is_definitely_unique

DUMP_ORDER = [
                 'CC-MAIN-2016-50',
                 'CC-MAIN-2017-04',
                 'CC-MAIN-2017-09',
                 'CC-MAIN-2017-13',
                 'CC-MAIN-2017-17',
                 'CC-MAIN-2017-22',
                 'CC-MAIN-2017-26',
                 'CC-MAIN-2017-30',
                 'CC-MAIN-2017-34',
                 'CC-MAIN-2017-39',
                 'CC-MAIN-2017-43',
                 'CC-MAIN-2017-47',
                 'CC-MAIN-2017-51',
                 'CC-MAIN-2018-05',
                 'CC-MAIN-2018-09',
                 'CC-MAIN-2018-13',
                 'CC-MAIN-2018-17',
                 'CC-MAIN-2018-22',
                 'CC-MAIN-2018-26',
                 'CC-MAIN-2018-30',
                 'CC-MAIN-2018-34',
                 'CC-MAIN-2018-39',
                 'CC-MAIN-2018-43',
                 'CC-MAIN-2018-47',
                 'CC-MAIN-2018-51',
                 'CC-MAIN-2019-04',
                 'CC-MAIN-2019-09',
                 'CC-MAIN-2019-13',
             ][::-1]


def get_matching_s3_objects(bucket, prefix='', suffix=''):
    """
    Generate objects in an S3 bucket.
    THANK YOU https://alexwlchan.net/2018/01/listing-s3-keys-redux/

    :param bucket: Name of the S3 bucket.
    :param prefix: Only fetch objects whose key starts with
        this prefix (optional).
    :param suffix: Only fetch objects whose keys end with
        this suffix (optional).
    """
    kwargs = {'Bucket': bucket}

    # If the prefix is a single string (not a tuple of strings), we can
    # do the filtering directly in the S3 API.
    if isinstance(prefix, str):
        kwargs['Prefix'] = prefix

    while True:

        # The S3 API response is a large blob of metadata.
        # 'Contents' contains information about the listed objects.
        resp = s3client.list_objects_v2(**kwargs)

        try:
            contents = resp['Contents']
        except KeyError:
            return

        for obj in contents:
            key = obj['Key']
            if key.startswith(prefix) and key.endswith(suffix):
                yield obj['Key''']

        # The S3 API is paginated, returning up to 1000 keys at a time.
        # Pass the continuation token into the next response, until we
        # reach the final page (when this field is missing).
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break


def iterate_over_batches(stream, batch_size=64):
    buffer = []
    for x in stream:
        buffer.append(x)
        if len(buffer) >= batch_size:
            yield buffer
            buffer = []
    if len(buffer) > 0:
        yield buffer
class Fetcher(object):
    def __init__(
            self,
            workers=8,
    ):
        self.workers = workers

    def download(self, obj_key_batch):
        """
        Download a thing.
        """
        with ThreadPoolExecutor(self.workers) as executor:
            yield from executor.map(self._thread, obj_key_batch)

    def _thread(self, obj_key):
        article_list = []

        with NamedTemporaryFile(mode='w+b', dir='/home/ubuntu/temp2/') as packet_temp:
            s3client.download_fileobj('periodista', obj_key, packet_temp)
            packet_temp.seek(0)

            with open(packet_temp.name, 'r') as fin:
                for l in fin:
                    article = json.loads(l)

                    # Preprocessing could go here
                    _fix_notfound_authors(article)
                    _fix_photos(article)
                    article_list.append(article)
        return article_list


def fast_article_iterator(cc_name, batch_size=256):
    for obj_key_batch in tqdm(iterate_over_batches(get_matching_s3_objects('periodista', prefix=cc_name),
                                                   batch_size=batch_size), total=64000 // batch_size):
        fetcher = Fetcher(workers=16)
        for article_list in fetcher.download(obj_key_batch):
            for article in article_list:
                yield article


def _get_mini_sample(num_to_return=1000):
    articles = []
    hits = 0
    misses = 0
    domain2count = defaultdict(int)
    for article in fast_article_iterator(DUMP_ORDER[0]):
        if _is_definitely_unique(article):
            domain2count[article['domain']] += 1
            articles.append(article)
            hits += 1
        else:
            misses += 1
        if (hits + misses) % 100000 == 0:
            print(f"{hits} hits and {misses} misses", flush=True)

        if len(articles) > (num_to_return * 1000):
            break
    random.shuffle(articles)
    return articles[:num_to_return], dict(domain2count)


def upload_to_s3(in_fn, out_fn):
    config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10,
                            multipart_chunksize=1024 * 25, use_threads=True)
    s3client.upload_file(in_fn, 'periodista', out_fn,
                         ExtraArgs={'ACL': 'public-read'},
                         Config=config,
                         )


def _iterate_through_archivedotorg(bucket_name):
    with NamedTemporaryFile(mode='w+b', dir='/home/ubuntu/temp2/') as packet_temp:
        s3client.download_fileobj(bucket_name, 'archivedotorg.jsonl', packet_temp)
        packet_temp.seek(0)

        with open(packet_temp.name, 'r') as fin:
            for l in fin:
                article = json.loads(l)
                article['split'] = _get_split(article['domain'])
                if article['split'] == 'ignore':
                    article['split'] = 'train'

                # Preprocessing could go here
                _fix_notfound_authors(article)
                _fix_photos(article)
                if _is_definitely_unique(article):
                    yield article


if __name__ == '__main__':
    # Iterate through and also get the archive.org scrape
    hits = 0
    misses = 0
    domain2count = defaultdict(int)

    BUCKET_NAME = "MYBUCKETNAME"

    with open('/home/ubuntu/temp2/news.jsonl', 'w') as f:
        # First get the archive.org scrape, which already is going to handle deduplication /etc
        for article in _iterate_through_archivedotorg(BUCKET_NAME):
            domain2count[article['domain']] += 1
            f.write(json.dumps(article) + '\n')
            hits += 1
            if hits % 1000 == 0:
                print(article, flush=True)

        print("Got {} from archive.org".format(hits))

        for cc_name in DUMP_ORDER:
            for article in fast_article_iterator(cc_name):
                if _is_definitely_unique(article):
                    domain2count[article['domain']] += 1

                    article['split'] = _get_split(article['domain'])
                    if article['split'] != 'ignore':
                        f.write(json.dumps(article) + '\n')
                    hits += 1
                    if hits % 100000 == 0:
                        print(article, flush=True)
                else:
                    misses += 1
                if (hits + misses) % 100000 == 0:
                    print(f"{hits} hits and {misses} misses", flush=True)

    upload_to_s3('/home/ubuntu/temp2/news.jsonl', out_fn='news-apr-15-2019.jsonl')
    with NamedTemporaryFile(mode='w', dir='/home/ubuntu/temp2/') as out_tmp:
        json.dump(dict(domain2count), out_tmp)
        s3client.upload_file(out_tmp.name, BUCKET_NAME, 'domain2count.json', ExtraArgs={'ACL': 'public-read'})
from pybloof import StringBloomFilter
from collections import defaultdict
import random
import os
import re


# this is hella usefl https://krisives.github.io/bloom-calculator/
has_seen_url = StringBloomFilter(size=14440984416, hashes=10)
has_seen_content_start = StringBloomFilter(size=14440984416, hashes=10)
# has_seen_content_end = StringBloomFilter(size=14440984416, hashes=10)


TRAIN_PORTION = 0.95
CONTENT_LENGTH = 100


def _get_split(domain):
    """ You could do this by domain, or not"""
    if random.random() < TRAIN_PORTION:
        return 'train'
    return 'val'

def _could_be_author(author):
    author_lower = author.lower().strip()
    if author_lower.startswith(('https', 'www.', 'min read')):
        return False
    if '.com' in author_lower:
        return False
    if author_lower in {'arts', 'politics', 'sports', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'}:
        return False
    return True

def _fix_notfound_authors(article):
    """
    # An extra preprocessing step: if author list is empty and article starts with By then let's fix things.
    :param article:
    :return:
    """
    if len(article['authors']) == 0 and article['text'].startswith('By ') and '\n' in article:
        possible_authors, text = article['text'][3:].split('\n', maxsplit=1)
        if len(possible_authors.split(' ')) < 6:
            article['authors'] = [possible_authors.strip()]
            article['text'] = text.strip()

    article['authors'] = [x for x in article['authors'] if _could_be_author(x)]

    # Those aren't summaries
    if article['summary'] is not None and article['summary'].endswith(('...','…')):
        article['summary'] = None


def _fix_photos(article):
    article['text'] += '\n'
    article['text'] = re.sub(r'(Facebook Twitter Pinterest |ADVERTISEMENT ADVERTISEMENT|ADVERTISEMENT Thanks for watching! Visit Website)', '', article['text'])
    article['text'] = re.sub(r'\nAdvertisement\s+Advertisement\n', '\n', article['text'])

    article['text'] = re.sub(r'\((Photo|Image|Source|Photograph): .{1, 60}\)', '', article['text'])
    article['text'] = re.sub(r'\n(Photo|Image|Source|Photograph): .{1, 60}\n', '\n', article['text'])
    article['text'] = re.sub(r'\nPhoto Published on .{1, 60}\n', '\n', article['text'])

    article['text'] = re.sub(r'\.\s+(Photo|Image): .{1, 60}\n', '.\n', article['text'])
    article['text'] = re.sub(r'\nPicture Courtesy: .{1, 60}\n', '\n', article['text'])
    article['text'] = re.sub(r'\n(\[Related:|RELATED|READ MORE:|PHOTOS:|SEE ALSO:|Also On News|MORE:) .{1, 120}\n', '\n', article['text'])
    article['text'] = re.sub(r'Share this: Facebook\nTwitter\nGoogle\nWhatsApp\nEmail\nCopy\n', '\n', article['text'])


    article['text'] = re.sub(r'\n+', '\n', article['text'])
    # article['text'] = re.sub(r'http.+\b', '', article['text'])
    article['text'].strip()



    # Forbes often has these duplications
    if article['domain'] == 'forbes.com':
        for company_name in ['Apple', 'Microsoft', 'Google', 'Amazon', 'Chase', 'Citigroup', 'Comcast',
                             'Cisco', 'Disney', 'Facebook', 'Intel', 'Netflix', 'Nike', 'Starbucks', 'NVIDIA',
                             'Raytheon', 'Visa', 'Verizon', 'ExxonMobil']:
            article['text'] = article['text'].replace(f'{company_name} {company_name}', f'{company_name}')

def _is_definitely_unique(article):
    # CERTAIN THINGS ALWAYS NEED TO BE BANNED
    if len(re.findall(r'Image \d+ of \d+', article['text'])) > 2:
        return False

    if ' '.join(article['authors']) == 'News Traffic Weather':
        return False

    if article['url'] in has_seen_url:
        return False

    if article['text'][:CONTENT_LENGTH] in has_seen_content_start:
        return False

    has_seen_url.add(article['url'])
    has_seen_content_start.add(article['text'][:CONTENT_LENGTH])
    return True

import pandas as pd
import copy
import os
import numpy as np
import re


from tqdm import tqdm
from collections import defaultdict
from os.path import abspath
from spacy.lang.vi import Vietnamese
from spacy.attrs import ORTH, LEMMA
from .constant import EMOTICONS, DEFAULT_MAX_FEATURES
from gensim.models.keyedvectors import KeyedVectors

def split_array(arr, condition):
    if len(arr) == 0:
        return []
    result = []
    accumulated = [arr[0]]
    for ele in arr[1:]:
        if condition(ele):
            result.append(copy.deepcopy(accumulated))
            accumulated = [copy.deepcopy(ele)]
        else:
            accumulated.append(copy.deepcopy(ele))
    result.append(copy.deepcopy(accumulated))
    return result


def read_file(file_path, is_train=True):
    file_path = abspath(file_path)
    data_lines = list(
        filter(lambda x: x != '', open(file_path).read().split('\n')))
    pattern = ('train' if is_train else 'test') + '_[0-9]{5}'
    datas = split_array(data_lines, lambda x: bool(re.match(pattern, x)))
    if is_train:
        result_array = list(map(
            lambda x: [x[0], ' '.join(x[1:-1]), int(x[-1])], datas))
    else:
        result_array = list(map(lambda x: [x[0], ' '.join(x[1:])], datas))
    columns = ['name', 'text', 'label'] if is_train else ['name', 'text']
    return pd.DataFrame(result_array, columns=columns)

def tokenize(texts):
    ExceptionsSet = {}
    for orth in EMOTICONS:
        ExceptionsSet[orth] = [{ORTH: orth}]


    nlp = Vietnamese()
    docs = []
    for text in texts:
        tokens = np.array([token.text for token in nlp(text.lower())[1:-1]])
        docs.append(tokens)

    return np.array(docs)


def make_embedding(texts, embedding_path, embed_size=300, max_features=DEFAULT_MAX_FEATURES):
    embedding_path = abspath(embedding_path)

    def get_coefs(word, *arr):
        return word, np.asarray(arr, dtype='float32')
    if embedding_path.endswith('.vec'):
        embedding_index = dict(get_coefs(*o.strip().split(" "))
                               for o in open(embedding_path))
        mean_embedding = np.mean(np.array(list(embedding_index.values())))
    elif embedding_path.endswith('bin'):
        embedding_index = KeyedVectors.load_word2vec_format(
            embedding_path, binary=True)
        mean_embedding = np.mean(embedding_index.vectors, axis=0)

    word_index = {word.lower() for sentence in texts for word in sentence}

    nb_words = min(max_features, len(word_index))

    embedding_matrix = np.zeros((nb_words + 1, embed_size))

    i = 0

    word_map = defaultdict(lambda: nb_words)

    for word in word_index:
        if i >= max_features:
            continue
        if word in embedding_index:
            embedding_matrix[i] = embedding_index[word]
        else:
            embedding_matrix[i] = mean_embedding
        word_map[word] = i
        i += 1

    embedding_matrix[-1] = mean_embedding

    return word_map, embedding_matrix


def text_to_sequences(texts, word_map):
    return np.array([np.array([word_map[word.lower()] for word in sentence]) for sentence in texts])


def predictions_to_submission(test_data, predictor):
    tqdm.pandas()
    submission = test_data[['id']]
    submission['label'] = test_data['text'].progress_apply(predictor)
    return submission
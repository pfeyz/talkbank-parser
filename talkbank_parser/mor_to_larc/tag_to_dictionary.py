import unittest
import string

# general tag format: {prefix}#{pos}:{subPos}|{lemma}&{fusion}-{suffix}

class ValidationResult(object):
    def __init__(self, value, valid, message):
        self.valid = valid
        self.value = value
        self.message = message

class Valid(ValidationResult):
    def __init__(self, value):
        super(Valid, self).__init__(value, True, None)

    def __repr__(self):
        return "Valid({})".format(self.value)

class Invalid(ValidationResult):
    def __init__(self, value, message):
        super(Invalid, self).__init__(value, True, message)

    def __repr__(self):
        return "Invalid({}, {})".format(repr(self.value), repr(self.message))

def valid_mor_dict(mor_dict):
    """ Returns True if `mor_dict` is a valid mor dictionary """

    # a mor dict can only contain the following 6 keys
    valid_keys = set(['prefix', 'pos', 'subPos', 'lemma', 'suffix',
                      'fusional_suffix', 'words', 'wordform'])
    observed_keys = set(mor_dict.keys())
    extra_keys = observed_keys.difference(valid_keys)
    if len(extra_keys) > 0:
        return Invalid(mor_dict, "extra keys")

    # 'pos' and 'lemma' are required
    if 'pos' not in mor_dict:
        return Invalid(mor_dict, "pos missing")
    if 'lemma' not in mor_dict:
        return Invalid(mor_dict, "lemma missing")

    # these keys must all have non-empty lists as values
    for key in ('subPos', 'suffix', 'fusional_suffix'):
        if key in mor_dict:
            if not isinstance(mor_dict[key], list):
                return Invalid(mor_dict, "{}='{}' is not a list".format(key, mor_dict[key]))
            elif len(mor_dict[key]) == 0:
                return Invalid(mor_dict, "{} is empty".format(key))

    # these keys must all have strings as values
    for key in ('prefix', 'pos', 'lemma'):
        if key in mor_dict and not isinstance(mor_dict[key], str):
            return Invalid(mor_dict, "non-string value for key '{}'".format(key))

    # compound words must contain valid component words
    if 'words' in mor_dict:
        for part in mor_dict['words']:
            if not valid_mor_dict(part).valid:
                return Invalid(mor_dict, "invalid compound word: {}".format(repr(part)))

    return Valid(mor_dict)

def tag_to_dictionary(tag):
    """inputs a tag as a string, and outputs the information contained within
    the tag in the form of a dictionary containg the prefix, pos, subpos, lemma,
    fusional_suffix, and suffix"""

    have_prefix = False
    have_subpos = False
    have_fusional = False
    have_suffix = False
    have_words = False
    pos_start = 0
    lemma_start = None

    # find boundaries for pos and (if present) prefix and subpos
    wordform = None
    if '/' in tag:
        wordform, tag = tag.split('/', 1)
    for i in range (0, len(tag)):
            if tag[i] == "#" and have_prefix == False:
                pos_start = i+1
                have_prefix = True
            if tag[i] == ":" and have_subpos == False:
                subpos_start = i
                have_subpos = True
            elif tag[i] == "|":
                lemma_start = i
                break

    if lemma_start is None:
        raise Exception("No lemma found in '{}'".format(tag))

    if have_subpos == True:
        pos_end = subpos_start
    else:
        pos_end = lemma_start

    # define prefix, pos, subpos
    if have_prefix == True:
        prefix = tag[0:pos_start-1]
    pos = tag[pos_start:pos_end]
    if have_subpos == True:
        subPos = tag[subpos_start+1:lemma_start]

    # define lemma for compounds (recursive)
    if '+' in tag:
        have_words = True
        words = tag.split('+')
        words = words[1:]
        words = map(tag_to_dictionary, words)
        lemma = words[0]['lemma']
        for word in words[1:]:
            lemma += '+' + word['lemma']


    # define lemma and suffixes for non-compounds
    else:
        lemma_end = len(tag)+1
        for i in range (lemma_start, len(tag)):
            if tag[i] == "&" and have_fusional == False:
                have_fusional = True
                lemma_end = i
                fusional_end = len(tag)+1
            elif tag[i] == "-" and have_suffix == False:
                have_suffix = True
                if have_fusional == False:
                    lemma_end = i
                else:
                    fusional_end = i
                suffix_start = i
        lemma = tag[lemma_start+1:lemma_end]
        if have_fusional == True:
            fusional_suffix = tag[lemma_end+1:fusional_end]
        if have_suffix == True:
            suffix = tag[suffix_start+1:]

    # put values in dictionary and return
    D = {'pos': pos, 'lemma': lemma, 'wordform': wordform}
    if have_subpos == True:
        D['subPos'] = subPos.split(':')
    if have_prefix == True:
        D['prefix'] = [prefix]
    else:
        D['prefix'] = []
    if have_fusional == True:
        D['fusional_suffix'] = fusional_suffix.split('&')
    if have_suffix == True:
        D['suffix'] = suffix.split('-')
    if have_words == True:
        D['words'] = words

    return D


class ParseCorrectionTests(unittest.TestCase):
    basicCases = [
        ['adj|different', {'pos': 'adj',
                           'wordform': None,
                           'lemma': 'different'}],
        ['n:prop|count', {'pos': 'n',
                          'wordform': None,
                          'subPos': ['prop'], 'lemma': 'count'}],
        ['pro:poss:det|your', {'pos': 'pro',
                               'wordform': None,
                               'subPos': ['poss', 'det'], 'lemma': 'your'}]
    ]

    def test_basics(self):
        for tag, expected in ParseCorrectionTests.basicCases:
            self.assertTrue(valid_mor_dict(expected).valid, "on no")
            observed = tag_to_dictionary(tag)
            self.assertEqual(observed, expected)

    compoundCases = [
        ['int|+v|look+pro:obj|it',  {'lemma': 'look+it', 'pos': 'int',
                                     'wordform': None,
                                     'words': [{'pos': 'v', 'lemma': 'look', 'wordform': None},
                                               {'pos': 'pro', 'subPos': ['obj'], 'lemma': 'it', 'wordform': None}]}],
        ['adj|+adj|funny+adj|looking', {'lemma': 'funny+looking', 'pos': 'adj',
                                        'wordform': None,
                                        'words': [{'pos': 'adj', 'lemma': 'funny', 'wordform': None},
                                                  {'pos': 'adj', 'lemma': 'looking', 'wordform': None}]}],
        ['n|+n|tow+n|truck-PL', {'pos': 'n', 'lemma': 'tow+truck',
                                 'wordform': None,
                                 'words': [{'pos': 'n', 'lemma': 'tow', 'wordform': None},
                                           {'pos': 'n', 'lemma': 'truck', 'suffix': ['PL'], 'wordform': None}]}],
        ['n|+n|sport-PL+n|car', {'pos': 'n', 'lemma': 'sport+car',
                                 'wordform': None,
                                 'words': [{'pos': 'n', 'lemma': 'sport', 'suffix': ['PL'], 'wordform': None},
                                           {'pos': 'n', 'lemma': 'car', 'wordform': None}]}],
        ['n|+n|sweet&dadj-DIM+n|pie', {'pos': 'n', 'lemma': 'sweet+pie',
                                       'wordform': None,
                                       'words': [{'pos': 'n', 'lemma': 'sweet', 'fusional_suffix': ['dadj'], 'suffix': ['DIM'], 'wordform': None},
                                                 {'pos': 'n', 'lemma': 'pie', 'wordform': None}]}],
        ['det:num|+det:num|twenty+det:num|fourth', {'pos': 'det', 'subPos': ['num'], 'lemma': 'twenty+fourth',
                                                    'wordform': None,
                                                    'words': [{'pos': 'det', 'subPos': ['num'], 'lemma': 'twenty', 'wordform': None},
                                                              {'pos': 'det', 'subPos': ['num'], 'lemma': 'fourth', 'wordform': None}]}],
        ['adv|+adv|never+det|the+adj|less', {'pos': 'adv', 'lemma': 'never+the+less',
                                             'wordform': None,
                                             'words': [{'pos': 'adv', 'lemma': 'never', 'wordform': None},
                                                       {'pos': 'det', 'lemma': 'the', 'wordform': None},
                                                       {'pos': 'adj', 'lemma': 'less', 'wordform': None}]}]

    ]

    def test_compounds(self):
        for tag, expected in ParseCorrectionTests.compoundCases:
            self.assertTrue(valid_mor_dict(expected).valid)
            observed = tag_to_dictionary(tag)
            self.assertEqual(observed, expected)

    prefixCases = [
        ['non#adj|sense', {'lemma': 'sense',
                           'wordform': None,
                           'prefix': 'non','pos': 'adj'}],
        ['un#n|till', {'prefix': 'un',
                       'wordform': None,
                       'pos': 'n', 'lemma': 'till'}]
    ]

    def test_prefixes(self):
        for tag, expected in ParseCorrectionTests.prefixCases:
            self.assertTrue(valid_mor_dict(expected).valid)
            observed = tag_to_dictionary(tag)
            self.assertEqual(observed, expected)

    suffixCases = [
        ['v:cop|be&PRES', {'lemma': 'be', 'pos': 'v', 'subPos': ['cop'],
                           'wordform': None,
                           'fusional_suffix': ['PRES']}],
        ['adj|mom&dn-Y', {'lemma': 'mom', 'pos': 'adj',
                          'wordform': None,
                          'fusional_suffix': ['dn'], 'suffix': ['Y']}],
        ['n|doll-DIM', {'pos': 'n',
                        'wordform': None,
                        'lemma': 'doll', 'suffix': ['DIM']}],
        ['n:gerund|write-PROG', {'pos': 'n', 'subPos': ['gerund'], 'lemma': 'write',
                                 'wordform': None,
                                 'suffix': ['PROG']}],
        ['v:cop|be&3s', {'pos': 'v', 'subPos': ['cop'],
                         'wordform': None,
                         'lemma': 'be', 'fusional_suffix': ['3s']}],
        ['aux|be&PAST&3S', {'pos': 'aux',
                            'wordform': None,
                            'lemma': 'be', 'fusional_suffix': ['PAST', '3S']}]
    ]

    def test_suffixes(self):
        for tag, expected in ParseCorrectionTests.suffixCases:
            self.assertTrue(valid_mor_dict(expected).valid3)
            observed = tag_to_dictionary(tag)
            self.assertEqual(observed, expected)



if __name__ == '__main__':
    unittest.main()

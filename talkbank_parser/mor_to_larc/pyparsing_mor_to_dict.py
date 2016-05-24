import unittest
from pyparsing import (Word, alphas, alphanums, ZeroOrMore, OneOrMore, Group,
                       StringStart, StringEnd, ParseException, Optional)
from pprint import pprint

def marker(char):
    """ A separator character that is not captured in the output. """
    return Group(char).suppress()

COLON = marker(':')
POUND = marker('#')
AMP = marker('&')
DASH = marker('-')
PLUS = marker('+')

WORDFORM = Word(alphanums + "+_'.!?-").setResultsName('wordform')
LEMMA =  Word(alphanums + '+_.!?-').setResultsName('lemma')
POS = Word(alphanums + '.!?-').setResultsName('pos')

SUBPOS = Group(ZeroOrMore(COLON + Word(alphanums))
              ).setResultsName('subPos')

PREFIXES = Group(ZeroOrMore(Word(alphanums) + POUND)
                ).setResultsName('prefix')

FUSIONAL_SUFFIXES = Group(ZeroOrMore(AMP + Word(alphanums))
                         ).setResultsName('fusional_suffix')

SUFFIXES = Group(ZeroOrMore(DASH + Word(alphanums))
                ).setResultsName('suffix')

SIMPLE_TAG = (PREFIXES +
              POS +
              SUBPOS +
              '|' + LEMMA +
              FUSIONAL_SUFFIXES +
              SUFFIXES)

COMPOUND_TAG = (PREFIXES + POS + SUBPOS + '|' +
                Group(PLUS + SIMPLE_TAG).setResultsName('word_1') +
                Group(PLUS + SIMPLE_TAG).setResultsName('word_2') +
                Optional(Group(PLUS + SIMPLE_TAG).setResultsName('word_3')) +
                Optional(Group(PLUS + SIMPLE_TAG).setResultsName('word_4')))

def combine_words(s, loc, toks):
    words = [toks.get('word_' + str(n)) for n in [1, 2, 3, 4]
             if toks.get('word_' + str(n))]
    if words:
        toks['words'] = words
    return toks

TAG = StringStart() + WORDFORM + '/' + (SIMPLE_TAG | COMPOUND_TAG) + StringEnd()

def parse_tag(tag):
    try:
        parsed = TAG.parseString(tag).asDict()
    except ParseException, e:
        raise ParseException('Failed parsing "{}" \n {}'.format(tag, repr(e)))

    word_keys = [w for w in ['word_1', 'word_2', 'word_3', 'word_4']
                 if parsed.get(w)]
    words = None
    if word_keys:
        words = [parsed[k] for k in word_keys]
    for k in word_keys:
        del parsed[k]
    if words:
        compound = {'prefix': [], 'subPos': [], 'suffix': [], 'fusional_suffix': []}
        compound.update(parsed)
        compound['words'] = words
        compound['lemma'] = '+'.join(w['lemma'] for w in words)
        for word in words:
            word['wordform'] = None
        return compound
    return parsed

def expand_tag(tag):
    """Accepts a tagged-word dictionary and returns a copy of that dictionary with
    default values for `prefix`, `subpos`, `fusional_suffix` and `suffix`
    defined.

    """
    assert 'pos' in tag
    assert 'wordform' in tag
    assert 'lemma' in tag

    if 'words' in tag:
        tag['words'] = [expand_tag(w) for w in tag['words']]

    fulltag = {'prefix': [], 'subPos': [], 'fusional_suffix': [], 'suffix': []}
    fulltag.update(tag)

    return fulltag

class ParseTests(unittest.TestCase):
    basicCases = [
        ['different/adj|different', {'pos': 'adj',
                                     'wordform': 'different',
                                     'lemma': 'different'}],
        ['count/n:prop|count', {'pos': 'n',
                                'wordform': 'count',
                                'subPos': ['prop'], 'lemma': 'count'}],
        ['your/pro:poss:det|your', {'pos': 'pro',
                                    'wordform': 'your',
                                    'subPos': ['poss', 'det'], 'lemma': 'your'}]
    ]

    def test_basics(self):
        for token, expected in ParseTests.basicCases:
            observed = parse_tag(token)
            self.assertEqual(observed, expand_tag(expected))

    #pylint: disable=line-too-long
    compoundCases = [
        ['look+it/int|+v|look+pro:obj|it', {'lemma': 'look+it', 'pos': 'int',
                                            'wordform': 'look+it',
                                            'words': [{'pos': 'v', 'lemma': 'look', 'wordform': None},
                                                      {'pos': 'pro', 'subPos': ['obj'], 'lemma': 'it', 'wordform': None}]}],
        ['funny+looking/adj|+adj|funny+adj|looking', {'lemma': 'funny+looking', 'pos': 'adj',
                                                      'wordform': 'funny+looking',
                                                      'words': [{'pos': 'adj', 'lemma': 'funny', 'wordform': None},
                                                                {'pos': 'adj', 'lemma': 'looking', 'wordform': None}]}],
        ['tow+truck/n|+n|tow+n|truck-PL', {'pos': 'n', 'lemma': 'tow+truck',
                                           'wordform': 'tow+truck',
                                           'words': [{'pos': 'n', 'lemma': 'tow', 'wordform': None},
                                                     {'pos': 'n', 'lemma': 'truck', 'suffix': ['PL'], 'wordform': None}]}],
        ['sport+car/n|+n|sport-PL+n|car', {'pos': 'n', 'lemma': 'sport+car',
                                           'wordform': 'sport+car',
                                           'words': [{'pos': 'n', 'lemma': 'sport', 'suffix': ['PL'], 'wordform': None},
                                                     {'pos': 'n', 'lemma': 'car', 'wordform': None}]}],
        ['sweetie+pie/n|+n|sweet&dadj-DIM+n|pie', {'pos': 'n', 'lemma': 'sweet+pie',
                                                   'wordform': 'sweetie+pie',
                                                   'words': [{'pos': 'n', 'lemma': 'sweet', 'fusional_suffix': ['dadj'], 'suffix': ['DIM'], 'wordform': None},
                                                             {'pos': 'n', 'lemma': 'pie', 'wordform': None}]}],
        ['twenty+fourth/det:num|+det:num|twenty+det:num|fourth', {'pos': 'det', 'subPos': ['num'], 'lemma': 'twenty+fourth',
                                                                  'wordform': 'twenty+fourth',
                                                                  'words': [{'pos': 'det', 'subPos': ['num'], 'lemma': 'twenty', 'wordform': None},
                                                                            {'pos': 'det', 'subPos': ['num'], 'lemma': 'fourth', 'wordform': None}]}],
        ['never+the+less/adv|+adv|never+det|the+adj|less', {'pos': 'adv', 'lemma': 'never+the+less',
                                                            'wordform': 'never+the+less',
                                                            'words': [{'pos': 'adv', 'lemma': 'never', 'wordform': None},
                                                                      {'pos': 'det', 'lemma': 'the', 'wordform': None},
                                                                      {'pos': 'adj', 'lemma': 'less', 'wordform': None}]}]
    ]


    def test_compounds(self):
        for tag, expected in ParseTests.compoundCases:
            observed = parse_tag(tag)
            self.assertEqual(observed, expand_tag(expected))

    prefixCases = [
        ['nonsense/non#adj|sense', {'lemma': 'sense',
                                    'wordform': 'nonsense',
                                    'prefix': ['non'],
                                    'pos': 'adj'}],
        ['untill/un#n|till', {'prefix': ['un'],
                              'wordform': 'untill',
                              'pos': 'n',
                              'lemma': 'till'}]
    ]

    def test_prefix(self):
        for token, expected in ParseTests.prefixCases:
            observed = parse_tag(token)
            self.assertEqual(observed, expand_tag(expected))

    suffixCases = [
        ['is/v:cop|be&PRES', {'lemma': 'be', 'pos': 'v', 'subPos': ['cop'],
                              'wordform': 'is',
                              'fusional_suffix': ['PRES']}],
        ['mommy/adj|mom&dn-Y', {'lemma': 'mom', 'pos': 'adj',
                                'wordform': 'mommy',
                                'fusional_suffix': ['dn'], 'suffix': ['Y']}],
        ['dolly/n|doll-DIM', {'pos': 'n',
                              'wordform': 'dolly',
                              'lemma': 'doll', 'suffix': ['DIM']}],
        ['writing/n:gerund|write-PROG', {'pos': 'n', 'subPos': ['gerund'], 'lemma': 'write',
                                         'wordform': 'writing',
                                         'suffix': ['PROG']}],
        ['is/v:cop|be&3s', {'pos': 'v', 'subPos': ['cop'],
                            'wordform': 'is',
                            'lemma': 'be', 'fusional_suffix': ['3s']}],
        ['was/aux|be&PAST&3S', {'pos': 'aux',
                                'wordform': 'was',
                                'lemma': 'be', 'fusional_suffix': ['PAST', '3S']}]
    ]

    def test_suffix(self):
        for token, expected in ParseTests.suffixCases:
            observed = parse_tag(token)
            self.assertEqual(observed, expand_tag(expected))

if __name__ == "__main__":
    unittest.main()

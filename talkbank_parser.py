# -*- py-which-shell: "python2" -*-
# -*- coding: utf-8 -*-

"""
Tools for parsing XML cha files

XML Parsing based on:
-  http://talkbank.org/software/xsddoc/

schema is here http://talkbank.org/software/talkbank.xsd
"""

import abc
import itertools
import re
from xml.etree.cElementTree import ElementTree, dump

from datatypes import MorToken, punctuation

class Flag(object):
    " Gets passed to parser to indicate nuanced behavior "
    pass

class DropShorts(Flag):
    """ Drop out parts of wordforms in shortening markers
    '(be)cause' becomes 'cause'  """
    pass

def flatten(list_of_lists):
    """Flatten one level of nesting
    from python.org
    """
    return itertools.chain.from_iterable(list_of_lists)

class TagTypeError(Exception):
    """Raised when parsing function receives an xml element of incorrect
    tag-type"""

    pass

class TalkbankParser(object):
    """ Parses entire CHA document.

    Maybe it should handle CA as well? Delegates actual parsing to objects that
    implement the Parser interface.

    """
    def __init__(self, *parsers):
        self.parsers = parsers

    def parse(self, filename):
        return MorParser().parse(filename)

class Parser:
    """ The Abstract Base Class for a TalkBank (sub-)parser.

    Convenience methods that are handy for general namespace-qualified XML
    parsing are defined here as well.

    """

    __metaclass__ = abc.ABCMeta
    def __init__(self, namespace="", options=None):
        self.namespace = namespace
        self.brokens = []
        self.options = options
        if self.options is None:
            self.options = []

    @abc.abstractmethod
    def parse(self, node):
        "Parses the XML-tree rooted at node into objects."

        raise NotImplementedError()

    def _qualify_path(self, path_string, namespace):
        return "/".join([self._qualify_with_namespace(i, namespace)
                         for i in path_string.split("/")])
    def _qualify_with_namespace(self, tag, namespace):
        return "%s%s" % (namespace, tag)

    def _findall(self, element, path_string):
        """ runs findall on element with a fully namespace qualified version
        of path_string"""
        return element.findall(self._qualify_path(path_string, self.namespace))

    def _find(self, element, path_string):
        """ runs find on element with a fully namespace qualified version
        of path_string"""

        return element.find(self._qualify_path(path_string, self.namespace))

    def ns(self, path):
        return self._qualify_path(path, self.namespace)

class MorParser(Parser):
    def parse_pos(self, element):
        """ Returns the pos and list of subPos found in element.

        element is an xml pos tag Element.

        """

        if element.tag != self.ns("pos"):
            raise TagTypeError("Passed non pos-tag to parse_pos")

        try:
            pos = self._find(element, "c").text
        except AttributeError:
            pos = None
        subPos = [i.text for i in self._findall(element, "s")]

        return pos, subPos

    def parse_mor_word(self, text, element):
        """ Parses a mw element into a MorToken

        args
          text: the word from the main tier
          element: the xml element of tag-type mw

        """

        if element.tag != self.ns("mw"):
            raise TagTypeError("Passed non mw-tag to parse_mor_word")

        pos, subPos = self.parse_pos(self._find(element, "pos"))
        try:
            stem = self._find(element, "stem").text
            stem = self.remove_bad_symbols(stem)
        except AttributeError:
            stem = None
        prefix = [i.text for i in self._findall(element, "mpfx")]

        suffixes = self._findall(element, "mk")
        sxfx = [i.text for i in suffixes if i.get("type") == "sxfx"]
        sfx = [i.text for i in suffixes if i.get("type") == "sfx"]

        return MorToken(prefix, text, stem, pos, subPos, sxfx, sfx)

    def parse_compound(self, text, compound):
        if compound.tag != self.ns("mwc"):
            raise TagTypeError("Passed non mwc to parse_compound")

        prefix = [i.text for i in self._findall(compound, "mpfx")]
        pos, subPos = self.parse_pos(self._find(compound, "pos"))
        words = [self.parse_mor_word("+", i)
                 for i in self._findall(compound, "mw")]
        return MorToken(prefix, text, "+".join([w.stem for w in words]),
                        pos, subPos, "", "")

    def parse_clitic(self, text, element):
        compound = self._find(element, "mwc")
        if compound is not None:
            return self.parse_compound(text, compound)
        word_elem = self._find(element, "mw")
        if word_elem is not None:
            return self.parse_mor_word(text, word_elem)

    def split_clitic_wordform(self, text):
        """ expands contracted and possesive words

        args:
          text: a word

        returns:
          A two-tuple of (base, post-clitic). This is english-centric.

        tokenization algorithm taken from:
            http://www.cis.upenn.edu/~treebank/tokenization.html
        """

        if text is None:
            return None, None
        # not sure if the s' makes sense.
        tails = ["('ll)", "('re)", "('ve)", "(n't)", "('LL)",
                 "('RE)", "('VE)", "(N'T)", r"('[sSmMdD])", "(s')$"]

        unmarked = [["([Cc])annot", r"\1na not"],
                    ["([Dd])'ye", r"\1' ye"],
                    ["([Gg])imme", r"\1im me"],
                    ["([Gg])onna", r"\1on na"],
                    ["([Gg])otta", r"\1ot ta"],
                    ["([Ll])emme", r"\1em me"],
                    ["([Mm])ore'n", r"\1or 'n"],
                    ["'([Tt])is", r"'\1 is"],
                    ["'([Tt])was", r"'\1 was"],
                    ["([Ww])anna", r"\1an na"]]

        encliticsFound = 0
        for pattern in tails + [pat for pat, word in unmarked]:
            if re.search(pattern, text):
                encliticsFound += 1
        del word

        if encliticsFound > 1:
            # HACK (maybe)
            # MOR seems to always tag multi-enclitics as unk anyway.
            return text, []

        if encliticsFound:
            for tail in tails:
                if re.search(tail, text):
                    parts = re.split(tail, text)[:-1]
            for pattern, rewrite in unmarked:
                if re.search(pattern, text):
                    parts = re.sub(pattern, rewrite, text).split(' ')
            if len(parts) > 1:
                return parts[0], parts[1:]
        return text, []

    def parse_mor_element(self, text, element):
        """ need to handle mor-pre and mor-post as well as mw """
        assert(element.tag == self.ns("mor"))
        compound = self._find(element, "mwc")
        base_word, post_clitic_words = self.split_clitic_wordform(text)

        pre_clitics = [self.parse_clitic("PRE-CLITIC", c)
                       for c in self._findall(element, "mor-pre")]
        try:
            post_clitics = [self.parse_clitic(post_clitic_words.pop(), c)
                            for c in self._findall(element, "mor-post")]
        except IndexError:
            print text
            dump(element)

            post_clitics = [self.parse_clitic("?", c)
                            for c in self._findall(element, "mor-post")]

        assert(len(post_clitics) < 2)
        if compound is not None:
            parts = pre_clitics
            parts.append(self.parse_compound(base_word, compound))
            parts += post_clitics
        else:
            parts = pre_clitics
            parts.append(self.parse_mor_word(base_word,
                                             self._find(element, "mw")))
            parts += post_clitics
        return parts

    def remove_bad_symbols(self, text):
        return re.sub(u"\u0294", "", text)
        # if text[0].encode("utf-8") == u"\u0294".encode('utf8'):  # ʔ
        #     text = text[1:]
        # return text

    def extract_word(self, mw_element):
        parts = [mw_element.text]
        for i in list(mw_element):
            if DropShorts in self.options and i.tag == self.ns("shortening"):
                parts.append(i.tail)
            else:
                parts.extend([i.text, i.tail])
        parts.append(mw_element.tail)
        parts = [p.rstrip() for p in filter(None, parts)]
        text = "".join(parts)
        text = self.remove_bad_symbols(text)
        return text

    def parseable(self, word):
        return not (word is None or len(word) == 0 or
                    word.attrib.get('type') == 'fragment')

    def parse_word(self, word):
        if word.tag == self.ns("w"):
            replacement = self._find(word, "replacement")
            if replacement:
                return [self.parse_mor_element(self.extract_word(rep_word),
                                               self._find(rep_word, "mor"))
                        for rep_word in self._findall(replacement, "w")]
            else:
                return self.parse_mor_element(self.extract_word(word),
                                              self._find(word, "mor"))
        elif word.tag == self.ns("t"):
            punct = punctuation.get(word.get("type"), "-")
            return [MorToken.punct(punct)]
        elif word.tag == self.ns("tagMarker"):
            punct = punctuation.get(word.get("type"), "-")
            return [MorToken.punct(punct)]

    def parse_utterance(self, utterance):
        uid = utterance.get("uID")
        speaker = utterance.get("who")
        words = (self.parse_word(word)
                 for word in utterance
                 if self.parseable(word))
        words = filter(None, words)  # filter out Nones
        return uid, speaker, words

    def parse(self, filename):
        doc = ElementTree(file=filename)
        for utterance in self._findall(doc, "u"):
            uid, speaker, words = self.parse_utterance(utterance)
            yield uid, speaker, list(flatten(words))

          #   elif j.tag == ns("s"):
          #     print punct(j.get("type")),
          #   elif j.tag == ns("t"):
          #     print endpunct(j.get("type")),
          # print

        # for speaker, utterance in parse_mor_tier(sys.argv[1]):
        #   print speaker, [unicode(i) for i in utterance]


    # # print "*%s:\t" % speaker , " ".join(unicode(word.word) for word in utterance if word is not None)
    # # print "%mor:\t", " ".join(unicode(word) for word in utterance)

if __name__ == "__main__":
    from sys import argv
    parser = MorParser("{http://www.talkbank.org/ns/talkbank}")
    for fn in argv[1:]:
        for uid, speaker, ut in parser.parse(fn):
            print fn, uid, speaker, ut

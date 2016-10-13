# -*- coding: utf-8 -*-

"""
Tools for parsing XML cha files

XML Parsing based on:
-  http://talkbank.org/software/xsddoc/

schema is here http://talkbank.org/software/talkbank.xsd
"""

from __future__ import print_function

import abc
import itertools
import re
from string import Template
from xml.etree.cElementTree import ElementTree

from pyparsing_mor_to_dict import parse_tag

class MorToken(object):
    "Represents an element within an utterance"

    def __init__(self, prefix, word, stem, pos, subPos, sxfx, sfx):
        self.prefix = prefix
        self.word = word
        self.stem = stem
        self.pos = pos
        self.subPos = subPos
        self.sxfx = sxfx
        self.sfx = sfx

    @classmethod
    def punct(self, char):
        return MorToken([], char, char, char, [], [], [])

    def is_punct(self):
        return self.pos in ['.', '?', '!', '-']


    template = Template("$word/$prefix$pos$subPos|$stem$sxfx$sfx")
    def _join_if_any(self, items, joiner):
        if len(items) == 0:
            return ""
        return joiner + joiner.join(items)

    def __eq__(self, other):
        keys = set(self.__dict__.keys()).union(other.__dict__.keys())
        for key in keys:
            if key == 'word':
                # FIXME: this is hacky. we don't care if the wordforms differ in
                # our specific matching case for correction application. in the
                # general case we should care. perhaps a WILDCARD singleton
                # class used as a value could signal for this case...
                continue
            if self.__dict__[key] != other.__dict__[key]:
                return False
        return True


    def __repr__(self):
        return MorToken.template.substitute(
            word=self.word,
            # prefixes have their delimiter char "#" right-appended.
            prefix='' if not self.prefix else ('#'.join(self.prefix) + '#'),
            pos=self.pos,
            subPos=self._join_if_any(self.subPos, ":"),
            stem=self.stem,
            sxfx=self._join_if_any(self.sxfx, "&"),
            sfx=self._join_if_any(self.sfx, "-"))

    def to_dict(self):
        return {
            'word': self.word,
            'prefix': self.prefix,
            'pos': self.pos,
            'subPos': self.subPos,
            'stem': self.stem,
            'fusion': self.sxfx,
            'suffix': self.sfx
            }

    @staticmethod
    def from_string(string, word=None):
        """ Construct an instance from a MOR-style string

        >>> MorToken.from_string('cooj:coo|and')
        and/cooj:coo|and
        """
        try:
            tdict = parse_tag(string)
        except:
            raise MalformedTokenString(string)

        return MorToken(
            prefix=tdict.get('prefix'),
            word=word or tdict.get('lemma'),
            stem=tdict.get('lemma'),
            pos=tdict.get('pos'),
            subPos=tdict.get('subPos', []),
            sxfx=tdict.get('fusional_suffix', []),
            sfx=tdict.get('suffix', []))

    # def __str__(self):
     #   return ("%s/%s" % (self.word, self.pos)).encode("utf8")

punctuation = {"p": ".",
               "q": "?"}

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

def prettyUtterance(words):
    """takes a list of words/tags representing one utterance and converts
    it into a single, one-line string without list punctuation
    """
    if words:
        prettystring = str(words[0])
        for word in words[1:]:
            prettystring += " " + str(word)
        return prettystring
    else:
        return ""

class MalformedTokenString(Exception):
    """ Raised by MorToken.from_string """
    pass

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
        sfxf = [i.text for i in suffixes if i.get("type") == "sfxf"]
        sfx = [i.text for i in suffixes if i.get("type") == "sfx"]

        return MorToken(prefix, text, stem, pos, subPos, sfxf, sfx)

    def parse_compound(self, text, compound):
        if compound.tag != self.ns("mwc"):
            raise TagTypeError("Passed non mwc to parse_compound")

        prefix = [i.text for i in self._findall(compound, "mpfx")]
        pos, subPos = self.parse_pos(self._find(compound, "pos"))
        words = [self.parse_mor_word("+", i)
                 for i in self._findall(compound, "mw")]
        return MorToken(prefix, text, "_".join([w.stem for w in words]),
                        pos, subPos, [], [])

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

        result = None
        if encliticsFound > 1:
            # HACK (maybe)
            # MOR seems to always tag multi-enclitics as unk anyway.
            result = text, []
        elif encliticsFound:
            for tail in tails:
                if re.search(tail, text):
                    parts = re.split(tail, text)[:-1]
            for pattern, rewrite in unmarked:
                if re.search(pattern, text):
                    parts = re.sub(pattern, rewrite, text).split(' ')
            if len(parts) > 1:
                result = parts[0], parts[1:]
            else:
                result = text, []
        else:
            result = text, []
        return result

    def parse_mor_element(self, text, element):
        """ need to handle mor-pre and mor-post as well as mw """
        if element is None:
            print("parse_mor_element(): element is None", text, element)
            return []
        assert(element.tag == self.ns("mor"))
        compound = self._find(element, "mwc")
        base_word, post_clitic_words = self.split_clitic_wordform(text)

        pre_clitics = [self.parse_clitic("PRE-CLITIC", c)
                       for c in self._findall(element, "mor-pre")]
        try:
            post_clitics = [self.parse_clitic(post_clitic_words.pop(), c)
                            for c in self._findall(element, "mor-post")]
        except IndexError:
            # this happens when there's a clitic without a wordform
            post_clitics = [self.parse_clitic("?", c)
                            for c in self._findall(element, "mor-post")]

        if len(post_clitics) > 1:
            print("too many clitics", post_clitics)

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

    def parse(self, filename):
        doc = ElementTree(file=filename)
        for utterance in self._findall(doc, "u"):
            speaker = utterance.get("who")
            uid = utterance.get("uID")

            words = []
            for word in utterance:
                if (word is None or len(word) == 0 or
                    word.attrib.get('type') == 'fragment'):
                    continue
                if word.tag == self.ns("w"):
                    replacement = self._find(word, "replacement")
                    if replacement:
                        for rep_word in self._findall(replacement, "w"):
                            words.append(self.parse_mor_element(self.extract_word(rep_word),
                                                                self._find(rep_word, "mor")))
                    else:
                        words.append(self.parse_mor_element(self.extract_word(word),
                                                            self._find(word, "mor")))
                elif word.tag == self.ns("t"):
                    punct = punctuation.get(word.get("type"), "-")
                    words.append([MorToken.punct(punct)])
                elif word.tag == self.ns("g"):
                    for sub_word in word:
                        if sub_word.tag != self.ns("w") or len(sub_word) == 0:
                            continue
                        sub_mor = self._find(sub_word, 'mor')
                        if sub_mor:
                            words.append(self.parse_mor_element(self.extract_word(sub_word),
                                                                sub_mor))
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

# if __name__ == "__main__":
#     from sys import argv
#     parser = MorParser("{http://www.talkbank.org/ns/talkbank}")
#     for fn in argv[1:]:
#         for uid, speaker, ut in parser.parse(fn):
#             print uid, speaker, prettyUtterance(ut)

if __name__ == "__main__":
    from sys import argv
    input_fn = argv[1]
    output_fn = argv[2]
    outfile = open(output_fn , 'w')
    parser = MorParser("{http://www.talkbank.org/ns/talkbank}")
    for uid, speaker, ut in parser.parse(input_fn):
        outputline = uid + ' ' + speaker + ' ' + prettyUtterance(ut) + '\n'
        outfile.writelines(outputline)

    outfile.close()

# -*- py-which-shell: "python2" -*-
import abc
import itertools
import sys
import unittest
from collections import namedtuple
from string import Template
from xml.etree.ElementTree import ElementTree, dump

import tests

class TagTypeError(Exception):
    pass

class Parser:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def parse(self, node):
        """ Parses the XML-tree rooted at node into objects.

        """

        pass

DEFAULT_NAMESPACE = ""
"{http://www.talkbank.org/ns/talkbank}"

ns = lambda x: qualify_with_namespace(x, DEFAULT_NAMESPACE)

def set_namespace(namespace):
    global DEFAULT_NAMESPACE
    DEFAULT_NAMESPACE = namespace

def qualify_with_namespace(tag, namespace):
    return "%s%s" % (namespace, tag)

def flatten(listOfLists):
    """Flatten one level of nesting
    from python.org
    """
    return itertools.chain.from_iterable(listOfLists)

def qualify_path(path_string, namespace):
    return "/".join([qualify_with_namespace(i, namespace)
                     for i in path_string.split("/")])

MT = namedtuple("MorToken", "prefix word stem pos subPos sxfx sfx")

class MorToken(MT):
    "Represents an element within an utterance"

    template = Template("$prefix$pos$subPos|$stem$sxfx$sfx")

    def _join_if_any(self, items, joiner):
        if len(items) == 0:
            return ""
        return joiner + joiner.join(items)

    def __repr__(self):
        s = MorToken.template.substitute(prefix=self._join_if_any(self.prefix, "#"),
                                         pos=self.pos,
                                         subPos=self._join_if_any(self.subPos, ":"),
                                         stem=self.stem,
                                         sxfx=self._join_if_any(self.sxfx, "&"),
                                         sfx=self._join_if_any(self.sfx, "-"))
        return unicode(s)


def findall(element, path_string, namespace=DEFAULT_NAMESPACE):
    """ runs findall on element with a fully namespace qualified version
    of path_string"""

    return element.findall(qualify_path(path_string, namespace))

def find(element, path_string, namespace=DEFAULT_NAMESPACE):
    """ runs find on element with a fully namespace qualified version
    of path_string"""

    return element.find(qualify_path(path_string, namespace))


def parse_pos(element):
    """ Returns the pos and list of subPos found in element.

    element is an xml pos tag Element.
    """

    if element.tag != ns("pos"):
        raise TagTypeError("Passed non pos-tag to parse_pos")

    try:
        pos = find(element, "c").text
    except AttributeError:
        pos = None
    subPos = [i.text for i in findall(element, "s")]

    return pos, subPos

def parse_mor_word(text, element):
    """ Parses a mw element into a MorToken

    args
      text: the word from the main tier
      element: the xml element of tag-type mw

    """

    if element.tag != ns("mw"):
        raise TagTypeError("Passed non mw-tag to parse_mor_word")

    pos, subPos = parse_pos(find(element, "pos"))
    try:
        stem = find(element, "stem").text
    except AttributeError:
        stem = None
    prefix = [i.text for i in findall(element, "mpfx")]

    suffixes = findall(element, "mk")
    sxfx = [i.text for i in suffixes if i.get("type") == "sxfx"]
    sfx = [i.text for i in suffixes if i.get("type") == "sfx"]

    return MorToken(prefix, text, stem, pos, subPos, sxfx, sfx)

def parse_compound(text, compound):
    if compound.tag != ns("mwc"):
        raise TagTypeError("Passed non mwc to parse_compound")

    prefix = [i.text for i in findall(compound, "mpfx")]
    pos, subPos = parse_pos(find(compound, "pos"))
    words = [parse_mor_word("+", i) for i in findall(compound, "mw")]
    return MorToken(prefix, text, "+".join([w.stem for w in words]),
                    pos, subPos, "", "")

def parse_clitic(text, element):
    compound = find(element, "mwc")
    if compound is not None:
        return parse_compound(text, compound)
    word_elem = find(element, "mw")
    if word_elem is not None:
        return parse_mor_word(text, word_elem)

def parse_mor_element(text, element):
    """ need to handle mor-pre and mor-post as well as mw """
    assert(element.tag == ns("mor"))
    compound = find(element, "mwc")
    pre_clitics = [parse_clitic("PRE-CLITIC", c) for c in findall(element, "mor-pre")]
    post_clitics = [parse_clitic("POST-CLITIC", c) for c in findall(element, "mor-post")]
    if compound is not None:
        parts = pre_clitics
        parts.append(parse_compound(text, compound))
        parts += post_clitics
    else:
        parts = pre_clitics
        parts.append(parse_mor_word(text, find(element, "mw")))
        parts += post_clitics
    return parts

def parse_mor_tier(filename):
    doc = ElementTree(file=filename)
    for i in findall(doc, "u"):
        print i
        speaker = i.get("who")
        words = list(flatten(parse_mor_element(j.text, find(j, "mor"))
                               for j in i if j != None and j.tag == ns("w")))
        if None in words:
            print dump(i)
            print words
            raise Exception
        yield speaker, words
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
    unittest.main(tests)

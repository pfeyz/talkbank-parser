import unittest
from os import path
from xml.etree.ElementTree import ElementTree, dump
import pdb

from talkbank_parser import MorParser


class TalkbankParserTest(unittest.TestCase):
    def setUp(self):
        self.compounds = ElementTree(file=path.join("fixtures",
                                                    "compounds.xml"))
        self.clitics = ElementTree(file=path.join("fixtures",
                                                  "clitics.xml"))
        self.utterances = ElementTree(file=path.join("fixtures",
                                                     "utterances.xml"))
    def test_compound(self):
        for word in self.compounds.findall("w/mor"):
            parser = MorParser(namespace="")
            tokens = parser.parse_mor_element(None, word)
            for token in tokens:
                self.assertGreaterEqual(token.stem.count("+"), 1)

    def test_clitics(self):
        # for word in self.clitics.findall("w/mor"):
        #     parser = MorParser(namespace="")
        #     tokens = parser.parse_mor_element(None, word)
        #     self.assertGreater(len(tokens), 1)
        #     print tokens
        parser = MorParser("{http://www.talkbank.org/ns/talkbank}")
        for i in parser.parse("fixtures/clitics.xml"):
            pass
        head, tail = parser.split_clitic_wordform("that's")
        self.assertEqual(head, "that")
        self.assertEqual(tail, ["'s"])

    def test_sentence(self):
        for word in self.compounds.findall("w/mor"):
            parser = MorParser(namespace="")
            tokens = parser.parse_mor_element(None, word)
            self.assertGreaterEqual(len(tokens), 1)

    def test_document(self):
        parser = MorParser("{http://www.talkbank.org/ns/talkbank}")
        for i in parser.parse("fixtures/test_doc.xml"):
            pass


    # @unittest.skip
    # def test_full_doc(self):
    #     parser = MorParser()
    #     print list(parser.parse("/home/paul/corpora/talkbank-xml/SBCSAE/01.xml"))

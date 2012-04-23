import unittest
from os import path
from xml.etree.ElementTree import ElementTree

from talkbank_parser import MorParser


class TalkbankParserTest(unittest.TestCase):
    def setUp(self):
        self.compounds = ElementTree(file=path.join("fixtures",
                                                    "compounds.xml"))
        # single-word utterances, all words are compounds
        self.clitics = ElementTree(file=path.join("fixtures",
                                                  "clitics.xml"))
        self.utterances = ElementTree(file=path.join("fixtures",
                                                     "utterances.xml"))
    def test_compound(self):
        for word in self.compounds.findall("w/mor"):
            parser = MorParser(namespace="")
            parts = parser.parse_mor_element(None, word)
            self.assertGreaterEqual(parts[0].stem.count("+"), 1)

    def test_clitics(self):
        parser = MorParser("{http://www.talkbank.org/ns/talkbank}")
        for speaker, tokens in parser.parse("fixtures/clitics.xml"):
            self.assertGreater(len(tokens), 1,
                               "failed splitting {0} into clitics".format(tokens))
        head, tail = parser.split_clitic_wordform("that's")
        self.assertEqual(head, "that")
        self.assertEqual(tail, ["'s"])

    def test_document(self):
        parser = MorParser("{http://www.talkbank.org/ns/talkbank}")
        for i in parser.parse("fixtures/test_doc.xml"):
            # iterate through an ensure no exceptions are thrown
            pass

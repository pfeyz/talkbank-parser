import pdb
import unittest
import talkbank_parser
from os import path
from talkbank_parser import findall, parse_mor_element
from xml.etree.ElementTree import ElementTree

talkbank_parser.set_namespace("")

class TalkbankParserTest(unittest.TestCase):
    def setUp(self):
        self.compounds = ElementTree(file=path.join("fixtures",
                                                    "compounds.xml"))
        self.clitics = ElementTree(file=path.join("fixtures",
                                                  "clitics.xml"))

    def test_compound(self):
        #pdb.set_trace()
        for word in self.compounds.findall("w/mor"):
            tokens = parse_mor_element(None, word)
            for token in tokens:
                self.assertGreaterEqual(token.stem.count("+"), 1)

    def test_clitics(self):
        for word in self.clitics.findall("w/mor"):
            tokens = parse_mor_element(None, word)
            self.assertGreater(len(tokens), 1)

"""
TODO:
- add tests for shortening
"""

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
            parser = MorParser()
            parser.namespace = ""
            parts = parser.parse_mor_element(None, word)
            self.assertGreaterEqual(parts[0].stem.count("_"), 1)

    def test_clitics(self):
        parser = MorParser()
        for uid, speaker, tokens in parser.parse("fixtures/clitics.xml"):
            self.assertGreater(len(tokens), 1,
                               "failed splitting {0} into clitics".format(tokens))
            self.assertNotIn("?", [w.word for w in tokens])
        self.assertEqual(' '.join(map(str, tokens)),
                         ("hidden/part|hide&PERF away/adv|away where/adv:wh|where "
                          "nobody/pro:indef|nobody 'd/mod|genmod be/v:cop|be ./.|."))
        head, tail = parser.split_clitic_wordform("that's")
        self.assertEqual(head, "that")
        self.assertEqual(tail, ["'s"])

    def test_document(self):
        parser = MorParser()
        for i in parser.parse("fixtures/test_doc.xml"):
            # iterate through an ensure no exceptions are thrown
            pass

    #written to test for abnormal tag reproduced in u7.xml
    def test_missing_pos(self):
        parser = MorParser()
        for uid, speaker, tokens in parser.parse("fixtures/missing_pos.xml"):

            for token in tokens:
               #print(token.word + '/' + token.pos + '|' + token.stem)
               self.assertNotEqual(token.pos, 'unk',
                                   'failed to parse known tag')
            #'''

if __name__ == "__main__":
    unittest.main()

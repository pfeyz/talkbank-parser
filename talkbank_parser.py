import sys
import pdb
from string import Template
from collections import namedtuple
from xml.etree.ElementTree import ElementTree, dump, tostring

MT = namedtuple("MorToken", "speaker prefix word stem pos subPos sxfx sfx")

class MorToken(MT):
  template = Template("$prefix$pos$subPos|$stem$sxfx$sfx")

  def _join_if_any(self, items, joiner):
    if len(items) == 0:
      return ""
    return joiner + joiner.join(items)

  def __repr__(self):
    return MorToken.template.substitute(#word=self.word,
                                        prefix=self._join_if_any(self.prefix, "#"),
                                        pos=self.pos,
                                        subPos=self._join_if_any(self.subPos, ":"),
                                        stem=self.stem,
                                        sxfx=self._join_if_any(self.sxfx, "&"),
                                        sfx=self._join_if_any(self.sfx, "-"),)

    # return "%s%s%s|%s/%s%s%s" % ("-".join(self.prefix), "#" if len(self.prefix) > 0 else "", self.stem, self.pos,
    #                             ":" if len(self.subPos) > 0 else "", ":".join(self.subPos))

ns = lambda x: "{http://www.talkbank.org/ns/talkbank}%s" % x
doc = ElementTree(file=sys.argv[1])
ptypes = {"comma": ",",
          "semicolon": ";",
          "colon": ":",}
          # "clause delimiter": "",
          # "rising to high": "",
          # "rising to mid": "",
          # "level": "",
          # "falling to mid": "",
          # "falling to low": "",
          # "unmarked ending": "",
          # "uptake": ""}

eptypes =  {"p": ".",
            "q": "?",
            "e": "!",
            "broken for coding": "",
            "trail off": "...",
            "trail off question": "...?",
            "question exclamation": "?!",
            "interruption": "-",
            "interruption question": "-",
            "self interruption": "-",
            "self interruption question": "-",}
              # "quotation next line": "",
              # "quotation precedes": "",
              # "missing CA terminator": "",
              # "technical break TCU continuation": "",
              # "no break TCU continuation": ""}


def findall(element, path_string):
  path_string = "/".join([ns(i) for i in path_string.split("/")])
  return element.findall(path_string)

def find(element, path_string):
  path_string = "/".join([ns(i) for i in path_string.split("/")])
  return element.find(path_string)


def punct(t):
  if t in ptypes:
    return ptypes[t]
  else:
    return ""

def endpunct(t):
  if t in eptypes:
    return eptypes[t]
  else:
    return ""

def parse_pos(element):
  try:
    pos = find(element, "c").text
  except AttributeError:
    pos = None
  subPos = [i.text for i in findall(element, "s")]

  return pos, subPos

def parse_mor_word(text, element, speaker):
  pos, subPos = parse_pos(find(element, "pos"))
  try:
    stem = find(element, "stem").text
  except AttributeError:
    stem = None
  prefix = [i.text for i in findall(element, "mpfx")]


  suffixes = findall(element, "mk")
  sxfx = [i.text for i in suffixes if i.get("type") == "sxfx"]
  sfx = [i.text for i in suffixes if i.get("type") == "sfx"]

  return MorToken(speaker, prefix, text, stem, pos, subPos, sxfx, sfx)

def parse_compound(text, compound, speaker):
    prefix = [i.text for i in findall(compound, "mpfx")]
    pos, subPos = parse_pos(find(compound, "pos"))
    words = [parse_mor_word("+", i, speaker) for i in findall(compound, "mw")]
    return MorToken(speaker, prefix, text, text, pos, subPos, "", "")

def make_token(text, element, speaker):
  """ need to handle mor-pre and mor-post as well as mw """
  compound = find(element, "mwc")
  if compound:
    return parse_compound(text, compound, speaker)
  else:
    return parse_mor_word(text, find(element, "mw"), speaker)


for i in findall(doc, "u"):
  speaker = i.get("who")
  print "%s:" % speaker,
  for j in i:
    if j.tag == ns("w"):
      token = make_token(j.text, find(j, "mor"), i.get("who"))
      print unicode(token),
    # if j.tag == ns("w"):
    #   token = make_token(j)

  print
  #   elif j.tag == ns("s"):
  #     print punct(j.get("type")),
  #   elif j.tag == ns("t"):
  #     print endpunct(j.get("type")),
  # print


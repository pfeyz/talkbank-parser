# Talkbank Parser

```python
from talkbank_parser import MorParser

parser = MorParser()
corpus = parser.parse("./corpora/Manchester-xml/anne/anne01a.xml")
corpus = list(corpus) # .parse() returns a generator. make it a list so
                      # we can index it for this example.

uid, speaker, utterance = corpus[15]

uid        # 'u15'
speaker    # 'MOT'
utterance  # [what/pro:int|what, 's/aux|be&3S, she/pro:sub|she, doing/part|do-PRESP, ?/?|?])

# let's look at a single word from the utterance list

word = utterance[1]

word.prefix  # []
word.word    # "'s"
word.stem    # "be"
word.pos     # "aux"
word.subPos  # []
word.sxfx    # ["3S"]
word.sfx     # []
```

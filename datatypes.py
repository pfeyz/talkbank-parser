from collections import namedtuple
from string import Template


MT = namedtuple("MorToken", "prefix word stem pos subPos sxfx sfx")
class MorToken(MT):
    "Represents an element within an utterance"

    template = Template("{$word}$prefix$pos$subPos|$stem$sxfx$sfx")
    def _join_if_any(self, items, joiner):
        if len(items) == 0:
            return ""
        return joiner + joiner.join(items)

    def __repr__(self):
        s = MorToken.template.substitute(
            word=self.word,
            prefix=self._join_if_any(self.prefix, "#"),
            pos=self.pos,
            subPos=self._join_if_any(self.subPos, ":"),
            stem=self.stem,
            sxfx=self._join_if_any(self.sxfx, "&"),
            sfx=self._join_if_any(self.sfx, "-"))

        return s.encode("utf-8")

    def __str__(self):
        return ("%s/%s" % (self.word, self.pos)).encode("utf8")

punctuation = {"p": ".",
               "q": "?"}

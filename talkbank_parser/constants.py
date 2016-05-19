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

class Punctuation:
    comma = ","
    semicolon = ";"
    colon = ":"
    # "clause delimiter": "",
    # "rising to high": "",
    # "rising to mid": "",
    # "level": "",
    # "falling to mid": "",
    # "falling to low": "",
    # "unmarked ending": "",
    # "uptake": "

class Pause:
    p = "."
    q = "?"
    e = "!"

# eptypes =  {"p": ".",
#             "q": "?",
#             "e": "!",
#             "broken for coding": "",
#             "trail off": "...",
#             "trail off question": "...?",
#             "question exclamation": "?!",
#             "interruption": "-",
#             "interruption question": "-",
#             "self interruption": "-",
#             "self interruption question": "-",}
---
              # "quotation next line": "",
              # "quotation precedes": "",
              # "missing CA terminator": "",
              # "technical break TCU continuation": "",
              # "no break TCU continuation": ""}

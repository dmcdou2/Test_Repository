import re
UA = ("Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
DEAD = re.compile(r"(not found|no longer available|page (cannot|can't) be found|404|"
                  r"listing (has )?(expired|been removed)|property (is )?(sold|no longer)|"
                  r"off[- ]market|under contract|sale pending|sold)", re.I)

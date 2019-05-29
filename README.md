

Helper for db based domain auth

# Installation

~~~~ sh
pip install spider-domainauth
~~~~

settings:

~~~~
...
INSTALLED_APPS = [
...
    spider_domainauth
...
]
~~~~

# Usage:

~~~~ python
from spider_domainauth.models import ReverseToken

# overloaded method
ReverseToken.object.create(secret="kskls")
~~~~


# TODO:
* overload other manager methods
* better examples

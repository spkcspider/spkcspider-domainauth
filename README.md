

Helper for db based domain auth

# Installation

~~~~ sh
pip install spkcspider-domainauth
~~~~

settings:

~~~~
...
INSTALLED_APPS = [
...
    spider_domainauth
...
]

DOMAINAUTH_URL = 'spider_domainauth:domainauth-db'
~~~~

# Usage:

url based:
~~~~ python
from django.conf import settings
from django.shortcuts import resolve_url

response = requests.post(
  resolve_url(settings.DOMAINAUTH_URL),
  {
    "urls": "http://foo/component/list/"
  }
)
token = response.json["tokens"]["foo"]

~~~~


Module based:
~~~~ python
from spider_domainauth.models import ReverseToken

# overloaded create method
rtoken = ReverseToken.objects.create()
"http://foo/token/list/?intent=domain&referrer={referrer}&payload={token}".format(
  referrer=resolve_url(settings.DOMAINAUTH_URL),
  token=rtoken.token
)
e.refresh_from_db()
# note: it is not token but secret, reason: token is reused and prefixed with id (for uniqueness)
e.secret

~~~~


## Other settings:

* DOMAINAUTH_RATELIMIT_FUNC: ratelimit access tries
* DOMAINAUTH_LIFETIME: token lifetime (default 1 hour) (Note: if "url based"-method is used, the token is automatically deleted afterwards)
*

# TODO:
* overload other manager methods
* better examples

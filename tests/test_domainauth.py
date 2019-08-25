
import pytest

from django.conf import settings
from django_webtest import TransactionWebTest
from django.shortcuts import resolve_url

try:
    from spkcspider.apps.spider_accounts.models import SpiderUser
    from spkcspider.apps.spider.models import AuthToken
    from spkcspider.apps.spider.signals import update_dynamic
    from spider_domainauth.models import ReverseToken
except ImportError:
    pass

# Create your tests here.


@pytest.mark.skipif(
    (
        "spkcspider.apps.spider" not in settings.INSTALLED_APPS and
        "spkcspider.apps.spider.apps.SpiderBaseConfig" not in settings.INSTALLED_APPS  # noqa: E501
    ),
    reason="requires spkcspider"
)
class TokenTest(TransactionWebTest):
    fixtures = ['test_default.json']

    def setUp(self):
        super().setUp()
        self.user = SpiderUser.objects.get(
            username="testuser1"
        )
        update_dynamic.send_robust(self)

    def test_reverse_token_manual(self):
        home = self.user.usercomponent_set.filter(name="home").first()
        self.assertTrue(home)
        self.app.set_user("testuser1")

        # try to create
        createurl = resolve_url(
            "spider_base:ucontent-add",
            **{
                "token": home.token,
                "type": "AnchorServer"
            }
        )
        form = self.app.get(createurl).forms["main_form"]
        response = form.submit().follow()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(home.contents.count(), 1)
        content = home.contents.first()
        secret = "abcdefg"
        e = ReverseToken.objects.create(assignedcontent=content)
        url = resolve_url(settings.DOMAINAUTH_URL)
        self.app.post(
            url, {
                "payload": e.token, "token": secret
            }
        )
        e.refresh_from_db()
        self.assertEqual(e.secret, secret)
        e2 = ReverseToken.objects.create(
            assignedcontent=content, secret=secret
        )
        self.assertEqual(e2.secret, secret)
        # trigger property
        secret = "abcdefgsdkldsklsdklsd"
        e2.secret = secret
        self.assertEqual(e2.secret, secret)

    def test_reverse_token_flow(self):
        home = self.user.usercomponent_set.filter(name="home").first()
        self.assertTrue(home)
        self.app.set_user("testuser1")

        # try to create
        createurl = resolve_url(
            "spider_base:ucontent-add",
            **{
                "token": home.token,
                "type": "SpiderTag"
            }
        )
        response = self.app.get(createurl)
        form = response.forms["main_form"]
        form["layout"].value = "address"
        response = form.submit().follow()
        self.assertEqual(response.status_code, 200)
        form = response.forms["main_form"]
        form["tag/name"] = "Alouis Alchemie AG"
        form["tag/place"] = "Holdenstreet"
        form["tag/street_number"] = "40C"
        form["tag/city"] = "Liquid-City"
        form["tag/post_code"] = "123456"
        form["tag/country_code"] = "de"
        response = form.submit()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(home.contents.count(), 1)
        content = home.contents.first()
        dauthurl = resolve_url(settings.DOMAINAUTH_URL)
        contenturl = "http://testserver{}".format(
            content.get_absolute_url()
        )
        body = {
            "urls": [contenturl]
        }
        response = self.app.post(
            dauthurl, body
        )
        self.assertIn(contenturl, response.json["tokens"])
        self.assertTrue(
            AuthToken.objects.filter(
                token=response.json["tokens"][contenturl]
            ).exists()
        )

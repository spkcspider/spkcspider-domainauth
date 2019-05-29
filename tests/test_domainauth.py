
from django_webtest import TransactionWebTest
from django.urls import reverse

from spkcspider.apps.spider_accounts.models import SpiderUser
from spider_domainauth.models import ReverseToken
from spkcspider.apps.spider.signals import update_dynamic

# Create your tests here.


class TokenTest(TransactionWebTest):
    fixtures = ['test_default.json']

    def setUp(self):
        super().setUp()
        self.user = SpiderUser.objects.get(
            username="testuser1"
        )
        update_dynamic.send_robust(self)

    def test_reverse_token(self):
        home = self.user.usercomponent_set.filter(name="home").first()
        self.assertTrue(home)
        self.app.set_user("testuser1")

        # try to create
        createurl = reverse(
            "spider_base:ucontent-add",
            kwargs={
                "token": home.token,
                "type": "AnchorServer"
            }
        )
        form = self.app.get(createurl).forms[0]
        response = form.submit().follow()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(home.contents.count(), 1)
        content = home.contents.first()
        secret = "abcdefg"
        e = ReverseToken.objects.create(assignedcontent=content)
        url = reverse("spider_domainauth:db-domainauth")
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
        secret = "abcdefgsdkldsklsdklsd"
        e2.secret = secret
        self.assertEqual(e2.secret, secret)

# coding=utf-8
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from oscar.apps.checkout import views
from oscar.apps.payment import forms, models
from oscar.apps.payment.models import SourceType, Source
from oscar.core.loading import get_class
from django.conf import settings
import hashlib
from urllib import quote

class EnduPaymentDetailsView(views.PaymentDetailsView):

    TPAY_URL = "https://secure.tpay.com?id=%s&kwota=%s&opis=%s&email=%s&nazwisko=%s&pow_url=%s&md5sum=%s"
    #TPAY_URL = "https://secure.tpay.com?id=%s&kwota=%s&opis=%s&email=%s&nazwisko=%s&md5sum=%s"
    TPAY_ID = "28921"
    SEC_CODE = "Lsc3I68kGnNSyKh4"

    def build_request(self,amount,order_no):
        email = self.request.user.email
        name = self.request.user.get_full_name()
        amount = str(amount)
        desc = str(order_no)

        absolute_url = self.request.build_absolute_uri(reverse('tpay:tpay-accept', kwargs={'basket_id':self.request.basket.id}))

        md5 = hashlib.md5()
        md5.update(self.TPAY_ID+str(amount)+self.SEC_CODE)
        
        request = self.TPAY_URL % (self.TPAY_ID,amount,quote(desc),email,quote(name),quote(absolute_url),md5.hexdigest())

        return request

    def handle_payment(self, order_number, total, **kwargs):

        RedirectRequired = get_class('oscar.apps.checkout.views', 'RedirectRequired')

        request = self.build_request(total.incl_tax,order_number)

        raise RedirectRequired(request)

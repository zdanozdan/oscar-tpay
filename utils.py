import hashlib
from urllib import quote
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.conf import settings

def build_tpay_request(amount,order_no,request,return_url=None):
    TPAY_URL = "https://secure.tpay.com?id=%s&kwota=%s&opis=%s&email=%s&nazwisko=%s&pow_url=%s&wyn_url=%s&md5sum=%s"

    email = request.user.email
    name = request.user.get_full_name().encode('utf-8')
    amount = str(amount)
    order_no = str(order_no)

    scheme = request.scheme
    server_name = get_current_site(request)

    confirm_url = scheme + "://" + server_name.domain + (reverse('tpay:tpay-accept', kwargs={'order_number':order_no}))

    if return_url:
        return_url = scheme + "://" + server_name.domain + return_url
    else:
        return_url = scheme + "://" + server_name.domain + (reverse('checkout:thank-you'))

    md5 = hashlib.md5()
    md5.update(settings.TPAY_ID+str(amount)+settings.TPAY_SEC_CODE)
        
    request = TPAY_URL % (settings.TPAY_ID,amount,quote(order_no),email,quote(name),quote(return_url),quote(confirm_url),md5.hexdigest())

    return request

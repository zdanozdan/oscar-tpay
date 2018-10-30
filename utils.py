import hashlib
from urllib import quote
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.conf import settings
from oscar.core.loading import get_class, get_model

Orders = get_model('order', 'Order')
TPaySourceType = get_model('payment', 'TPaySourceType')
 

def build_tpay_request(amount,order_no,request,return_url=None):
    TPAY_URL = "https://secure.tpay.com?id=%s&kwota=%s&opis=%s&email=%s&nazwisko=%s&pow_url=%s&wyn_url=%s&md5sum=%s"
    TPAY_ID = settings.TPAY_ID
    TPAY_SEC_CODE = settings.TPAY_SEC_CODE

    order = Orders.objects.get(number=order_no)
    lines = order.lines.all()
    consistentFlag = True
    consistentLast = None
    for line in lines:
        tpay = TPaySourceType.objects.get(name=line.stockrecord.source_type.name)
        if tpay:
            if consistentFlag and consistentLast and consistentLast.get_tpay_id() != tpay.get_tpay_id():
#               print "Found inconsitency in TPay - using default"
                consistentFlag = False
                TPAY_ID = settings.TPAY_ID
                TPAY_SEC_CODE = settings.TPAY_SEC_CODE
            else:
                TPAY_ID = tpay.get_tpay_id()
                TPAY_SEC_CODE = tpay.get_tpay_code()
            consistentLast = tpay
#       print str(TPAY_ID)
#       print str(TPAY_SEC_CODE)

    try:        
       email = request.user.email
       name = request.user.get_full_name().encode('utf-8')
    except:
       email = order.guest_email 
       name = email.encode('utf-8')

    amount = str(amount)
    order_no = str(order_no)
    TPAY_ID = str(TPAY_ID)
    TPAY_SEC_CODE = str(TPAY_SEC_CODE)

    scheme = request.scheme
    server_name = get_current_site(request)

    confirm_url = scheme + "://" + server_name.domain + (reverse('tpay:tpay-accept', kwargs={'order_number':order_no}))

    if return_url:
        return_url = scheme + "://" + server_name.domain + return_url
    else:
        return_url = scheme + "://" + server_name.domain + (reverse('checkout:thank-you'))

      

    md5 = hashlib.md5()
    md5.update(TPAY_ID+amount+TPAY_SEC_CODE)
        
    request = TPAY_URL % (TPAY_ID,amount,quote(order_no),email,quote(name),quote(return_url),quote(confirm_url),md5.hexdigest())

#    assert (consistentFlag != True, "Unfortunetly we do not support enrolling for events organized by diffrent parties at one step! Please remove some items from basket and try again!")

    return request

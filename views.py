#Create your views here.                                                                                                                   
import json
import requests
import logging
import hashlib
from decimal import Decimal as D

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect,HttpResponse,HttpResponseNotFound

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views.generic import View, TemplateView

from oscar.core.loading import get_class, get_model
from roll.signals import payment_received

CheckoutSessionMixin = get_class('checkout.session', 'CheckoutSessionMixin')
CheckoutSessionData = get_class('checkout.session', 'CheckoutSessionData')
PaymentDetailsView = get_class('checkout.views', 'PaymentDetailsView')
Basket = get_model('basket', 'Basket')
Orders = get_model('order', 'Order')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
TPaySourceType = get_model('payment', 'TPaySourceType')

logger = logging.getLogger()
LOGGING_PREFIX = 'tpay'

class TpayAcceptPaymentView(PaymentDetailsView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CheckoutSessionMixin, self).dispatch(request, *args, **kwargs)
    '''skip checking pre conditions, just dispatch to get or post'''

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        post = request.POST

        order_number = int(self.kwargs.get('order_number'))

        try:
            order = Orders.objects.get(number=order_number)
            logger.info('%s - accept view. ORDER ID: %s' % (LOGGING_PREFIX, order.number))
        except Exception as e:
            messages.error(request, e.message)
            return HttpResponseRedirect(reverse('basket:summary'))

        TPAY_ID = settings.TPAY_ID
        TPAY_SEC_CODE = settings.TPAY_SEC_CODE

        source_names = [l.stockrecord.source_type.name for l in order.lines.select_related().all()]

        #No split payments - all TPAY ids must be for one receiver
        try:
            test = source_names[0] #there have to be at least 1 item
            tpay_source_types = TPaySourceType.objects.filter(name__in=source_names)
            source_types_ids = [t.get_tpay_id() for t in tpay_source_types]

            def all_same(items):
                return all(x == items[0] for x in items)

            test = source_types_ids[0]
            if  all_same(source_types_ids):
                tpay = tpay_source_types[0]
                TPAY_ID = tpay.get_tpay_id()
                TPAY_SEC_CODE = tpay.get_tpay_code()
                print "Setting tpay id: (%s:%s)" % (tpay,TPAY_ID)
            else:
                print "There are different providers on this order. Unable to process payment"
                return HttpResponseNotFound()
        except:
            print "Unable to find Tpay for this lines. List is empty"
            return HttpResponseNotFound()

        # <QueryDict: {u'tr_id': [u'TR-AE9-GU2TDX'], u'tr_paid': [u'179.10'], u'tr_desc': [u'100015'], u'tr_email': [u'tomasz@enduhub.com'], u'tr_error'[u'none'], u'tr_date': [u'2017-05-11 14:29:12'], u'tr_amount': [u'179.10'], u'test_mode': [u'1'], u'tr_crc': [u''], u'tr_status': [u'TRUE'], u'md5sum': [u'7b73f39bacca881101ccaf3dcf07b07c'], u'id': [u'28921']}>                                                      

        #reverse proxy is unable to check remote address ip :-(                                                                             
        #ip = request.META.get('REMOTE_ADDR')       
        
         #check error status                                                                                                                 
        if post.get('tr_error') != 'none':
            #logger.error('%s - TPAY error (%s)' % (LOGGING_PREFIX, post.get('tr_error')))
            print('%s - TPAY error (%s)' % (LOGGING_PREFIX, post.get('tr_error')))

        # check order_number match                                                                                                          
        try:
            tpay_order_number = int(post.get('tr_desc'))
        except:
            print('%s - Unable to match order number from tr_dest field : (%s)' % (LOGGING_PREFIX, post.get('tr_desc')))
            return HttpResponseNotFound()

        if order_number != tpay_order_number:
            print('%s - ordere number (%s) does not match tr_dest field : (%s)' % (LOGGING_PREFIX, order.number,post.get('tr_dest')))
            return HttpResponseNotFound()

#check sum match
        try:
            tpay_paid = D(post.get('tr_paid'))
            tpay_amount = D(post.get('tr_amount'))
        except:
            print('%s - Unable to reead numeric values from tr_paid : (%s) and tr_amount : (%s)' % (LOGGING_PREFIX, post.get('tr_paid'),post.get('tr_amount')))
            return HttpResponseNotFound()

        # we accept any paid amount just log an error
        if order.total_incl_tax != tpay_paid:
            print('%s - order amount and paid do not match: (%s) : (%s)' % (LOGGING_PREFIX, order.total_incl_tax,tpay_paid))
            #return HttpResponseNotFound()

        #check md5 is OK                                                                                                             

        md5 = hashlib.md5()
        md5.update(TPAY_ID+post.get('tr_id')+str(tpay_paid)+post.get('tr_crc')+TPAY_SEC_CODE)

        if md5.hexdigest() != post.get('md5sum'):
            print('%s - MD5SUM does not match :  (%s)' % (LOGGING_PREFIX, md5.hexdigest()))
            return HttpResponseNotFound()

        # Payment successful! Record payment source                                                                                  
        self.handle_payment(order.number,order,tpay_paid)

        # save payment event                                                                                                         
        self.save_payment_details(order)

        #signal this order had been paid for
        payment_received.send_robust(sender=self, order=order,amount=tpay_paid)

        #just 200 OK response to make tpay happy                                                                                     
        return HttpResponse('TRUE')

    def handle_payment(self, order_number, order, tpay_paid, **kwargs):

        source_type, __ = SourceType.objects.get_or_create(name='tpay')
        #try:
        #    s = Source.objects.get(source_type=source_type,reference=str(order_number))
        #    logger.info('Order alredy paid: (%s)' % s)
        #    messages.error(self.request, _("This order is already paid"))
        #    return HttpResponseRedirect(reverse('basket:summary'))

        #except Source.MultipleObjectsReturned,e:
        #    messages.error(self.request, _("This order is already paid multiple times - this is serious error !"))
        #    messages.error(self.request, e.message)
        #    return HttpResponseRedirect(reverse('basket:summary'))

        source = Source(
            source_type=source_type,
            amount_allocated=tpay_paid,
            reference=str(order.number))

        self.add_payment_source(source)

        # Record payment event
        self.add_payment_event('tpay', tpay_paid)


# Create your views here.
import json
import requests
import logging
import hashlib
from decimal import Decimal as D

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views.generic import View, TemplateView

from oscar.core.loading import get_class, get_model

CheckoutSessionMixin = get_class('checkout.session', 'CheckoutSessionMixin')
CheckoutSessionData = get_class('checkout.session', 'CheckoutSessionData')
PaymentDetailsView = get_class('checkout.views', 'PaymentDetailsView')
Basket = get_model('basket', 'Basket')
Orders = get_model('order', 'Order')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')

logger = logging.getLogger()
LOGGING_PREFIX = 'tpay'

class TpayAcceptPaymentView(PaymentDetailsView):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(CheckoutSessionMixin, self).dispatch(request, *args, **kwargs)
        '''skip checking pre conditions, just dispatch to get or post'''
        #return super(TpayAcceptPaymentView, self).dispatch(request, *args, **kwargs)

    @method_decorator(csrf_exempt)
    def get(self, request, *args, **kwargs):

        order_number = int(self.kwargs.get('order_number'))

        try:
            order = Orders.objects.get(number=order_number)
            logger.info('%s - accept view. ORDER ID: %s' % (LOGGING_PREFIX, order.number))
        except Exception as e:
            messages.error(request, e.message)
            return HttpResponseRedirect(reverse('basket:summary'))

        # Payment successful! Record payment source
        self.handle_payment(order.number,order)

        # save payment event
        self.save_payment_details(order)

        return HttpResponseRedirect(reverse('basket:summary'))        
        
    def post(self, request, *args, **kwargs):
        post = request.POST

        logger.info('%s - accept view. Basket ID: %s POST: %s' % (LOGGING_PREFIX, self.basket_id, json.dumps(post)))

        if not self._verify_basket_id() or not self._verify_tpay_response():
            logger.error('%s - transaction incorrect' % (LOGGING_PREFIX,))
            return HttpResponseRedirect(reverse('basket:summary'))

        logger.info('%s - transaction verified. p24_session_id:  %s' % (LOGGING_PREFIX, post.get('p24_session_id')))

        submission = self.build_submission(basket=request.basket)
        return self.submit(**submission)

    def handle_payment(self, order_number, order, **kwargs):

        source_type, __ = SourceType.objects.get_or_create(name='tpay')
        try:
            s = Source.objects.get(source_type=source_type,reference=str(order_number))
            logger.info('Order alredy paid: (%s)' % s)
            messages.error(self.request, _("This order is already paid"))
            return HttpResponseRedirect(reverse('basket:summary'))
        
        except Source.MultipleObjectsReturned,e:
            messages.error(self.request, _("This order is already paid multiple times - this is serious error !"))
            messages.error(self.request, e.message)
            return HttpResponseRedirect(reverse('basket:summary'))
        
        except:
            pass

        source = Source(
            source_type=source_type,
            amount_allocated=order.total_incl_tax,
            reference=str(order.number))

        self.add_payment_source(source)

        # Record payment event
        self.add_payment_event('tpay', order.total_incl_tax)

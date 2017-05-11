from django.conf.urls import *
from django.views.decorators.csrf import csrf_exempt
from tpay.views import TpayAcceptPaymentView

app_name = 'tpay'

urlpatterns = [
    url(r'accept/(?P<order_number>\d+)/$',csrf_exempt(TpayAcceptPaymentView.as_view()),name='tpay-accept'),
    #url(r'reject/(?P<basket_id>\d+)/$',csrf_exempt(Przelewy24RejectPaymentView.as_view()),name='tpay-reject'),
    #url(r'accept-delayed/(?P<basket_id>\d+)/$',csrf_exempt(Przelewy24AcceptDelayedPaymentView.as_view()),name='tpay-accept-delayed'),
]

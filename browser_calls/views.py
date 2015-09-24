from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView
from twilio import twiml
from twilio.util import TwilioCapability

from .forms import SupportTicketForm
from .models import SupportTicket


class SupportTicketCreate(SuccessMessageMixin, CreateView):
    """Renders the home page and the support ticket form"""
    model = SupportTicket
    fields = ['name', 'phone_number', 'description']
    template_name = 'index.html'
    success_url = reverse_lazy('home')
    success_message = "Your ticket was submitted! An agent will call you soon."

@login_required(login_url=reverse_lazy('login'))
def support_dashboard(request):
    """Shows the list of support tickets to a support agent"""
    context = {}

    context['support_tickets'] = SupportTicket.objects.order_by('-timestamp')

    return render(request, 'browser_calls/support_dashboard.html', context)

def get_token(request):
    """Returns a Twilio Client token"""
    capability = TwilioCapability(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN)

    capability.allow_client_outgoing(settings.TWIML_APPLICATION_SID)

    # If the user is authenticated and on the support dashboard page,
    # we allow them to accept incoming calls to "support_user"
    if request.user.is_authenticated() and request.GET['forPage'] == reverse('dashboard'):
        capability.allow_client_incoming('support_agent')
    else:
        capability.allow_client_incoming('customer')

    token = capability.generate()

    return JsonResponse({'token': token})

@csrf_exempt
def call(request):
    """Returns TwiML instructions to Twilio's POST requests"""
    response = twiml.Response()

    with response.dial(callerId=settings.TWILIO_NUMBER) as r:
        # If the browser sent a phoneNumber param, we know this request
        # is a support agent trying to call a customer's phone
        if 'phoneNumber' in request.POST:
            r.number(request.POST['phoneNumber'])
        else:
            # Otherwise we assume this request is a customer trying
            # to contact support from the home page
            r.client('support_agent')

    return HttpResponse(str(response))
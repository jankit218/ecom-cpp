from django.contrib.messages.api import error
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.views.generic import ListView, DetailView, View

from catalog.sendmail import SendEmailService
from .models import Item, Order, OrderItem, Address, Payment, Coupon
from .forms import AddressForm, CouponForm
from csv_logger_pkg.csvlogger import csvlogger

import stripe
import json

stripe.api_key = ""
debug_mode = True

class HomeView(ListView):
    model = Item
    template_name = 'home.html'


class ProductDetail(DetailView):
    model = Item
    template_name = 'product.html'


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        # Logger library called for logging
        csv = csvlogger()
        csv.write_log("Debug", debug="OrderSummaryView - get - function Start", is_debug_mode_on=debug_mode)

        try:
            # Get order data from database
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'order': order
            }
            
            # Logger library called for logging
            csv.write_log("Debug", debug="OrderSummaryView - get - function Exit", is_debug_mode_on=debug_mode)
            
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            # ObjectDoesNotExist Exception
            messages.success(self.request, "You dont have an active order")
            csv.write_log("Error", error="ObjectDoesNotExist - You dont have an active order", is_debug_mode_on=debug_mode)
            return redirect('home')


class CheckoutView(View):
    def get(self, *args, **kwargs):
        # Logger library called for logging
        csv = csvlogger()
        csv.write_log("Debug", debug="CheckoutView - get - function Start", is_debug_mode_on=debug_mode)

        order = Order.objects.get(user=self.request.user, ordered=False)
        
        coupon_form = CouponForm()
        form = AddressForm()
        context = {
            'form': form,
            'order': order,
            'coupon_form': coupon_form,
            "DISPLAY_COUPON_FORM": True
        }
        # Logger library called for logging
        csv.write_log("Debug", debug="CheckoutView - get - function Exit", is_debug_mode_on=debug_mode)
        return render(self.request, 'checkout.html', context)

    def post(self, *args, **kwargs):
        # Logger library called for logging
        csv = csvlogger()
        csv.write_log("Debug", debug="CheckoutView - post - function Start", is_debug_mode_on=debug_mode)

        order = Order.objects.get(user=self.request.user, ordered=False)
        form = AddressForm(self.request.POST or None)

        # Verify if the form is valid
        if form.is_valid():
            street_address = form.cleaned_data.get('street_address')
            apartment_address = form.cleaned_data.get('apartment_address')
            country = form.cleaned_data.get('country')
            zip = form.cleaned_data.get('zip')
            save_info = form.cleaned_data.get('save_info')
            use_default = form.cleaned_data.get('use_default')
            payment_option = form.cleaned_data.get('payment_option')

            address = Address(
                user=self.request.user,
                street_address=street_address,
                apartment_address=apartment_address,
                country=country,
                zip=zip,
            )

            # Save Address and Order
            address.save()
            if save_info:
                address.default = True
                address.save()

            order.address = address
            order.save()

            if use_default:
                address = Address.objects.get(
                    user=self.request.user, default=True)
                order.address = address
                order.save()

            if payment_option == "S":
                return redirect('payment', payment_option="stripe")

            # Send Email using - AWS SES
            s = SendEmailService()
            s.SendMail(order.payment)
            messages.info(self.request, "Invalid payment option")
            # Logger library called for logging
            csv.write_log("Debug", debug="CheckoutView - post - function Exit", is_debug_mode_on=debug_mode)
            return redirect('checkout')
        else:
            # If form is invalid redirect to checkout
            print('form invalid')
            # Logger library called for logging
            csv.write_log("Debug", debug="CheckoutView - post - function Exit", is_debug_mode_on=debug_mode)
            return redirect('checkout')


def payment_complete(request):
    # Logger library called for logging
    csv = csvlogger()
    csv.write_log("Debug", debug="payment_complete - function Start", is_debug_mode_on=debug_mode)

    body = json.loads(request.body)
    order = Order.objects.get(
        user=request.user, ordered=False, id=body['orderID'])
    payment = Payment(
        user=request.user,
        stripe_charge_id=body['payID'],
        amount=order.get_total()
    )
    # Payment Saved
    payment.save()

    # Assign the payment to order
    order.payment = payment
    order.ordered = True
    order.save()
    messages.success(request, "Payment was successful")
    # Logger library called for logging
    csv.write_log("Debug", debug="payment_complete - function Exit", is_debug_mode_on=debug_mode)
    return redirect('home')


class PaymentView(View):
    def get(self, *args, **kwargs):
        # Logger library called for logging
        csv = csvlogger()
        csv.write_log("Debug", debug="PaymentView - get - function Start", is_debug_mode_on=debug_mode)
        order = Order.objects.get(user=self.request.user, ordered=False)

        context = {
            'order': order,
            "DISPLAY_COUPON_FORM": False

        }
        # Logger library called for logging
        csv.write_log("Debug", debug="PaymentView - get - function Exit", is_debug_mode_on=debug_mode)
        return render(self.request, 'payment.html', context)

    def post(self, *args, **kwargs):
        # Logger library called for logging
        csv = csvlogger()
        csv.write_log("Debug", debug="PaymentView - post - function Start", is_debug_mode_on=debug_mode)
        order = Order.objects.get(user=self.request.user, ordered=False)
        try:
            customer = stripe.Customer.create(
                email=self.request.user.email,
                description=self.request.user.username,
                source=self.request.POST['stripeToken']
            )
            amount = order.get_total()
            # Create stripe charge
            charge = stripe.Charge.create(
                amount=amount * 100,
                currency="usd",
                customer=customer,
                description="Test payment for buteks online",
            )
            # Create Payment request
            payment = Payment(
                user=self.request.user,
                stripe_charge_id=charge['id'],
                amount=amount
            )
            payment.save()

            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Payment was successful")
            return redirect('home')
        except stripe.error.CardError as e:
            messages.info(self.request, f"{e.error.message}")
            # Logger library called for logging
            csv.write_log("Error", error="CardError : " + str(e), is_debug_mode_on=debug_mode)
            return redirect('home')
        except stripe.error.InvalidRequestError as e:
            messages.success(self.request, "Invalid request")
            # Logger library called for logging
            csv.write_log("Error", error="InvalidRequestError : " + str(e), is_debug_mode_on=debug_mode)
            return redirect('home')
        except stripe.error.AuthenticationError as e:
            messages.success(self.request, "Authentication error")
            # Logger library called for logging
            csv.write_log("Error", error="Authentication : " + str(e), is_debug_mode_on=debug_mode)
            return redirect('home')
        except stripe.error.APIConnectionError as e:
            messages.success(self.request, "Check your connection")
            # Logger library called for logging
            csv.write_log("Error", error="APIConnectionError : " + str(e), is_debug_mode_on=debug_mode)
            return redirect('home')
        except stripe.error.StripeError as e:
            messages.success(
                self.request, "There was an error please try again")
            # Logger library called for logging
            csv.write_log("Error", error="StripeError : " + str(e), is_debug_mode_on=debug_mode)
            return redirect('home')
        except Exception as e:
            messages.success(
                self.request, "A serious error occured we were notified")
            # Logger library called for logging
            csv.write_log("Error", error="Exception : " + str(e), is_debug_mode_on=debug_mode)
            return redirect('home')


class CouponView(View):
    def post(self, *args, **kwargs):
        # Logger library called for logging
        csv = csvlogger()
        csv.write_log("Debug", debug="CouponView - post - function Start", is_debug_mode_on=debug_mode)
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            code = form.cleaned_data.get('code')
            try:
                # Add coupons
                order = Order.objects.get(user=self.request.user, ordered=False)
                order.coupon = Coupon.objects.get(code=code)
                order.save()
                messages.success(self.request, "Successfully added coupon !")
                return redirect('checkout')
            except ObjectDoesNotExist:
                # Logger library called for logging
                csv.write_log("Error", error="ObjectDoesNotExist : " + str(e), is_debug_mode_on=debug_mode)
                messages.success(self.request, "You don't have an active order")
                return redirect('home')
        messages.success(self.request, "Enter a valid coupon code")
        return redirect('checkout')



@login_required
def add_to_cart(request, slug):
    # Logger library called for logging
    csv = csvlogger()
    csv.write_log("Debug", debug="add_to_cart - function Start", is_debug_mode_on=debug_mode)
    
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False,
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.success(request, f"{item}'s quantity was updated")
            # Logger library called for logging
            csv.write_log("Debug", debug="add_to_cart function Exit", is_debug_mode_on=debug_mode)
            return redirect('order_summary')
        else:
            order.items.add(order_item)
            messages.success(request, f"{item} was added to your cart")
            # Logger library called for logging
            csv.write_log("Debug", debug="add_to_cart function Exit", is_debug_mode_on=debug_mode)
            return redirect('order_summary')

    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered=False, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.success(request, f"{item} was added to your cart")
        # Logger library called for logging
        csv.write_log("Debug", debug="add_to_cart function Exit", is_debug_mode_on=debug_mode)
        return redirect('order_summary')

    


@login_required
def remove_from_cart(request, slug):
    # Logger library called for logging
    csv = csvlogger()
    csv.write_log("Debug", debug="remove_from_cart - function Start", is_debug_mode_on=debug_mode)
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item, user=request.user, ordered=False)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            # Remove from DB 
            order.items.remove(order_item)
            order.save()
            messages.success(
                request, f"{item.title} was removed from your cart")
            # Logger library called for logging
            csv.write_log("Debug", debug="remove_from_cart function Exit", is_debug_mode_on=debug_mode)
            return redirect('order_summary')
        else:
            messages.info(request, f"{item.title} was not in your cart")
            # Logger library called for logging
            csv.write_log("Debug", debug="remove_from_cart function Exit", is_debug_mode_on=debug_mode)
            return redirect('order_summary')
    else:
        messages.info(request, "You don't have an active order!")
        # Logger library called for logging
        csv.write_log("Debug", debug="remove_from_cart function Exit", is_debug_mode_on=debug_mode)
        return redirect('order_summary')


@login_required
def remove_single_from_cart(request, slug):
    # Logger library called for logging
    csv = csvlogger()
    csv.write_log("Debug", debug="remove_single_from_cart - function Start", is_debug_mode_on=debug_mode)
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item, user=request.user, ordered=False)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # Check if item exsist
        if order.items.filter(item__slug=item.slug).exists():
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
                order.save()
            messages.success(request, f"{item}'s quantity was updated")
            # Logger library called for logging
            csv.write_log("Debug", debug="remove_single_from_cart function Exit", is_debug_mode_on=debug_mode)
            return redirect('order_summary')
        else:
            messages.info(request, f"{item.title} was not in your cart")
            # Logger library called for logging
            csv.write_log("Debug", debug="remove_single_from_cart function Exit", is_debug_mode_on=debug_mode)
            return redirect('order_summary')
    else:
        messages.info(request, "You don't have an active order!")
        # Logger library called for logging
        csv.write_log("Debug", debug="remove_single_from_cart function Exit", is_debug_mode_on=debug_mode)
        return redirect('order_summary')

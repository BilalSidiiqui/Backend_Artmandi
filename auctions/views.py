from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.db.models import Max
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from .models import ListingForm, Listing, UserListing, BiddingForm, CommentForm, Bid, Comment, Watchlist
from rest_framework import generics, permissions
from rest_framework.parsers import JSONParser
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django_filters.rest_framework import DjangoFilterBackend
from .models import User
from .models import Listing
from .serializers import WatchlistSerializer, RegisterSerializer, LoginSerializer, ListingSerializer, CommentSerializer, UserSerializer, BidSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from rest_framework.authtoken.views import ObtainAuthToken
import json




@method_decorator(csrf_exempt, name='dispatch')
class Register(APIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):    
        username = request.data['username']
        password = request.data['password']
        email = request.data['email']
        print(f"{username}, {password}, {email}" )
        confirmPassword = request.data['confirmPassword']
        if password != confirmPassword:
            return Response({"message": "Passwords must match."
            })
        
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            token, _ = Token.objects.get_or_create(user=user)
            #login(request, user)
            return Response({"message":"User saved Successfully", "token":token.key})
        except IntegrityError:
            return Response({"message": "Username already taken."
            })

            
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(ObtainAuthToken):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class= LoginSerializer
    queryset=User.objects.all()
    authentication_classes = (TokenAuthentication,)
    permission_classes = [AllowAny]
    @csrf_exempt
    def post(self,request):        
        username = request.data['username']
        password = request.data['password']
        user = authenticate(username=username, password=password)
        if user is not None:            
            if user.is_active:
                # print("here")
                
                # token, _ = Token.objects.get_or_create(user=user)
                # print(token)
                # data = {
                #     'Token':token.key
                # }
                login(request, user)
                return Response({"user_id":user.id, "username":username
                }, status=status.HTTP_200_OK)
            return Response(user,status=status.HTTP_400_BAD_REQUEST )
        return Response(user, status=status.HTTP_404_NOT_FOUND)


class Logout(APIView):
    permission_classes = [AllowAny]
    def get(self, request, format=None):
        logout(request)
        return Response({"message": "Logged out"},status=status.HTTP_200_OK)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    #authentication_classes = (TokenAuthentication,)
    permission_classes = [IsAuthenticated]
    


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id']

    def create(self, request):
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response( status=status.HTTP_201_CREATED)


    def perform_create(self, serializer):
        serializer.save(created_by= User.objects.get(pk=self.request.data['created_by']))


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['listing']
    
    

    
    def create(self, request):
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)        
        return Response( status=status.HTTP_201_CREATED)


    def perform_create(self, serializer):
        serializer.save(listing= Listing.objects.get(pk=self.request.data['listing']), 
        user= User.objects.get(pk=self.request.data['user']))


class BidViewSet(viewsets.ModelViewSet):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['listing']
    def create(self, request):
        print(request.data)
        serializer = self.get_serializer(data=request.data)
        
        serializer.is_valid(raise_exception=True)
        listing = Listing.objects.get(pk= self.request.data['listing'])
        current_bid= int(request.data['bid_price'])
        if current_bid <= listing.start_price:
            return Response({"alert": "Bid must be greater than the current price of Product "})
        all_bids = []
        all_bids = Bid.objects.values("bid_price").filter(listing = self.request.data['listing'])
        max_bid = all_bids.aggregate(Max("bid_price"))
        print(request.user)
        user = User.objects.get(pk = int(request.data['user']))
        watch = Watchlist(listing = listing, user = user)
        if all_bids.count() == 0:
            self.perform_create(serializer)
            watch.save()
            return Response(status=status.HTTP_201_CREATED)
        elif len(all_bids) == 1 and current_bid > max_bid["bid_price__max"]:
            self.perform_create(serializer)
            watch.save()
            return Response(status=status.HTTP_201_CREATED)
        elif len(all_bids) > 1 and current_bid > max_bid["bid_price__max"]:
            self.perform_create(serializer)
            watch.save()
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response({"alert": "Bid must be greater than Last Bid "}, status=status.HTTP_400_BAD_REQUEST)
        
        if current_bid <= max(all_bids):
            return Response({"alert": "Bid must be greater than the last bid "})

        self.perform_create(serializer)
        watch.save()        
        return Response( status=status.HTTP_201_CREATED)


    def perform_create(self, serializer):
        serializer.save(listing= Listing.objects.get(pk=self.request.data['listing']), 
        user= User.objects.get(pk=self.request.data['user']))


class WatchlistViewSet(viewsets.ModelViewSet):
    queryset = Watchlist.objects.all()
    serializer_class = WatchlistSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user']


def closebid(request):
    if request.method == "POST":
        listing_id = int(request.POST["listing"])
        sold = Listing.objects.get(pk = listing_id)
        sold.completed = True
        sold.save()
        all_bids = Bid.objects.filter(listing = listing_id)
        max_bid = all_bids.aggregate(Max("bid_price"))
        bid = Bid.objects.get(bid_price=max_bid["bid_price__max"])
        return JsonResponse({"bid":bid.bid_price, 
        "user":bid.user.username}, status=status.HTTP_202_ACCEPTED)
    return HttpResponse({"hi"})
        


    

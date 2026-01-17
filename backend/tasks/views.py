from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from rest_framework import viewsets, serializers, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Company, Contact, Deal, Task, Rating
from .serializers import (
    CompanySerializer, ContactSerializer, DealSerializer,
    TaskSerializer, UserSerializer, RatingSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout_view(request):
    if request.user.is_authenticated:
        request.user.auth_token.delete()
    return Response({'message': 'Logged out successfully'})


@api_view(['GET'])
def dashboard_stats(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    stats = {
        'total_contacts': Contact.objects.count(),
        'total_companies': Company.objects.count(),
        'total_deals': Deal.objects.count(),
        'total_tasks': Task.objects.count(),
        'deals_by_stage': list(Deal.objects.values('stage').annotate(count=Count('id'))),
        'total_deal_value': Deal.objects.aggregate(total=Sum('amount'))['total'] or 0,
        'won_deals_value': Deal.objects.filter(stage='won').aggregate(total=Sum('amount'))['total'] or 0,
        'pending_tasks': Task.objects.filter(status='pending').count(),
        'overdue_tasks': Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        ).count() if 'timezone' in dir() else 0,
    }
    return Response(stats)


from django.utils import timezone


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Automatically set the created_by field
        serializer.save(created_by=self.request.user)
    
    def get_queryset(self):
        queryset = Contact.objects.all()
        
        # Optional: Add search/filtering
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        return queryset
class DealViewSet(viewsets.ModelViewSet):
    queryset = Deal.objects.all()
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
# views.py - Update RatingViewSet
class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """
        Override create to check for duplicate ratings before serializer validation
        """
        contact_id = request.data.get('contact')
        
        # Check if user already rated this contact
        if contact_id:
            existing_rating = Rating.objects.filter(
                contact_id=contact_id,
                user=request.user
            ).first()
            
            if existing_rating:
                # Return existing rating with 200 OK (or 400 if you prefer)
                serializer = self.get_serializer(existing_rating)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        # No existing rating, proceed with normal creation
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Automatically set the user"""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Ensure users can only update their own ratings"""
        instance = self.get_object()
        if instance.user != self.request.user:
            raise PermissionDenied("You can only update your own ratings.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Ensure users can only delete their own ratings"""
        if instance.user != self.request.user:
            raise PermissionDenied("You can only delete your own ratings.")
        instance.delete()
    
    def get_queryset(self):
        queryset = Rating.objects.all()
        
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        if self.request.query_params.get('my_ratings') == 'true':
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Automatically set the user from the request
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        # Ensure users can only update their own ratings
        instance = self.get_object()
        if instance.user != self.request.user:
            raise PermissionDenied("You can only update your own ratings.")
        serializer.save()
    
    def get_queryset(self):
        queryset = Rating.objects.all()
        
        # Filter by contact ID
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        # Filter by current user
        if self.request.query_params.get('my_ratings') == 'true':
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
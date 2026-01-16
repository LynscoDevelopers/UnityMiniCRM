from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Company, Contact, Deal, Task, Rating


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class CompanySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    contacts_count = serializers.SerializerMethodField()
    deals_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = ['id', 'name', 'industry', 'website', 'phone', 'email', 'address',
                  'notes', 'created_at', 'updated_at', 'created_by', 'created_by_name',
                  'contacts_count', 'deals_count']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_contacts_count(self, obj):
        return obj.contacts.count()

    def get_deals_count(self, obj):
        return obj.deals.count()


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'position', 'company', 'company_name', 'notes', 'created_at',
            'updated_at', 'created_by', 'created_by_name',
            'average_rating', 'rating_count'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by', 
            'full_name', 'company_name', 'created_by_name',
            'average_rating', 'rating_count'
        ]
    
    def get_average_rating(self, obj):
        from django.db.models import Avg
        ratings = obj.ratings.all()
        if ratings.exists():
            return ratings.aggregate(Avg('rating'))['rating__avg']
        return None
    
    def get_rating_count(self, obj):
        return obj.ratings.count()
    
    def validate_email(self, value):
        """Ensure email is unique"""
        if self.instance and self.instance.email == value:
            return value
            
        if Contact.objects.filter(email=value).exists():
            raise serializers.ValidationError("A contact with this email already exists.")
        return value
    
class DealSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Deal
        fields = ['id', 'title', 'amount', 'stage', 'probability', 'expected_close_date',
                  'company', 'company_name', 'contact', 'contact_name', 'notes',
                  'created_at', 'updated_at', 'created_by', 'created_by_name']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

class TaskSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    deal_title = serializers.CharField(source='deal.title', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'priority', 'due_date',
                  'contact', 'contact_name', 'deal', 'deal_title', 'assigned_to',
                  'assigned_to_name', 'created_at', 'updated_at', 'created_by',
                  'created_by_name']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

class RatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    
    class Meta:
        model = Rating
        fields = ['id', 'contact', 'contact_name', 'user', 'user_name', 
                  'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['user', 'user_name', 'contact_name', 
                           'created_at', 'updated_at']  # Note: user is read_only
    
    def validate_rating(self, value):
        """Convert to integer and validate range"""
        try:
            rating_int = int(value)
            if rating_int < 1 or rating_int > 5:
                raise serializers.ValidationError("Rating must be between 1 and 5")
            return rating_int
        except (ValueError, TypeError):
            raise serializers.ValidationError("Rating must be an integer between 1 and 5")
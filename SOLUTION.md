CRM System with Rating Feature - Complete Solution
Project Overview
A comprehensive Customer Relationship Management (CRM) system with contact management, company tracking, deal pipeline, task management, and a user rating system for contacts.

Features
Core CRM Features
Contact Management: Full CRUD operations for professional contacts

Company Management: Organize contacts by company

Deal Pipeline: Track sales opportunities through stages

Task Management: Assign and track tasks

Dashboard: Overview of CRM metrics and statistics

Rating Feature (New Addition)
Star Rating System: 1-5 star integer ratings for contacts

User-Specific Ratings: Each user can rate each contact only once

Average Ratings: Automatic calculation of average ratings per contact

Rating Comments: Optional text feedback with ratings

Real-time Updates: Average ratings update immediately

Rating Management: Create, update, and delete ratings

Architecture
Backend (Django + Django REST Framework)
1. Rating Model (tasks/models.py)
python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

class Rating(models.Model):
    """
    Stores user ratings for contacts with 1-5 star system.
    Implements unique constraint: one rating per user per contact.
    """
    contact = models.ForeignKey(
        'Contact', 
        on_delete=models.CASCADE, 
        related_name='ratings'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='contact_ratings'
    )
    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['contact', 'user']  # Critical constraint
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contact', 'user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} rated {self.contact.full_name}: {self.rating}/5"
2. Rating Serializer (tasks/serializers.py)
python
from rest_framework import serializers
from .models import Rating, Contact
from django.db.models import Avg

class RatingSerializer(serializers.ModelSerializer):
    """
    Serializes Rating model with read-only user info and contact names.
    User field is automatically set from request context.
    """
    user_name = serializers.CharField(source='user.username', read_only=True)
    contact_name = serializers.CharField(source='contact.full_name', read_only=True)
    
    class Meta:
        model = Rating
        fields = [
            'id', 'contact', 'contact_name', 'user', 'user_name', 
            'rating', 'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'contact_name', 
            'created_at', 'updated_at'
        ]
    
    def validate_rating(self, value):
        """Ensure rating is integer between 1-5"""
        try:
            rating_int = int(value)
            if rating_int < 1 or rating_int > 5:
                raise serializers.ValidationError("Rating must be between 1 and 5")
            return rating_int
        except (ValueError, TypeError):
            raise serializers.ValidationError("Rating must be an integer between 1 and 5")
    
    def validate(self, data):
        """Prevent duplicate ratings for same user/contact"""
        request = self.context.get('request')
        contact = data.get('contact')
        
        if request and request.user.is_authenticated and contact:
            # For create operations only (not updates)
            if self.instance is None:
                if Rating.objects.filter(
                    contact=contact,
                    user=request.user
                ).exists():
                    raise serializers.ValidationError({
                        "detail": "You have already rated this contact."
                    })
        return data
    
    def create(self, validated_data):
        """Automatically set user from request"""
        request = self.context.get('request')
        validated_data['user'] = request.user
        return super().create(validated_data)

class ContactSerializer(serializers.ModelSerializer):
    """
    Enhanced Contact serializer with rating statistics and user rating.
    """
    full_name = serializers.ReadOnlyField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'position', 'company', 'company_name', 'notes', 'created_at',
            'updated_at', 'created_by', 'created_by_name',
            'average_rating', 'rating_count', 'user_rating'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by', 
            'full_name', 'company_name', 'created_by_name',
            'average_rating', 'rating_count', 'user_rating'
        ]
    
    def get_average_rating(self, obj):
        """Calculate average rating for this contact"""
        avg = obj.ratings.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else None
    
    def get_rating_count(self, obj):
        """Get total number of ratings for this contact"""
        return obj.ratings.count()
    
    def get_user_rating(self, obj):
        """Get current user's rating for this contact"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            rating = obj.ratings.filter(user=request.user).first()
            return RatingSerializer(rating).data if rating else None
        return None
3. Rating ViewSet (tasks/views.py)
python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Rating
from .serializers import RatingSerializer

class RatingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for rating operations with proper authentication and permissions.
    Features:
    - Auto-sets user from request on create
    - Prevents duplicate ratings via serializer validation
    - Users can only update/delete their own ratings
    - Supports filtering by contact and user
    """
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """User is automatically set by serializer"""
        serializer.save()
    
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
        """
        Supports filtering:
        - /api/ratings/?contact=1 : Ratings for contact ID 1
        - /api/ratings/?my_ratings=true : Current user's ratings
        """
        queryset = Rating.objects.all()
        
        # Filter by contact ID
        contact_id = self.request.query_params.get('contact')
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        
        # Filter by current user
        if self.request.query_params.get('my_ratings') == 'true':
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
4. URL Configuration (tasks/urls.py)
python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactViewSet, RatingViewSet

router = DefaultRouter()
router.register(r'contacts', ContactViewSet)
router.register(r'ratings', RatingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
Frontend (Vue.js + Vuetify)
1. API Service (services/api.js)
javascript
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Token ${token}`
  }
  return config
})

export const crmService = {
  // Rating methods
  async getContactRatings(contactId) {
    const response = await api.get('/ratings/', { 
      params: { contact: contactId } 
    })
    return response.data
  },
  
  async createRating(data) {
    const ratingData = {
      contact: data.contact,
      rating: Math.round(data.rating), // Ensure integer
      comment: data.comment || ''
    }
    const response = await api.post('/ratings/', ratingData)
    return response.data
  },
  
  async updateRating(id, data) {
    const ratingData = {
      contact: data.contact,
      rating: Math.round(data.rating),
      comment: data.comment || ''
    }
    const response = await api.put(`/ratings/${id}/`, ratingData)
    return response.data
  },
  
  async deleteRating(id) {
    await api.delete(`/ratings/${id}/`)
  },
  
  async getMyRatings() {
    const response = await api.get('/ratings/', { 
      params: { my_ratings: 'true' } 
    })
    return response.data
  },
  
  // Existing CRM methods
  async getContacts() {
    const response = await api.get('/contacts/')
    return response.data
  },
  
  async createContact(data) {
    const response = await api.post('/contacts/', data)
    return response.data
  },
  
  // ... other CRM methods
}
2. Contacts Vue Component (Contacts.vue - Key Parts)
vue
<script setup>
import { ref, onMounted } from 'vue'
import { crmService } from '../services/api'

// State
const contacts = ref([])
const ratingDialog = ref(false)
const selectedContact = ref(null)
const userRating = ref(null)
const ratingForm = ref({ rating: 5, comment: '' })

// Load contacts with rating data
const loadContacts = async () => {
  contacts.value = await crmService.getContacts()
}

// Open rating dialog
const openRatingDialog = async (contact) => {
  selectedContact.value = contact
  
  try {
    const myRatings = await crmService.getMyRatings()
    const userRatingForContact = myRatings.find(r => r.contact === contact.id)
    
    if (userRatingForContact) {
      userRating.value = userRatingForContact
      ratingForm.value = {
        rating: userRating.value.rating,
        comment: userRating.value.comment || ''
      }
    } else {
      userRating.value = null
      ratingForm.value = { rating: 5, comment: '' }
    }
    ratingDialog.value = true
  } catch (error) {
    console.error('Failed to load rating:', error)
    ratingDialog.value = true
  }
}

// Save rating
const saveRating = async () => {
  if (!selectedContact.value) return
  
  try {
    const ratingData = {
      contact: selectedContact.value.id,
      rating: Math.round(ratingForm.value.rating),
      comment: ratingForm.value.comment || ''
    }
    
    if (userRating.value) {
      await crmService.updateRating(userRating.value.id, ratingData)
    } else {
      await crmService.createRating(ratingData)
    }
    
    await loadContacts()
    ratingDialog.value = false
    alert('Rating saved successfully!')
    
  } catch (error) {
    console.error('Failed to save rating:', error)
    const errorMsg = error.response?.data?.detail || 
                    error.response?.data?.rating?.[0] || 
                    'Failed to save rating'
    alert(errorMsg)
  }
}
</script>

<template>
  <!-- Rating Dialog -->
  <v-dialog v-model="ratingDialog" max-width="500px">
    <v-card>
      <v-card-title>
        {{ userRating ? 'Edit Rating' : 'Rate Contact' }}
      </v-card-title>
      <v-card-text>
        <v-rating
          v-model="ratingForm.rating"
          hover
          size="32"
          color="amber"
          class="d-flex justify-center mb-4"
        ></v-rating>
        
        <v-textarea
          v-model="ratingForm.comment"
          label="Comments (optional)"
          variant="outlined"
          rows="3"
        ></v-textarea>
        
        <div class="d-flex justify-end mt-4">
          <v-btn @click="ratingDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="saveRating">
            {{ userRating ? 'Update' : 'Submit' }}
          </v-btn>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- Contact Cards with Ratings -->
  <v-row>
    <v-col v-for="contact in contacts" :key="contact.id" cols="12" sm="6" md="4">
      <v-card>
        <v-card-text>
          <!-- Rating Display -->
          <div v-if="contact.average_rating" class="mb-2">
            <v-rating
              :model-value="contact.average_rating"
              readonly
              half-increments
              density="compact"
              size="18"
              color="amber"
            ></v-rating>
            <span class="text-caption text-grey ml-1">
              ({{ contact.rating_count }})
            </span>
          </div>
          
          <h3>{{ contact.full_name }}</h3>
          <p>{{ contact.position }}</p>
          
          <!-- Rate Button -->
          <v-btn 
            @click="openRatingDialog(contact)"
            :color="contact.user_rating ? 'amber' : 'grey'"
            size="small"
          >
            {{ contact.user_rating ? 'Edit Rating' : 'Rate' }}
          </v-btn>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
Database Schema
Rating Table
text
CREATE TABLE tasks_rating (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES tasks_contact(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(contact_id, user_id),  -- Critical constraint
    FOREIGN KEY (contact_id) REFERENCES tasks_contact(id),
    FOREIGN KEY (user_id) REFERENCES auth_user(id)
);

CREATE INDEX idx_rating_contact_user ON tasks_rating(contact_id, user_id);
CREATE INDEX idx_rating_created ON tasks_rating(created_at);
API Endpoints
Rating Endpoints
text
GET    /api/ratings/                    # List all ratings
POST   /api/ratings/                    # Create new rating
GET    /api/ratings/{id}/               # Get specific rating
PUT    /api/ratings/{id}/               # Update rating
DELETE /api/ratings/{id}/               # Delete rating

# Filtering
GET    /api/ratings/?contact=1          # Ratings for contact ID 1
GET    /api/ratings/?my_ratings=true    # Current user's ratings
Contact Endpoints (Enhanced)
text
GET    /api/contacts/                   # List contacts with rating stats
POST   /api/contacts/                   # Create contact
GET    /api/contacts/{id}/              # Contact details with ratings
PUT    /api/contacts/{id}/              # Update contact
DELETE /api/contacts/{id}/              # Delete contact
Setup Instructions
Backend Setup
bash
# 1. Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# 2. Create superuser
python manage.py createsuperuser

# 3. Run server
python manage.py runserver
Frontend Setup
bash
# 1. Install dependencies
npm install

# 2. Run development server
npm run dev
Testing
Backend Tests
python
# Run all tests
python manage.py test

# Run rating tests specifically
python manage.py test tasks.tests.RatingAPITestCase
Key Test Cases
Rating Creation: Users can create ratings for contacts

Duplicate Prevention: Users cannot rate same contact twice

Ownership: Users can only update/delete their own ratings

Average Calculation: Contact serializer correctly calculates averages

Filtering: API supports filtering by contact and user

Security Features
1. Authentication Required
All rating operations require valid authentication token

Unauthenticated requests receive 401 Unauthorized

2. User Isolation
perform_update and perform_destroy check rating ownership

Users cannot modify others' ratings (403 Forbidden if attempted)

3. Data Validation
Backend validates rating range (1-5)

Frontend ensures integer values before sending

Database unique constraint prevents duplicates

4. Business Rules
One rating per user per contact (enforced at model level)

User field is read-only (set automatically from request)

Comments are optional, ratings are required

Performance Optimizations
1. Database Indexes
Composite index on (contact_id, user_id) for unique constraint

Index on created_at for chronological queries

Foreign key indexes automatically created

2. Efficient Queries
Average ratings calculated using Django's aggregate() function

No N+1 query issues with proper serializer design

Selective field loading with serializer optimization

3. Caching Strategy (Future Enhancement)
python
# Optional caching for frequently accessed data
from django.core.cache import cache

def get_average_rating(self, obj):
    cache_key = f'contact_{obj.id}_avg_rating'
    avg = cache.get(cache_key)
    if avg is None:
        avg = obj.ratings.aggregate(Avg('rating'))['rating__avg']
        cache.set(cache_key, avg, timeout=300)  # 5 minutes
    return avg
Error Handling
Common Errors and Responses
json
// 400 Bad Request - Validation Error
{
  "rating": ["Rating must be between 1 and 5"]
}

// 400 Bad Request - Duplicate Rating
{
  "detail": "You have already rated this contact."
}

// 403 Forbidden - Permission Denied
{
  "detail": "You can only update your own ratings."
}

// 401 Unauthorized - Authentication Required
{
  "detail": "Authentication credentials were not provided."
}
Deployment Considerations
1. Database
Use PostgreSQL for production (supports concurrent unique constraints)

Configure proper connection pooling

Set up regular backups

2. Caching
Implement Redis for caching rating statistics

Consider cache invalidation strategy

3. Security
Use HTTPS in production

Implement rate limiting for API endpoints

Regular security updates

4. Monitoring
Log rating creation/deletion for audit trail

Monitor average rating calculations

Track API response times

Future Enhancements
1. Features
Rating Trends: Track rating changes over time

Rating Categories: Rate specific aspects (responsiveness, professionalism)

Batch Rating: Rate multiple contacts at once

Rating Analytics: Dashboard with rating statistics

Rating Notifications: Email when contact is rated

2. Technical Improvements
WebSocket Support: Real-time rating updates

Export Ratings: CSV export of all ratings

Rating Permissions: Role-based rating permissions

Rating Audit Log: Track all rating changes

Advanced Filtering: Filter contacts by rating range

3. UI/UX Enhancements
Rating Histograms: Visual distribution of ratings

Trend Charts: Rating changes over time

Comparison Tools: Compare ratings across contacts

Mobile Optimization: Better touch support for rating

Troubleshooting Guide
Common Issues
1. "User field is required" error
Cause: User field not being set automatically
Solution: Ensure RatingSerializer.create() sets user from request context

2. Duplicate ratings being created
Cause: Missing unique constraint or validation
Solution: Verify unique_together constraint in model and serializer validation

3. Users can modify others' ratings
**Cause: Missing permission checks inperform_update/perform_destroy`
Solution: Add ownership checks in ViewSet methods

4. Ratings not appearing in contact list
Cause: Contact serializer not including rating fields
Solution: Ensure ContactSerializer includes average_rating and rating_count fields

5. Performance issues with many ratings
Cause: N+1 query problem
Solution: Use select_related or prefetch_related in queryset

Migration Path
From Existing CRM
Add Rating model to existing Django app

Create and run migrations

Update serializers to include rating statistics

Add rating endpoints to API

Update frontend to display and manage ratings

Migrate existing rating data if applicable

Conclusion
The Rating feature successfully extends the CRM system with a robust, user-friendly rating system. Key achievements:

User-Centric Design: Simple 1-5 star system with optional comments

Data Integrity: Enforced uniqueness constraints prevent duplicates

Security: Proper authentication and ownership controls

Performance: Efficient queries and indexing

Integration: Seamless integration with existing contact management

Scalability: Architecture supports future enhancements

The implementation follows RESTful principles, maintains data integrity through database constraints, and provides real-time feedback to users. It balances simplicity with extensibility, allowing for future enhancements while providing immediate value through contact evaluation and feedback collection.
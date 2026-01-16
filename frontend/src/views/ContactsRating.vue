<script setup>
import { ref, onMounted, computed } from 'vue'
import { crmService } from '../services/api'

const contacts = ref([])
const companies = ref([])
const loading = ref(true)
const dialog = ref(false)
const viewMode = ref('card')
const search = ref('')
const editedIndex = ref(-1)
const editedItem = ref({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  position: '',
  company: null
})

// Rating related refs
const ratingDialog = ref(false)
const selectedContactRatings = ref([])
const userRating = ref(null) // User's rating for the selected contact
const ratingForm = ref({
  rating: 5,
  comment: ''
})

const defaultItem = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  position: '',
  company: null
}

const headers = [
  { title: 'Name', key: 'full_name', sortable: true },
  { title: 'Rating', key: 'average_rating', sortable: true },
  { title: 'Email', key: 'email', sortable: true },
  { title: 'Phone', key: 'phone', sortable: false },
  { title: 'Company', key: 'company_name', sortable: true },
  { title: 'Position', key: 'position', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
]

const filteredContacts = computed(() => {
  if (!search.value) return contacts.value
  const searchLower = search.value.toLowerCase()
  return contacts.value.filter(contact =>
    contact.first_name && contact.first_name.toLowerCase().includes(searchLower) ||
    contact.last_name && contact.last_name.toLowerCase().includes(searchLower) ||
    contact.email && contact.email.toLowerCase().includes(searchLower) ||
    contact.company_name && contact.company_name.toLowerCase().includes(searchLower)
  )
})

const selectedContact = ref(null)
const showRuleForm = ref(false)
const existingRule = ref(null)

onMounted(async () => {
  await Promise.all([loadContacts(), loadCompanies()])
})

const loadContacts = async () => {
  loading.value = true
  try {
    const response = await crmService.getContacts()
    contacts.value = response.data || response
  } catch (error) {
    console.error('Failed to load contacts:', error)
  } finally {
    loading.value = false
  }
}

const loadCompanies = async () => {
  try {
    const response = await crmService.getCompanies()
    companies.value = response.data || response
  } catch (error) {
    console.error('Failed to load companies:', error)
  }
}

const viewItem = async (item) => {
  selectedContact.value = item
  await loadRule()
  await loadRatings(item.id) // Load ratings when viewing contact
}

const editItem = (item) => {
  editedIndex.value = contacts.value.indexOf(item)
  editedItem.value = Object.assign({}, item)
  dialog.value = true
}

const deleteItem = async (item) => {
  if (confirm('Are you sure you want to delete this contact?')) {
    try {
      await crmService.deleteContact(item.id)
      await loadContacts()
    } catch (error) {
      console.error('Failed to delete contact:', error)
    }
  }
}

// Rating methods
const openRatingDialog = async (contact) => {
  selectedContact.value = contact
  
  try {
    // Check if user has already rated this contact
    const ratings = await crmService.getMyRatings()
    // Filter for this specific contact
    const userRatingForContact = ratings.find(r => r.contact === contact.id)
    
    if (userRatingForContact) {
      userRating.value = userRatingForContact
      ratingForm.value = {
        rating: userRating.value.rating,
        comment: userRating.value.comment || ''
      }
    } else {
      userRating.value = null
      ratingForm.value = {
        rating: 5,
        comment: ''
      }
    }
    ratingDialog.value = true
  } catch (error) {
    console.error('Failed to load user rating:', error)
    // Still open dialog with default values
    userRating.value = null
    ratingForm.value = {
      rating: 5,
      comment: ''
    }
    ratingDialog.value = true
  }
}

const saveRating = async () => {
  if (!selectedContact.value) return
  
  try {
    const ratingData = {
      contact: selectedContact.value.id,
      rating: ratingForm.value.rating,
      comment: ratingForm.value.comment || ''  // Ensure comment is always a string
    }
    
    console.log('Sending rating data:', ratingData)
    
    if (userRating.value) {
      // Update existing rating
      const response = await crmService.updateRating(userRating.value.id, ratingData)
      console.log('Update response:', response)
    } else {
      // Create new rating
      const response = await crmService.createRating(ratingData)
      console.log('Create response:', response)
    }
    
    // Reload contacts to update ratings
    await loadContacts()
    ratingDialog.value = false
    
    // Show success message
    alert('Rating saved successfully!')
    
  } catch (error) {
    console.error('Failed to save rating:', error)
    console.error('Full error object:', error)
    console.error('Error status:', error.response?.status)
    console.error('Error data:', error.response?.data)
    console.error('Error config:', error.config)
    
    let errorMessage = 'Failed to save rating'
    if (error.response?.data) {
      if (typeof error.response.data === 'string') {
        errorMessage = error.response.data
      } else if (error.response.data.detail) {
        errorMessage = error.response.data.detail
      } else {
        // Try to format validation errors
        errorMessage = JSON.stringify(error.response.data, null, 2)
      }
    }
    alert(errorMessage)
  }
}

const loadRatings = async (contactId) => {
  if (!contactId) return
  
  try {
    const response = await crmService.getContactRatings(contactId)
    selectedContactRatings.value = response.data || response
  } catch (error) {
    console.error('Failed to load ratings:', error)
    selectedContactRatings.value = []
  }
}


const deleteRating = async (ratingId) => {
  if (confirm('Are you sure you want to delete this rating?')) {
    try {
      await crmService.deleteRating(ratingId)
      await loadContacts()
      if (selectedContact.value) {
        await loadRatings(selectedContact.value.id)
      }
      alert('Rating deleted successfully!')
    } catch (error) {
      console.error('Failed to delete rating:', error)
      alert('Failed to delete rating')
    }
  }
}

const getStars = (rating) => {
  if (!rating) return '☆☆☆☆☆'
  const fullStars = '★'.repeat(Math.floor(rating))
  const halfStar = rating % 1 >= 0.5 ? '½' : ''
  const emptyStars = '☆'.repeat(5 - Math.ceil(rating))
  return fullStars + halfStar + emptyStars
}

const getStarColor = (rating) => {
  if (rating >= 4.5) return 'amber-darken-3'
  if (rating >= 4) return 'amber'
  if (rating >= 3) return 'orange'
  if (rating >= 2) return 'deep-orange'
  return 'grey'
}

const getInitials = (firstName, lastName) => {
  const first = firstName && firstName.length > 0 ? firstName[0] : ''
  const last = lastName && lastName.length > 0 ? lastName[0] : ''
  return (first + last).toUpperCase()
}

const getAvatarColor = (index) => {
  const colors = ['primary', 'secondary', 'success', 'info', 'warning', 'purple', 'pink', 'indigo', 'teal', 'orange']
  return colors[index % colors.length]
}

const loadRule = async () => {
  if (!selectedContact.value) return
  try {
    const response = await crmService.get('/followup-rules/', { params: { contact_id: selectedContact.value.id } })
    existingRule.value = response.data[0] || null
    showRuleForm.value = false
  } catch (error) {
    console.error('Failed to load follow-up rule:', error)
    existingRule.value = null
  }
}

const deleteRule = async () => {
  if (confirm('Are you sure you want to delete this follow-up rule?')) {
    try {
      await crmService.delete(`/followup-rules/${existingRule.value.id}/`)
      await loadRule()
    } catch (error) {
      console.error('Failed to delete rule:', error)
    }
  }
}

const close = () => {
  dialog.value = false
  setTimeout(() => {
    editedItem.value = Object.assign({}, defaultItem)
    editedIndex.value = -1
  }, 300)
}

const save = async () => {
  try {
    if (editedIndex.value > -1) {
      await crmService.updateContact(editedItem.value.id, editedItem.value)
    } else {
      await crmService.createContact(editedItem.value)
    }
    await loadContacts()
    close()
  } catch (error) {
    console.error('Failed to save contact:', error)
  }
}
</script>


<template>
  <v-container fluid class="pa-6">
    <v-row>
      <v-col cols="12">
        <div class="d-flex justify-space-between align-center mb-6 flex-wrap gap-3">
          <div>
            <h1 class="text-h3 font-weight-bold text-navy mb-2">Scoreboard</h1>
            <p class="text-h6 text-grey-darken-1">Rate interactions and track relationship value</p>
          </div>
          
        </div>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card elevation="2" class="mb-4">
          <v-card-text class="pa-4">
            <div class="d-flex align-center gap-3 flex-wrap">
              <v-text-field
                v-model="search"
                prepend-inner-icon="mdi-magnify"
                label="Search contacts..."
                variant="outlined"
                density="compact"
                hide-details
                clearable
                class="flex-grow-1"
                style="max-width: 400px;"
              ></v-text-field>
              <v-spacer></v-spacer>
              <v-btn-toggle v-model="viewMode" mandatory variant="outlined" divided density="compact">
                <v-btn value="card" size="small"><v-icon>mdi-view-grid</v-icon></v-btn>
                <v-btn value="table" size="small"><v-icon>mdi-view-list</v-icon></v-btn>
              </v-btn-toggle>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="loading">
      <v-col cols="12" class="text-center py-12">
        <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
      </v-col>
    </v-row>

    <v-row v-else-if="viewMode === 'card'">
      <v-col v-for="(contact, index) in filteredContacts" :key="contact.id" cols="12" sm="6" md="4" lg="3">
        <v-card elevation="3" class="contact-card h-100" hover>
          <v-card-text class="pa-4 text-center">
            <v-avatar :color="getAvatarColor(index)" size="64" class="mb-3">
              <span class="text-h5 font-weight-bold text-white">
                {{ getInitials(contact.first_name, contact.last_name) }}
              </span>
            </v-avatar>
            
            <!-- Rating stars -->
            <div class="mb-2" v-if="contact.average_rating">
              <v-rating
                v-model="contact.average_rating"
                readonly
                half-increments
                density="compact"
                size="18"
                color="amber"
                class="d-inline-flex"
              ></v-rating>
              <span class="text-caption text-grey ml-1">
                ({{ contact.rating_count || 0 }})
              </span>
            </div>
            <div v-else class="mb-2">
              <span class="text-caption text-grey">No ratings yet</span>
            </div>
            
            <h3 class="text-h6 font-weight-bold mb-1">{{ contact.first_name }} {{ contact.last_name }}</h3>
            <p class="text-caption text-grey mb-3">{{ contact.position || 'No position' }}</p>
            
            <v-divider class="my-3"></v-divider>
            
            <div class="contact-details text-left">
              <div class="d-flex align-center mb-2" v-if="contact.company_name">
                <v-icon size="small" class="mr-2" color="grey-darken-1">mdi-office-building</v-icon>
                <span class="text-caption font-weight-medium">{{ contact.company_name }}</span>
              </div>
              <div class="d-flex align-center mb-2" v-if="contact.email">
                <v-icon size="small" class="mr-2" color="grey-darken-1">mdi-email</v-icon>
                <span class="text-caption text-truncate">{{ contact.email }}</span>
              </div>
              <div class="d-flex align-center" v-if="contact.phone">
                <v-icon size="small" class="mr-2" color="grey-darken-1">mdi-phone</v-icon>
                <span class="text-caption">{{ contact.phone }}</span>
              </div>
            </div>
          </v-card-text>
          <v-card-actions class="pa-3 pt-0">
            <v-btn size="small" variant="text" color="info" prepend-icon="mdi-eye" @click="viewItem(contact)">
              View
            </v-btn>
            <v-btn size="small" variant="text" color="amber" prepend-icon="mdi-star" @click="openRatingDialog(contact)">
              {{ contact.user_rating ? 'Edit Rating' : 'Rate' }}
            </v-btn>
            <v-spacer></v-spacer>
           
            <v-btn size="small" variant="text" color="error" icon="mdi-delete" @click="deleteItem(contact)"></v-btn>
          </v-card-actions>
        </v-card>
      </v-col>

      <v-col v-if="filteredContacts.length === 0" cols="12">
        <v-card elevation="2" class="pa-12">
          <div class="text-center">
            <v-icon size="64" color="grey-lighten-1" class="mb-4">mdi-account-outline</v-icon>
            <h3 class="text-h5 mb-2 text-grey-darken-1">No contacts found</h3>
            <p class="text-body-2 text-grey mb-4">
              {{ search ? 'Try adjusting your search' : 'Get started by adding your first contact' }}
            </p>
            <v-btn v-if="!search" color="primary" @click="dialog = true" prepend-icon="mdi-plus">Add Contact</v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-else>
      <v-col cols="12">
        <v-card elevation="3">
          <v-data-table :headers="headers" :items="filteredContacts" :loading="loading" items-per-page="15">
            <template v-slot:item.full_name="{ item, index }">
              <div class="d-flex align-center py-2">
                <v-avatar :color="getAvatarColor(index)" size="36" class="mr-3">
                  <span class="text-caption font-weight-bold text-white">
                    {{ getInitials(item.first_name, item.last_name) }}
                  </span>
                </v-avatar>
                <div>
                  <span class="font-weight-medium">{{ item.first_name }} {{ item.last_name }}</span>
                  <div v-if="item.average_rating" class="d-flex align-center mt-1">
                    <v-rating
                      :model-value="item.average_rating"
                      readonly
                      half-increments
                      density="compact"
                      size="14"
                      color="amber"
                    ></v-rating>
                    <span class="text-caption text-grey ml-1">({{ item.average_rating.toFixed(1) }})</span>
                  </div>
                </div>
              </div>
            </template>
            <template v-slot:item.average_rating="{ item }">
              <div class="d-flex align-center">
                <v-rating
                  v-if="item.average_rating"
                  :model-value="item.average_rating"
                  readonly
                  half-increments
                  density="compact"
                  size="16"
                  color="amber"
                ></v-rating>
                <span v-else class="text-grey">No ratings</span>
                <v-btn
                  v-if="item.user_rating"
                  icon="mdi-pencil"
                  size="x-small"
                  variant="text"
                  color="amber"
                  class="ml-2"
                  @click="openRatingDialog(item)"
                ></v-btn>
              </div>
            </template>
            <template v-slot:item.company_name="{ item }">
              <v-chip v-if="item.company_name" size="small" variant="tonal" prepend-icon="mdi-office-building">
                {{ item.company_name }}
              </v-chip>
              <span v-else class="text-grey">-</span>
            </template>
            <template v-slot:item.actions="{ item }">
              <v-icon size="small" class="mr-2" @click="viewItem(item)" color="info">mdi-eye</v-icon>
              <v-icon size="small" class="mr-2" @click="openRatingDialog(item)" color="amber">mdi-star</v-icon>
              <v-icon size="small" class="mr-2" @click="editItem(item)" color="primary">mdi-pencil</v-icon>
              <v-icon size="small" @click="deleteItem(item)" color="error">mdi-delete</v-icon>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- Rating Dialog -->
    <v-dialog v-model="ratingDialog" max-width="500px">
      <v-card>
        <v-card-title class="pa-4 bg-grey-lighten-4">
          <div class="d-flex align-center">
            <v-icon class="mr-2" color="amber">mdi-star</v-icon>
            <span class="text-h6 font-weight-bold">
              {{ userRating ? 'Edit Rating' : 'Rate Contact' }}
            </span>
          </div>
        </v-card-title>
        <v-divider></v-divider>
        <v-card-text class="pa-6">
          <div v-if="selectedContact" class="text-center mb-6">
            <v-avatar :color="getAvatarColor(0)" size="64" class="mb-3">
              <span class="text-h5 font-weight-bold text-white">
                {{ getInitials(selectedContact.first_name, selectedContact.last_name) }}
              </span>
            </v-avatar>
            <h3 class="text-h6 font-weight-bold">{{ selectedContact.first_name }} {{ selectedContact.last_name }}</h3>
            <p class="text-caption text-grey">{{ selectedContact.position || 'No position' }}</p>
          </div>
          
          <v-form @submit.prevent="saveRating">
            <v-rating
              v-model="ratingForm.rating"
              hover
              half-increments
              size="32"
              color="amber"
              class="d-flex justify-center mb-4"
            ></v-rating>
            
            <v-textarea
              v-model="ratingForm.comment"
              label="Comments (optional)"
              variant="outlined"
              rows="3"
              auto-grow
              prepend-inner-icon="mdi-comment"
            ></v-textarea>
            
            <div class="d-flex justify-end mt-4">
              <v-btn color="grey" variant="text" @click="ratingDialog = false" class="mr-2">Cancel</v-btn>
              <v-btn color="primary" type="submit" variant="flat">
                {{ userRating ? 'Update Rating' : 'Submit Rating' }}
              </v-btn>
              <v-btn
                v-if="userRating"
                color="error"
                variant="text"
                @click="deleteRating(userRating.id)"
                class="ml-2"
              >
                Delete
              </v-btn>
            </div>
          </v-form>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Existing Details Dialog with Follow-Up Integration -->
    <v-dialog v-model="selectedContact" max-width="700px" persistent>
      <v-card>
        <v-card-title class="pa-4 bg-grey-lighten-4">
          <div class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-account-details</v-icon>
            <span class="text-h6 font-weight-bold">{{ selectedContact?.first_name }} {{ selectedContact?.last_name }}</span>
            <v-spacer></v-spacer>
            <v-btn color="amber" variant="tonal" @click="openRatingDialog(selectedContact)" prepend-icon="mdi-star">
              {{ selectedContact?.user_rating ? 'Edit Rating' : 'Rate Contact' }}
            </v-btn>
          </div>
        </v-card-title>
        <v-divider></v-divider>
        <v-card-text class="pa-6">
          <v-container>
            <!-- Rating Summary -->
            <v-row class="mb-4">
              <v-col cols="12">
                <v-card variant="outlined" class="pa-4">
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-h4 font-weight-bold">
                        {{ selectedContact?.average_rating?.toFixed(1) || '0.0' }}
                        <span class="text-h6 text-grey">/5</span>
                      </div>
                      <v-rating
                        v-if="selectedContact?.average_rating"
                        :model-value="selectedContact.average_rating"
                        readonly
                        half-increments
                        density="compact"
                        size="20"
                        color="amber"
                        class="d-inline-flex"
                      ></v-rating>
                      <span v-else class="text-grey">No ratings yet</span>
                      <div class="text-caption text-grey mt-1">
                        Based on {{ userRating || 0 }} ratings
                      </div>
                    </div>
                    <v-btn color="amber" @click="openRatingDialog(selectedContact)" prepend-icon="mdi-star">
                      {{ selectedContact?.user_rating ? 'Edit Your Rating' : 'Add Rating' }}
                    </v-btn>
                  </div>
                </v-card>
              </v-col>
            </v-row>

            <v-row>
              <v-col cols="12" sm="6">
                <strong>Email:</strong> {{ selectedContact?.email || '-' }}
              </v-col>
              <v-col cols="12" sm="6">
                <strong>Phone:</strong> {{ selectedContact?.phone || '-' }}
              </v-col>
              <v-col cols="12" sm="6">
                <strong>Position:</strong> {{ selectedContact?.position || '-' }}
              </v-col>
              <v-col cols="12" sm="6">
                <strong>Company:</strong> {{ selectedContact?.company_name || '-' }}
              </v-col>
            </v-row>
          </v-container>

          <!-- Recent Ratings -->
          <v-expansion-panels class="mt-6">
            <v-expansion-panel title="Recent Ratings" elevation="1">
              <v-expansion-panel-text>
                <div v-if="selectedContactRatings.length > 0">
                  <v-list>
                    <v-list-item
                      v-for="rating in selectedContactRatings"
                      :key="rating.id"
                      class="mb-2"
                    >
                      <template v-slot:prepend>
                        <v-avatar size="36" color="grey-lighten-3">
                          <span class="text-caption font-weight-bold">
                            {{ getInitials(rating.user_name || '', '') }}
                          </span>
                        </v-avatar>
                      </template>
                      <v-list-item-title class="font-weight-medium">
                        {{ rating.user_name }}
                      </v-list-item-title>
                      <v-list-item-subtitle>
                        <v-rating
                          :model-value="rating.rating"
                          readonly
                          density="compact"
                          size="14"
                          color="amber"
                          class="d-inline-flex"
                        ></v-rating>
                        <span class="text-caption text-grey ml-2">
                          {{ new Date(rating.created_at).toLocaleDateString() }}
                        </span>
                      </v-list-item-subtitle>
                      <v-list-item-subtitle v-if="rating.comment" class="mt-1">
                        {{ rating.comment }}
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </div>
                <div v-else class="text-center py-4">
                  <v-icon size="48" color="grey-lighten-1" class="mb-2">mdi-star-outline</v-icon>
                  <p class="text-grey">No ratings yet</p>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <!-- Existing Follow-Up Automation Section -->
          <v-expansion-panels class="mt-6">
            <v-expansion-panel title="Follow-Up Automation" elevation="1">
              <v-expansion-panel-text>
                <FollowUpRuleForm 
                  v-if="showRuleForm" 
                  :contactId="selectedContact?.id" 
                  :rule="existingRule" 
                  @success="loadRule" 
                  @cancel="showRuleForm = false" 
                />
                <v-btn v-else color="primary" @click="showRuleForm = true">
                  {{ existingRule ? 'Edit Rule' : 'Add Rule' }}
                </v-btn>
                <v-btn v-if="existingRule" color="error" class="ml-2" @click="deleteRule">Delete Rule</v-btn>
                <div v-if="existingRule" class="mt-4">
                  <p><strong>Inactivity Days:</strong> {{ existingRule.inactivity_days }}</p>
                  <p><strong>Reminder Template:</strong> {{ existingRule.reminder_template }}</p>
                  <p><strong>Enabled:</strong> {{ existingRule.enabled ? 'Yes' : 'No' }}</p>
                </div>
                <p v-else class="text-grey mt-4">No follow-up rule configured for this contact.</p>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="selectedContact = null; showRuleForm = false" size="large">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Existing Add/Edit Contact Dialog -->
    <v-dialog v-model="dialog" max-width="700px" persistent>
      <!-- ... existing contact dialog code ... -->
    </v-dialog>
  </v-container>
</template>

<style scoped>
.contact-card {
  transition: all 0.3s ease;
  border-top: 4px solid transparent;
}

.contact-card:hover {
  transform: translateY(-4px);
  border-top-color: rgb(var(--v-theme-primary));
}

.contact-details {
  min-height: 72px;
}

.text-navy {
  color: #1a237e;
}

.rating-stars {
  display: inline-flex;
  align-items: center;
}
</style>

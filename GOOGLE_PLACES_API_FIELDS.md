# Google Places API - Additional Fields for LineUp

## Currently Using ✅
- `name`
- `formatted_address`
- `formatted_phone_number`
- `opening_hours`
- `website`
- `price_level`
- `rating`
- `user_ratings_total`
- `photos`

## Highly Useful for Barbershop Platform

### 1. **Reviews & Feedback** (Enterprise SKU)
```
fields: ...,reviews,review_summary
```
- **`reviews`**: Array of user reviews with:
  - Author name
  - Rating (1-5 stars)
  - Review text
  - Timestamp
  - Profile photo
- **`review_summary`**: AI-generated summary of all reviews
- **Use case**: Display real customer reviews on your platform

### 2. **Business Status** (Pro SKU)
```
fields: ...,business_status
```
- **`business_status`**: `OPERATIONAL`, `CLOSED_TEMPORARILY`, `CLOSED_PERMANENTLY`
- **Use case**: Show if barbershop is currently open/closed

### 3. **Current vs Regular Hours** (Enterprise SKU)
```
fields: ...,current_opening_hours,regular_opening_hours
```
- **`current_opening_hours`**: Today's actual hours (handles holidays, special hours)
- **`regular_opening_hours`**: Standard weekly hours
- **Use case**: More accurate "open now" status, show if closed for holiday

### 4. **Phone Numbers** (Enterprise SKU)
```
fields: ...,international_phone_number,national_phone_number
```
- **`international_phone_number`**: Full international format (+1-555-123-4567)
- **`national_phone_number`**: National format
- **Use case**: Better phone number formatting

### 5. **Place Descriptions** (Enterprise + Atmosphere SKU)
```
fields: ...,editorial_summary,generative_summary
```
- **`editorial_summary`**: Curated description of the place
- **`generative_summary`**: AI-generated summary from reviews
- **Use case**: Rich descriptions for barbershop profiles

### 6. **Payment Options** (Enterprise + Atmosphere SKU)
```
fields: ...,payment_options
```
- **`payment_options`**: Array of accepted payment methods:
  - `CASH`, `CREDIT_CARD`, `DEBIT_CARD`, `DIGITAL_WALLET`, etc.
- **Use case**: Show what payment methods each barber accepts

### 7. **Accessibility** (Pro SKU)
```
fields: ...,accessibility_options
```
- **`accessibility_options`**: Features like wheelchair accessible, accessible parking
- **Use case**: Help users find accessible barbershops

### 8. **Address Components** (Essentials SKU)
```
fields: ...,address_components
```
- **`address_components`**: Breakdown of address:
  - Street number, route, city, state, postal code, country
- **Use case**: Better location filtering (by city, ZIP code, etc.)

### 9. **Google Maps Links** (Pro SKU)
```
fields: ...,google_maps_uri,google_maps_links
```
- **`google_maps_uri`**: Direct Google Maps URI
- **`google_maps_links`**: Object with different map link types
- **Use case**: Alternative to manually constructing URLs

### 10. **Price Range** (Enterprise SKU)
```
fields: ...,price_range
```
- **`price_range`**: Detailed price range info
- **Use case**: More accurate pricing data than `price_level`

## Cost Considerations

**SKU Tiers:**
- **Essentials**: Basic fields (cheapest)
- **Pro**: Enhanced fields (moderate cost)
- **Enterprise**: Advanced fields (higher cost)
- **Enterprise + Atmosphere**: Full features (most expensive)

**Cost Optimization Tip**: Only request fields you actually use! Each field adds to API cost.

## Recommended Additions for LineUp

Based on your platform needs, I'd recommend adding:

1. **High Priority:**
   - `business_status` - Show if shop is operational
   - `current_opening_hours` - Better "open now" accuracy
   - `address_components` - Better location filtering

2. **Medium Priority:**
   - `reviews` - Display real customer reviews
   - `payment_options` - Show accepted payment methods
   - `editorial_summary` or `generative_summary` - Rich descriptions

3. **Nice to Have:**
   - `accessibility_options` - Accessibility features
   - `international_phone_number` - Better phone formatting

## Example Updated Request

```python
details_params = {
    'place_id': place['place_id'],
    'fields': 'name,formatted_address,formatted_phone_number,international_phone_number,opening_hours,current_opening_hours,regular_opening_hours,website,price_level,price_range,rating,user_ratings_total,photos,business_status,address_components,payment_options,editorial_summary,reviews,review_summary,accessibility_options',
    'key': GOOGLE_PLACES_API_KEY
}
```

**Note**: Not all fields are available for all places. Always check if fields exist before using them.


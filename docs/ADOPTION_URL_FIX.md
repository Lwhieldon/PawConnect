# Adoption URL Fix

## Problem

When users interacted with the PawConnect AI agent through ADK web interface, the adoption URLs returned were dead links:
```
https://rescuegroups.org/animal/10552500
```

These URLs returned 404 errors and didn't work.

## Root Cause

The application was constructing adoption URLs using only the animal's external ID in the format:
```
https://rescuegroups.org/animal/{id}
```

However, RescueGroups.org uses a different URL structure that requires the animal's slug field.

## Solution

### Changes Made

#### 1. Updated `pawconnect_ai/utils/helpers.py`
- Added capture of the `slug` field from RescueGroups API response
- Added slug to the pet_data dictionary that gets parsed from API responses

```python
# Get slug for URL construction
slug = animal.get("slug")

pet_data = {
    ...
    "slug": slug,  # Add slug for URL construction
    ...
}
```

#### 2. Updated `pawconnect_ai/schemas/pet_data.py`
- Added `slug` field to the Pet model schema

```python
slug: Optional[str] = Field(
    default=None,
    description="URL slug for pet listing page"
)
```

#### 3. Updated `pawconnect_ai/agent.py` (Final Solution)
- **Removed RescueGroups URL generation** - RescueGroups doesn't have a standardized public URL format
- Only use shelter's own website when available
- Updated system instructions to direct users to contact information when no URL is available

```python
# Construct adoption URL - only use shelter's website if available
# Note: RescueGroups doesn't have a standardized public URL format
# Each organization has their own subdomain or custom website
adoption_url = None
if pet.shelter and hasattr(pet.shelter, 'website') and pet.shelter.website:
    adoption_url = str(pet.shelter.website)
```

### URL Format - Final Approach

After testing multiple approaches, the solution is:

1. **ONLY use shelter's website URL** when available
2. **If no website URL**: Direct users to contact the shelter using provided contact information (phone, email, address)
3. **Why this works**:
   - RescueGroups doesn't provide standardized public URLs for individual pets
   - Each rescue organization using RescueGroups has their own subdomain or custom website
   - The API doesn't provide the organization's subdomain information
   - Shelter websites are the most reliable source for adoption information

#### 4. Added Pet Photo Display Support
- Updated system instructions to enable photo display via markdown
- Modified `get_rescue_contact()` function to include `photo_url` in results
- Agent now displays pet photos using markdown syntax: `![Pet Name](photo_url)`

```python
# In get_rescue_contact function
contact_info = {
    "pet_name": pet.name,
    "pet_breed": pet.breed or "Mixed Breed",
    "pet_age": pet.age.value if hasattr(pet.age, 'value') else str(pet.age),
    "pet_description": pet.description[:200] + "..." if len(pet.description) > 200 else pet.description,
    "photo_url": str(pet.primary_photo_url) if pet.primary_photo_url else None,
    # ... contact information
}
```

## Testing

The changes have been tested and verified:

```bash
# Run tests
python -m pytest tests/unit/test_vision_agent.py -v
```

All tests pass successfully.

## How to Verify

After restarting the ADK web server, verify the following:

```bash
# Restart the server
adk web
```

Then interact with the agent and verify:

1. **Adoption URLs**:
   - When available, adoption URLs should link to the shelter's website
   - When not available, agent should provide contact information instead

2. **Pet Photos**:
   - Ask "Can you show me a picture of [Pet Name]?"
   - Agent should display the photo directly using markdown
   - Photo should be visible in the web interface

3. **Contact Information**:
   - Ask about scheduling appointments
   - Agent should provide phone, email, website, and address

## Notes

- The shelter's website URL is the ONLY adoption URL provided (when available)
- If no shelter website URL is available, users are directed to contact information
- RescueGroups doesn't provide standardized public pet listing URLs that work across all organizations
- Pet photos are now displayable directly in the agent interface
- All search results include complete shelter contact information (phone, email, address, website)

## Opening Links in New Tabs

**For Users:**
- Right-click any adoption link and select "Open link in new tab"
- Or hold Ctrl (Windows/Linux) or Cmd (Mac) while clicking

**For Developers:**
- The ADK web interface renders markdown links as standard HTML `<a>` tags
- Opening in new tabs is controlled by user behavior (right-click, Ctrl+click)
- The agent's system instructions now remind users about this option

**Technical Note:**
Standard markdown doesn't support `target="_blank"`. To have all external links open in new tabs automatically, you would need to:
1. Modify the ADK web interface's markdown renderer
2. Add a post-processing step to add `target="_blank"` to external links
3. Or use a different markdown rendering library that supports this

## Related Files

- `pawconnect_ai/utils/helpers.py:396` - Slug capture
- `pawconnect_ai/schemas/pet_data.py:160` - Slug field definition
- `pawconnect_ai/agent.py:583-596` - URL construction logic

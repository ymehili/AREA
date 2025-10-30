# 📖 Marketplace User Guide

## How to Use the Workflow Marketplace

The AREA Marketplace allows you to **share your automations with the community** and **discover pre-built workflows** created by other users.

---

## 🗺️ Accessing the Marketplace

### Option 1: Navigation Menu
1. Log in to your AREA account
2. Click **"Marketplace"** in the top navigation menu
3. Browse all published templates

### Option 2: Direct URL
- Navigate to: **http://localhost:3000/marketplace**
- No authentication required for browsing (public access)

---

## 📚 Browsing Templates

### Search & Filter
On the marketplace page, you can:

1. **Search by keyword** - Type in the search bar (e.g., "email", "github")
   - Search is debounced (500ms delay)
   - Searches template titles and descriptions

2. **Filter by Category** - Select from dropdown:
   - Productivity
   - Communication
   - Development
   - Social Media
   - Utilities
   - etc.

3. **Filter by Tags** - Multi-select tags:
   - Select multiple tags to narrow results
   - Click X on selected tags to remove filters

4. **Sort Results**:
   - Most Popular (by usage count)
   - Newest (recently published)
   - Highest Rated
   - Title (A-Z or Z-A)

### Template Cards
Each card shows:
- **Title** - Template name
- **Description** - What the automation does
- **Category Badge** - Template category
- **Tags** - First 3 tags (+ overflow count)
- **Stats**:
  - 👥 Usage count (how many times cloned)
  - 📋 Clone count
  - ⭐ Average rating (if rated)

Click any card to view full details.

---

## 🔍 Viewing Template Details

### Template Detail Page
URL: `/marketplace/{template-id}`

Shows:
- **Full description** - Detailed explanation
- **Long description** - Setup instructions, use cases
- **Tags** - All associated tags
- **Statistics**:
  - Usage count
  - Clone count
  - Average rating
  - Published date
- **Workflow Structure** - Visual preview of:
  - Trigger (what starts the automation)
  - Actions (what happens when triggered)
  - Additional steps

### Clone Button
- Large "Clone Template" button
- Opens dialog with:
  - **Automation Name** field (pre-filled with "Clone of {title}")
  - Optional parameter overrides
- Requires authentication

---

## 📤 Publishing Your Workflow to Marketplace

### Step 1: Create & Test Your Workflow
1. Go to **Dashboard**
2. Create an automation using Simple Wizard or Advanced Builder
3. Test it to ensure it works correctly

### Step 2: Publish to Marketplace

**Method 1: From Dashboard**
1. Navigate to **Dashboard**
2. Find the workflow you want to publish
3. Click the **"Publish to Marketplace"** button (with share icon)
4. You'll be redirected to the publish form

**Method 2: Direct Navigation**
1. Navigate to **http://localhost:3000/marketplace/publish**
2. Select a workflow from the dropdown

### Step 3: Fill Publishing Form

Required fields:
1. **Automation to Publish** (dropdown)
   - Select from your existing workflows
   
2. **Template Title** (10-255 characters)
   - Clear, descriptive name
   - Example: "Save Gmail Attachments to Google Drive"

3. **Short Description** (50-500 characters)
   - Brief explanation of what it does
   - Appears in search results and cards

4. **Category** (required)
   - Choose the most relevant category
   - Helps users find your template

5. **Tags** (1-10 tags)
   - Type to search existing tags
   - Select from autocomplete suggestions
   - Tags show usage count
   - Click X to remove selected tags

Optional fields:
6. **Detailed Description**
   - Longer explanation
   - Setup instructions
   - Use cases and tips

7. **Visibility** (default: Public)
   - **Public**: Anyone can discover and use
   - **Unlisted**: Only people with direct link
   - **Private**: Only you can see it

### Step 4: Preview & Submit
- Review the **Workflow Preview** section
- Shows sanitized JSON (credentials removed)
- Click **"Publish Template"**

### Step 5: Approval Process
- Your template is submitted with **status: "pending"**
- An admin must approve it before it appears in marketplace
- You'll be notified when approved/rejected

---

## 📥 Cloning a Template

### From Template Detail Page
1. Browse marketplace and find a template
2. Click to view full details
3. Click **"Clone Template"** button
4. In the dialog:
   - Enter a name for your new automation
   - (Optional) Override parameters
5. Click **"Clone Template"**
6. Template is copied to your dashboard

### What Happens:
- New Area (workflow) created in your account
- All steps copied with correct connections
- **Credentials NOT copied** (security)
- You'll need to connect your own services
- Redirected to Dashboard to see new workflow

### After Cloning:
1. Go to **Dashboard** to see your cloned workflow
2. Click **Edit** to configure service connections
3. Connect your own OAuth accounts (Gmail, GitHub, etc.)
4. Enable the workflow
5. It's now active!

---

## 🔐 Security & Privacy

### Credential Sanitization
**IMPORTANT**: When you publish a template:
- All credentials are automatically removed
- `service_connection_id` fields are stripped
- Access tokens, API keys, passwords are NEVER included
- Templates only contain workflow structure and logic

### What Gets Published:
✅ Workflow name and description  
✅ Trigger service and action  
✅ Action services and actions  
✅ Step order and connections  
✅ Parameter names (not values)  

### What's Protected:
🔒 Service connection IDs  
🔒 OAuth access tokens  
🔒 API keys  
🔒 Passwords  
🔒 Any sensitive credentials  

### When Cloning:
- You must connect your OWN services
- No credentials from original author are copied
- Each user has isolated service connections

---

## 🎯 API Endpoints Reference

### Public Endpoints (No Auth)
```
GET  /api/v1/marketplace/templates
     - List all approved templates
     - Query params: q, category, tags, sort_by, order, page, size

GET  /api/v1/marketplace/templates/{id}
     - Get template details

GET  /api/v1/marketplace/categories
     - List all categories

GET  /api/v1/marketplace/tags
     - List popular tags (with usage counts)
```

### Authenticated Endpoints (Requires Token)
```
POST /api/v1/marketplace/templates
     - Publish a template
     - Body: { area_id, title, description, category, tags, visibility }

POST /api/v1/marketplace/templates/{id}/clone
     - Clone a template to your account
     - Body: { area_name, parameter_overrides }
```

### Admin Endpoints (Requires Admin Role)
```
POST /api/v1/admin/templates/{id}/approve
     - Approve a pending template

POST /api/v1/admin/templates/{id}/reject
     - Reject a pending template
```

---

## 💡 Tips & Best Practices

### Publishing Tips:
1. **Test First** - Ensure your workflow works before publishing
2. **Clear Title** - Use descriptive, searchable names
3. **Good Description** - Explain the use case and benefits
4. **Relevant Tags** - Add 3-5 specific, searchable tags
5. **Long Description** - Include setup instructions and examples

### Search Tips:
1. Use specific keywords (e.g., "gmail drive" vs just "email")
2. Combine filters (category + tags) to narrow results
3. Sort by "Most Popular" to find tried-and-tested templates
4. Check template stats before cloning

### Cloning Tips:
1. Read the full description before cloning
2. Check required services (make sure you can connect them)
3. Give your clone a descriptive name
4. After cloning, test with sample data first
5. Review and customize parameters for your needs

---

## 🐛 Troubleshooting

### "Template not found" Error
- Template may have been deleted or rejected
- Check if you have the correct URL

### "Authentication required" Error
- You must be logged in to publish or clone
- Check if your session expired

### "Already published" Error
- You've already published this workflow
- Can only publish each workflow once
- Edit existing template instead (future feature)

### Clone button not working
- Ensure you're logged in
- Check browser console for errors
- Template must be approved (status: "approved")

### Publish button missing on dashboard
- Make sure you have at least one workflow created
- Button appears on each workflow card

---

## 📊 Workflow Status

Templates can have these statuses:

- **pending** - Submitted, awaiting admin approval
- **approved** - Published and visible in marketplace
- **rejected** - Not approved by admin
- **archived** - Removed from marketplace (soft delete)

Only **approved** templates with **public** visibility appear in marketplace search.

---

## 🚀 Quick Start Example

### Publishing Your First Template:
```
1. Dashboard → Create a simple workflow (e.g., "Star GitHub repo when issue created")
2. Test it works
3. Click "Publish to Marketplace" button
4. Fill form:
   - Title: "Auto-star GitHub repos with new issues"
   - Description: "Automatically star repositories when new issues are created"
   - Category: "Development"
   - Tags: ["github", "automation", "productivity"]
5. Submit → Wait for admin approval
```

### Cloning Your First Template:
```
1. Click "Marketplace" in navigation
2. Search for "gmail"
3. Click a template card
4. Review details
5. Click "Clone Template"
6. Enter name: "My Gmail Automation"
7. Confirm → Go to Dashboard
8. Edit → Connect Gmail service → Enable
```

---

## 📞 Need Help?

- Check execution logs in **History** page
- Review service connections in **Connections** page
- Contact support if templates aren't appearing
- Report inappropriate templates to admins

---

**Happy Automating! 🎉**

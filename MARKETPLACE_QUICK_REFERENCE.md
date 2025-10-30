# Marketplace Feature - Quick Reference

## 🎯 Access Points

```
┌─────────────────────────────────────────────────────────────┐
│                    AREA Platform                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Navigation Menu:  Dashboard | Marketplace | Connections   │
│                                    ↑                        │
│                                    │                        │
│                             Click here to browse            │
└─────────────────────────────────────────────────────────────┘
```

## 📤 Publishing Flow

```
Dashboard
   │
   ├─ My Workflows
   │    └─ [Workflow Card]
   │         ├─ Enable/Disable Switch
   │         ├─ Edit Button
   │         ├─ Delete Button
   │         └─ 📤 "Publish to Marketplace" Button ← NEW!
   │              │
   │              ↓
   │         Publish Form Page (/marketplace/publish)
   │              │
   │              ├─ Select Automation (dropdown)
   │              ├─ Template Title (input)
   │              ├─ Short Description (textarea)
   │              ├─ Detailed Description (textarea, optional)
   │              ├─ Category (select)
   │              ├─ Tags (multi-select with autocomplete)
   │              ├─ Visibility (radio: public/unlisted/private)
   │              └─ Workflow Preview (JSON)
   │              │
   │              ↓
   │         Click "Publish Template"
   │              │
   │              ↓
   │         ✅ Template Created (status: pending)
   │              │
   │              ↓
   │         ⏳ Admin Approval Required
   │              │
   │              ├─ Approved → Appears in Marketplace
   │              └─ Rejected → Notification sent
```

## 📥 Browsing & Cloning Flow

```
Marketplace Page (/marketplace)
   │
   ├─ Search Bar (debounced 500ms)
   ├─ Filters Sidebar
   │    ├─ Category Dropdown
   │    ├─ Tag Multi-Select
   │    └─ Sort Options
   │
   └─ Template Grid
        │
        ├─ [Template Card] ← Click to view details
        │    ├─ Title
        │    ├─ Description
        │    ├─ Category Badge
        │    ├─ Tags (first 3)
        │    └─ Stats (👥 uses, 📋 clones, ⭐ rating)
        │
        ↓ Click Card
        │
   Template Detail Page (/marketplace/{id})
        │
        ├─ Full Description
        ├─ Long Description
        ├─ All Tags
        ├─ Stats
        ├─ Workflow Structure
        │    ├─ Trigger: service - action
        │    ├─ Action: service - action
        │    └─ Additional Steps
        │
        └─ 🎯 "Clone Template" Button ← Click here
             │
             ↓
        Clone Dialog
             │
             ├─ Automation Name (input)
             └─ Parameter Overrides (optional)
             │
             ↓ Click "Clone Template"
             │
        ✅ New Area Created in Dashboard
             │
             ↓
        Redirect to Dashboard
             │
             └─ Configure Service Connections
                  └─ Enable Workflow
```

## 🔐 Security Architecture

```
Your Workflow (Private)
   │
   ├─ Trigger Config
   │    ├─ service: "github"
   │    ├─ action: "new_issue"
   │    ├─ service_connection_id: "abc123" ← CREDENTIAL
   │    └─ access_token: "ghp_xxxx"        ← CREDENTIAL
   │
   ↓ Click "Publish to Marketplace"
   │
Sanitization Process
   │
   ├─ Strip service_connection_id ✅
   ├─ Strip access_token ✅
   ├─ Strip refresh_token ✅
   ├─ Strip encrypted tokens ✅
   ├─ Strip API keys ✅
   ├─ Add placeholder: "{{user_credential:github}}" ✅
   │
   ↓
Published Template (Public)
   │
   └─ Trigger Config
        ├─ service: "github"
        ├─ action: "new_issue"
        └─ credential_placeholder: "{{user_credential:github}}"
        
   ↓ Someone Clones Your Template
   │
Cloned Workflow (Their Private Copy)
   │
   └─ Trigger Config
        ├─ service: "github"
        ├─ action: "new_issue"
        └─ service_connection_id: null ← They must connect their own!
```

## 🎨 UI Components Map

```
/marketplace
   ├─ <TemplateSearch />          Search input with icon
   ├─ <TemplateFilters />         Sidebar with category/tags/sort
   └─ <TemplateCard /> (grid)     Preview cards

/marketplace/{id}
   ├─ Template metadata display
   ├─ Workflow structure preview
   └─ Clone dialog (modal)

/marketplace/publish
   ├─ Area selection dropdown
   ├─ Form fields (title, description, etc.)
   ├─ Tag multi-select with autocomplete
   ├─ Radio group for visibility
   └─ JSON preview card

Dashboard (modified)
   └─ Workflow cards
        └─ "Publish to Marketplace" button (new)
```

## 📡 API Flow

```
PUBLISHING:
  Browser → POST /api/v1/marketplace/templates
         ← 201 Created { template_id, status: "pending" }

BROWSING:
  Browser → GET /api/v1/marketplace/templates?q=email&category=productivity
         ← 200 OK { items: [...], total: 10, page: 1 }

DETAIL:
  Browser → GET /api/v1/marketplace/templates/{id}
         ← 200 OK { id, title, description, template_json, ... }

CLONING:
  Browser → POST /api/v1/marketplace/templates/{id}/clone
         ← 201 Created { created_area_id, message }

ADMIN APPROVAL:
  Admin → POST /api/v1/admin/templates/{id}/approve
       ← 200 OK { template, status: "approved" }
```

## 🚦 Quick Commands

### Start Development Server
```bash
cd /Users/ymehili/dev/EPITECH/AREA
make dev
```

### Access Marketplace
```
Frontend: http://localhost:3000/marketplace
Backend API: http://localhost:8080/api/v1/marketplace/templates
API Docs: http://localhost:8080/docs
```

### Test Endpoints (curl)
```bash
# Browse templates (no auth)
curl http://localhost:8080/api/v1/marketplace/templates | jq

# Get categories
curl http://localhost:8080/api/v1/marketplace/categories | jq

# Publish template (with auth)
curl -X POST http://localhost:8080/api/v1/marketplace/templates \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "area_id": "YOUR_AREA_ID",
    "title": "Test Template",
    "description": "A test automation template that does something useful",
    "category": "productivity",
    "tags": ["test", "automation"]
  }'

# Clone template (with auth)
curl -X POST http://localhost:8080/api/v1/marketplace/templates/TEMPLATE_ID/clone \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "area_name": "My Cloned Automation"
  }'
```

## ✅ Feature Checklist

- [x] Backend: 8 API endpoints
- [x] Backend: Credential sanitization (tested)
- [x] Backend: 37 tests passing (91% coverage)
- [x] Frontend: Marketplace browse page
- [x] Frontend: Template detail page
- [x] Frontend: Publish form page
- [x] Frontend: Search with debouncing
- [x] Frontend: Filters (category, tags, sort)
- [x] Frontend: Clone dialog
- [x] Navigation: "Marketplace" link in menu
- [x] Dashboard: "Publish to Marketplace" button
- [x] Security: Zero credentials in templates
- [x] Database: 5 tables with indexes
- [x] Admin: Approval workflow

## 🎓 Learning Resources

1. **User Guide**: `MARKETPLACE_USER_GUIDE.md`
2. **Validation Report**: `MARKETPLACE_VALIDATION_REPORT.md`
3. **PRP Document**: `PRPs/marketplace-workflow-sharing.md`
4. **API Docs**: http://localhost:8080/docs (when server running)

---

**Everything is ready! Start the server and explore the marketplace! 🚀**

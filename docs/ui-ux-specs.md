# Action-Reaction UI/UX Specification

### Section 1: Introduction & Overall UX Goals & Principles

This document defines the user experience goals, information architecture, user flows, and visual design specifications for the "Action-Reaction" platform's user interface. It serves as the foundation for visual design and frontend development, ensuring a cohesive and user-centered experience.

**Target User Personas**
*   **The Everyday Integrator**: A moderately tech-savvy user who wants to save time by connecting their daily apps (social media, email, cloud storage) without writing code. They value an intuitive, guided experience.
*   **The Administrator**: A platform manager who needs a clear and efficient dashboard to manage user accounts and ensure the platform is operating smoothly.

**Usability Goals**
*   **Ease of Learning**: A new user should be able to connect two services and create their first simple "AREA" in under 5 minutes.
*   **Efficiency of Use**: Creating a new automation should feel intuitive and require minimal clicks.
*   **Error Prevention**: The interface must provide clear feedback and confirmation steps to prevent users from making mistakes.
*   **Memorability**: An infrequent user should be able to return to the platform and create a new automation without needing to re-learn the entire process.

**Design Principles**
1.  **Clarity Above All**: Prioritize clear, simple language and visual cues over clever or abstract design. The user should always understand what is happening and what to do next.
2.  **Guided Progression**: The UI should act as a guide, leading the user step-by-step through complex processes like connecting services and building automations.
3.  **Consistent Patterns**: Use familiar and consistent UI patterns throughout the web and mobile applications to create a predictable and trustworthy experience.
4.  **Immediate Feedback**: Every user action, from a button click to a successful connection, must provide immediate and clear visual feedback.

**Change Log**

| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-09-15 | 1.0 | Initial UI/UX Spec Draft | Youssef |

### Section 2: Information Architecture (IA)

**Site Map / Screen Inventory**
This diagram shows the primary screens of the application and how they are connected.

```mermaid
graph TD
    subgraph Public Area
        A[Login / Register Page]
    end

    subgraph Authenticated User Area
        B[Dashboard] --> C[AREA Creation Wizard]
        B --> D[Service Connection Hub]
        B --> E[Account Management]
        
        E --> E1[User Profile]
        E --> E2[Automation History]
        E --> E3[Activity Log]
        E --> E4[Billing Post-MVP]
    end
    
    subgraph Admin Area
        F[Admin Login] --> G[Admin Dashboard]
        G --> H[User Management]
        H --> I[View User Details]
    end

    A --> B
```

**Navigation Structure**
*   **Primary Navigation (Authenticated User)**: After logging in, the user will have a persistent main navigation bar (e.g., a sidebar or top header). This will provide access to the core sections of the application:
    *   **Dashboard** (My AREAs)
    *   **Connections** (Service Hub)
    *   **History** (Post-MVP)
    *   A prominent **"Create AREA"** button.
    *   **Account/Profile** (leading to the Account Management section).
*   **Secondary Navigation**: Within the "Account Management" section, there will be secondary navigation (e.g., tabs or a sub-menu) for Profile, History, and Activity Log.
*   **Breadcrumb Strategy**: Breadcrumbs will be used within nested views, such as when a user is editing a specific AREA, to show the path from the Dashboard (e.g., `Dashboard > My First AREA > Edit`).

### Section 3: User Flows

#### User Onboarding (Registration & Login)
**User Goal:** To create a new account or log in to an existing account to access the platform.
**Entry Points:** Visiting the application's root URL as a non-authenticated user.
**Success Criteria:** A new user successfully creates and confirms their account and is redirected to the Dashboard. An existing user successfully logs in and is redirected to the Dashboard.

**Flow Diagram**
```mermaid
graph TD
    A[Start: User visits app] --> B{Has an account?};
    B -->|No| C[Chooses to Register];
    C --> D{Register with Email or OAuth?};
    D -->|Email| E[Fills out Registration Form];
    E --> F[Submits Form];
    F --> G[Receives Confirmation Email];
    G --> H[Clicks Confirmation Link];
    H --> I[Account Confirmed];
    I --> J[Logs in];

    D -->|OAuth| K[Selects OAuth Provider e.g., Google];
    K --> L[Redirects to Provider for Auth];
    L --> M[Grants Permission];
    M --> N[Redirects back to App];
    N --> O[Account Created & Confirmed];
    O --> J;

    B -->|Yes| P[Chooses to Login];
    P --> Q{Login with Email or OAuth?};
    Q -->|Email| R[Enters Email & Password];
    R --> S{Credentials Valid?};
    S -->|Yes| J;
    S -->|No| T[Shows Error Message];
    T --> R;

    Q -->|OAuth| K;

    J --> U[End: Redirected to Dashboard];
```

#### Connecting a New Service
**User Goal:** To authorize the "Action-Reaction" platform to access a third-party service account (e.g., their Google account) on their behalf.
**Entry Points:** Clicking the "Connect" button for a service in the "Service Connection Hub."
**Success Criteria:** The user successfully authenticates with the third-party service and grants permission. The platform securely stores the necessary credentials (OAuth tokens). The UI updates to clearly indicate that the service is now successfully connected.

**Flow Diagram**
```mermaid
graph TD
    A[Start: User is on the Service Connection Hub] --> B[Clicks Connect on a service, e.g., Google Drive];
    B --> C[Application redirects user to Google's OAuth consent screen];
    C --> D{User grants or denies permission?};
    D -->|Grants| E[Google redirects back to the application's callback URL];
    E --> F[Backend exchanges code for tokens];
    F --> G[Backend securely saves the connection];
    G --> H[Backend redirects user to a success page in the app];
    H --> I[UI shows a Successfully Connected message];
    I --> J[End: Service now appears in the Connected list];

    D -->|Denies| K[Google redirects back to the application];
    K --> L[UI shows a Permission Denied message];
    L --> A;
```

#### Creating a Simple AREA (MVP)
**User Goal:** To create and activate a simple, single-step automation that connects two different services.
**Entry Points:** Clicking the "Create AREA" button from the main Dashboard.
**Success Criteria:** The user successfully navigates the creation wizard. A new "AREA" is created and saved to the user's account. The new AREA appears on the user's Dashboard in an "enabled" state, ready to be triggered.

**Flow Diagram**
```mermaid
graph TD
    A[Start: User on Dashboard] --> B[Clicks Create AREA];
    B --> C[Wizard Step 1: Choose Trigger Service];
    C --> D{Has user connected services?};
    D -->|No| E[Prompt: Please connect a service first];
    E --> F[Redirect to Service Connection Hub];
    F --> C;
    
    D -->|Yes| G[User selects a service, e.g., Gmail];
    G --> H[Wizard Step 2: Choose Action];
    H --> I[User selects an Action, e.g., On New Email];
    I --> J[Wizard Step 3: Choose REAction Service];
    J --> K[User selects a service, e.g., Dropbox];
    K --> L[Wizard Step 4: Choose REAction];
    L --> M[User selects a REAction, e.g., Upload Attachment];
    M --> N[Wizard Step 5: Review & Confirm];
    N --> O[User reviews the summary: If New Email in Gmail, then Upload Attachment to Dropbox];
    O --> P[Clicks Finish];
    P --> Q[Frontend sends AREA config to Backend];
    Q --> R{Save successful?};
    R -->|Yes| S[Backend saves the new AREA];
    S --> T[UI shows AREA Created! message];
    T --> U[End: Redirect to Dashboard, new AREA is listed];

    R -->|No| V[UI shows Error saving AREA message];
    V --> N;
```

#### Creating an Advanced AREA (Final Product)
**User Goal:** To create a sophisticated, multi-step automation with custom logic by visually connecting different functional blocks on a canvas.
**Entry Points:** Clicking the "Create AREA" button from the main Dashboard (this would now launch the advanced builder).
**Success Criteria:** The user can drag and drop different types of nodes (Triggers, Actions, Conditions, Delays) onto a canvas. The user can visually connect the output of one node to the input of another to define the flow of execution. The user can configure each node's specific parameters (e.g., setting the condition, mapping variables). The final workflow is saved and executes according to the visual logic defined by the user.

**Conceptual Flow Diagram**
```mermaid
graph TD
    subgraph AREA Builder Canvas
        A[Start Node] --> B(Trigger: New Email);
        B --> C{Condition: Subject contains 'Invoice'?};
        C -->|Yes| D[Action: Upload Attachment to Dropbox];
        D --> E[Delay: 1 Hour];
        E --> F[Action: Send Slack Message];
        C -->|No| G[End];
        F --> H[End];
    end

    subgraph User Actions
        U1[User drags Trigger node] --> U2[User drags Condition node];
        U2 --> U3[User drags Action nodes];
        U3 --> U4[User connects nodes with lines];
        U4 --> U5[User configures each node's settings];
        U5 --> U6[User clicks Save & Activate];
    end

    U6 --> S[System saves the node graph and execution logic];
```

### Section 4: Wireframes & Mockups

#### Key Screen Layout: Dashboard
**Purpose:** To provide users with an immediate overview of their existing automations ("AREAs") and a clear starting point for creating new ones.
**Key Elements:** Header, Primary Call-to-Action (CTA), AREA List, Individual AREA Card, Empty State.

#### Key Screen Layout: AREA Creation Wizard (MVP)
**Purpose:** To guide the user through the process of creating a simple, single-step automation in a clear and foolproof manner.
**Key Elements:** Wizard Container, Progress Indicator, Step 1: "When this happens..." (Choose Trigger), Step 2: "Then do this..." (Choose REAction), Step 3: Review & Confirm, Navigation.

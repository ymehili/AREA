# Project Brief: Action-Reaction

### Executive Summary

The "Action-Reaction" project is a full-stack automation platform designed to function similarly to services like IFTTT and Zapier. It aims to solve the problem of disconnected digital services by allowing users to create custom automated workflows. The target market consists of users who utilize a wide array of digital tools—including cloud services (Google, Outlook 365), social media platforms (Facebook, X), and AI APIs—and wish to interconnect them. The platform's key value proposition is enabling users to define an "AREA" where a specific **Action** in one service automatically triggers a **REAction** in another, thereby creating powerful, personalized automations.

### Problem Statement

In today's digital environment, users rely on a multitude of disconnected applications and services for productivity, communication, and social media. This fragmentation creates significant inefficiencies, forcing users to perform manual, repetitive tasks to transfer information or coordinate actions between platforms (e.g., saving an email attachment to cloud storage, posting a social media update across multiple networks). Existing solutions can be limited in the services they support or too complex for the average user to configure effectively. The core problem is a lack of a simple, centralized, and extensible platform for users to create seamless automations that match their unique digital workflows, leading to wasted time and potential for human error.

### Proposed Solution

The proposed solution is a comprehensive automation platform, "Action-Reaction," that will be delivered as a software suite consisting of three core components: a central **Application Server**, a **Web Client**, and a **Mobile Client** (Android/iOS).

The platform will empower authenticated users to subscribe to various third-party **Services** (e.g., Google, Facebook, Dropbox). Each service will expose a set of trigger **Actions** (e.g., "a new file is present in a directory") and resulting **REActions** (e.g., "post a message in a group"). Users can then create a custom workflow, called an **AREA**, by linking a specific Action to a REaction. The system will use **hooks** to automatically detect when a trigger Action occurs and execute the corresponding REaction, effectively creating a seamless bridge between disparate services. All business logic will be centralized in the Application Server, which will expose its functionalities via a REST API to the lightweight web and mobile clients.

### Target Users

**Primary User Segment: The Everyday Integrator**
This segment includes individuals who regularly use multiple digital services for personal or professional productivity. They are moderately tech-savvy but are not necessarily developers. Their primary goal is to save time and reduce manual effort by connecting the apps they use daily (e.g., social media, email, cloud storage). They need an intuitive interface to create simple "if this, then that" style automations without writing any code. Their pain point is the friction and repetition involved in making their digital tools work together.

**Secondary User Segment: The Administrator**
This user is responsible for managing the platform itself. As mentioned in the "User Management" section of your document, an administration section is needed to manage site users. This persona requires access to a dashboard to view user accounts, manage registrations, and potentially oversee the health of the services connected to the platform. Their goal is to ensure the smooth operation of the platform for all users.

### Goals & Success Metrics

**Business Objectives**
*   **User Acquisition & Growth:** Achieve a steady increase in user registrations to establish a strong user base.
*   **Service Ecosystem Expansion:** Continuously integrate with a wide range of popular third-party services and APIs to enhance the platform's utility and appeal.
*   **Monetization:** Introduce premium features or subscription tiers (e.g., multi-step "AREAs," faster execution) to create a sustainable revenue stream.

**User Success Metrics**
*   **High Automation Adoption:** A high percentage of registered users should successfully create and activate at least one "AREA."
*   **Increased User Efficiency:** Users should report a noticeable reduction in time spent on manual, repetitive tasks.
*   **High User Engagement:** A significant portion of active users should be creating new "AREAs" or modifying existing ones on a regular basis.

**Key Performance Indicators (KPIs)**
*   **Number of Active Users:** The total count of users who have at least one active "AREA."
*   **Number of "AREAs" Created:** The total number of automations created on the platform.
*   **Automation Execution Rate:** The number of successful "AREA" executions versus failures.
*   **Service Integration Growth:** The rate at which new services are added to the platform.
*   **User Adoption Rate:** The percentage of new users who create their first "AREA" within 7 days of signing up.
*   **Customer Satisfaction (CSAT/NPS):** User feedback scores to measure overall satisfaction with the platform.

### MVP Scope

**Core Features (Must Have)**
*   **User Account Management**: Users must be able to register for a new account, confirm their enrollment, and log in. This includes both username/password and OAuth2 (e.g., Google, Facebook) authentication methods.
*   **Service Subscription**: Authenticated users must be able to connect their accounts from a core set of third-party services via OAuth2.
*   **Simple AREA Creation**: A user interface on both web and mobile clients that allows an authenticated user to create, view, and manage a simple automation ("AREA") by linking **one** `Action` to **one** `REAction`.
*   **Core Automation Engine**: The backend mechanism (hooks) that automatically detects a trigger `Action` and executes the corresponding `REAction`.
*   **Functional Application Server**: The server must be built and expose all MVP functionalities through a REST API.
*   **Functional Web Client**: A browser-based client that can query the application server to perform all the user-facing MVP features.
*   **Functional Mobile Client**: An Android and iOS client that can query the application server to perform all the user-facing MVP features.

**Out of Scope for MVP**
*   **Multi-step AREAs**: Automations involving more than one Action or REAction, conditional logic, time delays, or variables.
*   **Administration Panel**: The full-featured user management dashboard for site administrators.
*   **Advanced User Features**: User profile pages, detailed automation history, or activity logs.
*   **Paid/Premium Tiers**: All functionality will be available to all users.
*   **Extensive Service Library**: The MVP will launch with a limited number of services to prove the core concept.

**MVP Success Criteria**
The MVP will be considered a success when a new user can, without assistance:
1.  Successfully register and log into the platform using either the web or mobile client.
2.  Connect at least two different third-party services to their account.
3.  Create and activate a simple "AREA" that links an `Action` from one service to a `REAction` in the other.
4.  Trigger the `Action` in the source service and verify that the `REAction` is automatically and correctly executed in the target service.

### Post-MVP Vision

**Phase 2 Features (The Final Product)**
Following the successful launch of the MVP, the focus will shift to building out the full feature set to reach the "Final Product" milestone.
*   **Enhanced Automation Logic**: Introduce the full suite of advanced automation capabilities, including **multi-step AREAs**, **conditional logic**, **time delays**, and the use of **variables** to pass data between steps.
*   **Administration Panel**: Develop and launch the comprehensive dashboard for site administrators to manage users and platform health.
*   **Advanced User Features**: Implement user profile pages, a detailed automation history, and activity logs to enhance the user experience.
*   **Rapid Service Expansion**: Systematically expand the library of supported services, actions, and reactions.
*   **Introduce Premium Tiers**: Launch subscription plans to unlock the most advanced features and create a path to monetization.

**Long-term Vision**
Over the next 1-2 years, the "Action-Reaction" platform aims to evolve from a powerful tool into a comprehensive automation ecosystem. The vision is to become a competitive alternative to established players by focusing on user experience and a broad, community-driven service library. This includes potentially developing a marketplace where users can share and discover pre-built "AREA" templates.

**Expansion Opportunities**
*   **Developer Platform**: Open up the platform with a public API, allowing third-party developers to build and submit their own service integrations, accelerating the growth of the ecosystem.
*   **Team & Enterprise Features**: Introduce collaboration features, allowing teams to share automations, manage billing centrally, and connect to enterprise-grade software.
*   **IoT Integration**: Expand beyond software services to include integrations with Internet of Things (IoT) devices, enabling automations for smart homes and offices.

### Technical Considerations

**Platform Requirements**
*   **Target Platforms**: The application must be accessible via a responsive web client and dedicated mobile clients for Android and iOS.
*   **Browser/OS Support**: The web client should support the latest versions of major browsers (Chrome, Firefox, Safari, Edge). Mobile apps should target recent OS versions (e.g., Android 10+ and iOS 14+).
*   **Performance Requirements**: The application server's REST API should have a low latency (e.g., <500ms response time for typical requests) to ensure a smooth user experience on all clients.

**Technology Preferences**
*   **Frontend (Web & Mobile)**: **Next.js (web)** and **Expo React Native (mobile)** are used to build and maintain the web, Android, and iOS clients, ensuring a consistent user experience across platforms.
*   **Backend**: The backend REST API and automation engine will be built using **Python** with the **FastAPI** framework, known for its high performance and modern features.
*   **Database**: A combination of a primary relational database (like PostgreSQL) for user data and structured information, and a non-relational database (like Redis) for caching and managing job queues for the automation engine is recommended.
*   **Hosting/Infrastructure**: The application will be deployed on the **Railway** platform. The entire application should be containerized using Docker and managed with Docker Compose to ensure consistent environments from local development to production on Railway.

**Architecture Considerations**
*   **Repository Structure**: A monorepo structure is used for managing the shared code between the server and the web/mobile clients, though a polyrepo (separate repositories) is also a viable approach.
*   **Service Architecture**: The backend should be designed with a service-oriented or microservices architecture to ensure that different parts of the system can be developed, deployed, and scaled independently.
*   **Integration Requirements**: The architecture must be designed for extensibility, making it easy to add new third-party services in the future.
*   **Security/Compliance**: The platform must handle user credentials and API keys for third-party services securely, using encryption for data at rest and in transit. OAuth2 will be the primary mechanism for service integrations.

### Constraints & Assumptions

**Constraints**
*   **Budget**: Not specified in the project documentation. Assumed to be limited to free or low-cost tiers of any required third-party services.
*   **Timeline**: The project is structured around three key milestones: 1) Planning, 2) Minimum Viable Product, and 3) Final Product. Specific dates are not defined.
*   **Resources**: The project will be developed by a group of 'X' students.
*   **Technical**: The project MUST be containerized using Docker and orchestrated with a `docker-compose.yml` file. This setup includes three services (`server`, `web`, `mobile_web`) with defined port mappings (8080 for the server, 3000 for the web client, 19006 for Expo web preview) and dependencies. The server must expose a specific `/about.json` endpoint.

**Key Assumptions**
*   It is assumed that the development team possesses or will acquire the necessary skills to work with the chosen technology stack (Next.js, Expo React Native, FastAPI, Docker, Railway).
*   It is assumed that the primary development effort will be "glue code," integrating a wide range of existing libraries rather than building everything from scratch.
*   It is assumed that the web and mobile clients will remain "thin clients," containing only user interface logic, with all business logic residing on the application server and accessed via the REST API.
*   It is assumed that the third-party services targeted for integration (e.g., Google, Facebook, etc.) will have accessible APIs and developer free tiers for the project's purposes.
*   It is assumed that the team will implement effective project management practices to meet the milestone-based deadlines.

### Risks & Open Questions

**Key Risks**
*   **Technical Complexity Risk**: While the goal is to use existing libraries, the "glue code" required to integrate a diverse set of third-party APIs can be complex. Each service has unique authentication flows, rate limits, and data formats that could pose significant integration challenges.
*   **Scope Creep Risk**: The project has a very broad potential scope. There is a risk that the requirements for the "Final Product" milestone could expand beyond the team's capacity, jeopardizing the timeline.
*   **Dependency Risk**: The platform's core functionality is entirely dependent on the stability and availability of third-party APIs. A change or deprecation in a key service's API could break critical automations for users.
*   **Security Risk**: The application will store sensitive user credentials and API tokens. A security breach could have severe consequences, making robust security measures for data at rest and in transit a critical, high-risk area.

**Open Questions**
*   What is the specific list of services that will be supported for the MVP launch?
*   What is the strategy for handling errors and notifying users when an automation (AREA) fails to execute?
*   How will the system manage and refresh OAuth2 tokens for long-lived automations?
*   What are the specific requirements and features for the administration panel for the "Final Product" milestone?

**Areas Needing Further Research**
*   A "State of the Art" analysis is required to evaluate and select the best existing libraries for tasks like OAuth2 handling, background job processing (for the automation engine), and API client generation.
*   Proof of Concepts (POCs) should be developed for the most critical and complex third-party service integrations to validate the technical approach before full implementation.

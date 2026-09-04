Emergency Response & Resource Allocation Platform

Project Master Specification — Final Baseline

Project Title: Emergency Response & Resource Allocation Platform Using Cloud-Native Architecture
Project Type: College Final-Year Group Project
Development Strategy: Minor Project → Major Project Extension
Document Role: Canonical project baseline / source of truth
Current Stage: Minor Project
Last Updated: 2026-09-03

1. Document Purpose

This document is the master specification and baseline for the Emergency Response & Resource Allocation Platform.

It is written so that a developer, teammate, evaluator, or AI assistant can understand the project without needing access to previous conversations.

It defines:

What the project is

Why it is being built

What the Minor Project must contain

What is intentionally reserved for the Major Project

Approved architecture

Users and roles

Database model

API strategy

Resource Allocation Engine

Security principles

Development rules

Current implementation state

Rules for future changes

This document should be treated as the project's primary source of truth.

If future development proposes a change to an approved decision, the change should be explicitly discussed and documented before implementation.

2. Project Identity

The project is a college prototype/simulation of an emergency response and resource allocation platform.

It models a simplified emergency-response workflow:

Emergency occurs
      ↓
Dispatcher creates incident
      ↓
System stores incident
      ↓
System evaluates incident requirements
      ↓
System finds suitable resources
      ↓
Resource Allocation Engine selects resources
      ↓
Dispatcher tracks the incident

The project is designed to demonstrate:

Cloud Computing

AWS

Serverless Architecture

Full Stack Development

Database Design

Resource Allocation Algorithms

API Development

Git/GitHub

Later Event-Driven Architecture

Later Analytics

Later Monitoring

The system is an academic prototype/simulation.

It must not be represented as a real production emergency-services system.

3. Core Problem

During an emergency, a dispatcher needs to identify appropriate available resources quickly.

A simplistic system might select only the geographically nearest ambulance or hospital.

This project intentionally aims to make allocation more meaningful by considering multiple factors, including:

Availability

Distance

Emergency severity

Required resources

Ambulance equipment

Hospital facilities

Hospital capacity

The Resource Allocation Engine is the heart of the project.

The objective is to build an allocation mechanism that is:

Functional

Explainable

Defensible in a viva

Simple enough to implement for the Minor

Extensible for the Major

The system should not randomly choose a resource or blindly choose the closest resource when that resource does not satisfy mandatory requirements.

4. Basic System Workflow

The intended high-level workflow is:

Emergency occurs
        ↓
Dispatcher creates incident
        ↓
Incident is stored
        ↓
System evaluates severity and requirements
        ↓
Candidate ambulances are retrieved
        ↓
Unsuitable ambulances are filtered
        ↓
Suitable ambulance is scored
        ↓
Best ambulance is selected
        ↓
Candidate hospitals are retrieved
        ↓
Hospitals are checked for capacity/facilities
        ↓
Suitable hospital is scored
        ↓
Best hospital is selected
        ↓
Allocation is saved
        ↓
Resource and incident state are updated
        ↓
Dispatcher tracks incident

The exact scoring formula for the Resource Allocation Engine is not yet frozen.

It will be designed and documented before allocation implementation begins.

5. Project Strategy: Minor → Major

The project is deliberately developed in two stages.

5.1 Minor Project

The Minor establishes the working core system.

The Minor should demonstrate:

Basic authentication

Incident management

Ambulance management

Hospital management

Resource matching

Resource allocation

Distance calculation

Equipment/facility matching

Hospital capacity matching

Dispatcher dashboard

Incident tracking

Basic AWS deployment

API development

Database usage

Documentation

The Minor must remain manageable for a beginner while still demonstrating meaningful cloud-native engineering.

5.2 Major Project

The Major is an extension of the same Minor system.

The Major must not be treated as a completely new project or a replacement architecture.

The Major may extend the existing system with:

EventBridge

SQS

Dead Letter Queue

Step Functions

SNS

Cognito / advanced authentication

Improved IAM

CloudWatch monitoring

Retry/error workflows

Audit logging

Historical data pipeline

S3 data lake

AWS Glue

Athena

Analytics dashboard

Optional ML for severity prediction

Optional ML for emergency/resource demand prediction

More advanced distributed/event-driven architecture

The Major should demonstrate how the initial working serverless MVP can evolve into a more advanced cloud-native and event-driven system.

6. Minor Project Scope — Approved and Frozen

The following Minor MVP is approved.

6.1 Users / Roles

Exactly two initial roles:

Dispatcher

Resource Operator

There is intentionally no separate Admin role in the Minor.

6.2 Dispatcher

A Dispatcher can:

Create/manage incidents

View incidents

Allocate resources

Track incidents

View resource information

6.3 Resource Operator

A Resource Operator can:

Manage ambulance availability

Manage ambulance information/equipment

Manage hospital capacity

Manage hospital information/facilities

7. Minor Features

The Minor includes:

Basic authentication

Emergency incident creation

Incident location

Incident severity

Emergency type

People affected

Required resources

Required equipment/facilities

Ambulance registration

Ambulance availability management

Hospital registration

Hospital capacity management

Resource matching/allocation

Dispatcher dashboard

Incident status tracking

Basic backend/API functionality

AWS deployment

GitHub documentation

Features will be implemented incrementally.

The entire system must not be coded simultaneously.

8. Minor Architecture — Approved

The approved Minor architecture is:

React Frontend
      ↓
API Gateway
      ↓
AWS Lambda
      ↓
DynamoDB
      ↓
Resource Allocation Logic

8.1 React Frontend

Provides the user interface for:

Dispatcher

Resource Operator

8.2 API Gateway

Provides the HTTP/API entry point for the frontend to communicate with the backend.

8.3 AWS Lambda

Runs backend application logic without requiring management of traditional servers.

Lambda will handle operations such as:

Authentication-related backend logic

Incident operations

Ambulance operations

Hospital operations

Allocation logic

8.4 DynamoDB

Stores operational application state.

The approved logical entities are:

Users

Incidents

Ambulances

Hospitals

8.5 Resource Allocation Logic

The allocation engine runs in the backend/Lambda layer.

It reads current resource and incident state from DynamoDB, performs calculations, and determines suitable resources.

9. API Strategy — Critical Distinction

The project does use APIs.

There are two different concepts:

Our own application APIs

Third-party external APIs

These must never be confused.

9.1 Our Own APIs — Required

The Minor uses APIs exposed through Amazon API Gateway and implemented by AWS Lambda.

Examples:

POST /auth/register
POST /auth/login

POST /incidents
GET /incidents
GET /incidents/{id}
PUT /incidents/{id}/status

POST /ambulances
GET /ambulances
PUT /ambulances/{id}

POST /hospitals
GET /hospitals
PUT /hospitals/{id}

POST /incidents/{id}/allocate

These are our application's own APIs.

Therefore:

"No third-party external API" does NOT mean "no APIs."

The application absolutely requires APIs for frontend/backend communication.

10. Third-Party External API Strategy

10.1 Minor — Third-Party APIs Are Not Required

The Minor does not require any third-party external API for its core functionality.

The project is an academic simulation, so operational data can be created and managed inside our own application.

For example:

Resource Operator
      ↓
React
      ↓
POST /ambulances
      ↓
API Gateway
      ↓
Lambda
      ↓
DynamoDB

An ambulance can be registered with:

Vehicle number

Latitude

Longitude

Availability status

Equipment

Similarly, hospitals and incidents are created through our own application APIs.

Therefore the Minor does not depend on live external emergency data.

10.2 Minor Data Source

For the Minor, operational data comes from the application's users and simulated project data.

Examples:

Incident

INC-001
Type: ROAD_ACCIDENT
Latitude: 18.5204
Longitude: 73.8567
Severity: CRITICAL
People affected: 3
Required equipment:
- OXYGEN
- BASIC_LIFE_SUPPORT

Ambulance

AMB-001
Latitude: 18.5200
Longitude: 73.8550
Status: AVAILABLE
Equipment:
- OXYGEN
- BASIC_LIFE_SUPPORT

Hospital

HOSP-001
Latitude: 18.5230
Longitude: 73.8500
Available beds: 12
Facilities:
- EMERGENCY
- ICU
- TRAUMA

This data is stored in DynamoDB.

10.3 Location Data in the Minor

The Minor stores latitude and longitude for:

Incidents

Ambulances

Hospitals

The coordinates can be realistic/simulated coordinates.

The system does not require real-time GPS.

Lambda can calculate approximate geographical distance from the stored coordinates internally.

For example:

Incident coordinates
        +
Ambulance coordinates
        ↓
Distance calculation in Lambda
        ↓
Approximate distance

A mathematical distance formula such as the Haversine formula may be used.

No mapping/routing provider is required for this Minor functionality.

10.4 Major — Third-Party APIs Are Optional

The Major does not permanently prohibit third-party APIs.

A third-party API may be introduced if it provides meaningful functionality that improves the system and is technically justified.

One possible example is a mapping/routing service that can provide:

Road distance

Estimated travel time

Route information

This could improve the allocation engine beyond straight-line geographical distance.

However:

No third-party API is currently approved for the Major.

It remains a future design decision.

We will decide later based on actual project requirements rather than adding an API simply to make the architecture look advanced.

10.5 Conditions for Introducing an External API

Before introducing a third-party API, the project must document:

Why it is needed

What functionality/data it provides

Why the functionality cannot reasonably be provided internally

Where it fits in the architecture

Cost

Rate limits and usage restrictions

Reliability considerations

Security implications

API key/secret handling

Error handling

Fallback behavior

API keys and secrets must never be hardcoded into source code.

10.6 API Strategy Summary

MINOR

React
  ↓
Our API Gateway APIs
  ↓
Our Lambda functions
  ↓
Our DynamoDB
  ↓
Our allocation logic

Third-party API:
NOT REQUIRED

MAJOR

Our existing application APIs
          ↓
Major cloud/event-driven extensions
          ↓
Optional third-party API
          ↓
Only if technically justified

Third-party API:
OPTIONAL — NOT YET APPROVED

11. Minor AWS Boundary

The following services are intentionally not required in the Minor:

EventBridge

SQS

Dead Letter Queue

Step Functions

SNS

AWS Glue

Athena

ML systems

Advanced monitoring infrastructure

They are reserved for future Major expansion unless a specific justified requirement appears.

S3 may be used in the Minor only if it is genuinely useful.

AWS services must not be added merely to make the project appear more complex.

12. Database Strategy

The Minor uses four logical DynamoDB entities/tables:

Users

Incidents

Ambulances

Hospitals

This design is intentionally simple because it is:

Easier for a beginner to understand

Easier to implement

Easier to debug

Easier to demonstrate

Easier to defend in a viva

A DynamoDB single-table design is not currently approved.

It should not be introduced without a clear technical reason and explicit discussion.

13. Users Entity

Fields:

userId

name

email

passwordHash / authentication reference

role

createdAt

Example:

{
  "userId": "USR-001",
  "name": "Rahul Sharma",
  "email": "rahul@example.com",
  "passwordHash": "...",
  "role": "DISPATCHER",
  "createdAt": "2026-09-03T10:30:00Z"
}

Plain-text passwords must never be stored.

14. Incidents Entity

Fields:

incidentId

type

description

latitude

longitude

severity

peopleAffected

requiredResources

requiredEquipment

status

assignedAmbulanceId

assignedHospitalId

createdAt

updatedAt

Example:

{
  "incidentId": "INC-001",
  "type": "ROAD_ACCIDENT",
  "description": "Vehicle collision",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "severity": "CRITICAL",
  "peopleAffected": 3,
  "requiredResources": [
    "AMBULANCE"
  ],
  "requiredEquipment": [
    "OXYGEN",
    "BASIC_LIFE_SUPPORT"
  ],
  "status": "PENDING",
  "assignedAmbulanceId": null,
  "assignedHospitalId": null,
  "createdAt": "2026-09-03T10:35:00Z",
  "updatedAt": "2026-09-03T10:35:00Z"
}

15. Ambulances Entity

Fields:

ambulanceId

vehicleNumber

latitude

longitude

status

equipment

assignedIncidentId

updatedAt

Possible statuses:

AVAILABLE

BUSY

OFFLINE

Example:

{
  "ambulanceId": "AMB-001",
  "vehicleNumber": "MH12AB1234",
  "latitude": 18.5200,
  "longitude": 73.8550,
  "status": "AVAILABLE",
  "equipment": [
    "OXYGEN",
    "BASIC_LIFE_SUPPORT"
  ],
  "assignedIncidentId": null,
  "updatedAt": "2026-09-03T10:30:00Z"
}

16. Hospitals Entity

Fields:

hospitalId

name

latitude

longitude

totalBeds

availableBeds

facilities

status

updatedAt

Example:

{
  "hospitalId": "HOSP-001",
  "name": "City General Hospital",
  "latitude": 18.5230,
  "longitude": 73.8500,
  "totalBeds": 100,
  "availableBeds": 12,
  "facilities": [
    "EMERGENCY",
    "ICU",
    "TRAUMA"
  ],
  "status": "AVAILABLE",
  "updatedAt": "2026-09-03T10:30:00Z"
}

17. Database Relationship Approach

The project does not use complicated SQL-style relationships.

Entities are connected using IDs.

Example:

Incident INC-001
      │
      ├── assignedAmbulanceId → AMB-001
      │
      └── assignedHospitalId → HOSP-001

The ambulance may also contain:

assignedIncidentId → INC-001

This approach is intentionally simple.

18. State vs Calculation Principle

The database stores application state.

Examples:

Latitude

Longitude

Availability

Capacity

Equipment

Facilities

Assignment state

Calculated distance should not be permanently stored as the source of truth.

Instead:

DynamoDB current state
        ↓
Lambda
        ↓
Distance calculation
        ↓
Suitability calculation
        ↓
Best resource

This separates persistent state from runtime decision-making logic.

19. Incident Lifecycle

Initial incident lifecycle:

CREATED
   ↓
PENDING
   ↓
ALLOCATED
   ↓
IN_PROGRESS
   ↓
RESOLVED

The first implementation should remain simple.

20. Initial API Requirements

Authentication

POST /auth/register
POST /auth/login

Incidents

POST /incidents
GET /incidents
GET /incidents/{id}
PUT /incidents/{id}/status

Ambulances

POST /ambulances
GET /ambulances
PUT /ambulances/{id}

Hospitals

POST /hospitals
GET /hospitals
PUT /hospitals/{id}

Allocation

POST /incidents/{id}/allocate

The allocation endpoint is a core endpoint because it invokes the Resource Allocation Engine.

API implementation will be incremental.

21. Resource Allocation Engine

The Resource Allocation Engine is the central technical feature of the project.

The intended logical process is:

1. Get candidate ambulances
        ↓
2. Remove BUSY/OFFLINE ambulances
        ↓
3. Check required equipment
        ↓
4. Calculate distance from ambulance to incident
        ↓
5. Calculate ambulance suitability score
        ↓
6. Select best suitable ambulance
        ↓
7. Find candidate hospitals
        ↓
8. Check hospital capacity
        ↓
9. Check required facilities
        ↓
10. Calculate hospital suitability score
        ↓
11. Select best hospital
        ↓
12. Save allocation
        ↓
13. Update ambulance status
        ↓
14. Update incident status

The exact scoring formula is not yet frozen.

Before implementation, it must be designed to be:

Explainable

Simple enough for the Minor

Defensible in a viva

Based on meaningful factors

Deterministic/reproducible where practical

22. Resource Matching Principles

22.1 Ambulance Matching

Candidate ambulances should be evaluated using factors including:

Availability

Required equipment

Distance

Incident severity/priority where appropriate

An ambulance that fails a mandatory equipment requirement should normally be excluded before scoring.

22.2 Hospital Matching

Candidate hospitals should be evaluated using factors including:

Availability/status

Available capacity

Required facilities

Distance

Incident requirements

A hospital that fails a mandatory capacity or facility requirement should normally be excluded before scoring.

23. Security Principles

Even though the system is an academic prototype, basic security principles must be followed.

Never store plain-text passwords.

Never hardcode API keys or secrets.

Validate API input.

Avoid exposing unnecessary sensitive information.

Use appropriate IAM permissions.

Keep secrets out of source control.

Do not claim production-grade security unless it has actually been implemented.

Advanced authentication and authorization improvements are planned for the Major.

24. Development Environment

Operating system:

Windows

Local project path:

C:\Users\tomax\Projects\emergency-resource-allocation-platform

Editor:

VS Code

Git:

2.54.0.windows.1

Node:

v24.15.0

npm:

11.12.1

25. Frontend Status

The existing frontend is a React + Vite application.

Location:

emergency-resource-allocation-platform\frontend

Created using:

npm create vite@latest frontend -- --template react

Setup included:

ESLint

Installed dependencies

Successful Vite startup

Vite version:

v8.2.2

The frontend was successfully verified at:

http://localhost:5173/

The existing React project must not be recreated or unnecessarily reinstalled.

Future frontend work should modify the existing project.

26. GitHub Status

Repository:

emergency-resource-allocation-platform

The repository already exists and is public.

The local repository has already been cloned.

Git was verified with:

main branch

Up to date with origin/main

Clean working tree

Teammates may be added as GitHub collaborators after the project is finished.

Contributors must not be fabricated.

Fake commits and fake contribution history must not be created.

Git history should honestly reflect work that was actually performed.

Documentation may identify the project as a group project.

27. Approved Project Folder Structure

The project is organized approximately as follows:

emergency-resource-allocation-platform
│
├── backend
│   └── functions
│       ├── auth
│       ├── incidents
│       ├── ambulances
│       ├── hospitals
│       └── allocation
│
├── docs
│
├── frontend
│   ├── src
│   ├── public
│   ├── package.json
│   └── ...
│
├── infrastructure
│
└── README.md

The existence of folders does not mean the corresponding backend or AWS implementation has already been completed.

28. Minor vs Major Boundary

Capability

Minor

Major

React frontend

Yes

Extend

API Gateway

Yes

Extend

Lambda

Yes

Extend

DynamoDB

Yes

Extend

Basic authentication

Yes

Improve

Incident management

Yes

Extend

Ambulance management

Yes

Extend

Hospital management

Yes

Extend

Resource Allocation Engine

Yes

Improve

Distance-based matching

Yes

Improve

Equipment matching

Yes

Improve

Hospital capacity matching

Yes

Improve

Dispatcher dashboard

Yes

Extend

Incident tracking

Yes

Extend

Basic AWS deployment

Yes

Extend

EventBridge

No

Yes

SQS

No

Yes

DLQ

No

Yes

Step Functions

No

Yes

SNS

No

Yes

Cognito / advanced authentication

No

Yes

Advanced IAM

No

Yes

CloudWatch monitoring

Limited/basic if needed

Yes

Advanced retry/error workflows

No

Yes

Audit logging

No

Yes

S3 data lake

No / only if genuinely useful

Yes

AWS Glue

No

Yes

Athena

No

Yes

Analytics dashboard

No

Yes

ML

No

Optional

Advanced event-driven architecture

No

Yes

Third-party external API

Not required

Optional, not yet approved

29. Major Extension Philosophy

The Major should demonstrate evolution rather than replacement.

The Minor starts with a synchronous serverless architecture:

React
 ↓
API Gateway
 ↓
Lambda
 ↓
DynamoDB

The Major may evolve this toward:

React
 ↓
CloudFront
 ↓
API Gateway
 ↓
Lambda
 ↓
DynamoDB / S3 / Cognito
 ↓
EventBridge
 ↓
SQS
 ↓
Resource Allocation Lambda
 ↓
Step Functions
 ↓
SNS / additional workflows

Historical data may later flow through:

S3
 ↓
Glue
 ↓
Athena
 ↓
Analytics Dashboard

Monitoring may later be expanded using:

CloudWatch

A third-party API may optionally be introduced if a future Major requirement justifies it, such as road-distance or ETA information.

None of these Major extensions should be treated as implemented during the Minor.

30. Engineering Principles

Principle 1 — Working system over service count

Do not add AWS services simply to make the architecture look impressive.

Principle 2 — Simple before advanced

Implement and verify the simplest correct solution before introducing complexity.

Principle 3 — Preserve working components

Do not rebuild working components unnecessarily.

Principle 4 — Explainability

Important decisions, especially resource allocation, must be explainable.

Principle 5 — Security by default

Avoid plain-text passwords, hardcoded secrets, and unnecessarily broad permissions.

Principle 6 — Cost-conscious design

Use managed/serverless services appropriately without introducing unnecessary infrastructure.

Principle 7 — Incremental development

Build → test → verify → continue.

Principle 8 — Honest project history

Git commits and contributor history must represent actual work.

Principle 9 — Minor becomes Major

The Major must extend the Minor rather than replace it.

Principle 10 — APIs are not automatically external APIs

The project requires its own internal/application APIs.

Third-party external APIs are a separate optional dependency and must be justified independently.

31. Development Method

Development follows a strict incremental workflow.

For every development step:

State the step number.

Explain what is being done.

Explain why it is needed.

Explain relevant concepts for a complete beginner.

Give exact click-by-click instructions where applicable.

Give complete copy/paste code when code is required.

Specify the exact filename and location.

Do not provide partial code when a complete file is required.

Explain exactly what should be visible after the action.

Verify the result.

Stop and wait for confirmation before continuing.

Do not dump the entire implementation into one response.

32. Debugging Method

When an error occurs:

Read the exact error.

Explain what it means.

Identify the likely cause.

Apply the smallest necessary fix.

Verify the fix.

Continue.

Do not rebuild working components because a later component has an error.

Do not change the architecture to solve a small implementation issue unless there is a genuine technical reason.

33. Decision Classification

Important project decisions should be described using four categories.

FACT

What is objectively true.

ASSUMPTION

What is assumed for the prototype.

DESIGN DECISION

What the project intentionally chooses and why.

OPTIONAL IMPROVEMENT

A useful enhancement that is not required at the current stage.

This classification helps distinguish confirmed requirements from assumptions and future ideas.

34. Project Quality Goals

The project should optimize for:

Functionality

Simplicity

Security

Cost-consciousness

Maintainability

Resume value

Viva/interview defensibility

Clear architecture

Explainable algorithms

Incremental development

The project is not optimized for maximum AWS service count.

35. Current Development State

Completed:

GitHub repository setup

Local repository cloning

Git verification

Node/npm verification

React + Vite setup

Local frontend verification

Minor MVP scope definition

Minor MVP approval

Logical DynamoDB data model design

Four-table database model approval

Initial project folder structure setup

Project Master Specification baseline

Current approved state:

Minor MVP: FROZEN
Database model: APPROVED
Minor architecture: APPROVED
Application APIs: REQUIRED
Third-party API for Minor: NOT REQUIRED
Third-party API for Major: OPTIONAL / NOT YET APPROVED
Development approach: INCREMENTAL
Major: EXTENSION OF MINOR

36. Current Development Step

The project is currently at:

STEP 7 — Create the Proper Project Structure

The initial folder structure has been created.

The next implementation work should continue from this state.

37. What Has NOT Been Implemented Yet

Unless separately recorded in the development log, the following should be treated as not yet implemented:

DynamoDB tables

Lambda backend functions

API Gateway APIs

Authentication implementation

Incident APIs

Ambulance APIs

Hospital APIs

Allocation endpoint

Final allocation scoring formula

AWS deployment

Major event-driven services

Third-party external API integration

The existence of specifications or folders does not mean implementation exists.

38. Change Control

The following decisions should not be changed casually:

Minor/Major separation

Two Minor roles

Four logical database entities

No required third-party API for Minor

React + API Gateway + Lambda + DynamoDB Minor architecture

Dynamic distance calculation

Resource Allocation Engine as the core feature

Major as an extension of Minor

If a future change appears beneficial, first document:

Existing decision

Proposed change

Technical reason

Benefits

Drawbacks

Impact on Minor

Impact on Major

Whether existing work must be modified

Only then should the change be adopted.

39. AI Continuation Instructions

Any AI assistant continuing this project must follow these rules:

Treat this document as the project baseline.

Do not restart the project.

Do not recreate working components.

Do not silently redesign the architecture.

Do not move Major features into the Minor without explicit discussion.

Do not interpret "no third-party API" as "no APIs."

Remember that our own API Gateway/Lambda APIs are required.

Do not add external APIs without justification.

Do not assume a third-party API will definitely be used in the Major.

Do not add AWS services merely for complexity.

Follow one-step-at-a-time development.

Explain concepts for a complete beginner.

Give exact filenames and locations.

Provide complete code when a complete file is required.

Debug actual errors before proposing redesigns.

Preserve approved database decisions unless a justified change is discussed.

Treat the Resource Allocation Engine as the core technical feature.

Keep the system framed as an academic prototype/simulation.

Maintain honest Git history and contributor representation.

Update documentation when significant design decisions or implementation milestones occur.

Preserve the Minor → Major extension strategy.

When uncertain about a project decision, consult this document before making assumptions.

40. Definition of Success for the Minor

The Minor Project is successful when the working prototype can demonstrate this end-to-end scenario:

Dispatcher logs in
      ↓
Creates emergency incident
      ↓
Incident is stored
      ↓
System evaluates requirements
      ↓
System identifies suitable available ambulance(s)
      ↓
Allocation Engine selects the best ambulance
      ↓
System identifies suitable hospital(s)
      ↓
Allocation Engine selects the best hospital
      ↓
Incident stores the allocation
      ↓
Ambulance becomes BUSY
      ↓
Dispatcher tracks incident status
      ↓
Incident is eventually RESOLVED

The demonstration should allow the team to explain:

What happened

Where the data came from

How the data was stored

Which AWS component handled each operation

Why a particular resource was selected

How the allocation algorithm works

How the Minor architecture can evolve into the Major architecture

The difference between our own APIs and optional third-party APIs

41. Final Project Principle

The project should answer one central question:

Can we build a genuinely working, explainable emergency resource allocation prototype using cloud-native architecture, while keeping the system simple enough to understand and strong enough to defend in a college viva?

The Minor proves the working foundation.

The Major extends that foundation with more advanced cloud-native, event-driven, analytics, monitoring, security, and optionally intelligent capabilities.

The project should remain technically meaningful rather than becoming a collection of AWS services added only for appearance.

End of Project Master Specification — Final Baseline
Emergency Response & Resource Allocation Platform

Architecture Specification

Project Title: Emergency Response & Resource Allocation Platform Using Cloud-Native Architecture
Project Type: College Final-Year Group Project
Development Strategy: Minor Project → Major Project Extension
Document Role: Technical Architecture Baseline
Current Stage: Minor Project
Last Updated: 2026-09-04

1. Purpose of This Document

This document defines the technical architecture of the Emergency Response & Resource Allocation Platform.

It explains:

How the system components interact

The approved Minor architecture

The planned Major architecture

Responsibilities of each component

Application data flow

API flow

Database interaction

Resource allocation flow

Security boundaries

Deployment direction

Minor → Major architectural evolution

Current, planned, optional, and not-yet-approved components

This document should be read together with:

docs/PROJECT_MASTER_SPEC_FINAL.md

The Project Master Specification defines the overall project scope and decisions.

This document focuses specifically on how the system is structured and how its components communicate.

2. Architecture Goals

The architecture is designed around the following goals:

Build a genuinely working academic prototype.

Use cloud-native/serverless architecture.

Keep the Minor simple enough for a beginner to implement and understand.

Make the Resource Allocation Engine the core technical feature.

Separate frontend, API, backend logic, and persistent data.

Avoid unnecessary infrastructure complexity.

Keep the Minor architecture extensible toward the Major.

Make architectural decisions explainable in a viva/interview.

Keep operational state in DynamoDB and runtime calculations in Lambda.

Avoid unnecessary dependence on third-party external APIs.

Allow the Major to introduce event-driven architecture without rebuilding the entire project.

3. Core Architecture Principle

The project uses a layered architecture.

Presentation Layer
       ↓
API Layer
       ↓
Application / Business Logic Layer
       ↓
Data Layer

For the Minor:

React
  ↓
API Gateway
  ↓
Lambda
  ↓
DynamoDB

The Resource Allocation Engine belongs to the backend/business-logic layer.

The frontend should request allocation through an API rather than performing the final allocation decision itself.

4. Minor Architecture — Approved

The approved Minor architecture is:

┌──────────────────────────┐
│      React Frontend      │
│                          │
│ Dispatcher               │
│ Resource Operator        │
└────────────┬─────────────┘
             │ HTTP / HTTPS
             ↓
┌──────────────────────────┐
│     Amazon API Gateway   │
│                          │
│ Application API Routes   │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│        AWS Lambda        │
│                          │
│ Auth Logic               │
│ Incident Logic           │
│ Ambulance Logic          │
│ Hospital Logic           │
│ Allocation Logic         │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│        Amazon DynamoDB   │
│                          │
│ Users                    │
│ Incidents                │
│ Ambulances               │
│ Hospitals                │
└──────────────────────────┘

This is the baseline architecture for the Minor Project.

5. Minor Component Responsibilities

5.1 React Frontend

React is the presentation layer.

It provides the user interface for the two Minor roles:

Dispatcher

The Dispatcher interface supports:

Login

Incident creation

Incident viewing

Resource allocation

Incident tracking

Resource information

Resource Operator

The Resource Operator interface supports:

Ambulance registration

Ambulance availability management

Ambulance equipment information

Hospital registration

Hospital capacity management

Hospital facility information

React is responsible for:

Collecting user input

Displaying application data

Calling backend APIs

Displaying API responses

Showing application state to users

React is not the authoritative location for resource allocation decisions.

6. API Gateway

Amazon API Gateway is the HTTP/API entry point between the frontend and backend.

Conceptually:

React
  ↓
HTTP Request
  ↓
API Gateway
  ↓
Lambda

API Gateway exposes the application's own APIs.

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

These are our own application APIs, not third-party APIs.

7. AWS Lambda

AWS Lambda is the backend execution layer.

Lambda is responsible for application/business logic such as:

Request validation

Authentication-related logic

Incident operations

Ambulance operations

Hospital operations

Allocation operations

DynamoDB reads

DynamoDB writes

Distance calculations

Suitability calculations

The local backend is organized by logical responsibility:

backend/
└── functions/
    ├── auth/
    ├── incidents/
    ├── ambulances/
    ├── hospitals/
    └── allocation/

This logical organization does not require that every folder immediately become a separate deployed Lambda function.

The exact deployment arrangement may be refined during implementation while preserving the logical separation.

8. DynamoDB

DynamoDB is the operational data store for the Minor.

The approved logical entities are:

Users
Incidents
Ambulances
Hospitals

DynamoDB stores current application state.

Examples of stored state include:

User information/authentication reference

Incident information

Incident status

Incident location

Ambulance location

Ambulance availability

Ambulance equipment

Hospital location

Hospital capacity

Hospital facilities

Resource assignments

The system connects related records through IDs rather than traditional SQL joins.

Example:

Incident INC-001
      │
      ├── assignedAmbulanceId → AMB-001
      │
      └── assignedHospitalId → HOSP-001

9. Internal API vs External API

This distinction is important throughout the architecture.

9.1 Internal/Application APIs

These are required.

React
  ↓
API Gateway
  ↓
Lambda

They are APIs owned by this project.

Examples:

POST /incidents
GET /incidents
POST /ambulances
POST /hospitals
POST /incidents/{id}/allocate

9.2 Third-Party External APIs

These are separate services operated by another organization.

Example:

Our Lambda
     ↓
Third-Party Routing API
     ↓
Road distance / ETA

Third-party APIs are not required for the Minor.

For the Major, they are optional and not yet approved.

10. Minor Data Source Architecture

The Minor is an academic simulation.

Therefore, the application does not require live emergency-service data.

Operational data is entered or managed through our application.

Example:

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

An ambulance can contain:

AMB-001
Vehicle: MH12AB1234
Latitude: 18.5200
Longitude: 73.8550
Status: AVAILABLE
Equipment:
- OXYGEN
- BASIC_LIFE_SUPPORT

A hospital can contain:

HOSP-001
Latitude: 18.5230
Longitude: 73.8500
Available beds: 12
Facilities:
- EMERGENCY
- ICU
- TRAUMA

An incident can contain:

INC-001
Latitude: 18.5204
Longitude: 73.8567
Severity: CRITICAL
People affected: 3
Required equipment:
- OXYGEN
- BASIC_LIFE_SUPPORT

These records are stored in DynamoDB.

11. Location Architecture

The Minor stores latitude and longitude for:

Incidents

Ambulances

Hospitals

The coordinates may be realistic or simulated.

The Minor does not require real-time GPS.

For allocation, Lambda can calculate approximate geographical distance internally.

Conceptually:

Incident coordinates
        +
Ambulance coordinates
        ↓
Lambda
        ↓
Distance calculation
        ↓
Allocation score

A mathematical geographical-distance method such as the Haversine formula may be used.

This avoids making the Minor dependent on an external mapping service.

12. Minor Request/Response Flow

A normal application request follows:

User
 ↓
React
 ↓
API Gateway
 ↓
Lambda
 ↓
DynamoDB
 ↓
Lambda
 ↓
API Gateway
 ↓
React
 ↓
User

Example:

Dispatcher submits incident
        ↓
React sends POST /incidents
        ↓
API Gateway receives request
        ↓
Lambda validates request
        ↓
Lambda writes incident
        ↓
DynamoDB stores incident
        ↓
Lambda returns response
        ↓
React updates dashboard

13. Incident Creation Architecture

The incident creation flow is:

Dispatcher
    ↓
Incident Form
    ↓
React
    ↓
POST /incidents
    ↓
API Gateway
    ↓
Lambda
    ↓
Validate input
    ↓
Generate incident ID
    ↓
Create incident record
    ↓
DynamoDB
    ↓
Return response
    ↓
React

The incident then follows the approved lifecycle.

14. Resource Operator Architecture

14.1 Ambulance Management

Resource Operator
       ↓
React
       ↓
POST/PUT /ambulances
       ↓
API Gateway
       ↓
Lambda
       ↓
DynamoDB

The ambulance record contains:

Location

Status

Equipment

Assignment state

14.2 Hospital Management

Resource Operator
       ↓
React
       ↓
POST/PUT /hospitals
       ↓
API Gateway
       ↓
Lambda
       ↓
DynamoDB

The hospital record contains:

Location

Capacity

Facilities

Status

15. Resource Allocation Architecture

The Resource Allocation Engine is the core business logic of the system.

The allocation endpoint is:

POST /incidents/{id}/allocate

High-level architecture:

Dispatcher
      ↓
React
      ↓
POST /incidents/{id}/allocate
      ↓
API Gateway
      ↓
Allocation Lambda
      ↓
Read Incident
      ↓
Read Candidate Ambulances
      ↓
Filter Unsuitable Ambulances
      ↓
Calculate Distance
      ↓
Calculate Ambulance Score
      ↓
Select Ambulance
      ↓
Read Candidate Hospitals
      ↓
Filter Unsuitable Hospitals
      ↓
Calculate Distance
      ↓
Calculate Hospital Score
      ↓
Select Hospital
      ↓
Save Allocation
      ↓
Update Incident
      ↓
Update Ambulance
      ↓
Return Result

The exact scoring formula is not yet frozen.

16. Ambulance Matching Architecture

The ambulance matching process is:

Get ambulance records
        ↓
Filter BUSY
        ↓
Filter OFFLINE
        ↓
Check required equipment
        ↓
Remove unsuitable candidates
        ↓
Calculate distance
        ↓
Calculate suitability score
        ↓
Compare candidates
        ↓
Select best suitable ambulance

Mandatory requirements should be checked before final scoring.

The system should not select a closer ambulance if it lacks required equipment.

17. Hospital Matching Architecture

The hospital matching process is:

Get hospital records
        ↓
Check status
        ↓
Check available capacity
        ↓
Check required facilities
        ↓
Remove unsuitable candidates
        ↓
Calculate distance
        ↓
Calculate suitability score
        ↓
Compare candidates
        ↓
Select best suitable hospital

Mandatory requirements should be checked before final scoring.

A hospital without sufficient capacity or required facilities should normally be excluded.

18. Allocation State Update

After successful allocation, related state must be updated.

Conceptually:

Incident INC-001
    |
    ├── assignedAmbulanceId = AMB-001
    ├── assignedHospitalId = HOSP-001
    └── status = ALLOCATED

and:

Ambulance AMB-001
    |
    ├── assignedIncidentId = INC-001
    └── status = BUSY

The implementation must consider consistency between these updates.

The exact DynamoDB update/transaction strategy will be determined during backend implementation.

19. Incident Lifecycle Architecture

The initial lifecycle is:

CREATED
   ↓
PENDING
   ↓
ALLOCATED
   ↓
IN_PROGRESS
   ↓
RESOLVED

The Minor should keep this workflow simple.

The Major may introduce more sophisticated workflow orchestration.

20. Authentication Architecture

The Minor requires basic authentication.

Conceptually:

User
 ↓
React Login
 ↓
POST /auth/login
 ↓
API Gateway
 ↓
Lambda
 ↓
Authentication Validation
 ↓
Response
 ↓
React

Plain-text passwords must never be stored.

The exact authentication implementation will be established during backend development.

The Major may later introduce Amazon Cognito and more advanced authorization.

21. Security Architecture

The intended Minor trust boundary is:

User
 ↓
React
 ↓
API Gateway
 ↓
Lambda
 ↓
DynamoDB

The frontend should not directly access DynamoDB.

Backend operations should pass through the API/application layer.

Security principles:

No plain-text passwords

No hardcoded secrets

No hardcoded API keys

Validate API input

Use appropriate IAM permissions

Keep secrets out of source control

Avoid exposing unnecessary data

The project must not claim production-grade security unless it has actually been implemented.

22. Minor AWS Boundary

The following are intentionally not required for the Minor:

EventBridge

SQS

Dead Letter Queue

Step Functions

SNS

AWS Glue

Athena

ML systems

Complex monitoring infrastructure

S3 may be used in the Minor only if a genuine requirement appears.

The Minor should remain focused on:

React
 ↓
API Gateway
 ↓
Lambda
 ↓
DynamoDB

23. Major Architecture — Planned Evolution

The Major extends the Minor architecture.

A planned direction is:

                    ┌───────────────┐
                    │     React     │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │  CloudFront   │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │ API Gateway   │
                    └───────┬───────┘
                            ↓
                    ┌───────────────┐
                    │    Lambda     │
                    └───────┬───────┘
                            │
               ┌────────────┼────────────┐
               ↓            ↓            ↓
          DynamoDB         S3         Cognito
               │
               ↓
          EventBridge
               │
               ↓
              SQS
               │
               ↓
    Resource Allocation Processing
               │
               ↓
         Step Functions
               │
               ↓
              SNS

This is planned architecture, not current implementation.

24. Major Event-Driven Evolution

The Minor is primarily synchronous:

Request
 ↓
API Gateway
 ↓
Lambda
 ↓
DynamoDB
 ↓
Response

The Major may introduce asynchronous processing:

Incident Created
      ↓
EventBridge
      ↓
SQS
      ↓
Allocation Processor
      ↓
Resource Allocation

Benefits that may be demonstrated:

Decoupling

Asynchronous processing

Retry handling

Failure isolation

Dead-letter recovery

Event-driven workflows

These are Major capabilities.

25. Major Step Functions Evolution

Step Functions may later orchestrate multi-step workflows.

Possible conceptual flow:

Incident
   ↓
Validate
   ↓
Find Ambulance
   ↓
Find Hospital
   ↓
Confirm Allocation
   ↓
Update State
   ↓
Notify

Step Functions are not required in the Minor.

26. Major Notification Evolution

SNS may later be used for notifications.

Conceptually:

Allocation / Status Event
        ↓
       SNS
        ↓
Notifications

The exact notification requirements will be designed during the Major stage.

SNS is not required for the Minor.

27. Major Historical Data Architecture

The Major may introduce an analytics pipeline:

Operational / Historical Data
            ↓
           S3
            ↓
          Glue
            ↓
         Athena
            ↓
    Analytics Dashboard

Potential analytics:

Incident trends

Emergency type frequency

Resource utilization

Average allocation distance

Hospital utilization

Ambulance utilization

Resource demand patterns

These are Major possibilities.

They are not part of the Minor MVP.

28. Major Monitoring Architecture

CloudWatch may later be used for advanced monitoring.

Potential monitoring areas:

Lambda errors

API failures

Execution metrics

Event processing

Resource processing

Operational alerts

The Minor should not build unnecessarily complex monitoring.

29. Major Security Evolution

The Major may improve security using:

Amazon Cognito

More detailed authorization

Improved IAM policies

Least-privilege access

Better secret management

Audit logging

Better authentication workflows

These improvements should be introduced when they have a clear requirement.

30. Optional Third-Party API Architecture for Major

The Major may optionally use a third-party routing/mapping API.

Possible architecture:

Incident coordinates
        +
Ambulance coordinates
        ↓
Allocation Lambda
        ↓
Third-Party Routing API
        ↓
Road distance / ETA
        ↓
Allocation Engine

Potential benefit:

Road distance instead of straight-line distance

Estimated travel time

Route information

Potentially more realistic resource ranking

However:

A third-party API is not currently approved as a required Major component.

It is an optional future design decision.

Before using one, the project must evaluate:

Technical value

Cost

Rate limits

Reliability

Security

API key handling

Error handling

Fallback behavior

Architectural impact

The system must never depend on an external API simply to appear more advanced.

31. Minor → Major Architectural Mapping

Minor

Major Evolution

React

Continue and extend

API Gateway

Continue and extend

Lambda

Continue, split, and extend where justified

DynamoDB

Continue

Basic authentication

Cognito / advanced authorization

Synchronous processing

Event-driven processing

Direct Lambda workflow

EventBridge + SQS

Basic allocation

More advanced allocation workflow

Basic state updates

Step Functions where justified

No notification system

SNS

Operational data

Historical S3 data

No analytics pipeline

Glue + Athena

Basic/limited monitoring

CloudWatch

Simulated coordinates

Optional routing API if justified

Basic error handling

Retry + DLQ + recovery workflows

32. Deployment Architecture Direction

The Minor deployment direction is:

Developer
    ↓
GitHub Repository
    ↓
Frontend + Backend Code
    ↓
AWS Resources
    ↓
Working Cloud Prototype

The exact deployment tooling will be selected during implementation.

A complex CI/CD system should not be introduced unless it provides clear project value.

The Major may improve deployment and infrastructure management if required.

33. Local Development Architecture

Current frontend:

React + Vite

Current local address:

http://localhost:5173/

Current repository structure:

emergency-resource-allocation-platform
│
├── backend/
│   └── functions/
│       ├── auth/
│       ├── incidents/
│       ├── ambulances/
│       ├── hospitals/
│       └── allocation/
│
├── docs/
│
├── frontend/
│
├── infrastructure/
│
└── README.md

AWS integration will be introduced incrementally.

34. Error Handling Architecture

The Minor should provide basic validation and application-level error handling.

Examples:

Invalid incident input
        ↓
Validation error

No suitable ambulance
        ↓
Allocation failure response

No suitable hospital
        ↓
Allocation failure response

The Major may later add:

Event failure
    ↓
Retry
    ↓
SQS
    ↓
DLQ if required
    ↓
Monitoring / recovery

Advanced failure workflows are Major extensions.

35. Data Ownership and Responsibility

React

Responsible for:

User interaction

Form input

Display

API calls

API Gateway

Responsible for:

HTTP/API entry

Routing requests to backend

Lambda

Responsible for:

Validation

Business logic

Runtime calculations

Allocation decisions

Database interaction

DynamoDB

Responsible for:

Persistent operational state

External APIs

If introduced later:

Provide specific external functionality

Must not become an uncontrolled source of core application logic

36. Architecture Anti-Patterns

The project should avoid:

36.1 Service Sprawl

Do not add AWS services without a real requirement.

36.2 Frontend Allocation Logic

Do not put the authoritative Resource Allocation Engine only in React.

36.3 Direct Frontend-to-DynamoDB Access

The frontend should use the API/backend layer.

36.4 Hardcoded Secrets

Never put passwords, API keys, tokens, or secrets in source code.

36.5 Premature Event-Driven Complexity

Do not add EventBridge/SQS/Step Functions during the Minor just because they are available.

36.6 Premature External APIs

Do not add a mapping/routing API until its value has been established.

36.7 Major Rebuild

Do not rebuild the Minor from scratch when entering the Major.

36.8 Confusing Internal and External APIs

The project has its own APIs.

A third-party API is an optional external dependency.

These are separate concepts.

37. Architecture Decision Status

Approved / Current

React + Vite

API Gateway

AWS Lambda

DynamoDB

Four logical entities

Two Minor roles

Serverless Minor architecture

Runtime distance calculation

Backend Resource Allocation Engine

No required third-party API for Minor

Planned Major

CloudFront

EventBridge

SQS

DLQ

Step Functions

SNS

Cognito

Advanced IAM

CloudWatch

S3 historical data

Glue

Athena

Analytics

Advanced event-driven architecture

Optional / Not Yet Approved

Third-party routing/mapping API

ML for severity prediction

ML for emergency/resource demand prediction

Other future services not yet justified

38. Architecture Evolution Principle

The intended evolution is:

MINOR

Simple synchronous serverless application
        ↓
Working emergency resource allocation prototype

then:

MAJOR

Extended cloud-native architecture
        ↓
Event-driven processing
        ↓
Advanced workflows
        ↓
Improved reliability
        ↓
Analytics
        ↓
Monitoring
        ↓
Optional intelligence / external integrations

The Major demonstrates architectural maturity rather than simply increasing the number of services.

39. Current Implementation Status

Completed

GitHub repository

Local repository

Git verification

Node/npm verification

React + Vite setup

Local frontend verification

Minor scope approval

Database model approval

Initial project folder structure

Project Master Specification

Not yet implemented

DynamoDB tables

Lambda backend functions

API Gateway deployment

Authentication implementation

Incident APIs

Ambulance APIs

Hospital APIs

Allocation endpoint

Final allocation scoring formula

AWS deployment

Major event-driven services

External API integration

The architecture described for future components is design intent, not evidence that those components are already deployed.

40. Architecture Change Control

Any significant architectural change should be evaluated using:

Existing architecture

Proposed architecture

Technical reason

Benefits

Drawbacks

Cost impact

Security impact

Complexity impact

Minor impact

Major impact

Migration/reuse impact

No architectural change should silently invalidate the Minor foundation.

41. AI Continuation Instructions

Any AI assistant continuing this project should use this architecture document together with the Project Master Specification.

The AI must:

Preserve the approved Minor architecture unless a change is explicitly discussed.

Understand that API Gateway APIs are our own application APIs.

Understand that "no third-party API" does not mean "no APIs."

Treat third-party APIs as optional Major possibilities, not mandatory requirements.

Keep the Resource Allocation Engine in the backend.

Keep DynamoDB as the Minor operational state store.

Keep distance as a runtime calculation rather than permanent source-of-truth data.

Avoid adding Major services during Minor implementation.

Extend working Minor components when developing the Major.

Avoid unnecessary rewrites.

Preserve security principles.

Follow incremental development and verification.

Distinguish current implementation from planned architecture.

Never claim a component is deployed or working unless it has actually been verified.

Explain architectural trade-offs before proposing major changes.

Preserve the Minor → Major evolution strategy.

Do not introduce a third-party API unless its value and operational implications have been evaluated.

Keep the project framed as an academic prototype/simulation.

42. Final Architecture Summary

Minor

                    ┌───────────────┐
                    │     React     │
                    │   Frontend    │
                    └───────┬───────┘
                            │
                            ↓
                    ┌───────────────┐
                    │ API Gateway   │
                    │  Our APIs     │
                    └───────┬───────┘
                            │
                            ↓
                    ┌───────────────┐
                    │    Lambda     │
                    │               │
                    │ Business Logic│
                    │ Allocation    │
                    └───────┬───────┘
                            │
                            ↓
                    ┌───────────────┐
                    │   DynamoDB    │
                    │               │
                    │ Users         │
                    │ Incidents     │
                    │ Ambulances    │
                    │ Hospitals     │
                    └───────────────┘

Major

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
Allocation Processing
  ↓
Step Functions
  ↓
SNS

Historical:
S3 → Glue → Athena → Analytics

Monitoring:
CloudWatch

Optional:
Third-party Routing/Mapping API

The Major architecture is a planned evolution.

It should be implemented only after the Minor system is working and verified.

End of Architecture Specification
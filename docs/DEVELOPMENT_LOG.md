DEVELOPMENT LOG

Emergency Response & Resource Allocation Platform Using Cloud-Native Architecture

Project: Emergency Response & Resource Allocation Platform Using
Cloud-Native Architecture
Stage: Minor Project
Repository: emergency-resource-allocation-platform
Development Environment: Windows + VS Code
Frontend: React + Vite
Backend: AWS API Gateway + AWS Lambda
Database: Amazon DynamoDB

1. Purpose

This document records the actual development history of the project.

It is a living engineering log and will be updated throughout
development.

It records:

implementation work

technical decisions

changes

errors

debugging

fixes

verification

milestones

important development observations

This document must reflect actual work performed.

No fabricated commits, contributors, implementation history, or test
results should be added.

2. Project Starting State

The project planning and design phase was completed before backend
implementation began.

Completed Project Documents

PROJECT_MASTER_SPEC.md

ARCHITECTURE.md

DATABASE_AND_API_SPEC.md

DEVELOPMENT_LOG.md

Approved Project Direction

The project is being developed as a Minor Project that will later be
extended into the Major Project.

The Major Project will extend the same working Minor system rather than
rebuilding it from scratch.

3. Approved Minor Architecture

The approved Minor architecture is:

React Frontend
      ↓
Amazon API Gateway
      ↓
AWS Lambda
      ↓
Amazon DynamoDB
      ↓
Resource Allocation Logic

The Minor does not require third-party mapping or routing APIs.

Incident, ambulance, and hospital locations use latitude and longitude.

Approximate geographical distance will be calculated inside the backend
using the stored coordinates.

4. Approved Minor Roles

The Minor contains exactly two roles:

DISPATCHER
RESOURCE_OPERATOR

There is no separate Admin role in the Minor.

5. Approved Minor Entities

The Minor uses four logical DynamoDB entities:

Users
Incidents
Ambulances
Hospitals

6. Approved API Contract

The initial approved API contract is:

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

The allocation endpoint is a core part of the Minor Project.

7. Development Environment

The project is being developed on Windows using VS Code.

The known development versions at the start of the implementation phase
are:

Git: 2.54.0.windows.1
Node: v24.15.0
npm: 11.12.1
Vite: v8.2.2

Project location:

C:\Users\tomax\Projects\emergency-resource-allocation-platform

8. Repository Setup

The GitHub repository is:

emergency-resource-allocation-platform

The repository is public and has been cloned locally.

The working branch is:

main

At the documentation baseline, the working tree was clean and
synchronized with the remote repository.

Git history must represent actual work performed.

9. Frontend Setup

The React frontend was created using Vite.

Frontend location:

frontend

The frontend was created with:

npm create vite@latest frontend -- --template react

ESLint was selected during setup.

Dependencies were installed successfully.

The frontend was successfully tested using:

http://localhost:5173/

The Vite development server worked successfully.

Important Development Rule

The working React frontend must not be unnecessarily recreated,
reinstalled, or replaced.

10. Project Folder Structure

The planned project structure is:

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
│   ├── PROJECT_MASTER_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE_AND_API_SPEC.md
│   └── DEVELOPMENT_LOG.md
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

At the folder-structure stage, implementation files were intentionally
not created before their implementation phase.

11. Development History

2026-09-04 --- Project Documentation and Development Baseline

Objective

Complete the project documentation baseline and establish the starting
point for implementation.

Work Completed

Project concept finalized.

Minor → Major strategy finalized.

Minor roles finalized.

Minor feature scope finalized.

Minor architecture finalized.

API strategy clarified.

Third-party API policy clarified.

Database entities finalized.

Initial API list finalized.

Incident lifecycle finalized.

Resource Allocation Engine concept finalized.

Local development environment established.

Git installed/configured.

GitHub repository created and cloned.

React/Vite frontend created.

Frontend dependencies installed.

Frontend successfully tested.

Project folder structure created.

Documentation strategy finalized.

PROJECT_MASTER_SPEC.md completed.

ARCHITECTURE.md completed.

DATABASE_AND_API_SPEC.md completed.

DEVELOPMENT_LOG.md created.

Important Decisions Recorded

Minor contains only Dispatcher and Resource Operator roles.

Minor uses Users, Incidents, Ambulances, and Hospitals as logical
entities.

Minor architecture uses React, API Gateway, Lambda, and DynamoDB.

Minor does not require a third-party external API.

Latitude and longitude are stored for relevant resources.

Approximate distance is calculated by backend logic.

Major will extend the Minor rather than rebuild it.

Allocation scoring will be designed and finalized when allocation
implementation begins.

Verification

Frontend development server successfully opened at:

http://localhost:5173/

The frontend was confirmed working before moving toward backend
implementation.

Status

COMPLETED

12. Future Development Entry Format

Every significant future development activity should be recorded using
this structure:

YYYY-MM-DD --- Milestone/Task Name

Objective

What we intended to accomplish.

Work Completed

What was actually implemented.

Files Changed

Files created, modified, or deleted.

Technical Decisions

Important decisions made during implementation.

Issues

Actual errors or unexpected behavior encountered.

Fix

How the issue was diagnosed and resolved.

Verification

How the implementation was tested and the observed result.

Status

COMPLETED

or:

IN PROGRESS

or:

BLOCKED

13. Engineering Rules for Development

The following rules apply throughout implementation:

Work incrementally.

Verify meaningful changes.

Do not rebuild working components unnecessarily.

Diagnose actual errors before changing working architecture.

Do not expose secrets.

Keep AWS costs low.

Keep the Minor implementation understandable.

Preserve the approved architecture unless a change is explicitly
justified.

Ensure the Major extends the Minor.

Record important technical decisions honestly.

Do not fabricate development history.

Do not claim a feature is complete until it has been implemented and
verified.

14. Major Project Extension

The Major Project may extend the Minor with services and capabilities
such as:

Amazon EventBridge

Amazon SQS

Dead Letter Queue

AWS Step Functions

Amazon SNS

Amazon Cognito

CloudWatch

Amazon S3

AWS Glue

Amazon Athena

historical analytics

audit logging

optional routing/mapping integration

These services must only be introduced when there is a clear technical
purpose.

The Major should build on the Minor's existing working components.

15. Current Project Status

Project planning                  COMPLETE
Architecture definition           COMPLETE
Database/API specification        COMPLETE
Frontend setup                    COMPLETE
Frontend verification             COMPLETE
Development log                   COMPLETE
Backend implementation            NOT STARTED
DynamoDB implementation           NOT STARTED
API Gateway implementation        NOT STARTED
Authentication implementation     NOT STARTED
Incident API implementation       NOT STARTED
Ambulance API implementation      NOT STARTED
Hospital API implementation       NOT STARTED
Allocation engine implementation  NOT STARTED
Frontend-backend integration      NOT STARTED
End-to-end testing                NOT STARTED
AWS deployment                    NOT STARTED

16. Next Development Milestone

The next milestone is:

Backend development foundation

Implementation will proceed one verified step at a time.

17. Change Control

Changes that affect the approved architecture or API contract should be
recorded and discussed before implementation.

Examples include:

adding or removing a core entity

changing an approved endpoint

changing required API fields

changing role definitions

changing status values

replacing DynamoDB

adding a third-party API

introducing additional AWS services into the Minor

substantially changing the allocation engine

Implementation-level fixes that improve correctness, security, or
maintainability may be made without redesigning the project.

18. Documentation Relationship

The four project documents have different purposes:

| Document | Purpose |
|---|---|
| `PROJECT_MASTER_SPEC.md` | Defines what the project is |
| `ARCHITECTURE.md` | Defines how the system is architected |
| `DATABASE_AND_API_SPEC.md` | Defines the database model and API contracts |
| `DEVELOPMENT_LOG.md` | Records what was actually built and verified |

These documents should remain consistent with one another.

`DEVELOPMENT_LOG.md` should record implementation reality rather than becoming another planning document.
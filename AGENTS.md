# AGENTS.md

## Project

This repository contains the Cyclone project.

The following documents are the authoritative sources for the project:

- `Cyclone_Business_Requirements_Document.docx`
- `Cyclone_GCP_Gemini_Technical_Design_Document.docx`
- `Cyclone_GCP_Gemini_Phase_by_Phase_Implementation_Plan.docx`

Read these documents before making significant implementation decisions.

---

## Source of Truth

Use the documents in this order:

1. Business requirements → what needs to be built
2. Technical design → how it should be built
3. Implementation plan → when/how it should be implemented

Do not invent major requirements or features that are not supported by the documents.

If the documents contain an ambiguity that affects implementation, identify it rather than silently inventing a solution.

If implementation intentionally deviates from the documents, document the reason.

---

## Development Approach

Build the system incrementally according to the implementation plan.

DO NOT implement the entire project in one pass.

For each phase:

1. Understand the requirements.
2. Implement only the required scope.
3. Add/update tests.
4. Run the tests.
5. Verify the application locally.
6. Update documentation.
7. Review and simplify the implementation.
8. Only then proceed to the next phase.

Every completed phase should leave the repository runnable.

Do not break functionality from previous phases.

---

## Code Quality

Write clean, maintainable and production-quality code.

Prefer:

- simple implementations
- readable code
- small focused functions
- clear naming
- strong separation of concerns
- type safety where appropriate
- testable components
- meaningful error handling
- structured logging
- minimal dependencies

Avoid:

- unnecessary abstractions
- premature optimization
- duplicated logic
- giant functions/classes
- dead code
- commented-out code
- magic values
- unnecessary design patterns
- unnecessary dependencies

Follow the principle:

> Prefer the simplest design that satisfies the documented requirements.

---

## Architecture

Follow the architecture defined in the Technical Design Document.

Keep business logic separated from infrastructure and external services where practical.

Avoid tightly coupling core business logic to:

- GCP SDKs
- Gemini APIs
- databases
- external APIs
- UI/framework-specific code

Use interfaces/abstractions only where they provide a real benefit.

Do not introduce architectural patterns simply for the sake of abstraction.

---

## GCP and Gemini

GCP and Gemini integrations must be configuration-driven.

Never hardcode:

- API keys
- passwords
- tokens
- service-account credentials
- secrets
- private keys

Use environment variables or the authentication mechanism defined by the technical design.

Keep cloud-specific functionality isolated where practical.

The application should remain runnable locally wherever possible.

When a GCP service cannot reasonably be run locally:

- provide a mock/emulator/test implementation where appropriate
- clearly document the limitation
- keep external-service tests separate from normal unit tests

---

## Local Development

Local execution is a core requirement.

A developer should be able to:

1. Install dependencies.
2. Configure environment variables.
3. Start the application.
4. Run tests.
5. Exercise the core functionality locally.

Maintain:

`.env.example`

Never commit real `.env` files or credentials.

Document all required setup commands in `README.md`.

---

## Testing

Testing must be implemented alongside functionality.

Use appropriate levels of testing:

- Unit tests
- Integration tests
- End-to-end tests for important workflows

Tests should be deterministic and runnable locally.

External GCP/Gemini services should be mocked where appropriate for unit tests.

Do not make the complete test suite dependent on live paid services unless explicitly required.

After every meaningful implementation:

- run existing tests
- run new tests
- fix regressions
- verify local execution

---

## Documentation

Maintain `README.md` throughout development.

The README must accurately describe the current state of the project.

Keep it updated with:

- project introduction
- problem statement
- key features
- architecture
- technology stack
- project structure
- prerequisites
- local setup
- environment variables
- running locally
- testing
- implementation status
- deployment instructions when applicable

Do not document functionality that has not been implemented.

---

## Project Structure

Keep the repository organized and predictable.

Prefer clear separation between:

- application/business logic
- APIs/interfaces
- data access
- external integrations
- GCP services
- Gemini services
- configuration
- tests
- scripts

Do not create directories or layers unless they serve a clear purpose.

---

## Configuration

Configuration must be environment-driven.

Use:

`.env.example`

for documenting required variables.

Never hardcode environment-specific values.

Keep development, testing and production configuration separable.

---

## Error Handling

Errors should be handled explicitly.

Do not silently swallow exceptions.

At system boundaries:

- validate inputs
- return meaningful errors
- log useful diagnostic information
- never expose secrets

Avoid broad exception handling unless there is a clear reason.

---

## Logging and Observability

Use structured and useful logging where appropriate.

Logs should help diagnose:

- application failures
- integration failures
- important processing steps
- unexpected conditions

Do not log:

- passwords
- API keys
- tokens
- credentials
- sensitive user data

Do not introduce unnecessary observability infrastructure unless required by the technical design.

---

## Performance

Optimize based on actual requirements and measurable bottlenecks.

Prefer:

- efficient data processing
- avoiding unnecessary network calls
- batching where appropriate
- asynchronous processing where justified
- sensible caching where justified

Do not sacrifice readability for insignificant performance improvements.

Avoid premature optimization.

---

## Code Review Before Completion

Before considering a phase complete, review the implementation for:

- duplicated code
- unnecessary abstractions
- unnecessary dependencies
- overly complex logic
- missing error handling
- missing tests
- hardcoded configuration
- security issues
- documentation gaps

Simplify where possible without changing required behavior.

---

## Git-Friendly Changes

Keep changes logically grouped.

Avoid mixing unrelated changes.

Prefer commits such as:

- `feat: add cyclone data ingestion`
- `feat: add cyclone risk analysis`
- `test: add ingestion tests`
- `docs: update local setup`
- `refactor: simplify data processing`

Do not make large unrelated changes without justification.

---

## Phase Completion

Before declaring a phase complete, verify:

- [ ] Requirements for the phase are implemented
- [ ] Tests are present
- [ ] Existing tests pass
- [ ] New tests pass
- [ ] Application runs locally
- [ ] No secrets are committed
- [ ] README is updated
- [ ] Configuration documentation is updated
- [ ] Code has been reviewed for unnecessary complexity
- [ ] Previous functionality still works

Then provide a concise completion summary.

---

## Important Rule

Do not move ahead just to produce more code.

A smaller, tested, understandable implementation is preferable to a large incomplete implementation.

Build incrementally.

Keep the project runnable.

Keep the code simple.

Keep the documentation accurate.
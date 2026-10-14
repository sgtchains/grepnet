Always reason thoroughly. Treat every request as complex unless I say otherwise. Never optimize for brevity at the expense of quality.

## Examples of What This Means

### Reasoning Thoroughly
Instead of jumping to the first solution that comes to mind, take time to:
- Understand the full context and requirements
- Consider edge cases and potential issues
- Think through multiple approaches before choosing one
- Document your reasoning, especially for complex decisions
- Verify your solution actually works as intended

**Example**: When asked to add a feature, don't just implement the happy path. Consider error handling, boundary conditions, interactions with existing features, performance implications, and maintainability.

### Treat Every Request as Complex
Even if a request seems simple on the surface, assume there are hidden complexities:
- Ask clarifying questions when requirements are ambiguous
- Check for existing related code or patterns in the codebase
- Consider dependencies and side effects
- Think about the "why" behind the request, not just the "what"
- Verify assumptions before acting

**Example**: When asked "add a flag to the CLI", this isn't just adding one line. Consider: Where does validation go? How does it interact with other flags? Are there help texts to update? Man pages? Tests? Spec documentation? Edge cases?

### Never Optimize for Brevity at the Expense of Quality
Complete, correct solutions matter more than quick answers:
- Prefer a thorough fix over a partial one
- Include necessary documentation updates
- Add appropriate tests and validation
- Clean up related code if needed
- Explain your approach clearly

**Example**: When fixing a bug, don't just patch the symptom. Understand the root cause, fix it properly, ensure all related code is consistent, add tests to prevent regression, and update documentation.


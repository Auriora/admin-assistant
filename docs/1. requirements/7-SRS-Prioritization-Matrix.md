# 7. Requirements Prioritization Matrix

This section provides a comprehensive framework for prioritizing requirements based on their importance, complexity, and value. Use this matrix to make informed decisions about what to implement and in what order.

## How to Use This Matrix

1. **List all requirements** in the table below, using their unique IDs
2. **Assign a MoSCoW priority** to each requirement:
   - **Must Have**: Critical requirements without which the system will not function
   - **Should Have**: Important requirements that should be included if possible
   - **Could Have**: Desirable requirements that can be omitted if necessary
   - **Won't Have**: Requirements that will not be implemented in the current version
3. **Rate the complexity** of implementing each requirement on a scale of 1-5:
   - **1**: Very simple, can be implemented quickly with minimal effort
   - **2**: Simple, requires moderate effort but no significant challenges
   - **3**: Moderate, requires significant effort but is well understood
   - **4**: Complex, requires substantial effort and may involve technical challenges
   - **5**: Very complex, requires extensive effort and involves significant technical challenges
4. **Rate the value** of each requirement on a scale of 1-5:
   - **1**: Minimal value, nice to have but not essential
   - **2**: Low value, provides some benefit to users
   - **3**: Moderate value, provides significant benefit to users
   - **4**: High value, provides substantial benefit to users
   - **5**: Critical value, essential for meeting user needs
5. **Calculate the Value/Complexity Ratio** (optional but helpful):
   - Divide the Value rating by the Complexity rating
   - Higher ratios indicate better "bang for your buck"
6. **Determine the implementation order** based on:
   - MoSCoW priority (implement "Must Have" items first)
   - Value/Complexity ratio (higher ratios should generally be implemented earlier)
   - Dependencies between requirements
7. **Document your rationale** for prioritization decisions

## Prioritization Matrix Template

| Requirement ID | Priority (MoSCoW) | Complexity (1-5) | Value (1-5) | Value/Complexity Ratio | Implementation Order | Rationale/Notes |
|----------------|-------------------|------------------|-------------|------------------------|----------------------|-----------------|
| <ID>           | <Priority>        | <Complexity>     | <Value>     | <Ratio>                | <Order>              | <Notes>         |

## Prioritization Strategies

Consider these strategies when prioritizing requirements:

1. **Risk-based prioritization**: Implement high-risk items early to address uncertainties
2. **Value-driven prioritization**: Focus on high-value items first to deliver business benefits quickly
3. **Dependency-based prioritization**: Implement prerequisites before dependent requirements
4. **Technical foundation prioritization**: Build core technical components before features that rely on them

## AI Assistance for Prioritization

Use these prompts with your AI assistant to help with the prioritization process:

- "Help me assess the complexity of implementing [requirement] on a scale of 1-5."
- "What would be the business or user value of [requirement] on a scale of 1-5?"
- "Are there any dependencies I should consider between these requirements?"
- "Based on these ratings, what would be a logical implementation order?"
- "What risks should I consider when prioritizing [requirement]?"
- "How might the complexity change if I implement [requirement A] before [requirement B]?"

## Example: Completed Prioritization Matrix

Here's an example of a completed prioritization matrix for a generic system:

| Requirement ID | Priority (MoSCoW) | Complexity (1-5) | Value (1-5) | Value/Complexity Ratio | Implementation Order | Rationale/Notes |
|----------------|-------------------|------------------|-------------|------------------------|----------------------|-----------------|
| FR-DOC-001     | Must Have         | 3                | 5           | 1.67                   | 1                    | Integration is core functionality needed for the system to work |
| FR-USR-001     | Must Have         | 2                | 5           | 2.5                    | 2                    | User authentication is essential for security and access control |
| NFR-SEC-001    | Must Have         | 2                | 5           | 2.5                    | 3                    | HTTPS is required for secure communications |

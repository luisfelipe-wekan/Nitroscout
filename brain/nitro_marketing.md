# NitroStack Knowledge Base

## 1. Identity & Purpose (What is NitroStack?)
**NitroStack** is the premier production-ready, open-source framework for building **Model Context Protocol (MCP)** servers using TypeScript.

While early MCP implementations were often simple, single-file scripts suitable for prototyping, NitroStack allows for the creation of **enterprise-grade AI infrastructure**. It draws deep inspiration from **NestJS and Angular** to bring robustness and modularity to the emerging world of AI agentic tools.

* **Core Mission:** To professionalize and standardize the development of MCP servers. 
* **Key Technology Stack:**
    * **TypeScript:** Native support for static typing.
    * **Decorators:** Declarative code style for defining tools and resources.
    * **Dependency Injection (DI):** Efficient management of service dependencies.
    * **Zod Validation:** Runtime schema validation for AI inputs.
    * **Model Context Protocol:** Full compliance with the open standard.

---

## 2. Core Philosophy (Why use NitroStack?)
As AI agents move from "toy" demos to mission-critical business applications, NitroStack addresses architectural rigor through several key pillars:

### Type Safety as a First Principle
NitroStack deeply integrates with **Zod schemas**, automatically inferring TypeScript types from runtime validation. This prevents "garbage in, garbage out" scenarios and reduces hallucinations caused by malformed data.

### Modular Architecture for Scalability
Using a **Module system** (e.g., `DatabaseModule`, `SlackModule`), large teams can work on different parts of a complex system simultaneously without conflict.

### Production Readiness
* **Structured Logging:** JSON-formatted logs for observability.
* **Global Exception Filters:** Uniform error responses to the AI client.
* **Lifecycle Events:** Hooks like `onModuleInit` and `onModuleDestroy` for managing resources like database connections.

### Superior Developer Experience (DX)
The framework includes a CLI for scaffolding and a development server that supports **Hot Module Replacement (HMR)** for immediate testing with LLMs.

---

## 3. Architecture & Mechanics (How it works?)
NitroStack operates on a Decorator-based architecture utilizing **Inversion of Control (IoC)**.

### 3.1 The Application Graph
* **@McpApp:** The root decorator defining the application entry point and configuration.
* **@Module:** The organizational unit grouping related Controllers and Providers.
* **McpApplicationFactory:** The bootstrap utility that creates the runtime instance and establishes the transport layer (stdio or SSE).

### 3.2 Request Lifecycle
Requests flow through a sophisticated pipeline:
1.  **Transport Layer:** Raw JSON-RPC message received.
2.  **Router:** Determines the appropriate handler.
3.  **Guards:** Gatekeepers for authorization.
4.  **Interceptors:** Wraps execution for logging or data transformation.
5.  **Pipes:** Enforces Zod validation schemas.
6.  **Handler:** Executes the business logic.
7.  **Response Handling:** Serializes results back to the MCP format.

---

## 4. Key Components (The "Building Blocks")

### 4.1 Tools (@Tool)
Tools are the "hands" of the agent—executable functions.
* **Structure:** Defined as methods within a class, allowing access to injected services.
* **Example:**
    ```typescript
    @Tool({
      name: 'register_user',
      description: 'Registers a new user.',
      inputSchema: z.object({ email: z.string().email() })
    })
    async register(input: RegisterDto) { ... }
    ```

### 4.2 Resources (@Resource)
Resources are the "eyes" of the agent—read-only data sources.
* **URI Templates:** Supports dynamic patterns like `file://logs/{date}`.
* **Mime Types:** Helps the LLM understand how to parse the data (e.g., `text/plain`).

### 4.3 Prompts (@Prompt)
Reusable templates that standardize interaction, allowing for dynamic template generation using arguments (e.g., a "debug-error" prompt).

### 4.4 Authentication (@Guard)
* **API Key Auth:** Simple secret validation.
* **OAuth 2.1:** For user-facing integrations where the agent acts on behalf of a user.
* **Custom Guards:** Logic for IP allow-listing or JWT verification.

---

## 5. Development Workflow

### 5.1 CLI Commands
* `nitro init <name>`: Scaffolds a new project.
* `nitro dev`: Starts the server in watch mode.
* `nitro build`: Creates a production-ready bundle.
* `nitro generate <schematic>`: Generates modules or tools automatically.

### 5.2 Testing Strategy
Utilizes `@nitrostack/core/testing` to provide:
* **TestingModule:** For overriding real providers with mocks.
* **createMockContext:** To simulate tool execution and assert logs or progress updates.

---

## 6. Deployment

### 6.1 Scenarios
* **Complex Tool Sets:** Managing multi-domain agents (AWS, GitHub, Jira).
* **Enterprise Integration:** High-compliance environments requiring strict validation.
* **Team Development:** Facilitating parallel workflows via strict contracts.

### 6.2 Hosting
* **Docker:** Standard containerization for Node.js.
* **Serverless:** Deployment via adaptors for AWS Lambda or Vercel.
* **Edge:** Lightweight runtime support for Cloudflare Workers.

---

## 7. Quick Reference: Best Practices
* **One Module per Domain:** Adhere to separation of concerns.
* **Strict Zod Schemas:** Use `.describe()` heavily; LLMs use these instructions.
* **Interceptors for Logging:** Don't clutter business logic with manual logs.
* **Secure via Guards:** Protect mutating tools from unauthorized execution.
* **Thin Handlers:** Keep logic in `@Injectable()` services, not the tool itself.
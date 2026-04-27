# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run setup          # Install deps + generate Prisma client + run migrations (first-time setup)
npm run dev            # Start dev server with Turbopack at http://localhost:3000
npm run build          # Production build
npm run lint           # ESLint
npm test               # Run Vitest tests (all)
npx vitest run src/lib/__tests__/file-system.test.ts  # Run a single test file
npm run db:reset       # Reset SQLite database (destructive)
```

All `next` commands must use `NODE_OPTIONS='--require ./node-compat.cjs'` (handled by npm scripts — do not run `next` directly).

## Architecture

UIGen is an AI-powered React component generator. Users describe components in chat; the AI generates/edits code in a virtual file system; a live preview renders the result in an iframe.

### Request flow

1. User sends a chat message → `POST /api/chat`
2. The API route streams a response via Vercel AI SDK (`streamText`) using `claude-haiku-4-5` (or `MockLanguageModel` if no API key)
3. The AI calls two tools to modify the virtual file system:
   - `str_replace_editor` — create/str_replace/insert in files
   - `file_manager` — rename/delete files
4. Tool call events stream back to the client via `result.toDataStreamResponse()`
5. `FileSystemContext` (`handleToolCall`) processes each tool call and updates the in-memory `VirtualFileSystem`
6. `PreviewFrame` reacts to `refreshTrigger`, calls `createImportMap()` + `createPreviewHTML()`, and sets the iframe `srcdoc`

### Key modules

| Path | Role |
|------|------|
| `src/app/api/chat/route.ts` | Streaming AI endpoint; persists to DB on finish |
| `src/lib/file-system.ts` | `VirtualFileSystem` class — in-memory tree, serialize/deserialize |
| `src/lib/transform/jsx-transformer.ts` | Babel-transforms JSX/TSX → blob URLs; builds import map; generates preview HTML |
| `src/lib/provider.ts` | `getLanguageModel()` — returns real Anthropic model or `MockLanguageModel` |
| `src/lib/contexts/file-system-context.tsx` | React context wrapping `VirtualFileSystem`; dispatches tool calls |
| `src/lib/contexts/chat-context.tsx` | Wraps Vercel AI SDK `useChat`; feeds tool call results to file system |
| `src/lib/auth.ts` | JWT sessions via `jose` (server-only); stored in httpOnly cookies |
| `src/middleware.ts` | Protects `/api/projects` and `/api/filesystem` routes |
| `src/lib/prompts/generation.tsx` | System prompt for component generation |
| `prisma/schema.prisma` | SQLite: `User` + `Project` (messages and file data stored as JSON strings) |

### Preview rendering

The preview runs entirely client-side in a sandboxed iframe. `createImportMap()` in `jsx-transformer.ts`:
- Babel-transforms all JS/JSX/TS/TSX files to ES modules and wraps them as blob URLs
- Resolves `@/` path aliases
- Stubs missing local imports with placeholder components
- Maps third-party packages to `https://esm.sh/<pkg>`
- Injects Tailwind CSS from CDN

The entry point is `/App.jsx` by default (auto-selected by `FileSystemContext`).

### Auth

- JWT-based, no third-party auth library
- Sessions expire in 7 days; stored in `auth-token` httpOnly cookie
- Anonymous use is allowed; projects only persist for authenticated users
- `JWT_SECRET` env var defaults to `"development-secret-key"` if unset

### Environment

Required in `.env`:
```
ANTHROPIC_API_KEY=   # Optional; falls back to MockLanguageModel if absent
JWT_SECRET=          # Optional; defaults to development value
```

### Testing

Tests use Vitest + jsdom + React Testing Library. Test files live alongside source in `__tests__/` subdirectories. The Prisma client output is at `src/generated/prisma` (not the default location).

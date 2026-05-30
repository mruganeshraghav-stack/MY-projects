# Aura — Palm Reader · Source Code Documentation

> An AI-powered palm reading web app. Point your camera at your palm, capture a photo, and receive a personalised reading grounded in traditional palmistry science.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Structure](#2-project-structure)
3. [Tech Stack](#3-tech-stack)
4. [Database Schema](#4-database-schema)
5. [API Contract (OpenAPI)](#5-api-contract-openapi)
6. [Backend — Express Server](#6-backend--express-server)
   - [app.ts — Server Bootstrap](#appts--server-bootstrap)
   - [palm-readings.ts — Route Handlers](#palm-readingsts--route-handlers)
   - [palm-analysis.ts — AI Analysis Engine](#palm-analysiststhe-ai-engine)
7. [Frontend — React App](#7-frontend--react-app)
   - [App.tsx — Root & Router](#apptsx--root--router)
   - [layout.tsx — Shell & Divine Background](#layouttsx--shell--divine-background)
   - [home.tsx — Camera Capture & Results](#hometsx--camera-capture--results)
   - [history.tsx — Reading History](#historytsx--reading-history)
   - [reading.tsx — Reading Detail](#readingtsx--reading-detail)
8. [Styling System](#8-styling-system)
9. [Data Flow — End to End](#9-data-flow--end-to-end)
10. [Key Design Decisions](#10-key-design-decisions)

---

## 1. Architecture Overview

```
Browser
  │
  │  camera → base64 image
  ▼
React Frontend  (Vite · port 22721)
  │
  │  POST /api/palm-readings  { imageBase64 }
  ▼
Express API Server  (port 8080)
  │
  │  vision prompt + image
  ▼
OpenAI GPT-5.1  (via Replit AI Integrations proxy)
  │
  │  structured JSON reading
  ▼
PostgreSQL Database  (Drizzle ORM)
  │
  │  saved reading
  ▼
React Frontend  ← GET /api/palm-readings/:id
```

A **reverse proxy** (managed by Replit) routes all traffic:
- `/` → React Vite app
- `/api` → Express server

---

## 2. Project Structure

```
workspace/
├── artifacts/
│   ├── palm-reader/              # React + Vite frontend
│   │   └── src/
│   │       ├── App.tsx           # Root component & router
│   │       ├── index.css         # Global styles & animations
│   │       ├── components/
│   │       │   └── layout.tsx    # App shell + divine background
│   │       └── pages/
│   │           ├── home.tsx      # Camera capture + results
│   │           ├── history.tsx   # Reading history list
│   │           └── reading.tsx   # Single reading detail
│   │
│   └── api-server/               # Express 5 backend
│       └── src/
│           ├── app.ts            # Express setup & middleware
│           ├── routes/
│           │   ├── index.ts      # Router mount point
│           │   └── palm-readings.ts  # All palm reading routes
│           └── lib/
│               ├── logger.ts     # Pino structured logger
│               └── palm-analysis.ts  # OpenAI vision + parsing
│
└── lib/
    ├── db/src/schema/
    │   └── palm-readings.ts      # Drizzle table definition
    ├── api-spec/
    │   └── openapi.yaml          # Single source of truth for API
    ├── api-client-react/         # Auto-generated React Query hooks
    └── api-zod/                  # Auto-generated Zod validators
```

---

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 18 + Vite 7 |
| Routing | Wouter |
| Data fetching | TanStack React Query (via Orval-generated hooks) |
| Styling | Tailwind CSS v4 + custom CSS animations |
| UI components | shadcn/ui |
| Backend framework | Express 5 |
| Database | PostgreSQL + Drizzle ORM |
| Validation | Zod v4 + drizzle-zod |
| AI | OpenAI GPT-5.1 vision (via Replit AI Integrations) |
| API codegen | Orval (OpenAPI → React Query hooks + Zod schemas) |
| Logging | Pino + pino-http |
| Language | TypeScript 5.9 throughout |

---

## 4. Database Schema

**File:** `lib/db/src/schema/palm-readings.ts`

```typescript
import { pgTable, serial, text, integer, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

// Shape of each palm line stored in the JSONB column
export const palmLinesSchema = z.array(
  z.object({
    name: z.string(),           // e.g. "Life Line"
    description: z.string(),    // What this line represents in palmistry
    interpretation: z.string(), // Personalised reading for this palm
    strength: z.string(),       // "strong" | "moderate" | "faint"
  })
);

// PostgreSQL table definition
export const palmReadingsTable = pgTable("palm_readings", {
  id: serial("id").primaryKey(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  overallReading: text("overall_reading").notNull(),
  healthInsights: text("health_insights").notNull(),
  futureOutlook: text("future_outlook").notNull(),
  dominantTraits: jsonb("dominant_traits").$type<string[]>().notNull().default([]),
  luckyNumber: integer("lucky_number").notNull(),
  luckyColor: text("lucky_color").notNull(),
  lines: jsonb("lines").$type<z.infer<typeof palmLinesSchema>>().notNull().default([]),
  imageBase64: text("image_base64").notNull(), // Full image stored for display
});

// Drizzle-zod insert schema (id + createdAt omitted — auto-generated)
export const insertPalmReadingSchema = createInsertSchema(palmReadingsTable).omit({
  id: true,
  createdAt: true,
});

export type InsertPalmReading = z.infer<typeof insertPalmReadingSchema>;
export type PalmReading = typeof palmReadingsTable.$inferSelect;
```

### Column Summary

| Column | Type | Description |
|---|---|---|
| `id` | `serial` | Auto-incrementing primary key |
| `created_at` | `timestamp` | When the reading was taken |
| `overall_reading` | `text` | 3–4 sentence personalised summary |
| `health_insights` | `text` | Health observations from the palm |
| `future_outlook` | `text` | Future path derived from the lines |
| `dominant_traits` | `jsonb` | Array of personality/destiny trait strings |
| `lucky_number` | `integer` | Numerologically derived lucky number (1–9) |
| `lucky_color` | `text` | Colour derived from dominant mount |
| `lines` | `jsonb` | Array of `PalmLine` objects |
| `image_base64` | `text` | Full base64 image data URI |

---

## 5. API Contract (OpenAPI)

**File:** `lib/api-spec/openapi.yaml`

This is the **single source of truth** for all API shapes. Running `pnpm --filter @workspace/api-spec run codegen` generates:
- `lib/api-client-react/` — React Query hooks for the frontend
- `lib/api-zod/` — Zod validators for the backend

### Endpoints

```
GET  /api/healthz                → HealthStatus
GET  /api/palm-readings          → PalmReading[]
POST /api/palm-readings          → PalmReading        (body: PalmReadingInput)
GET  /api/palm-readings/stats    → PalmReadingStats
GET  /api/palm-readings/:id      → PalmReading
```

### Core Schemas

```yaml
PalmReadingInput:
  imageBase64: string   # base64 data URI from the camera

PalmLine:
  name: string          # e.g. "Heart Line"
  description: string   # Palmistry definition of this line
  interpretation: string # Personalised reading
  strength: string      # "strong" | "moderate" | "faint"

PalmReading:
  id: integer
  createdAt: string     # ISO 8601 date
  overallReading: string
  healthInsights: string
  futureOutlook: string
  dominantTraits: string[]
  luckyNumber: integer
  luckyColor: string
  lines: PalmLine[]
  imageBase64: string

PalmReadingStats:
  totalReadings: integer
  mostCommonTrait: string | null
  averageLuckyNumber: number | null
```

---

## 6. Backend — Express Server

### app.ts — Server Bootstrap

**File:** `artifacts/api-server/src/app.ts`

```typescript
import express, { type Express } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

// Structured request/response logging via pino-http
// Strips query strings from logged URLs to prevent sensitive data leakage
app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return { id: req.id, method: req.method, url: req.url?.split("?")[0] };
      },
      res(res) {
        return { statusCode: res.statusCode };
      },
    },
  }),
);

app.use(cors());

// Body limit raised to 25 MB to accommodate base64-encoded camera images
app.use(express.json({ limit: "25mb" }));
app.use(express.urlencoded({ extended: true, limit: "25mb" }));

app.use("/api", router);

export default app;
```

---

### palm-readings.ts — Route Handlers

**File:** `artifacts/api-server/src/routes/palm-readings.ts`

```typescript
import { Router, type IRouter } from "express";
import { eq, sql } from "drizzle-orm";
import { db, palmReadingsTable } from "@workspace/db";
import {
  CreatePalmReadingBody,
  GetPalmReadingParams,
  GetPalmReadingResponse,
  GetPalmReadingStatsResponse,
  ListPalmReadingsResponse,
} from "@workspace/api-zod";
import { analysePalm } from "../lib/palm-analysis";

const router: IRouter = Router();

// ── GET /palm-readings ─────────────────────────────────────────────────────
// Returns all readings ordered newest first
router.get("/palm-readings", async (req, res): Promise<void> => {
  const readings = await db
    .select()
    .from(palmReadingsTable)
    .orderBy(sql`${palmReadingsTable.createdAt} DESC`);

  const mapped = readings.map((r) => ({
    ...r,
    createdAt: r.createdAt.toISOString(), // DB timestamp → ISO string
  }));

  res.json(ListPalmReadingsResponse.parse(mapped));
});

// ── POST /palm-readings ────────────────────────────────────────────────────
// Accepts a base64 palm image, runs AI analysis, stores and returns the result
router.post("/palm-readings", async (req, res): Promise<void> => {
  const parsed = CreatePalmReadingBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const { imageBase64 } = parsed.data;

  if (!imageBase64 || imageBase64.length < 100) {
    res.status(400).json({ error: "Invalid image data" });
    return;
  }

  // Calls OpenAI vision API — see palm-analysis.ts
  const analysis = await analysePalm(imageBase64);

  const [reading] = await db
    .insert(palmReadingsTable)
    .values({
      overallReading: analysis.overallReading,
      healthInsights: analysis.healthInsights,
      futureOutlook: analysis.futureOutlook,
      dominantTraits: analysis.dominantTraits,
      luckyNumber: analysis.luckyNumber,
      luckyColor: analysis.luckyColor,
      lines: analysis.lines,
      imageBase64,
    })
    .returning();

  res.status(201).json(
    GetPalmReadingResponse.parse({
      ...reading,
      createdAt: reading.createdAt.toISOString(),
    })
  );
});

// ── GET /palm-readings/stats ───────────────────────────────────────────────
// Aggregates total readings, most common trait, and average lucky number
router.get("/palm-readings/stats", async (_req, res): Promise<void> => {
  const [countResult] = await db
    .select({ count: sql<number>`count(*)::int` })
    .from(palmReadingsTable);

  const totalReadings = countResult?.count ?? 0;
  let mostCommonTrait: string | null = null;
  let averageLuckyNumber: number | null = null;

  if (totalReadings > 0) {
    const readings = await db
      .select({
        dominantTraits: palmReadingsTable.dominantTraits,
        luckyNumber: palmReadingsTable.luckyNumber,
      })
      .from(palmReadingsTable);

    const traitCounts: Record<string, number> = {};
    let luckySum = 0;

    for (const r of readings) {
      luckySum += r.luckyNumber;
      for (const trait of (r.dominantTraits as string[])) {
        traitCounts[trait] = (traitCounts[trait] ?? 0) + 1;
      }
    }

    const topTrait = Object.entries(traitCounts).sort((a, b) => b[1] - a[1])[0];
    mostCommonTrait = topTrait ? topTrait[0] : null;
    averageLuckyNumber = Math.round(luckySum / readings.length);
  }

  res.json(
    GetPalmReadingStatsResponse.parse({ totalReadings, mostCommonTrait, averageLuckyNumber })
  );
});

// ── GET /palm-readings/:id ─────────────────────────────────────────────────
router.get("/palm-readings/:id", async (req, res): Promise<void> => {
  const raw = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
  const params = GetPalmReadingParams.safeParse({ id: parseInt(raw, 10) });
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }

  const [reading] = await db
    .select()
    .from(palmReadingsTable)
    .where(eq(palmReadingsTable.id, params.data.id));

  if (!reading) {
    res.status(404).json({ error: "Reading not found" });
    return;
  }

  res.json(
    GetPalmReadingResponse.parse({ ...reading, createdAt: reading.createdAt.toISOString() })
  );
});

export default router;
```

---

### palm-analysis.ts — The AI Engine

**File:** `artifacts/api-server/src/lib/palm-analysis.ts`

This is the heart of the app. It sends the palm image to OpenAI's vision model with a detailed palmistry system prompt and parses the structured JSON response.

```typescript
import { openai } from "@workspace/integrations-openai-ai-server";

export interface PalmLine {
  name: string;
  description: string;
  interpretation: string;
  strength: string;
}

export interface PalmAnalysisResult {
  overallReading: string;
  healthInsights: string;
  futureOutlook: string;
  dominantTraits: string[];
  luckyNumber: number;
  luckyColor: string;
  lines: PalmLine[];
}

// ── System prompt ──────────────────────────────────────────────────────────
// Instructs the model to act as a master palmist with knowledge of:
//   Major lines: Life, Heart, Head, Fate
//   Minor lines: Sun (Apollo), Mercury, Marriage, Intuition
//   Mounts: the raised fleshy areas under each finger
//   Hand shape, skin texture, finger proportions
//
// Rules enforced in the prompt:
//   - Be specific and personal, not generic
//   - Use both Western and Indian/Vedic palmistry traditions
//   - Rate each line as: strong | moderate | faint
//   - Derive lucky number from numerological line features (1–9)
//   - Derive lucky colour from dominant mount's planetary association
//   - Respond ONLY with valid JSON (no prose outside the JSON block)

const SYSTEM_PROMPT = `You are a master palmist with decades of experience in traditional palmistry science...
[See full prompt in artifacts/api-server/src/lib/palm-analysis.ts]`;

// ── analysePalm() ──────────────────────────────────────────────────────────
export async function analysePalm(imageBase64: string): Promise<PalmAnalysisResult> {
  // Strip data URI prefix if present (canvas.toDataURL returns "data:image/jpeg;base64,...")
  const base64Data = imageBase64.includes(",")
    ? imageBase64.split(",")[1]
    : imageBase64;

  // Reconstruct a clean data URI for OpenAI's vision API
  const dataUri = `data:image/jpeg;base64,${base64Data}`;

  const response = await openai.chat.completions.create({
    model: "gpt-5.1",           // Vision-capable model
    max_completion_tokens: 2048,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: [
          {
            type: "image_url",
            image_url: { url: dataUri, detail: "high" }, // "high" = full resolution analysis
          },
          {
            type: "text",
            text: "Please analyse this palm image and provide a detailed reading following the JSON format specified.",
          },
        ],
      },
    ],
  });

  const content = response.choices[0]?.message?.content ?? "";

  // Handle cases where the model wraps JSON in markdown code fences
  const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/) ?? null;
  const jsonString = jsonMatch ? jsonMatch[1].trim() : content.trim();

  const parsed = JSON.parse(jsonString) as PalmAnalysisResult;

  // Validate and normalise — guards against partial/malformed AI output
  return {
    overallReading: String(parsed.overallReading ?? ""),
    healthInsights: String(parsed.healthInsights ?? ""),
    futureOutlook: String(parsed.futureOutlook ?? ""),
    dominantTraits: Array.isArray(parsed.dominantTraits)
      ? parsed.dominantTraits.map(String)
      : [],
    luckyNumber: Number(parsed.luckyNumber ?? 7),
    luckyColor: String(parsed.luckyColor ?? "Gold"),
    lines: Array.isArray(parsed.lines)
      ? parsed.lines.map((l) => ({
          name: String(l.name ?? ""),
          description: String(l.description ?? ""),
          interpretation: String(l.interpretation ?? ""),
          strength: String(l.strength ?? "moderate"),
        }))
      : [],
  };
}
```

---

## 7. Frontend — React App

### App.tsx — Root & Router

**File:** `artifacts/palm-reader/src/App.tsx`

```typescript
import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import Home from "@/pages/home";
import History from "@/pages/history";
import ReadingDetail from "@/pages/reading";
import Layout from "@/components/layout";

const queryClient = new QueryClient();

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={Home} />           {/* Camera + results */}
        <Route path="/history" component={History} />  {/* Reading history */}
        <Route path="/reading/:id" component={ReadingDetail} /> {/* Detail view */}
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        {/* Base URL from Vite env — handles path-based proxy routing */}
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
```

---

### layout.tsx — Shell & Divine Background

**File:** `artifacts/palm-reader/src/components/layout.tsx`

Wraps every page. Renders the animated divine background system and the top navigation bar.

```typescript
import React from "react";
import { Link, useLocation } from "wouter";
import { Hand, History, Sparkles } from "lucide-react";

export default function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();

  return (
    <div className="min-h-[100dvh] w-full flex flex-col items-center relative overflow-hidden">

      {/* ── Divine background (fixed, pointer-events: none) ── */}
      <div className="divine-bg">
        <div className="divine-noise" />      {/* Stardust texture overlay */}
        <div className="divine-core" />       {/* Breathing purple-gold core */}
        <div className="aurora aurora-1" />   {/* Aurora band 1 */}
        <div className="aurora aurora-2" />   {/* Aurora band 2 */}
        <div className="aurora aurora-3" />   {/* Aurora band 3 */}

        {/* 11 golden light rays fanning from top */}
        <div className="ray-container">
          <div className="ray" /> {/* × 11 */}
        </div>

        {/* 5 floating energy orbs */}
        <div className="orb orb-1" /> {/* Purple, top-left */}
        <div className="orb orb-2" /> {/* Gold, bottom-right */}
        <div className="orb orb-3" /> {/* Deep purple, bottom-left */}
        <div className="orb orb-4" /> {/* Gold, middle-right */}
        <div className="orb orb-5" /> {/* Purple, top-right */}

        {/* 8 rising sparks */}
        <div className="spark" /> {/* × 8, gold + violet */}

        {/* Ancient rotating SVG sigil (60s rotation) */}
        <svg className="divine-eye" viewBox="0 0 200 200">
          {/* Concentric dashed circles, 8-pointed star,
              Star of David triangles, all-seeing eye */}
        </svg>
      </div>

      <header className="w-full max-w-2xl mx-auto p-6 flex justify-between items-center z-10 relative">
        <Link href="/" className="flex items-center gap-2 text-primary">
          <Sparkles className="w-5 h-5" />
          <span className="font-serif text-xl tracking-wider">Aura</span>
        </Link>
        <nav className="flex gap-4">
          {/* Camera icon → home */}
          <Link href="/" className={location === '/' ? 'text-primary bg-primary/10 ...' : '...'}>
            <Hand className="w-5 h-5" />
          </Link>
          {/* History icon → /history */}
          <Link href="/history" className={location === '/history' ? '...' : '...'}>
            <History className="w-5 h-5" />
          </Link>
        </nav>
      </header>

      <main className="flex-1 w-full max-w-2xl mx-auto p-4 z-10 relative flex flex-col">
        {children}
      </main>
    </div>
  );
}
```

---

### home.tsx — Camera Capture & Results

**File:** `artifacts/palm-reader/src/pages/home.tsx`

This page manages three sequential UI states: **camera viewfinder → loading → results**.

```typescript
import React, { useRef, useState, useEffect, useCallback } from "react";
import { useCreatePalmReading, getListPalmReadingsQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

export default function Home() {
  const videoRef  = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Stream stored in a ref (not state) to avoid re-render loops.
  // Storing in state would recreate stopCamera on every stream change,
  // retriggering the useEffect and causing the camera to blink.
  const streamRef = useRef<MediaStream | null>(null);

  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [readingResult, setReadingResult] = useState<PalmReading | null>(null);

  const queryClient = useQueryClient();
  const createReading = useCreatePalmReading(); // Orval-generated mutation hook

  // ── Camera management ────────────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    if (streamRef.current) return; // Already running — do nothing
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" } // Prefer rear camera on mobile
      });
      streamRef.current = mediaStream;
      if (videoRef.current) videoRef.current.srcObject = mediaStream;
      setCameraReady(true);
      setCameraError(null);
    } catch {
      setCameraError("Unable to access camera. Please ensure permissions are granted.");
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      setCameraReady(false);
      if (videoRef.current) videoRef.current.srcObject = null;
    }
  }, []);

  // Start camera once on mount; clean up on unmount.
  // Deliberately omits startCamera/stopCamera from deps to prevent loops.
  useEffect(() => {
    startCamera();
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Image capture ────────────────────────────────────────────────────────
  const captureAndAnalyze = () => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    // Draw the current video frame onto a hidden canvas at full resolution
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Encode as JPEG base64 (0.8 quality = good fidelity at reasonable size)
    const imageBase64 = canvas.toDataURL("image/jpeg", 0.8);

    stopCamera(); // Release camera before network request

    createReading.mutate({ data: { imageBase64 } }, {
      onSuccess: (data) => {
        setReadingResult(data);
        // Invalidate the list so /history shows the new reading immediately
        queryClient.invalidateQueries({ queryKey: getListPalmReadingsQueryKey() });
      },
      onError: () => startCamera(), // Re-open camera if the API call fails
    });
  };

  const handleRetake = () => {
    setReadingResult(null);
    createReading.reset();
    startCamera(); // Re-open camera for another shot
  };

  // ── UI State 1: Loading (isPending) ──────────────────────────────────────
  if (createReading.isPending) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center space-y-8">
        {/* Animated palm icon with scan-line effect */}
        <div className="relative w-48 h-48 rounded-full mystic-border ...">
          <div className="scan-line" />
        </div>
        <div className="text-center">
          <h2 className="text-2xl text-primary/90">Divining your path...</h2>
          <p className="text-muted-foreground text-sm tracking-widest uppercase">
            Consulting the ancients
          </p>
        </div>
      </div>
    );
  }

  // ── UI State 2: Results (readingResult) ──────────────────────────────────
  if (readingResult) {
    return (
      <div className="flex-1 flex flex-col space-y-8 pb-12">
        <h1 className="text-4xl text-primary text-center">Your Reading</h1>
        <p className="text-muted-foreground italic">{readingResult.overallReading}</p>

        {/* Destiny & Traits card — dominant traits badges + lucky number/colour */}
        {/* The Lines card — each palm line with name, interpretation, strength */}
        {/* Future Outlook card — full paragraph */}

        <div className="flex justify-center gap-4">
          <Button onClick={handleRetake}>New Reading</Button>
          <Button asChild>
            <Link href={`/reading/${readingResult.id}`}>Save & View Full Details</Link>
          </Button>
        </div>
      </div>
    );
  }

  // ── UI State 3: Camera viewfinder (default) ───────────────────────────────
  return (
    <div className="flex-1 flex flex-col">
      <h1 className="text-3xl text-center mb-2">Reveal Your Path</h1>
      <p className="text-muted-foreground text-center">Align your palm within the frame</p>

      <div className="relative w-full aspect-[3/4] rounded-2xl overflow-hidden mystic-border bg-black">
        {/* Live camera feed */}
        <video ref={videoRef} autoPlay playsInline muted className="absolute inset-0 w-full h-full object-cover" />

        {/* Palm placement guide — dashed oval overlay */}
        <div className="absolute inset-0 palm-guide-overlay">
          <div className="absolute inset-x-8 top-1/4 bottom-1/4 border-2 border-dashed border-primary/30 rounded-[100px] animate-pulse" />
        </div>

        {/* Capture button */}
        <div className="absolute bottom-8 left-0 right-0 flex justify-center z-10">
          <Button
            size="lg"
            className="rounded-full w-20 h-20 ..."
            onClick={captureAndAnalyze}
            disabled={!cameraReady} // Disabled until stream is ready
          >
            <Camera className="w-8 h-8" />
          </Button>
        </div>
      </div>

      {/* Hidden canvas used for frame capture */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
```

---

### history.tsx — Reading History

**File:** `artifacts/palm-reader/src/pages/history.tsx`

```typescript
import { useListPalmReadings, useGetPalmReadingStats } from "@workspace/api-client-react";

export default function History() {
  const { data: readings, isLoading: readingsLoading } = useListPalmReadings();
  const { data: stats } = useGetPalmReadingStats();

  return (
    <div className="flex-1 flex flex-col space-y-8 pb-12">
      <h1 className="text-3xl text-primary text-center">Your Journey</h1>

      {/* Stats banner — total readings, top trait, average lucky number */}
      {stats && stats.totalReadings > 0 && (
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Readings"   value={stats.totalReadings} />
          <StatCard label="Top Trait"  value={stats.mostCommonTrait ?? "-"} />
          <StatCard label="Avg Lucky #" value={stats.averageLuckyNumber ?? "-"} />
        </div>
      )}

      {/* Reading list — skeleton while loading, empty state, or cards */}
      {readingsLoading ? (
        <SkeletonCards />
      ) : readings?.length === 0 ? (
        <EmptyState />
      ) : (
        readings?.map(reading => (
          <Link key={reading.id} href={`/reading/${reading.id}`}>
            <Card>
              {/* Date + lucky colour dot */}
              {/* First 2 lines of overallReading */}
              {/* First 3 dominantTraits as badges, +N overflow */}
            </Card>
          </Link>
        ))
      )}
    </div>
  );
}
```

---

### reading.tsx — Reading Detail

**File:** `artifacts/palm-reader/src/pages/reading.tsx`

```typescript
import { useGetPalmReading, getGetPalmReadingQueryKey } from "@workspace/api-client-react";

export default function ReadingDetail() {
  const params = useParams();
  const id = parseInt(params.id || "0", 10);

  const { data: reading, isLoading, isError } = useGetPalmReading(id, {
    query: {
      enabled: !!id,
      queryKey: getGetPalmReadingQueryKey(id), // Required when passing options
    }
  });

  return (
    <div className="flex-1 flex flex-col space-y-8 pb-16">
      {/* Back link */}
      {/* Palm image thumbnail with luminosity blend + gradient fade */}
      {/* Oracle quote — overallReading */}

      {/* Lucky number + lucky colour grid */}
      {/* Traits Revealed — badge list */}

      {/* Health & Vitality panel */}
      {/* Future Journey panel */}

      {/* The Lines of Destiny — full table:
            each line shows name, strength, description (palmistry definition),
            and personalised interpretation */}
    </div>
  );
}
```

---

## 8. Styling System

**File:** `artifacts/palm-reader/src/index.css`

### Theme Variables (CSS custom properties)

```css
:root {
  --background: 20 15% 7%;       /* Very dark warm brown */
  --foreground: 40 40% 90%;      /* Warm cream text */
  --primary:    40 70% 50%;      /* Antique gold */
  --card:       20 15% 10%;      /* Slightly lighter than background */
  --muted-foreground: 40 20% 65%;

  --app-font-sans:  'Outfit', sans-serif;  /* Body text */
  --app-font-serif: 'Cinzel', serif;       /* Headings — ancient engraved feel */
}
```

### Divine Background Layers (rendered in order)

| Layer | Class | Effect |
|---|---|---|
| 1 | `.divine-bg` | Multi-stop radial gradient base: purple crown, amber corners, dark core |
| 2 | `.divine-noise` | Stardust texture PNG at 6% opacity, `mix-blend-mode: screen` |
| 3 | `.divine-core` | 700px blurred sphere, slow breathe animation (8s, scale 0.85→1.1) |
| 4 | `.aurora-1/2/3` | Three 180px-tall blurred bands sweeping left→right at 14/18/16s |
| 5 | `.ray-container + .ray` | 11 rays fanning from top centre, each pulsing independently |
| 6 | `.orb-1..5` | 5 floating orbs (60–150px), drifting in looping paths (15–26s) |
| 7 | `.spark` | 8 tiny particles rising from bottom, gold and violet |
| 8 | `.divine-eye` | SVG sigil slowly rotating (60s), 12% opacity |

### Component Utility Classes

```css
.mystic-border   /* Gold border + subtle glow + inner purple tint */
.candle-glow     /* scale + opacity pulse, 4s alternate */
.scan-line       /* Gold line sweeping top→bottom, 3s, used in loading state */
.palm-guide-overlay  /* Vignette + inset shadow for camera guide frame */
```

---

## 9. Data Flow — End to End

```
1. USER opens the app
   └─ layout.tsx mounts the divine background animations
   └─ home.tsx useEffect() fires once → startCamera()
   └─ navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
   └─ Stream stored in streamRef (ref, not state — avoids render loops)
   └─ Video element receives the live stream via srcObject

2. USER taps the capture button
   └─ captureAndAnalyze() draws video frame onto hidden <canvas>
   └─ canvas.toDataURL("image/jpeg", 0.8) → base64 data URI string
   └─ stopCamera() releases the device camera
   └─ createReading.mutate({ data: { imageBase64 } })
      └─ POST /api/palm-readings  (body: ~200–400 KB base64 string)

3. EXPRESS receives POST /api/palm-readings
   └─ Zod validates body with CreatePalmReadingBody
   └─ analysePalm(imageBase64) called

4. analysePalm() sends to OpenAI
   └─ Model: gpt-5.1 (vision-capable)
   └─ System prompt: master palmist persona + JSON output format
   └─ User message: high-detail image + analysis instruction
   └─ Response: JSON with overallReading, lines[], healthInsights, etc.
   └─ Strips markdown code fences if present
   └─ Normalises all fields defensively

5. Reading saved to PostgreSQL
   └─ INSERT INTO palm_readings (...) RETURNING *
   └─ 201 response with full PalmReading object

6. FRONTEND receives response
   └─ setReadingResult(data) → home.tsx switches to results UI state
   └─ queryClient.invalidateQueries(getListPalmReadingsQueryKey())
      → history page will refetch on next visit

7. USER navigates to /history
   └─ useListPalmReadings() → GET /api/palm-readings
   └─ useGetPalmReadingStats() → GET /api/palm-readings/stats

8. USER taps a reading card → /reading/:id
   └─ useGetPalmReading(id) → GET /api/palm-readings/:id
   └─ Full detail view with palm image thumbnail
```

---

## 10. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Stream in `useRef` not `useState`** | Storing `MediaStream` in state caused a re-render loop: stream change → new `stopCamera` ref → `useEffect` re-fires → camera restarts → repeat. `useRef` breaks the cycle. |
| **25 MB body limit** | A 3:4 JPEG at camera resolution encoded to base64 can reach 10–15 MB. The default Express 100 KB limit was too restrictive. |
| **Base64 stored in DB** | Simplest approach with no external storage dependency. Trade-off: larger rows, but avoids S3/object-store setup for an MVP. |
| **JSON-only AI response** | The system prompt instructs the model to output pure JSON. A regex strips markdown fences as a safety net. All fields are normalised defensively to guard against partial output. |
| **OpenAPI as single source of truth** | Both Zod validators (used server-side) and React Query hooks (used client-side) are generated from the same `openapi.yaml`. No hand-written types in either layer. |
| **`gpt-5.1` with `detail: "high"`** | `high` detail mode sends the image at full resolution in tiles, enabling the model to see fine palm line features rather than a downsampled thumbnail. |
| **Cinzel + Outfit fonts** | Cinzel is a serif engraved in the style of Roman inscriptions — ancient authority without being unreadable. Outfit is a clean geometric sans that pairs well without competing. |
| **All CSS animations, no JS** | The divine background uses only CSS keyframes. Zero JavaScript overhead, GPU-composited, works even if React hydration is slow. |
